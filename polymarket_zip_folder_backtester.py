#!/usr/bin/env python3
"""
Polymarket BTC 5-minute raw order-book backtester
=================================================

Designed for the seller's daily ZIP archives containing files named like:
    polymarket-btc-updown-5m-1786756200-2026-08-15.txt.zst

You can point this script at ONE folder containing all nine daily .zip files.
It reads .zst members directly from the ZIPs; you do NOT need to extract them.
It also still accepts already-extracted .zst files/folders.

The timestamp inside `btc-updown-5m-<timestamp>` is treated as the MARKET
START. This is based on the actual raw files: the book starts moving through
the five-minute BTC round at that timestamp and converges toward 0/1 by
<timestamp> + 300 seconds.

What this script does
---------------------
1. Recursively scans one root folder for daily .zip archives and/or .zst files.
2. Reads .zst members directly from ZIP archives without extracting them first.
3. Streams zstd content; it never expands a whole daily archive into RAM.
4. Reconstructs the normalized UP order book from full snapshots + deltas.
5. Derives DOWN prices/depth by binary complement:
       DOWN ask = 1 - UP best bid
       DOWN depth comes from UP bid depth at price (1 - bid_price)
6. Checks sequence continuity and five-minute coverage.
7. Runs the 75/74/76 delayed re-breakout strategy in TWO ways:
       RAW     = every recorded order-book event can trigger the rule.
       SAMPLED = state sampled once per second, matching our earlier style.
8. Saves the exact book depth at entry and simulates a real marketable order.
9. Includes current crypto taker-fee math by default:
       fee = shares * fee_rate * p * (1-p)
   Default fee_rate = 0.07. Change it at the top or with --fee-rate.
10. Infers the final UP/DOWN outcome conservatively from the last seconds of
   the recorded market. Ambiguous rounds remain UNKNOWN and are not scored.
11. Deduplicates overlapping copies of the same market, keeping the best file.
12. Runs a chronological bankroll test:
       starting balance = $300
       stake = min(10% of current balance, $300)
13. Writes CSV + JSON reports.

IMPORTANT
---------
- This is a research backtester, not a trading bot.
- Inferred outcomes are marked as such. If you later obtain an official
  settlement file, add those labels before treating the results as final.
- The dynamic bankroll simulation assumes settlement proceeds are available
  before the next qualifying trade.

Fast install:
    python3 -m pip install orjson zstandard

Run after editing DATA_ROOTS below:
    python3 polymarket_zip_folder_backtester.py

Or point to the one folder containing all nine ZIP files:
    python3 polymarket_zip_folder_backtester.py \
      --data-root /path/to/folder-with-nine-zips --output ./btc_report

Quick scan check before a long run:
    python3 polymarket_zip_folder_backtester.py \
      --data-root /path/to/folder-with-nine-zips --list-only
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import re
import shutil
import statistics
import subprocess
import sys
import time
import zipfile
import atexit
import threading
from collections import deque
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional

# ---------------------------------------------------------------------------
# EDIT ONLY THIS BLOCK. Point it to the ONE folder that contains your nine
# daily ZIP files. CLI --data-root overrides this list.
#
# Windows example:
# DATA_ROOTS = [r"D:\Polymarket\BTC5m"]
#
# Linux/VPS example:
# DATA_ROOTS = [r"/home/user/polymarket/btc5m_archives"]
# ---------------------------------------------------------------------------
DATA_ROOTS = [
    # r"/path/to/folder/that/contains/the/nine/zip/files",
]

OUTPUT_DIR = r"./btc_757476_zip_report"

# Strategy discovered in the earlier historical test.
LEADER_THRESHOLD = 0.75
PULLBACK_THRESHOLD = 0.74
CONFIRM_THRESHOLD = 0.76
MIN_SECONDS_AFTER_PULLBACK = 40.0
MIN_MARKET_AGE_SECONDS = 180.0
SAMPLE_INTERVAL_MS = 1000

# Execution / bankroll.
FLAT_STAKE = 300.0
STARTING_BALANCE = 300.0
BANKROLL_RISK_PCT = 0.10
BANKROLL_STAKE_CAP = 300.0
MIN_FILL_RATIO = 0.99
CRYPTO_TAKER_FEE_RATE = 0.07  # Set 0.0 for fee-free comparison.

# Data-quality / outcome inference.
ROUND_SECONDS = 300
COMPLETE_FIRST_EVENT_MAX_SEC = 5.0
COMPLETE_LAST_EVENT_MIN_SEC = 295.0
OUTCOME_LOOKBACK_SECONDS = 15
OUTCOME_HIGH = 0.90
OUTCOME_LOW = 0.10

# Parallelism. 0 = choose automatically.
WORKERS = 0

FILE_RE = re.compile(r"btc-updown-5m-(\d+)")

try:
    import orjson  # type: ignore

    def json_loads(raw: bytes | str) -> Any:
        return orjson.loads(raw)

except Exception:
    def json_loads(raw: bytes | str) -> Any:
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw)

try:
    import zstandard as zstd  # type: ignore
except Exception:
    zstd = None


# ---------------------------------------------------------------------------
# Low-level I/O
# ---------------------------------------------------------------------------

_ZIP_CACHE: dict[str, zipfile.ZipFile] = {}


def _close_zip_cache() -> None:
    for zf in list(_ZIP_CACHE.values()):
        try:
            zf.close()
        except Exception:
            pass
    _ZIP_CACHE.clear()


atexit.register(_close_zip_cache)


def make_zip_source(zip_path: str, member: str) -> str:
    return f"zip://{zip_path}::{member}"


def split_source(source: str) -> tuple[str, str, str | None]:
    """Return (kind, outer_path, member). kind is 'zip' or 'file'."""
    if source.startswith("zip://"):
        body = source[6:]
        outer, member = body.split("::", 1)
        return "zip", outer, member
    return "file", source, None


def source_display_name(source: str) -> str:
    kind, outer, member = split_source(source)
    if kind == "zip":
        return Path(member or "").name
    return Path(outer).name


def source_container_name(source: str) -> str:
    kind, outer, _ = split_source(source)
    return Path(outer).name if kind == "zip" else ""


def _iter_zstd_stream(fh: Any) -> Iterator[bytes]:
    """Decompress a binary zstd stream from any file-like object."""
    if zstd is not None:
        dctx = zstd.ZstdDecompressor()
        with dctx.stream_reader(fh) as reader:
            buf = bytearray()
            while True:
                chunk = reader.read(1024 * 1024)
                if not chunk:
                    break
                buf.extend(chunk)
                start = 0
                while True:
                    pos = buf.find(b"\n", start)
                    if pos < 0:
                        if start:
                            del buf[:start]
                        break
                    yield bytes(buf[start:pos])
                    start = pos + 1
            if buf:
                yield bytes(buf)
        return

    # Fallback for machines with the `zstd` executable but no Python package.
    # A background thread feeds the compressed stream while this thread drains
    # stdout, preventing pipe deadlock on large members.
    zstd_bin = shutil.which("zstd")
    if not zstd_bin:
        raise RuntimeError(
            "Install either Python zstandard (`python -m pip install zstandard`) "
            "or the zstd command-line program."
        )

    proc = subprocess.Popen(
        [zstd_bin, "-dc"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1024 * 1024,
    )
    assert proc.stdin is not None and proc.stdout is not None
    pump_error: list[BaseException] = []

    def pump() -> None:
        try:
            while True:
                chunk = fh.read(1024 * 1024)
                if not chunk:
                    break
                proc.stdin.write(chunk)
            proc.stdin.close()
        except BaseException as exc:
            pump_error.append(exc)
            try:
                proc.stdin.close()
            except Exception:
                pass

    th = threading.Thread(target=pump, daemon=True)
    th.start()
    try:
        for line in proc.stdout:
            yield line.rstrip(b"\n")
    finally:
        try:
            proc.stdout.close()
        except Exception:
            pass
        th.join()
        stderr = proc.stderr.read().decode("utf-8", "replace") if proc.stderr else ""
        rc = proc.wait()
        if pump_error:
            raise RuntimeError(f"Failed feeding zstd stream: {pump_error[0]!r}")
        if rc != 0:
            raise RuntimeError(f"zstd stream decompression failed: {stderr[:500]}")


def iter_zst_lines(source: str) -> Iterator[bytes]:
    """Yield decompressed lines from local .zst or a .zst member inside ZIP."""
    kind, outer, member = split_source(source)

    if kind == "zip":
        zf = _ZIP_CACHE.get(outer)
        if zf is None:
            zf = zipfile.ZipFile(outer, "r", allowZip64=True)
            _ZIP_CACHE[outer] = zf
        assert member is not None
        with zf.open(member, "r") as member_fh:
            yield from _iter_zstd_stream(member_fh)
        return

    path = outer
    if zstd is not None:
        with open(path, "rb") as fh:
            yield from _iter_zstd_stream(fh)
        return

    zstd_bin = shutil.which("zstd")
    if not zstd_bin:
        raise RuntimeError(
            "Need either `pip install zstandard` or the `zstd` command installed."
        )

    proc = subprocess.Popen(
        [zstd_bin, "-dc", "--", path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1024 * 1024,
    )
    assert proc.stdout is not None
    try:
        for line in proc.stdout:
            yield line.rstrip(b"\n")
    finally:
        proc.stdout.close()
        stderr = proc.stderr.read().decode("utf-8", "replace") if proc.stderr else ""
        rc = proc.wait()
        if rc != 0:
            raise RuntimeError(f"zstd failed for {path}: {stderr[:500]}")


def market_start_from_filename(source: str) -> int:
    m = FILE_RE.search(source_display_name(source))
    if not m:
        raise ValueError("No btc-updown-5m-<timestamp> in filename")
    return int(m.group(1))


def _scan_zip(zip_path: Path) -> list[str]:
    found: list[str] = []
    try:
        with zipfile.ZipFile(zip_path, "r", allowZip64=True) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                name = info.filename
                base = Path(name).name
                if FILE_RE.search(base) and base.lower().endswith(".zst"):
                    found.append(make_zip_source(str(zip_path.resolve()), name))
    except zipfile.BadZipFile as exc:
        print(f"WARNING: bad ZIP skipped: {zip_path}: {exc}", file=sys.stderr)
    except Exception as exc:
        print(f"WARNING: could not scan ZIP {zip_path}: {exc}", file=sys.stderr)
    return found


def scan_sources(data_roots: list[str]) -> tuple[list[str], dict[str, int]]:
    """
    Find seller BTC 5m .zst files either directly on disk or inside ZIP files.
    Returns (sources, scan_stats).
    """
    found: list[str] = []
    archives_seen = 0
    local_zst_seen = 0

    for raw in data_roots:
        p = Path(raw).expanduser().resolve()
        if not p.exists():
            print(f"WARNING: path does not exist: {p}", file=sys.stderr)
            continue

        if p.is_file():
            low = p.name.lower()
            if low.endswith(".zip"):
                archives_seen += 1
                found.extend(_scan_zip(p))
            elif low.endswith(".zst") and FILE_RE.search(p.name):
                local_zst_seen += 1
                found.append(str(p))
            continue

        # One folder can contain all nine daily ZIPs. Recursion also allows
        # subfolders if you organize them by date.
        for z in p.rglob("*.zip"):
            if z.is_file():
                archives_seen += 1
                found.extend(_scan_zip(z))

        # Also accept extracted seller files in the same tree.
        for f in p.rglob("*.zst"):
            if f.is_file() and FILE_RE.search(f.name):
                local_zst_seen += 1
                found.append(str(f.resolve()))

    unique = sorted(set(found))
    stats = {
        "archives_seen": archives_seen,
        "local_zst_seen": local_zst_seen,
        "candidate_sources": len(unique),
    }
    return unique, stats


# ---------------------------------------------------------------------------
# Order book + execution
# ---------------------------------------------------------------------------

class Book:
    __slots__ = ("bids", "asks")

    def __init__(self) -> None:
        self.bids: dict[float, float] = {}
        self.asks: dict[float, float] = {}

    def clear(self) -> None:
        self.bids.clear()
        self.asks.clear()

    def apply(self, changes: Any) -> None:
        if not isinstance(changes, list):
            return
        for ch in changes:
            try:
                side = int(ch[0])
                price = float(ch[1])
                size = float(ch[2])
            except Exception:
                continue
            target = self.bids if side == 0 else self.asks
            if size <= 0:
                target.pop(price, None)
            else:
                target[price] = size

    def up_best_bid(self) -> Optional[float]:
        return max(self.bids) if self.bids else None

    def up_best_ask(self) -> Optional[float]:
        return min(self.asks) if self.asks else None

    def asks_for_side(self, side: str, max_total_cash: float, fee_rate: float) -> list[list[float]]:
        """
        Return [price, shares_available] levels sufficient to spend roughly
        max_total_cash including fees.
        """
        out: list[list[float]] = []
        cumulative = 0.0
        if side == "UP":
            levels = ((p, q) for p, q in sorted(self.asks.items()))
        else:
            # Buying DOWN corresponds to taking normalized UP bids.
            levels = ((1.0 - p, q) for p, q in sorted(self.bids.items(), reverse=True))

        for p, q in levels:
            if p <= 0 or p >= 1.0000001 or q <= 0:
                continue
            fee_per_share = fee_rate * p * (1.0 - p)
            total_per_share = p + fee_per_share
            out.append([round(p, 8), float(q)])
            cumulative += total_per_share * q
            if cumulative >= max_total_cash * 1.02:
                break
        return out


def quote_asks(book: Book) -> tuple[Optional[float], Optional[float]]:
    """Return (UP ask, DOWN ask) from the normalized binary book."""
    ua = book.up_best_ask()
    ub = book.up_best_bid()
    da = None if ub is None else 1.0 - ub
    return ua, da


def market_fill(
    levels: list[list[float]],
    cash_budget: float,
    fee_rate: float,
) -> dict[str, float]:
    """
    Simulate a taker market buy through depth while keeping TOTAL cash debit
    (principal + taker fee) within cash_budget.
    """
    remaining = max(0.0, float(cash_budget))
    principal = 0.0
    fees = 0.0
    shares = 0.0
    worst_price = math.nan
    levels_used = 0

    for p_raw, q_raw in levels:
        p = float(p_raw)
        q = float(q_raw)
        if remaining <= 1e-12:
            break
        if p <= 0 or p > 1 or q <= 0:
            continue

        fee_per_share = fee_rate * p * (1.0 - p)
        debit_per_share = p + fee_per_share
        take = min(q, remaining / debit_per_share)
        if take <= 0:
            continue

        cost = take * p
        fee = take * fee_per_share
        debit = cost + fee

        shares += take
        principal += cost
        fees += fee
        remaining -= debit
        worst_price = p
        levels_used += 1

    total_debit = principal + fees
    avg_price = principal / shares if shares > 0 else math.nan
    effective_cost_per_share = total_debit / shares if shares > 0 else math.nan
    return {
        "cash_budget": cash_budget,
        "total_debit": total_debit,
        "principal": principal,
        "fee": fees,
        "shares": shares,
        "avg_price": avg_price,
        "effective_cost_per_share": effective_cost_per_share,
        "worst_price": worst_price,
        "levels_used": float(levels_used),
        "fill_ratio": (total_debit / cash_budget) if cash_budget > 0 else 0.0,
    }


# ---------------------------------------------------------------------------
# Strategy state machine
# ---------------------------------------------------------------------------

@dataclass
class SignalResult:
    status: str = "no_leader"
    leader: str = ""
    leader_time: Optional[float] = None
    pullback_time: Optional[float] = None
    confirm_time: Optional[float] = None
    entry_side: str = ""
    up_ask_at_entry: Optional[float] = None
    down_ask_at_entry: Optional[float] = None
    entry_levels: Optional[list[list[float]]] = None


class Strategy757476:
    def __init__(
        self,
        leader_threshold: float,
        pullback_threshold: float,
        confirm_threshold: float,
        min_after_pullback: float,
        min_market_age: float,
        max_depth_cash: float,
        fee_rate: float,
    ) -> None:
        self.lt = leader_threshold
        self.pt = pullback_threshold
        self.ct = confirm_threshold
        self.min_after = min_after_pullback
        self.min_age = min_market_age
        self.max_depth_cash = max_depth_cash
        self.fee_rate = fee_rate
        self.r = SignalResult()
        self.phase = "leader"

    def observe(self, age: float, book: Book) -> None:
        if age < 0 or age > ROUND_SECONDS or self.phase == "done":
            return

        ua, da = quote_asks(book)
        if ua is None or da is None:
            return

        if self.phase == "leader":
            up_hit = ua >= self.lt
            down_hit = da >= self.lt
            if up_hit and down_hit:
                self.r.status = "ambiguous_initial"
                self.phase = "done"
                return
            if up_hit or down_hit:
                self.r.leader = "UP" if up_hit else "DOWN"
                self.r.leader_time = age
                self.r.status = "leader_only"
                self.phase = "pullback"
            return

        if self.phase == "pullback":
            leader_ask = ua if self.r.leader == "UP" else da
            if leader_ask <= self.pt:
                self.r.pullback_time = age
                self.r.status = "pulled_back"
                self.phase = "confirm"
            return

        if self.phase == "confirm":
            up_hit = ua >= self.ct
            down_hit = da >= self.ct
            if not up_hit and not down_hit:
                return
            if up_hit and down_hit:
                self.r.status = "ambiguous_confirm"
                self.phase = "done"
                return

            first_side = "UP" if up_hit else "DOWN"
            self.r.confirm_time = age

            if first_side != self.r.leader:
                self.r.status = "opposite_confirmed_first"
                self.phase = "done"
                return

            since_pullback = age - float(self.r.pullback_time or 0.0)
            if since_pullback < self.min_after:
                self.r.status = "leader_confirm_too_soon_after_pullback"
                self.phase = "done"
                return
            if age < self.min_age:
                self.r.status = "leader_confirm_too_early_in_market"
                self.phase = "done"
                return

            self.r.status = "trade"
            self.r.entry_side = first_side
            self.r.up_ask_at_entry = ua
            self.r.down_ask_at_entry = da
            self.r.entry_levels = book.asks_for_side(
                first_side, self.max_depth_cash, self.fee_rate
            )
            self.phase = "done"

    def finish(self) -> SignalResult:
        if self.phase == "pullback":
            self.r.status = "no_pullback"
        elif self.phase == "confirm":
            self.r.status = "no_confirm_after_pullback"
        return self.r


# ---------------------------------------------------------------------------
# One-file analysis
# ---------------------------------------------------------------------------

@dataclass
class Config:
    leader_threshold: float
    pullback_threshold: float
    confirm_threshold: float
    min_after_pullback: float
    min_market_age: float
    sample_interval_ms: int
    flat_stake: float
    bankroll_cap: float
    fee_rate: float
    min_fill_ratio: float


def _median_or_none(xs: list[float]) -> Optional[float]:
    return statistics.median(xs) if xs else None


def infer_outcome(sample_tail: deque[tuple[float, Optional[float]]], trade_tail: deque[tuple[float, float]]) -> tuple[str, str, Optional[float], Optional[float]]:
    """Conservative settlement inference from final recorded seconds."""
    quote_vals = [v for _, v in sample_tail if v is not None and 0 <= v <= 1]
    trade_vals = [p for _, p in trade_tail if 0 <= p <= 1]
    qm = _median_or_none(quote_vals[-8:])
    tm = _median_or_none(trade_vals[-20:])

    votes: list[str] = []
    for v in (qm, tm):
        if v is None:
            continue
        if v >= OUTCOME_HIGH:
            votes.append("UP")
        elif v <= OUTCOME_LOW:
            votes.append("DOWN")

    if not votes:
        return "UNKNOWN", "not_extreme", qm, tm
    if all(v == votes[0] for v in votes):
        source = "quotes+trades" if len(votes) >= 2 else ("quotes" if qm is not None and ((qm >= OUTCOME_HIGH) or (qm <= OUTCOME_LOW)) else "trades")
        return votes[0], source, qm, tm
    return "UNKNOWN", "conflicting_final_indicators", qm, tm


def analyze_file(path: str, cfg_dict: dict[str, Any]) -> dict[str, Any]:
    cfg = Config(**cfg_dict)
    t0 = time.time()
    try:
        start_s = market_start_from_filename(path)
    except Exception as exc:
        return {"path": path, "fatal_error": repr(exc)}

    start_ns = start_s * 1_000_000_000
    end_ns = (start_s + ROUND_SECONDS) * 1_000_000_000
    sample_step_ns = int(cfg.sample_interval_ms * 1_000_000)
    next_sample_ns = start_ns

    max_depth_cash = max(cfg.flat_stake, cfg.bankroll_cap)
    raw_sig = Strategy757476(
        cfg.leader_threshold,
        cfg.pullback_threshold,
        cfg.confirm_threshold,
        cfg.min_after_pullback,
        cfg.min_market_age,
        max_depth_cash,
        cfg.fee_rate,
    )
    sampled_sig = Strategy757476(
        cfg.leader_threshold,
        cfg.pullback_threshold,
        cfg.confirm_threshold,
        cfg.min_after_pullback,
        cfg.min_market_age,
        max_depth_cash,
        cfg.fee_rate,
    )

    book = Book()
    metadata: dict[str, Any] = {}
    line_count = 0
    book_messages_total = 0
    in_window_book_messages = 0
    trade_count_window = 0
    snapshots = 0
    deltas = 0
    sequence_breaks = 0
    last_sequence: Optional[str] = None
    first_book_age: Optional[float] = None
    last_book_age: Optional[float] = None
    raw_started = False

    sample_tail: deque[tuple[float, Optional[float]]] = deque(maxlen=64)
    trade_tail: deque[tuple[float, float]] = deque(maxlen=256)

    # Track sample count for data diagnostics.
    sampled_points = 0

    def probability_proxy() -> Optional[float]:
        bb = book.up_best_bid()
        aa = book.up_best_ask()
        if bb is not None and aa is not None:
            return (bb + aa) / 2.0
        if aa is not None:
            return aa
        if bb is not None:
            return bb
        return None

    def emit_sample(sample_ns: int) -> None:
        nonlocal sampled_points
        age = (sample_ns - start_ns) / 1e9
        sampled_sig.observe(age, book)
        sampled_points += 1
        if age >= ROUND_SECONDS - OUTCOME_LOOKBACK_SECONDS:
            sample_tail.append((age, probability_proxy()))

    try:
        for raw_line in iter_zst_lines(path):
            if not raw_line:
                continue
            line_count += 1
            try:
                obj = json_loads(raw_line)
            except Exception:
                continue

            if isinstance(obj, dict):
                # First line in these seller files is instrument metadata.
                if not metadata:
                    metadata = obj
                continue
            if not isinstance(obj, list) or not obj:
                continue

            typ = obj[0]

            # 0 = full book snapshot, 1 = incremental absolute-level update.
            if typ in (0, 1) and len(obj) >= 7:
                book_messages_total += 1
                if typ == 0:
                    snapshots += 1
                else:
                    deltas += 1

                try:
                    prev_seq = str(obj[2])
                    new_seq = str(obj[3])
                    source_ns = int(obj[5])
                    changes = obj[6]
                except Exception:
                    continue

                # Evaluate fixed-grid samples strictly BEFORE the new source
                # timestamp using the last known book. If source_ns equals a
                # sample point, the sample is delayed until all same-timestamp
                # changes have been applied.
                if source_ns > start_ns:
                    while next_sample_ns < min(source_ns, end_ns + 1):
                        emit_sample(next_sample_ns)
                        next_sample_ns += sample_step_ns

                # Sequence continuity. Full snapshots are allowed to reset it.
                if typ == 1 and last_sequence is not None and prev_seq != last_sequence:
                    sequence_breaks += 1
                if typ == 0:
                    book.clear()
                book.apply(changes)
                last_sequence = new_seq

                if source_ns < start_ns:
                    continue
                if source_ns > end_ns:
                    # We already emitted samples up to end before applying this
                    # post-market event. No strategy state should see it.
                    continue

                age = (source_ns - start_ns) / 1e9
                in_window_book_messages += 1
                if first_book_age is None:
                    first_book_age = age
                last_book_age = age

                if not raw_started:
                    # If the first in-window update arrived after t=0, also let
                    # the strategy see the reconstructed state that existed at
                    # the opening instant. This is normally only milliseconds.
                    raw_started = True
                raw_sig.observe(age, book)

            # 2 = trades. Prices are on the same normalized UP-probability axis.
            elif typ == 2 and len(obj) >= 7:
                try:
                    source_ns = int(obj[5])
                    trades = obj[6]
                except Exception:
                    continue
                if start_ns <= source_ns <= end_ns and isinstance(trades, list):
                    age = (source_ns - start_ns) / 1e9
                    for tr in trades:
                        try:
                            p = float(tr[1])
                        except Exception:
                            continue
                        trade_count_window += 1
                        if age >= ROUND_SECONDS - OUTCOME_LOOKBACK_SECONDS:
                            trade_tail.append((age, p))

        # Complete remaining sampled grid through t=300 using last known book.
        while next_sample_ns <= end_ns:
            emit_sample(next_sample_ns)
            next_sample_ns += sample_step_ns

    except Exception as exc:
        return {
            "path": path,
            "market_start": start_s,
            "fatal_error": repr(exc),
            "line_count_before_error": line_count,
        }

    raw_r = raw_sig.finish()
    sampled_r = sampled_sig.finish()

    outcome, outcome_source, final_quote_proxy, final_trade_proxy = infer_outcome(sample_tail, trade_tail)

    complete = (
        first_book_age is not None
        and last_book_age is not None
        and first_book_age <= COMPLETE_FIRST_EVENT_MAX_SEC
        and last_book_age >= COMPLETE_LAST_EVENT_MIN_SEC
        and in_window_book_messages > 0
    )

    def result_dict(prefix: str, r: SignalResult) -> dict[str, Any]:
        d: dict[str, Any] = {
            f"{prefix}_status": r.status,
            f"{prefix}_leader": r.leader,
            f"{prefix}_leader_time": r.leader_time,
            f"{prefix}_pullback_time": r.pullback_time,
            f"{prefix}_confirm_time": r.confirm_time,
            f"{prefix}_entry_side": r.entry_side,
            f"{prefix}_up_ask_at_entry": r.up_ask_at_entry,
            f"{prefix}_down_ask_at_entry": r.down_ask_at_entry,
            f"{prefix}_entry_levels": r.entry_levels,
        }
        if r.status == "trade" and r.entry_levels:
            fill = market_fill(r.entry_levels, cfg.flat_stake, cfg.fee_rate)
            for k, v in fill.items():
                d[f"{prefix}_flat_{k}"] = v
            if outcome in ("UP", "DOWN") and fill["fill_ratio"] >= cfg.min_fill_ratio:
                win = r.entry_side == outcome
                pnl = (fill["shares"] - fill["total_debit"]) if win else -fill["total_debit"]
                d[f"{prefix}_flat_win"] = win
                d[f"{prefix}_flat_pnl"] = pnl
            else:
                d[f"{prefix}_flat_win"] = None
                d[f"{prefix}_flat_pnl"] = None
        return d

    out: dict[str, Any] = {
        "path": path,
        "filename": source_display_name(path),
        "archive": source_container_name(path),
        "market_start": start_s,
        "market_end": start_s + ROUND_SECONDS,
        "complete": complete,
        "line_count": line_count,
        "book_messages_total": book_messages_total,
        "in_window_book_messages": in_window_book_messages,
        "trade_count_window": trade_count_window,
        "snapshots": snapshots,
        "deltas": deltas,
        "sequence_breaks": sequence_breaks,
        "first_book_age": first_book_age,
        "last_book_age": last_book_age,
        "sampled_points": sampled_points,
        "outcome": outcome,
        "outcome_source": outcome_source,
        "final_quote_proxy": final_quote_proxy,
        "final_trade_proxy": final_trade_proxy,
        "elapsed_seconds": time.time() - t0,
        "fatal_error": "",
    }
    out.update(result_dict("raw", raw_r))
    out.update(result_dict("sampled", sampled_r))
    return out


# ---------------------------------------------------------------------------
# Aggregation, de-duplication, reports
# ---------------------------------------------------------------------------

def quality_key(r: dict[str, Any]) -> tuple:
    """Higher tuple = better copy when the same market exists in >1 archive."""
    return (
        1 if r.get("complete") else 0,
        -int(r.get("sequence_breaks") or 0),
        float(r.get("last_book_age") or -999),
        int(r.get("in_window_book_messages") or 0),
        int(r.get("trade_count_window") or 0),
    )


def dedupe_results(results: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    groups: dict[int, list[dict[str, Any]]] = {}
    errors: list[dict[str, Any]] = []
    for r in results:
        if r.get("fatal_error"):
            errors.append(r)
            continue
        groups.setdefault(int(r["market_start"]), []).append(r)

    chosen: list[dict[str, Any]] = []
    dupes: list[dict[str, Any]] = []
    for _, rows in groups.items():
        rows = sorted(rows, key=quality_key, reverse=True)
        chosen.append(rows[0])
        for extra in rows[1:]:
            x = dict(extra)
            x["duplicate_of"] = rows[0].get("path")
            dupes.append(x)
    chosen.sort(key=lambda x: int(x["market_start"]))
    return chosen, dupes + errors


def bankroll_run(
    markets: list[dict[str, Any]],
    mode: str,
    starting_balance: float,
    risk_pct: float,
    cap: float,
    fee_rate: float,
    min_fill_ratio: float,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    balance = starting_balance
    peak = balance
    max_drawdown = 0.0
    rows: list[dict[str, Any]] = []
    wins = losses = 0
    skipped_unknown = skipped_fill = 0
    bust_trade = None

    for m in markets:
        if not m.get("complete"):
            continue
        if m.get(f"{mode}_status") != "trade":
            continue
        outcome = m.get("outcome")
        if outcome not in ("UP", "DOWN"):
            skipped_unknown += 1
            continue
        levels = m.get(f"{mode}_entry_levels") or []
        side = m.get(f"{mode}_entry_side")

        if balance <= 1e-9:
            break
        target = min(balance * risk_pct, cap, balance)
        fill = market_fill(levels, target, fee_rate)
        if fill["fill_ratio"] < min_fill_ratio:
            skipped_fill += 1
            continue

        before = balance
        win = side == outcome
        pnl = (fill["shares"] - fill["total_debit"]) if win else -fill["total_debit"]
        balance += pnl
        if balance < 0 and balance > -1e-7:
            balance = 0.0
        if win:
            wins += 1
        else:
            losses += 1

        peak = max(peak, balance)
        dd = (peak - balance) / peak if peak > 0 else 0.0
        max_drawdown = max(max_drawdown, dd)

        row = {
            "trade_no": len(rows) + 1,
            "market_start": m["market_start"],
            "filename": m["filename"],
            "entry_side": side,
            "outcome": outcome,
            "win": win,
            "entry_time": m.get(f"{mode}_confirm_time"),
            "balance_before": before,
            "target_stake": target,
            **fill,
            "pnl": pnl,
            "balance_after": balance,
            "peak_balance": peak,
            "drawdown_pct": dd * 100.0,
        }
        rows.append(row)

        if balance <= 1e-9:
            bust_trade = len(rows)
            break

    summary = {
        "mode": mode,
        "starting_balance": starting_balance,
        "ending_balance": balance,
        "net_pnl": balance - starting_balance,
        "account_multiple": (balance / starting_balance) if starting_balance > 0 else None,
        "trades": len(rows),
        "wins": wins,
        "losses": losses,
        "win_rate": wins / len(rows) if rows else None,
        "peak_balance": peak,
        "max_drawdown_pct": max_drawdown * 100.0,
        "bust_trade": bust_trade,
        "skipped_unknown_outcome": skipped_unknown,
        "skipped_insufficient_depth": skipped_fill,
        "risk_pct": risk_pct,
        "stake_cap": cap,
        "fee_rate": fee_rate,
    }
    return rows, summary


def flatten_for_csv(row: dict[str, Any]) -> dict[str, Any]:
    out = dict(row)
    for k, v in list(out.items()):
        if isinstance(v, (list, dict)):
            out[k] = json.dumps(v, separators=(",", ":"))
    return out


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    flat = [flatten_for_csv(r) for r in rows]
    fields: list[str] = []
    seen = set()
    for r in flat:
        for k in r:
            if k not in seen:
                seen.add(k)
                fields.append(k)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(flat)


def mode_summary(markets: list[dict[str, Any]], mode: str, cfg: Config) -> dict[str, Any]:
    complete = [m for m in markets if m.get("complete")]
    trades = [m for m in complete if m.get(f"{mode}_status") == "trade"]
    resolved = [m for m in trades if m.get("outcome") in ("UP", "DOWN") and m.get(f"{mode}_flat_pnl") is not None]
    wins = [m for m in resolved if m.get(f"{mode}_flat_win") is True]
    pnl = sum(float(m[f"{mode}_flat_pnl"]) for m in resolved)
    deployed = sum(float(m.get(f"{mode}_flat_total_debit") or 0) for m in resolved)
    status_counts: dict[str, int] = {}
    for m in complete:
        s = str(m.get(f"{mode}_status"))
        status_counts[s] = status_counts.get(s, 0) + 1

    return {
        "mode": mode,
        "complete_markets": len(complete),
        "signals": len(trades),
        "resolved_signals": len(resolved),
        "wins": len(wins),
        "losses": len(resolved) - len(wins),
        "win_rate": (len(wins) / len(resolved)) if resolved else None,
        "flat_net_pnl": pnl,
        "flat_total_debit": deployed,
        "flat_roi_on_debit": (pnl / deployed) if deployed else None,
        "status_counts": status_counts,
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Backtest raw Polymarket BTC 5m depth files directly from daily ZIP archives")
    p.add_argument("--data-root", action="append", default=[], help="Folder containing daily ZIP archives (or extracted .zst files). Repeat only if needed.")
    p.add_argument("--list-only", action="store_true", help="Scan inputs and print archive/member counts without backtesting.")
    p.add_argument("--max-files", type=int, default=0, help="Optional test limit after scanning. 0 = all files.")
    p.add_argument("--output", default=OUTPUT_DIR)
    p.add_argument("--workers", type=int, default=WORKERS)
    p.add_argument("--leader", type=float, default=LEADER_THRESHOLD)
    p.add_argument("--pullback", type=float, default=PULLBACK_THRESHOLD)
    p.add_argument("--confirm", type=float, default=CONFIRM_THRESHOLD)
    p.add_argument("--min-after-pullback", type=float, default=MIN_SECONDS_AFTER_PULLBACK)
    p.add_argument("--min-market-age", type=float, default=MIN_MARKET_AGE_SECONDS)
    p.add_argument("--sample-ms", type=int, default=SAMPLE_INTERVAL_MS)
    p.add_argument("--flat-stake", type=float, default=FLAT_STAKE)
    p.add_argument("--starting-balance", type=float, default=STARTING_BALANCE)
    p.add_argument("--risk-pct", type=float, default=BANKROLL_RISK_PCT)
    p.add_argument("--stake-cap", type=float, default=BANKROLL_STAKE_CAP)
    p.add_argument("--fee-rate", type=float, default=CRYPTO_TAKER_FEE_RATE)
    p.add_argument("--min-fill-ratio", type=float, default=MIN_FILL_RATIO)
    return p


def main() -> None:
    args = build_parser().parse_args()
    data_roots = args.data_root or DATA_ROOTS
    if not data_roots:
        raise SystemExit(
            "No data root configured. Edit DATA_ROOTS near the top of the script "
            "or pass --data-root /path/to/folder-containing-the-nine-zips."
        )

    files, scan_stats = scan_sources(data_roots)
    if not files:
        raise SystemExit("No matching btc-updown-5m-*.zst files found directly or inside ZIP archives.")

    if args.max_files and args.max_files > 0:
        files = files[: args.max_files]

    print(f"ZIP archives found:   {scan_stats['archives_seen']:,}")
    print(f"Local .zst files:     {scan_stats['local_zst_seen']:,}")
    print(f"BTC market sources:   {scan_stats['candidate_sources']:,}")
    if args.max_files and args.max_files > 0:
        print(f"TEST LIMIT active:    {len(files):,} files")

    if args.list_only:
        archives: dict[str, int] = {}
        for s in files:
            kind, outer, _ = split_source(s)
            key = Path(outer).name if kind == "zip" else "[local .zst files]"
            archives[key] = archives.get(key, 0) + 1
        print("\nSources by archive:")
        for name, n in sorted(archives.items()):
            print(f"  {name}: {n:,}")
        return

    output = Path(args.output).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)

    cfg = Config(
        leader_threshold=args.leader,
        pullback_threshold=args.pullback,
        confirm_threshold=args.confirm,
        min_after_pullback=args.min_after_pullback,
        min_market_age=args.min_market_age,
        sample_interval_ms=args.sample_ms,
        flat_stake=args.flat_stake,
        bankroll_cap=args.stake_cap,
        fee_rate=args.fee_rate,
        min_fill_ratio=args.min_fill_ratio,
    )
    cfg_dict = asdict(cfg)

    workers = args.workers
    if workers <= 0:
        workers = max(1, min(8, (os.cpu_count() or 2) - 1))

    print(f"Backtesting {len(files):,} candidate market files")
    print(f"Workers: {workers}")
    print(f"Output:  {output}")
    print(
        f"Strategy: {args.leader:.2f}/{args.pullback:.2f}/{args.confirm:.2f}, "
        f">={args.min_after_pullback:g}s after pullback, age >= {args.min_market_age:g}s"
    )
    print(f"Execution: taker fee_rate={args.fee_rate}, flat stake=${args.flat_stake:.2f}")

    start_wall = time.time()
    results: list[dict[str, Any]] = []

    if workers == 1:
        for i, f in enumerate(files, 1):
            results.append(analyze_file(f, cfg_dict))
            if i % 25 == 0 or i == len(files):
                print(f"Processed {i:,}/{len(files):,}")
    else:
        with ProcessPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(analyze_file, f, cfg_dict): f for f in files}
            done = 0
            for fut in as_completed(futs):
                done += 1
                try:
                    results.append(fut.result())
                except Exception as exc:
                    results.append({"path": futs[fut], "fatal_error": repr(exc)})
                if done % 25 == 0 or done == len(files):
                    elapsed = time.time() - start_wall
                    rate = done / elapsed if elapsed else 0
                    print(f"Processed {done:,}/{len(files):,} ({rate:.2f} files/s)")

    markets, rejected = dedupe_results(results)

    # Add readable UTC timestamps without external packages.
    from datetime import datetime, timezone
    for m in markets:
        m["market_start_utc"] = datetime.fromtimestamp(int(m["market_start"]), tz=timezone.utc).isoformat()
        m["market_end_utc"] = datetime.fromtimestamp(int(m["market_end"]), tz=timezone.utc).isoformat()

    raw_summary = mode_summary(markets, "raw", cfg)
    sampled_summary = mode_summary(markets, "sampled", cfg)

    raw_bankroll_rows, raw_bankroll_summary = bankroll_run(
        markets, "raw", args.starting_balance, args.risk_pct, args.stake_cap,
        args.fee_rate, args.min_fill_ratio
    )
    sampled_bankroll_rows, sampled_bankroll_summary = bankroll_run(
        markets, "sampled", args.starting_balance, args.risk_pct, args.stake_cap,
        args.fee_rate, args.min_fill_ratio
    )

    complete_count = sum(bool(m.get("complete")) for m in markets)
    unknown_outcomes = sum(m.get("outcome") == "UNKNOWN" for m in markets if m.get("complete"))
    seq_break_markets = sum((m.get("sequence_breaks") or 0) > 0 for m in markets)

    summary = {
        "generated_at_epoch": time.time(),
        "input_roots": [str(Path(x).expanduser()) for x in data_roots],
        "scan_stats": scan_stats,
        "files_found": len(files),
        "unique_markets": len(markets),
        "complete_markets": complete_count,
        "incomplete_markets": len(markets) - complete_count,
        "duplicate_or_error_files": len(rejected),
        "complete_markets_unknown_outcome": unknown_outcomes,
        "markets_with_sequence_breaks": seq_break_markets,
        "config": {
            **cfg_dict,
            "starting_balance": args.starting_balance,
            "bankroll_risk_pct": args.risk_pct,
        },
        "raw_strategy": raw_summary,
        "sampled_strategy": sampled_summary,
        "raw_bankroll": raw_bankroll_summary,
        "sampled_bankroll": sampled_bankroll_summary,
        "runtime_seconds": time.time() - start_wall,
        "notes": [
            "Filename timestamp is treated as market START; round end is +300 seconds.",
            "Outcome is inferred from extreme final recorded quote/trade prices, not an official settlement API.",
            "DOWN ask/depth is derived as the binary complement of the normalized UP book.",
            "Bankroll simulation assumes settlement proceeds are available before the next qualifying trade.",
        ],
    }

    write_csv(output / "markets_all.csv", markets)
    write_csv(output / "rejected_duplicates_errors.csv", rejected)
    write_csv(output / "raw_trades.csv", [m for m in markets if m.get("complete") and m.get("raw_status") == "trade"])
    write_csv(output / "sampled_1s_trades.csv", [m for m in markets if m.get("complete") and m.get("sampled_status") == "trade"])
    write_csv(output / "raw_bankroll.csv", raw_bankroll_rows)
    write_csv(output / "sampled_1s_bankroll.csv", sampled_bankroll_rows)
    with (output / "summary.json").open("w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, sort_keys=True)

    print("\n================ RESULT ================")
    print(f"Unique markets:      {len(markets):,}")
    print(f"Complete markets:    {complete_count:,}")
    print(f"Unknown outcomes:    {unknown_outcomes:,}")
    print(f"Sequence-break mkts: {seq_break_markets:,}")
    for label, s, b in (
        ("RAW", raw_summary, raw_bankroll_summary),
        ("SAMPLED 1s", sampled_summary, sampled_bankroll_summary),
    ):
        wr = s["win_rate"]
        roi = s["flat_roi_on_debit"]
        print(f"\n{label}")
        print(f"  Signals:          {s['signals']:,}")
        print(f"  Resolved signals: {s['resolved_signals']:,}")
        print(f"  Win rate:         {wr*100:.2f}%" if wr is not None else "  Win rate:         n/a")
        print(f"  Flat net P&L:     ${s['flat_net_pnl']:,.2f}")
        print(f"  Flat ROI/debit:   {roi*100:.2f}%" if roi is not None else "  Flat ROI/debit:   n/a")
        print(f"  $300 bankroll ->  ${b['ending_balance']:,.2f}")
        print(f"  Max drawdown:     {b['max_drawdown_pct']:.2f}%")
        print(f"  Bust trade:       {b['bust_trade']}")

    print(f"\nReports written to: {output}")
    print("Main files:")
    print("  summary.json")
    print("  markets_all.csv")
    print("  raw_trades.csv")
    print("  sampled_1s_trades.csv")
    print("  raw_bankroll.csv")
    print("  sampled_1s_bankroll.csv")


if __name__ == "__main__":
    main()
