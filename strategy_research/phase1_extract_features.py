#!/usr/bin/env python3
"""
Phase 1: Deep Microstructure Analysis of Polymarket BTC 5m markets
===================================================================
Scans all 7 ZIP archives. For each complete market round:
- Reconstructs the full order book (both sides independently)
- Tracks trade flow, aggressor imbalance, price trajectory
- Measures book depth at various price levels over time
- Captures time-series features at 1-second resolution

Produces a Parquet (or CSV) feature matrix: one row per round,
hundreds of columns capturing book/trade microstructure at various
points in the round's lifecycle.
"""

from __future__ import annotations

import csv
import io
import json
import math
import os
import re
import statistics
import sys
import time
import zipfile
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator, Optional

try:
    import zstandard as zstd
except ImportError:
    zstd = None

try:
    import orjson
    def json_loads(raw):
        return orjson.loads(raw)
except ImportError:
    def json_loads(raw):
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return json.loads(raw)

# ── Config ──────────────────────────────────────────────────────────────────

DATA_DIR = Path("/Users/bradamanka/Downloads/Stratgey testing")
OUTPUT_DIR = DATA_DIR / "strategy_research"
OUTPUT_DIR.mkdir(exist_ok=True)

ROUND_SECONDS = 300
FILE_RE = re.compile(r"btc-updown-5m-(\d+)")

# Fee parameters
TAKER_FEE_RATE = 0.07  # Polymarket crypto taker fee coefficient

# ── I/O helpers ─────────────────────────────────────────────────────────────

def iter_zst_from_zip(zip_path: str, member: str) -> Iterator[bytes]:
    """Yield decompressed lines from a .zst member inside a ZIP."""
    with zipfile.ZipFile(zip_path, "r", allowZip64=True) as zf:
        with zf.open(member, "r") as fh:
            if zstd is None:
                raise RuntimeError("pip install zstandard")
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


def scan_all_zips() -> list[tuple[str, str, int]]:
    """Return [(zip_path, member_name, market_start_ts), ...] sorted by timestamp."""
    results = []
    for f in sorted(DATA_DIR.glob("polymarket-btc-5m_*.zip")):
        try:
            with zipfile.ZipFile(f, "r", allowZip64=True) as zf:
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    m = FILE_RE.search(info.filename)
                    if m and info.filename.lower().endswith(".zst"):
                        ts = int(m.group(1))
                        results.append((str(f), info.filename, ts))
        except Exception as e:
            print(f"WARNING: {f}: {e}", file=sys.stderr)
    results.sort(key=lambda x: x[2])
    return results


# ── Order Book ──────────────────────────────────────────────────────────────

class OrderBook:
    """Level-based order book with independent bid/ask tracking."""
    __slots__ = ("bids", "asks")

    def __init__(self):
        self.bids: dict[float, float] = {}  # price -> qty
        self.asks: dict[float, float] = {}  # price -> qty

    def clear(self):
        self.bids.clear()
        self.asks.clear()

    def apply(self, changes):
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

    def best_bid(self) -> Optional[float]:
        return max(self.bids) if self.bids else None

    def best_ask(self) -> Optional[float]:
        return min(self.asks) if self.asks else None

    def mid(self) -> Optional[float]:
        bb, ba = self.best_bid(), self.best_ask()
        if bb is not None and ba is not None:
            return (bb + ba) / 2.0
        return bb or ba

    def spread(self) -> Optional[float]:
        bb, ba = self.best_bid(), self.best_ask()
        if bb is not None and ba is not None:
            return ba - bb
        return None

    def depth_within(self, side: str, max_price_deviation: float) -> float:
        """Total qty available within max_price_deviation of best."""
        if side == "bid":
            if not self.bids:
                return 0.0
            bb = max(self.bids)
            return sum(q for p, q in self.bids.items() if p >= bb - max_price_deviation)
        else:
            if not self.asks:
                return 0.0
            ba = min(self.asks)
            return sum(q for p, q in self.asks.items() if p <= ba + max_price_deviation)

    def total_bid_depth(self) -> float:
        return sum(self.bids.values())

    def total_ask_depth(self) -> float:
        return sum(self.asks.values())

    def vwap_cost(self, side: str, budget: float, fee_rate: float) -> dict:
        """Simulate market order. side='buy_up' means taking asks, 'buy_down' means taking bids."""
        if side == "buy_up":
            levels = sorted(self.asks.items())
        elif side == "buy_down":
            # Buying DOWN = selling UP = hitting UP bids
            # DOWN price for buyer = 1 - UP bid price
            levels = [(1.0 - p, q) for p, q in sorted(self.bids.items(), reverse=True)]
        else:
            return {"shares": 0, "cost": 0, "avg_price": float("nan"), "fee": 0}

        remaining = budget
        shares = 0.0
        principal = 0.0
        fees = 0.0
        levels_used = 0

        for p, q in levels:
            if remaining <= 1e-12:
                break
            if p <= 0 or p >= 1.0001 or q <= 0:
                continue
            fee_per_share = fee_rate * p * (1.0 - p)
            debit_per_share = p + fee_per_share
            take = min(q, remaining / debit_per_share)
            if take <= 0:
                continue
            cost = take * p
            fee = take * fee_per_share
            shares += take
            principal += cost
            fees += fee
            remaining -= (cost + fee)
            levels_used += 1

        total = principal + fees
        return {
            "shares": shares,
            "cost": total,
            "principal": principal,
            "fee": fees,
            "avg_price": principal / shares if shares > 0 else float("nan"),
            "levels_used": levels_used,
            "fill_ratio": total / budget if budget > 0 else 0,
        }


# ── Feature Extraction ─────────────────────────────────────────────────────

@dataclass
class RoundFeatures:
    """All features extracted from a single 5-minute market round."""
    market_start: int = 0
    filename: str = ""
    archive: str = ""
    complete: bool = False
    
    # Outcome
    outcome: str = "UNKNOWN"  # UP or DOWN
    outcome_confidence: float = 0.0
    
    # Time-series snapshots (at specific second marks)
    # We sample at seconds: 30, 60, 90, 120, 150, 180, 210, 240, 270
    # For each: mid price, spread, bid depth, ask depth
    
    # Book features at key timestamps
    mid_30: float = float("nan")
    mid_60: float = float("nan")
    mid_90: float = float("nan")
    mid_120: float = float("nan")
    mid_150: float = float("nan")
    mid_180: float = float("nan")
    mid_210: float = float("nan")
    mid_240: float = float("nan")
    mid_270: float = float("nan")
    
    spread_30: float = float("nan")
    spread_60: float = float("nan")
    spread_90: float = float("nan")
    spread_120: float = float("nan")
    spread_150: float = float("nan")
    spread_180: float = float("nan")
    spread_210: float = float("nan")
    spread_240: float = float("nan")
    spread_270: float = float("nan")
    
    # Bid depth within 5 cents of best
    bid_depth5c_120: float = 0.0
    bid_depth5c_180: float = 0.0
    bid_depth5c_210: float = 0.0
    bid_depth5c_240: float = 0.0
    
    # Ask depth within 5 cents of best
    ask_depth5c_120: float = 0.0
    ask_depth5c_180: float = 0.0
    ask_depth5c_210: float = 0.0
    ask_depth5c_240: float = 0.0
    
    # Trade flow features (cumulative by timestamp)
    buy_vol_0_120: float = 0.0     # Total buy aggressor volume seconds 0-120
    sell_vol_0_120: float = 0.0
    buy_vol_120_180: float = 0.0
    sell_vol_120_180: float = 0.0
    buy_vol_180_240: float = 0.0
    sell_vol_180_240: float = 0.0
    buy_vol_240_300: float = 0.0
    sell_vol_240_300: float = 0.0
    
    # Trade counts
    trade_count_total: int = 0
    trade_count_0_120: int = 0
    trade_count_120_180: int = 0
    trade_count_180_240: int = 0
    trade_count_240_300: int = 0
    
    # Price trajectory features
    max_mid_0_180: float = float("nan")  # highest mid in first 3 min
    min_mid_0_180: float = float("nan")
    max_mid_180_300: float = float("nan")  # highest mid in last 2 min
    min_mid_180_300: float = float("nan")
    
    # Momentum features
    momentum_60_120: float = float("nan")  # mid change from 60s to 120s
    momentum_120_180: float = float("nan")
    momentum_180_240: float = float("nan")
    
    # Volatility (std of mid-price changes, sampled every second)
    volatility_0_120: float = float("nan")
    volatility_120_240: float = float("nan")
    
    # Order flow imbalance
    ofi_0_120: float = float("nan")   # (buy_vol - sell_vol) / (buy_vol + sell_vol)
    ofi_120_180: float = float("nan")
    ofi_180_240: float = float("nan")
    
    # Book imbalance at key times (bid_depth / (bid_depth + ask_depth))
    book_imbalance_120: float = float("nan")
    book_imbalance_180: float = float("nan")
    book_imbalance_210: float = float("nan")
    book_imbalance_240: float = float("nan")
    
    # Execution simulation features
    # What would $20, $50, $100, $200 buy cost in avg price?
    up_vwap_20_at_180: float = float("nan")
    up_vwap_50_at_180: float = float("nan")
    up_vwap_20_at_210: float = float("nan")
    up_vwap_50_at_210: float = float("nan")
    down_vwap_20_at_180: float = float("nan")
    down_vwap_50_at_180: float = float("nan")
    down_vwap_20_at_210: float = float("nan")
    down_vwap_50_at_210: float = float("nan")
    
    # First touch timestamps (when UP or DOWN ask first hits various thresholds)
    up_first_75: float = float("nan")
    up_first_80: float = float("nan")
    up_first_85: float = float("nan")
    down_first_75: float = float("nan")
    down_first_80: float = float("nan")
    down_first_85: float = float("nan")
    
    # Persistence features: how long does the leader side stay above threshold
    up_seconds_above_75: float = 0.0
    down_seconds_above_75: float = 0.0
    up_seconds_above_80: float = 0.0
    down_seconds_above_80: float = 0.0
    
    # Leader/pullback/re-break dynamics
    leader_side: str = ""
    leader_time: float = float("nan")
    leader_peak_before_180: float = float("nan")
    leader_trough_after_peak: float = float("nan")
    
    # Data quality
    book_events: int = 0
    trade_events: int = 0
    first_book_age: float = float("nan")
    last_book_age: float = float("nan")
    

def extract_features(zip_path: str, member: str, market_start: int) -> RoundFeatures:
    """Extract comprehensive features from one market round."""
    feat = RoundFeatures()
    feat.market_start = market_start
    feat.filename = Path(member).name
    feat.archive = Path(zip_path).name
    
    start_ns = market_start * 1_000_000_000
    end_ns = (market_start + ROUND_SECONDS) * 1_000_000_000
    
    book = OrderBook()
    
    # 1-second sampling state
    sample_interval_ns = 1_000_000_000
    next_sample_ns = start_ns
    
    # Time-series accumulators
    mid_series: list[tuple[float, float]] = []  # (age_s, mid)
    
    # Trade accumulators
    buy_volumes = defaultdict(float)   # bucket -> volume
    sell_volumes = defaultdict(float)
    trade_counts = defaultdict(int)
    
    # Threshold touch tracking
    up_ask_first_75 = float("nan")
    up_ask_first_80 = float("nan")
    up_ask_first_85 = float("nan")
    down_ask_first_75 = float("nan")
    down_ask_first_80 = float("nan")
    down_ask_first_85 = float("nan")
    
    up_seconds_above_75 = 0.0
    down_seconds_above_75 = 0.0
    up_seconds_above_80 = 0.0
    down_seconds_above_80 = 0.0
    
    last_sample_age = -1.0
    last_up_ask = None
    last_down_ask = None
    
    # Book snapshots at specific times
    book_snapshots: dict[int, dict] = {}  # second -> {mid, spread, bid_depth, ask_depth, ...}
    
    # Execution snapshots
    exec_snapshots: dict[str, dict] = {}
    
    # Leader tracking
    leader_side = ""
    leader_time = float("nan")
    leader_peak = 0.0
    leader_trough = 1.0
    leader_peaked = False
    
    first_book_age = None
    last_book_age = None
    book_events = 0
    trade_events = 0
    last_sequence = None
    
    # Outcome inference
    outcome_tail_quotes: deque[tuple[float, float]] = deque(maxlen=64)
    outcome_tail_trades: deque[tuple[float, float]] = deque(maxlen=256)
    
    def capture_sample(sample_ns):
        nonlocal last_sample_age, last_up_ask, last_down_ask
        nonlocal up_seconds_above_75, down_seconds_above_75
        nonlocal up_seconds_above_80, down_seconds_above_80
        nonlocal up_ask_first_75, up_ask_first_80, up_ask_first_85
        nonlocal down_ask_first_75, down_ask_first_80, down_ask_first_85
        nonlocal leader_side, leader_time, leader_peak, leader_trough, leader_peaked
        
        age = (sample_ns - start_ns) / 1e9
        m = book.mid()
        if m is not None:
            mid_series.append((age, m))
        
        bb = book.best_bid()
        ba = book.best_ask()
        sp = book.spread()
        
        # UP ask = best ask price for UP token
        up_ask = ba  
        # DOWN ask = 1 - best bid (binary complement)
        down_ask = (1.0 - bb) if bb is not None else None
        
        # Persistence tracking
        if last_sample_age >= 0 and age - last_sample_age <= 1.5:
            dt = age - last_sample_age
            if up_ask is not None and up_ask >= 0.75:
                up_seconds_above_75 += dt
            if down_ask is not None and down_ask >= 0.75:
                down_seconds_above_75 += dt
            if up_ask is not None and up_ask >= 0.80:
                up_seconds_above_80 += dt
            if down_ask is not None and down_ask >= 0.80:
                down_seconds_above_80 += dt
        
        # First touch tracking
        if up_ask is not None:
            if up_ask >= 0.75 and math.isnan(up_ask_first_75):
                up_ask_first_75 = age
            if up_ask >= 0.80 and math.isnan(up_ask_first_80):
                up_ask_first_80 = age
            if up_ask >= 0.85 and math.isnan(up_ask_first_85):
                up_ask_first_85 = age
        if down_ask is not None:
            if down_ask >= 0.75 and math.isnan(down_ask_first_75):
                down_ask_first_75 = age
            if down_ask >= 0.80 and math.isnan(down_ask_first_80):
                down_ask_first_80 = age
            if down_ask >= 0.85 and math.isnan(down_ask_first_85):
                down_ask_first_85 = age
        
        # Leader tracking (first side to hit 0.75)
        if not leader_side:
            up_hit = up_ask is not None and up_ask >= 0.75
            down_hit = down_ask is not None and down_ask >= 0.75
            if up_hit and not down_hit:
                leader_side = "UP"
                leader_time = age
            elif down_hit and not up_hit:
                leader_side = "DOWN"
                leader_time = age
        
        if leader_side:
            leader_ask = up_ask if leader_side == "UP" else down_ask
            if leader_ask is not None:
                if age <= 180:
                    if leader_ask > leader_peak:
                        leader_peak = leader_ask
                        leader_peaked = True
                if leader_peaked and leader_ask < leader_trough:
                    leader_trough = leader_ask
        
        # Snapshot at key seconds
        sec = int(round(age))
        if sec in (30, 60, 90, 120, 150, 180, 210, 240, 270):
            snap = {
                "mid": m,
                "spread": sp,
                "bid_depth_5c": book.depth_within("bid", 0.05),
                "ask_depth_5c": book.depth_within("ask", 0.05),
                "total_bid": book.total_bid_depth(),
                "total_ask": book.total_ask_depth(),
                "up_ask": up_ask,
                "down_ask": down_ask,
            }
            book_snapshots[sec] = snap
        
        # Execution snapshots at 180 and 210
        if sec in (180, 210):
            for budget in (20, 50):
                up_fill = book.vwap_cost("buy_up", budget, TAKER_FEE_RATE)
                down_fill = book.vwap_cost("buy_down", budget, TAKER_FEE_RATE)
                exec_snapshots[f"up_{budget}_{sec}"] = up_fill
                exec_snapshots[f"down_{budget}_{sec}"] = down_fill
        
        # Outcome inference tail
        if age >= ROUND_SECONDS - 15:
            proxy = m
            if proxy is not None:
                outcome_tail_quotes.append((age, proxy))
        
        last_sample_age = age
        last_up_ask = up_ask
        last_down_ask = down_ask
    
    # ── Main event loop ────────────────────────────────────────────────
    try:
        for raw_line in iter_zst_from_zip(zip_path, member):
            if not raw_line:
                continue
            try:
                obj = json_loads(raw_line)
            except Exception:
                continue
            
            if isinstance(obj, dict):
                continue  # header
            if not isinstance(obj, list) or not obj:
                continue
            
            typ = obj[0]
            
            if typ in (0, 1) and len(obj) >= 7:
                try:
                    source_ns = int(obj[5])
                    changes = obj[6]
                except Exception:
                    continue
                
                # Emit samples before applying
                if source_ns > start_ns:
                    while next_sample_ns < min(source_ns, end_ns + 1):
                        capture_sample(next_sample_ns)
                        next_sample_ns += sample_interval_ns
                
                if typ == 0:
                    book.clear()
                book.apply(changes)
                
                if source_ns < start_ns or source_ns > end_ns:
                    continue
                
                age = (source_ns - start_ns) / 1e9
                book_events += 1
                if first_book_age is None:
                    first_book_age = age
                last_book_age = age
            
            elif typ == 2 and len(obj) >= 7:
                try:
                    source_ns = int(obj[5])
                    trades = obj[6]
                except Exception:
                    continue
                if start_ns <= source_ns <= end_ns and isinstance(trades, list):
                    age = (source_ns - start_ns) / 1e9
                    
                    # Determine time bucket
                    if age < 120:
                        bucket = "0_120"
                    elif age < 180:
                        bucket = "120_180"
                    elif age < 240:
                        bucket = "180_240"
                    else:
                        bucket = "240_300"
                    
                    for tr in trades:
                        try:
                            side = int(tr[0])
                            price = float(tr[1])
                            qty = float(tr[2])
                        except Exception:
                            continue
                        trade_events += 1
                        trade_counts[bucket] += 1
                        if side == 0:  # buy aggressor
                            buy_volumes[bucket] += qty
                        else:
                            sell_volumes[bucket] += qty
                        
                        if age >= ROUND_SECONDS - 15:
                            outcome_tail_trades.append((age, price))
        
        # Complete remaining samples
        while next_sample_ns <= end_ns:
            capture_sample(next_sample_ns)
            next_sample_ns += sample_interval_ns
    
    except Exception as e:
        feat.complete = False
        return feat
    
    # ── Completeness check ──────────────────────────────────────────
    feat.book_events = book_events
    feat.trade_events = trade_events
    feat.first_book_age = first_book_age if first_book_age is not None else float("nan")
    feat.last_book_age = last_book_age if last_book_age is not None else float("nan")
    
    feat.complete = (
        first_book_age is not None
        and last_book_age is not None
        and first_book_age <= 5.0
        and last_book_age >= 295.0
        and book_events > 0
    )
    
    if not feat.complete:
        return feat
    
    # ── Outcome inference ───────────────────────────────────────────
    quote_vals = [v for _, v in outcome_tail_quotes if 0 <= v <= 1]
    trade_vals = [p for _, p in outcome_tail_trades if 0 <= p <= 1]
    qm = statistics.median(quote_vals[-8:]) if len(quote_vals) >= 4 else None
    tm = statistics.median(trade_vals[-20:]) if len(trade_vals) >= 5 else None
    
    votes = []
    for v in (qm, tm):
        if v is None:
            continue
        if v >= 0.90:
            votes.append("UP")
        elif v <= 0.10:
            votes.append("DOWN")
    
    if votes and all(v == votes[0] for v in votes):
        feat.outcome = votes[0]
        feat.outcome_confidence = max(qm or 0, 1 - (qm or 1))
    else:
        feat.outcome = "UNKNOWN"
    
    # ── Populate features from snapshots ────────────────────────────
    for sec in (30, 60, 90, 120, 150, 180, 210, 240, 270):
        snap = book_snapshots.get(sec, {})
        m = snap.get("mid")
        if m is not None:
            setattr(feat, f"mid_{sec}", m)
        sp = snap.get("spread")
        if sp is not None:
            setattr(feat, f"spread_{sec}", sp)
    
    for sec in (120, 180, 210, 240):
        snap = book_snapshots.get(sec, {})
        setattr(feat, f"bid_depth5c_{sec}", snap.get("bid_depth_5c", 0.0))
        setattr(feat, f"ask_depth5c_{sec}", snap.get("ask_depth_5c", 0.0))
        
        bd = snap.get("total_bid", 0)
        ad = snap.get("total_ask", 0)
        total = bd + ad
        if total > 0:
            setattr(feat, f"book_imbalance_{sec}", bd / total)
    
    # Trade flow
    feat.buy_vol_0_120 = buy_volumes.get("0_120", 0)
    feat.sell_vol_0_120 = sell_volumes.get("0_120", 0)
    feat.buy_vol_120_180 = buy_volumes.get("120_180", 0)
    feat.sell_vol_120_180 = sell_volumes.get("120_180", 0)
    feat.buy_vol_180_240 = buy_volumes.get("180_240", 0)
    feat.sell_vol_180_240 = sell_volumes.get("180_240", 0)
    feat.buy_vol_240_300 = buy_volumes.get("240_300", 0)
    feat.sell_vol_240_300 = sell_volumes.get("240_300", 0)
    
    feat.trade_count_total = sum(trade_counts.values())
    feat.trade_count_0_120 = trade_counts.get("0_120", 0)
    feat.trade_count_120_180 = trade_counts.get("120_180", 0)
    feat.trade_count_180_240 = trade_counts.get("180_240", 0)
    feat.trade_count_240_300 = trade_counts.get("240_300", 0)
    
    # Order flow imbalance
    for bucket, attr in [("0_120", "ofi_0_120"), ("120_180", "ofi_120_180"), ("180_240", "ofi_180_240")]:
        bv = buy_volumes.get(bucket, 0)
        sv = sell_volumes.get(bucket, 0)
        total = bv + sv
        if total > 0:
            setattr(feat, attr, (bv - sv) / total)
    
    # Price trajectory
    mids_0_180 = [m for a, m in mid_series if a <= 180]
    mids_180_300 = [m for a, m in mid_series if a > 180]
    if mids_0_180:
        feat.max_mid_0_180 = max(mids_0_180)
        feat.min_mid_0_180 = min(mids_0_180)
    if mids_180_300:
        feat.max_mid_180_300 = max(mids_180_300)
        feat.min_mid_180_300 = min(mids_180_300)
    
    # Momentum
    if not math.isnan(feat.mid_60) and not math.isnan(feat.mid_120):
        feat.momentum_60_120 = feat.mid_120 - feat.mid_60
    if not math.isnan(feat.mid_120) and not math.isnan(feat.mid_180):
        feat.momentum_120_180 = feat.mid_180 - feat.mid_120
    if not math.isnan(feat.mid_180) and not math.isnan(feat.mid_240):
        feat.momentum_180_240 = feat.mid_240 - feat.mid_180
    
    # Volatility
    mids_0_120_list = [m for a, m in mid_series if a <= 120]
    mids_120_240_list = [m for a, m in mid_series if 120 < a <= 240]
    if len(mids_0_120_list) > 2:
        changes = [mids_0_120_list[i+1] - mids_0_120_list[i] for i in range(len(mids_0_120_list)-1)]
        feat.volatility_0_120 = statistics.stdev(changes) if len(changes) > 1 else 0.0
    if len(mids_120_240_list) > 2:
        changes = [mids_120_240_list[i+1] - mids_120_240_list[i] for i in range(len(mids_120_240_list)-1)]
        feat.volatility_120_240 = statistics.stdev(changes) if len(changes) > 1 else 0.0
    
    # Execution features
    for key, attr in [
        ("up_20_180", "up_vwap_20_at_180"), ("up_50_180", "up_vwap_50_at_180"),
        ("up_20_210", "up_vwap_20_at_210"), ("up_50_210", "up_vwap_50_at_210"),
        ("down_20_180", "down_vwap_20_at_180"), ("down_50_180", "down_vwap_50_at_180"),
        ("down_20_210", "down_vwap_20_at_210"), ("down_50_210", "down_vwap_50_at_210"),
    ]:
        fill = exec_snapshots.get(key, {})
        setattr(feat, attr, fill.get("avg_price", float("nan")))
    
    # Threshold touches
    feat.up_first_75 = up_ask_first_75
    feat.up_first_80 = up_ask_first_80
    feat.up_first_85 = up_ask_first_85
    feat.down_first_75 = down_ask_first_75
    feat.down_first_80 = down_ask_first_80
    feat.down_first_85 = down_ask_first_85
    
    # Persistence
    feat.up_seconds_above_75 = up_seconds_above_75
    feat.down_seconds_above_75 = down_seconds_above_75
    feat.up_seconds_above_80 = up_seconds_above_80
    feat.down_seconds_above_80 = down_seconds_above_80
    
    # Leader
    feat.leader_side = leader_side
    feat.leader_time = leader_time
    feat.leader_peak_before_180 = leader_peak
    feat.leader_trough_after_peak = leader_trough
    
    return feat


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    print("=" * 70)
    print("PHASE 1: Deep Microstructure Feature Extraction")
    print("=" * 70)
    
    sources = scan_all_zips()
    print(f"Found {len(sources)} candidate market files across {len(set(s[0] for s in sources))} ZIP archives")
    
    # Group by market_start
    market_groups = defaultdict(list)
    for zp, mem, ts in sources:
        market_groups[ts].append((zp, mem))
    
    print(f"Unique markets: {len(market_groups)}")
    
    # Process all markets, picking the best version for each
    results: list[RoundFeatures] = []
    t0 = time.time()
    
    processed_count = 0
    for ts in sorted(market_groups.keys()):
        candidates = market_groups[ts]
        best_feat = None
        
        for zp, mem in candidates:
            feat = extract_features(zp, mem, ts)
            if best_feat is None or (feat.complete and not best_feat.complete) or (feat.complete and feat.book_events > best_feat.book_events):
                best_feat = feat
            if best_feat.complete:
                break
                
        if best_feat:
            results.append(best_feat)
            
        processed_count += 1
        if processed_count % 100 == 0 or processed_count == len(market_groups):
            elapsed = time.time() - t0
            rate = processed_count / elapsed if elapsed > 0 else 0
            print(f"  Processed {processed_count}/{len(market_groups)} ({rate:.1f}/s) "
                  f"— {sum(1 for r in results if r.complete)} complete, "
                  f"{sum(1 for r in results if r.outcome in ('UP','DOWN'))} with known outcome")
    
    elapsed = time.time() - t0
    print(f"\nTotal: {len(results)} markets processed in {elapsed:.1f}s")
    
    complete = [r for r in results if r.complete]
    known = [r for r in complete if r.outcome in ("UP", "DOWN")]
    print(f"Complete: {len(complete)}")
    print(f"Known outcome: {len(known)}")
    print(f"UP outcomes: {sum(1 for r in known if r.outcome == 'UP')}")
    print(f"DOWN outcomes: {sum(1 for r in known if r.outcome == 'DOWN')}")
    
    # Write feature matrix to CSV
    output_path = OUTPUT_DIR / "feature_matrix.csv"
    
    if known:
        # Get all field names from dataclass
        field_names = [f.name for f in known[0].__dataclass_fields__.values()]
        
        with open(output_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=field_names)
            writer.writeheader()
            for r in known:
                row = {}
                for fn in field_names:
                    val = getattr(r, fn)
                    if isinstance(val, float) and math.isnan(val):
                        row[fn] = ""
                    else:
                        row[fn] = val
                writer.writerow(row)
        
        print(f"\nFeature matrix written to: {output_path}")
        print(f"  Rows: {len(known)}, Columns: {len(field_names)}")
    
    return known


if __name__ == "__main__":
    main()
