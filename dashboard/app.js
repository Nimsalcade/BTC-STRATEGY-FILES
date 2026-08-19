/* ========================================
   BTC 75/74/76 Backtest Dashboard – App JS
   ======================================== */

// ──────────────────────────────────────────────
// Embedded Data (from summary.json + CSV files)
// ──────────────────────────────────────────────

const SUMMARY = {
  complete_markets: 2015,
  complete_markets_unknown_outcome: 9,
  config: {
    bankroll_cap: 300.0,
    bankroll_risk_pct: 0.1,
    confirm_threshold: 0.76,
    fee_rate: 0.07,
    flat_stake: 300.0,
    leader_threshold: 0.75,
    min_after_pullback: 40.0,
    min_fill_ratio: 0.99,
    min_market_age: 180.0,
    pullback_threshold: 0.74,
    sample_interval_ms: 1000,
    starting_balance: 300.0,
  },
  duplicate_or_error_files: 1458,
  files_found: 4056,
  incomplete_markets: 583,
  unique_markets: 2598,
  markets_with_sequence_breaks: 0,
  runtime_seconds: 748.60,
  raw_strategy: {
    complete_markets: 2015,
    flat_net_pnl: -629.73,
    flat_roi_on_debit: -0.03817,
    flat_total_debit: 16500.0,
    losses: 12,
    signals: 56,
    resolved_signals: 55,
    wins: 43,
    win_rate: 0.78182,
    status_counts: {
      leader_confirm_too_early_in_market: 114,
      leader_confirm_too_soon_after_pullback: 1425,
      no_pullback: 280,
      opposite_confirmed_first: 140,
      trade: 56,
    },
  },
  sampled_strategy: {
    complete_markets: 2015,
    flat_net_pnl: -249.06,
    flat_roi_on_debit: -0.01137,
    flat_total_debit: 21900.0,
    losses: 13,
    signals: 73,
    resolved_signals: 73,
    wins: 60,
    win_rate: 0.82192,
    status_counts: {
      leader_confirm_too_early_in_market: 121,
      leader_confirm_too_soon_after_pullback: 1182,
      no_pullback: 453,
      opposite_confirmed_first: 186,
      trade: 73,
    },
  },
  raw_bankroll: {
    account_multiple: 0.92612,
    bust_trade: null,
    ending_balance: 277.84,
    fee_rate: 0.07,
    losses: 12,
    max_drawdown_pct: 36.89,
    net_pnl: -22.16,
    peak_balance: 310.20,
    risk_pct: 0.1,
    stake_cap: 300.0,
    starting_balance: 300.0,
    trades: 55,
    win_rate: 0.78182,
    wins: 43,
    skipped_unknown_outcome: 1,
    skipped_insufficient_depth: 0,
  },
  sampled_bankroll: {
    account_multiple: 0.99199,
    bust_trade: null,
    ending_balance: 297.60,
    fee_rate: 0.07,
    losses: 13,
    max_drawdown_pct: 43.05,
    net_pnl: -2.40,
    peak_balance: 390.19,
    risk_pct: 0.1,
    stake_cap: 300.0,
    starting_balance: 300.0,
    trades: 73,
    win_rate: 0.82192,
    wins: 60,
    skipped_unknown_outcome: 0,
    skipped_insufficient_depth: 0,
  },
};

// Raw bankroll trades
const RAW_BANKROLL = [
  {n:1,ts:1786234800,side:"DOWN",outcome:"UP",win:false,et:184.756,bb:300.00,stake:30.00,debit:30.00,avgp:0.764,pnl:-30.00,ba:270.00,dd:10.0},
  {n:2,ts:1786242000,side:"UP",outcome:"UP",win:true,et:216.48,bb:270.00,stake:27.00,debit:27.00,avgp:0.774,pnl:7.33,ba:277.33,dd:7.56},
  {n:3,ts:1786253400,side:"UP",outcome:"UP",win:true,et:258.777,bb:277.33,stake:27.73,debit:27.73,avgp:0.762,pnl:8.08,ba:285.41,dd:4.86},
  {n:4,ts:1786255500,side:"UP",outcome:"UP",win:true,et:201.901,bb:285.41,stake:28.54,debit:28.54,avgp:0.762,pnl:8.31,ba:293.72,dd:2.09},
  {n:5,ts:1786255800,side:"UP",outcome:"UP",win:true,et:217.469,bb:293.72,stake:29.37,debit:29.37,avgp:0.764,pnl:8.46,ba:302.17,dd:0.0},
  {n:6,ts:1786257900,side:"DOWN",outcome:"DOWN",win:true,et:209.936,bb:302.17,stake:30.22,debit:30.22,avgp:0.782,pnl:7.86,ba:310.04,dd:0.0},
  {n:7,ts:1786275600,side:"DOWN",outcome:"UP",win:false,et:265.978,bb:310.04,stake:31.00,debit:31.00,avgp:0.760,pnl:-31.00,ba:279.03,dd:10.0},
  {n:8,ts:1786276500,side:"DOWN",outcome:"DOWN",win:true,et:244.775,bb:279.03,stake:27.90,debit:27.90,avgp:0.772,pnl:7.69,ba:286.72,dd:7.52},
  {n:9,ts:1786279500,side:"UP",outcome:"DOWN",win:false,et:259.217,bb:286.72,stake:28.67,debit:28.67,avgp:0.777,pnl:-28.67,ba:258.05,dd:16.77},
  {n:10,ts:1786302300,side:"DOWN",outcome:"UP",win:false,et:271.139,bb:258.05,stake:25.81,debit:25.81,avgp:0.769,pnl:-25.81,ba:232.25,dd:25.09},
  {n:11,ts:1786320900,side:"DOWN",outcome:"DOWN",win:true,et:232.409,bb:232.25,stake:23.22,debit:23.22,avgp:0.760,pnl:6.83,ba:239.08,dd:22.89},
  {n:12,ts:1786330500,side:"DOWN",outcome:"DOWN",win:true,et:278.297,bb:239.08,stake:23.91,debit:23.91,avgp:0.770,pnl:6.64,ba:245.71,dd:20.75},
  {n:13,ts:1786333200,side:"UP",outcome:"DOWN",win:false,et:189.878,bb:245.71,stake:24.57,debit:24.57,avgp:0.760,pnl:-24.57,ba:221.14,dd:28.67},
  {n:14,ts:1786338000,side:"UP",outcome:"UP",win:true,et:201.411,bb:221.14,stake:22.11,debit:22.11,avgp:0.760,pnl:6.50,ba:227.64,dd:26.58},
  {n:15,ts:1786378200,side:"DOWN",outcome:"DOWN",win:true,et:220.261,bb:227.64,stake:22.76,debit:22.76,avgp:0.760,pnl:6.69,ba:234.34,dd:24.42},
  {n:16,ts:1786382700,side:"UP",outcome:"UP",win:true,et:255.057,bb:234.34,stake:23.43,debit:23.43,avgp:0.801,pnl:5.41,ba:239.75,dd:22.67},
  {n:17,ts:1786393800,side:"DOWN",outcome:"DOWN",win:true,et:247.521,bb:239.75,stake:23.97,debit:23.97,avgp:0.764,pnl:6.88,ba:246.62,dd:20.45},
  {n:18,ts:1786404900,side:"DOWN",outcome:"DOWN",win:true,et:231.618,bb:246.62,stake:24.66,debit:24.66,avgp:0.774,pnl:6.72,ba:253.34,dd:18.29},
  {n:19,ts:1786409400,side:"UP",outcome:"UP",win:true,et:182.344,bb:253.34,stake:25.33,debit:25.33,avgp:0.760,pnl:7.45,ba:260.79,dd:15.88},
  {n:20,ts:1786419000,side:"DOWN",outcome:"DOWN",win:true,et:210.764,bb:260.79,stake:26.08,debit:26.08,avgp:0.760,pnl:7.67,ba:268.46,dd:13.41},
  {n:21,ts:1786438500,side:"DOWN",outcome:"DOWN",win:true,et:197.346,bb:268.46,stake:26.85,debit:26.85,avgp:0.760,pnl:7.89,ba:276.35,dd:10.86},
  {n:22,ts:1786451100,side:"UP",outcome:"UP",win:true,et:198.595,bb:276.35,stake:27.64,debit:27.64,avgp:0.769,pnl:7.73,ba:284.08,dd:8.37},
  {n:23,ts:1786468800,side:"UP",outcome:"UP",win:true,et:211.388,bb:284.08,stake:28.41,debit:28.41,avgp:0.761,pnl:8.31,ba:292.39,dd:5.69},
  {n:24,ts:1786469400,side:"UP",outcome:"DOWN",win:false,et:219.63,bb:292.39,stake:29.24,debit:29.24,avgp:0.763,pnl:-29.24,ba:263.15,dd:15.12},
  {n:25,ts:1786472100,side:"UP",outcome:"UP",win:true,et:247.156,bb:263.15,stake:26.32,debit:26.32,avgp:0.799,pnl:6.16,ba:269.31,dd:13.14},
  {n:26,ts:1786472400,side:"DOWN",outcome:"DOWN",win:true,et:212.742,bb:269.31,stake:26.93,debit:26.93,avgp:0.762,pnl:7.82,ba:277.13,dd:10.61},
  {n:27,ts:1786482300,side:"DOWN",outcome:"DOWN",win:true,et:270.445,bb:277.13,stake:27.71,debit:27.71,avgp:0.777,pnl:7.42,ba:284.55,dd:8.22},
  {n:28,ts:1786490100,side:"DOWN",outcome:"DOWN",win:true,et:180.263,bb:284.55,stake:28.45,debit:28.45,avgp:0.760,pnl:8.37,ba:292.91,dd:5.52},
  {n:29,ts:1786681800,side:"DOWN",outcome:"DOWN",win:true,et:187.561,bb:292.91,stake:29.29,debit:29.29,avgp:0.760,pnl:8.61,ba:301.53,dd:2.74},
  {n:30,ts:1786683000,side:"DOWN",outcome:"DOWN",win:true,et:199.849,bb:301.53,stake:30.15,debit:30.15,avgp:0.764,pnl:8.67,ba:310.20,dd:0.0},
  {n:31,ts:1786730700,side:"UP",outcome:"DOWN",win:false,et:230.186,bb:310.20,stake:31.02,debit:31.02,avgp:0.760,pnl:-31.02,ba:279.18,dd:10.0},
  {n:32,ts:1786742400,side:"DOWN",outcome:"DOWN",win:true,et:184.246,bb:279.18,stake:27.92,debit:27.92,avgp:0.760,pnl:8.21,ba:287.39,dd:7.35},
  {n:33,ts:1786743300,side:"DOWN",outcome:"UP",win:false,et:191.493,bb:287.39,stake:28.74,debit:28.74,avgp:0.760,pnl:-28.74,ba:258.65,dd:16.62},
  {n:34,ts:1786757700,side:"UP",outcome:"UP",win:true,et:233.019,bb:258.65,stake:25.86,debit:25.86,avgp:0.773,pnl:7.06,ba:265.71,dd:14.34},
  {n:35,ts:1786759200,side:"UP",outcome:"UP",win:true,et:184.682,bb:265.71,stake:26.57,debit:26.57,avgp:0.760,pnl:7.81,ba:273.52,dd:11.82},
  {n:36,ts:1786769700,side:"DOWN",outcome:"DOWN",win:true,et:213.546,bb:273.52,stake:27.35,debit:27.35,avgp:0.760,pnl:8.04,ba:281.56,dd:9.23},
  {n:37,ts:1786791000,side:"DOWN",outcome:"DOWN",win:true,et:193.066,bb:281.56,stake:28.16,debit:28.16,avgp:0.760,pnl:8.28,ba:289.84,dd:6.56},
  {n:38,ts:1786799400,side:"DOWN",outcome:"UP",win:false,et:239.168,bb:289.84,stake:28.98,debit:28.98,avgp:0.766,pnl:-28.98,ba:260.86,dd:15.91},
  {n:39,ts:1786800300,side:"UP",outcome:"DOWN",win:false,et:260.355,bb:260.86,stake:26.09,debit:26.09,avgp:0.760,pnl:-26.09,ba:234.77,dd:24.31},
  {n:40,ts:1786815300,side:"UP",outcome:"DOWN",win:false,et:187.303,bb:234.77,stake:23.48,debit:23.48,avgp:0.761,pnl:-23.48,ba:211.30,dd:31.88},
  {n:41,ts:1786830300,side:"DOWN",outcome:"DOWN",win:true,et:238.91,bb:211.30,stake:21.13,debit:21.13,avgp:0.760,pnl:6.21,ba:217.51,dd:29.88},
  {n:42,ts:1786830900,side:"UP",outcome:"DOWN",win:false,et:227.351,bb:217.51,stake:21.75,debit:21.75,avgp:0.760,pnl:-21.75,ba:195.76,dd:36.89},
  {n:43,ts:1786834800,side:"UP",outcome:"UP",win:true,et:215.258,bb:195.76,stake:19.58,debit:19.58,avgp:0.786,pnl:4.97,ba:200.73,dd:35.29},
  {n:44,ts:1786838700,side:"UP",outcome:"UP",win:true,et:204.118,bb:200.73,stake:20.07,debit:20.07,avgp:0.783,pnl:5.19,ba:205.92,dd:33.62},
  {n:45,ts:1786840800,side:"DOWN",outcome:"DOWN",win:true,et:216.419,bb:205.92,stake:20.59,debit:20.59,avgp:0.768,pnl:5.78,ba:211.70,dd:31.75},
  {n:46,ts:1786849200,side:"DOWN",outcome:"DOWN",win:true,et:207.436,bb:211.70,stake:21.17,debit:21.17,avgp:0.762,pnl:6.15,ba:217.84,dd:29.77},
  {n:47,ts:1786852800,side:"UP",outcome:"UP",win:true,et:228.422,bb:217.84,stake:21.78,debit:21.78,avgp:0.768,pnl:6.12,ba:223.96,dd:27.80},
  {n:48,ts:1786853100,side:"UP",outcome:"UP",win:true,et:181.525,bb:223.96,stake:22.40,debit:22.40,avgp:0.760,pnl:6.59,ba:230.55,dd:25.68},
  {n:49,ts:1786857000,side:"UP",outcome:"UP",win:true,et:181.349,bb:230.55,stake:23.05,debit:23.05,avgp:0.760,pnl:6.78,ba:237.33,dd:23.49},
  {n:50,ts:1786859100,side:"DOWN",outcome:"DOWN",win:true,et:231.063,bb:237.33,stake:23.73,debit:23.73,avgp:0.760,pnl:6.98,ba:244.31,dd:21.24},
  {n:51,ts:1786892700,side:"DOWN",outcome:"DOWN",win:true,et:206.521,bb:244.31,stake:24.43,debit:24.43,avgp:0.764,pnl:7.04,ba:251.35,dd:18.97},
  {n:52,ts:1786915800,side:"DOWN",outcome:"DOWN",win:true,et:240.183,bb:251.35,stake:25.13,debit:25.13,avgp:0.764,pnl:7.24,ba:258.58,dd:16.64},
  {n:53,ts:1786923300,side:"UP",outcome:"UP",win:true,et:181.485,bb:258.58,stake:25.86,debit:25.86,avgp:0.835,pnl:4.75,ba:263.33,dd:15.11},
  {n:54,ts:1786936500,side:"DOWN",outcome:"DOWN",win:true,et:197.507,bb:263.33,stake:26.33,debit:26.33,avgp:0.760,pnl:7.72,ba:271.05,dd:12.62},
  {n:55,ts:1786958400,side:"DOWN",outcome:"DOWN",win:true,et:182.503,bb:271.05,stake:27.11,debit:27.11,avgp:0.788,pnl:6.78,ba:277.84,dd:10.43},
];

// Sampled bankroll trades
const SAMPLED_BANKROLL = [
  {n:1,ts:1786234800,side:"DOWN",outcome:"UP",win:false,et:185.0,bb:300.00,stake:30.00,debit:30.00,avgp:0.764,pnl:-30.00,ba:270.00,dd:10.0},
  {n:2,ts:1786243200,side:"DOWN",outcome:"DOWN",win:true,et:186.0,bb:270.00,stake:27.00,debit:27.00,avgp:0.930,pnl:1.89,ba:271.89,dd:9.37},
  {n:3,ts:1786255800,side:"UP",outcome:"UP",win:true,et:218.0,bb:271.89,stake:27.19,debit:27.19,avgp:0.790,pnl:6.73,ba:278.62,dd:7.13},
  {n:4,ts:1786289100,side:"DOWN",outcome:"DOWN",win:true,et:183.0,bb:278.62,stake:27.86,debit:27.86,avgp:0.766,pnl:7.94,ba:286.56,dd:4.48},
  {n:5,ts:1786295100,side:"DOWN",outcome:"DOWN",win:true,et:237.0,bb:286.56,stake:28.66,debit:28.66,avgp:0.770,pnl:7.97,ba:294.53,dd:1.82},
  {n:6,ts:1786308300,side:"DOWN",outcome:"DOWN",win:true,et:227.0,bb:294.53,stake:29.45,debit:29.45,avgp:0.774,pnl:8.01,ba:302.53,dd:0.0},
  {n:7,ts:1786310400,side:"UP",outcome:"UP",win:true,et:219.0,bb:302.53,stake:30.25,debit:30.25,avgp:0.763,pnl:8.73,ba:311.26,dd:0.0},
  {n:8,ts:1786311000,side:"DOWN",outcome:"UP",win:false,et:252.0,bb:311.26,stake:31.13,debit:31.13,avgp:0.853,pnl:-31.13,ba:280.14,dd:10.0},
  {n:9,ts:1786320900,side:"DOWN",outcome:"DOWN",win:true,et:233.0,bb:280.14,stake:28.01,debit:28.01,avgp:0.790,pnl:6.93,ba:287.07,dd:7.77},
  {n:10,ts:1786330500,side:"DOWN",outcome:"DOWN",win:true,et:279.0,bb:287.07,stake:28.71,debit:28.71,avgp:0.830,pnl:5.47,ba:292.54,dd:6.01},
  {n:11,ts:1786333200,side:"UP",outcome:"DOWN",win:false,et:190.0,bb:292.54,stake:29.25,debit:29.25,avgp:0.760,pnl:-29.25,ba:263.29,dd:15.41},
  {n:12,ts:1786338000,side:"UP",outcome:"UP",win:true,et:212.0,bb:263.29,stake:26.33,debit:26.33,avgp:0.870,pnl:3.68,ba:266.96,dd:14.23},
  {n:13,ts:1786358100,side:"DOWN",outcome:"DOWN",win:true,et:182.0,bb:266.96,stake:26.70,debit:26.70,avgp:0.763,pnl:7.74,ba:274.70,dd:11.75},
  {n:14,ts:1786359300,side:"DOWN",outcome:"DOWN",win:true,et:180.0,bb:274.70,stake:27.47,debit:27.47,avgp:0.851,pnl:4.48,ba:279.18,dd:10.31},
  {n:15,ts:1786378200,side:"DOWN",outcome:"DOWN",win:true,et:221.0,bb:279.18,stake:27.92,debit:27.92,avgp:0.800,pnl:6.50,ba:285.68,dd:8.22},
  {n:16,ts:1786382700,side:"UP",outcome:"UP",win:true,et:256.0,bb:285.68,stake:28.57,debit:28.57,avgp:0.900,pnl:2.95,ba:288.63,dd:7.27},
  {n:17,ts:1786393800,side:"DOWN",outcome:"DOWN",win:true,et:248.0,bb:288.63,stake:28.86,debit:28.86,avgp:0.863,pnl:4.27,ba:292.91,dd:5.90},
  {n:18,ts:1786404900,side:"DOWN",outcome:"DOWN",win:true,et:232.0,bb:292.91,stake:29.29,debit:29.29,avgp:0.830,pnl:5.58,ba:298.49,dd:4.10},
  {n:19,ts:1786409400,side:"UP",outcome:"UP",win:true,et:183.0,bb:298.49,stake:29.85,debit:29.85,avgp:0.760,pnl:8.78,ba:307.27,dd:1.28},
  {n:20,ts:1786419000,side:"DOWN",outcome:"DOWN",win:true,et:211.0,bb:307.27,stake:30.73,debit:30.73,avgp:0.760,pnl:9.04,ba:316.30,dd:0.0},
  {n:21,ts:1786438500,side:"DOWN",outcome:"DOWN",win:true,et:198.0,bb:316.30,stake:31.63,debit:31.63,avgp:0.775,pnl:8.57,ba:324.87,dd:0.0},
  {n:22,ts:1786438800,side:"UP",outcome:"UP",win:true,et:261.0,bb:324.87,stake:32.49,debit:32.49,avgp:0.790,pnl:8.04,ba:332.91,dd:0.0},
  {n:23,ts:1786451100,side:"UP",outcome:"UP",win:true,et:200.0,bb:332.91,stake:33.29,debit:33.29,avgp:0.770,pnl:9.26,ba:342.17,dd:0.0},
  {n:24,ts:1786467900,side:"DOWN",outcome:"DOWN",win:true,et:209.0,bb:342.17,stake:34.22,debit:34.22,avgp:0.800,pnl:7.96,ba:350.13,dd:0.0},
  {n:25,ts:1786469400,side:"UP",outcome:"DOWN",win:false,et:220.0,bb:350.13,stake:35.01,debit:35.01,avgp:0.760,pnl:-35.01,ba:315.12,dd:10.0},
  {n:26,ts:1786472100,side:"UP",outcome:"UP",win:true,et:248.0,bb:315.12,stake:31.51,debit:31.51,avgp:0.900,pnl:3.26,ba:318.38,dd:9.07},
  {n:27,ts:1786472400,side:"DOWN",outcome:"DOWN",win:true,et:213.0,bb:318.38,stake:31.84,debit:31.84,avgp:0.770,pnl:8.85,ba:327.23,dd:6.54},
  {n:28,ts:1786486800,side:"UP",outcome:"UP",win:true,et:198.0,bb:327.23,stake:32.72,debit:32.72,avgp:0.780,pnl:8.59,ba:335.83,dd:4.09},
  {n:29,ts:1786490100,side:"DOWN",outcome:"DOWN",win:true,et:181.0,bb:335.83,stake:33.58,debit:33.58,avgp:0.766,pnl:9.58,ba:345.40,dd:1.35},
  {n:30,ts:1786669800,side:"DOWN",outcome:"DOWN",win:true,et:248.0,bb:345.40,stake:34.54,debit:34.54,avgp:0.900,pnl:3.57,ba:348.97,dd:0.33},
  {n:31,ts:1786681800,side:"DOWN",outcome:"DOWN",win:true,et:188.0,bb:348.97,stake:34.90,debit:34.90,avgp:0.770,pnl:9.71,ba:358.68,dd:0.0},
  {n:32,ts:1786682100,side:"DOWN",outcome:"DOWN",win:true,et:227.0,bb:358.68,stake:35.87,debit:35.87,avgp:0.760,pnl:10.55,ba:369.23,dd:0.0},
  {n:33,ts:1786683000,side:"DOWN",outcome:"DOWN",win:true,et:201.0,bb:369.23,stake:36.92,debit:36.92,avgp:0.766,pnl:10.51,ba:379.74,dd:0.0},
  {n:34,ts:1786694700,side:"DOWN",outcome:"DOWN",win:true,et:243.0,bb:379.74,stake:37.97,debit:37.97,avgp:0.772,pnl:10.45,ba:390.19,dd:0.0},
  {n:35,ts:1786707000,side:"DOWN",outcome:"UP",win:false,et:180.0,bb:390.19,stake:39.02,debit:39.02,avgp:0.819,pnl:-39.02,ba:351.17,dd:10.0},
  {n:36,ts:1786730700,side:"UP",outcome:"DOWN",win:false,et:231.0,bb:351.17,stake:35.12,debit:35.12,avgp:0.800,pnl:-35.12,ba:316.05,dd:19.0},
  {n:37,ts:1786742400,side:"DOWN",outcome:"DOWN",win:true,et:185.0,bb:316.05,stake:31.61,debit:31.61,avgp:0.770,pnl:8.79,ba:324.84,dd:16.75},
  {n:38,ts:1786743300,side:"DOWN",outcome:"UP",win:false,et:192.0,bb:324.84,stake:32.48,debit:32.48,avgp:0.770,pnl:-32.48,ba:292.36,dd:25.07},
  {n:39,ts:1786757700,side:"UP",outcome:"UP",win:true,et:234.0,bb:292.36,stake:29.24,debit:29.24,avgp:0.790,pnl:7.24,ba:299.59,dd:23.22},
  {n:40,ts:1786758300,side:"DOWN",outcome:"DOWN",win:true,et:202.0,bb:299.59,stake:29.96,debit:29.96,avgp:0.760,pnl:8.81,ba:308.40,dd:20.96},
  {n:41,ts:1786759200,side:"UP",outcome:"UP",win:true,et:185.0,bb:308.40,stake:30.84,debit:30.84,avgp:0.760,pnl:9.07,ba:317.47,dd:18.64},
  {n:42,ts:1786768200,side:"DOWN",outcome:"DOWN",win:true,et:222.0,bb:317.47,stake:31.75,debit:31.75,avgp:0.779,pnl:8.40,ba:325.87,dd:16.48},
  {n:43,ts:1786770900,side:"UP",outcome:"UP",win:true,et:248.0,bb:325.87,stake:32.59,debit:32.59,avgp:0.770,pnl:9.06,ba:334.93,dd:14.16},
  {n:44,ts:1786772400,side:"DOWN",outcome:"UP",win:false,et:190.0,bb:334.93,stake:33.49,debit:33.49,avgp:0.778,pnl:-33.49,ba:301.44,dd:22.74},
  {n:45,ts:1786775700,side:"DOWN",outcome:"DOWN",win:true,et:211.0,bb:301.44,stake:30.14,debit:30.14,avgp:0.842,pnl:5.26,ba:306.70,dd:21.40},
  {n:46,ts:1786787100,side:"UP",outcome:"UP",win:true,et:187.0,bb:306.70,stake:30.67,debit:30.67,avgp:0.760,pnl:9.02,ba:315.71,dd:19.09},
  {n:47,ts:1786793400,side:"UP",outcome:"DOWN",win:false,et:187.0,bb:315.71,stake:31.57,debit:31.57,avgp:0.774,pnl:-31.57,ba:284.14,dd:27.18},
  {n:48,ts:1786796100,side:"DOWN",outcome:"DOWN",win:true,et:240.0,bb:284.14,stake:28.41,debit:28.41,avgp:0.810,pnl:6.20,ba:290.35,dd:25.59},
  {n:49,ts:1786799400,side:"DOWN",outcome:"UP",win:false,et:240.0,bb:290.35,stake:29.03,debit:29.03,avgp:0.780,pnl:-29.03,ba:261.31,dd:33.03},
  {n:50,ts:1786800300,side:"UP",outcome:"DOWN",win:false,et:261.0,bb:261.31,stake:26.13,debit:26.13,avgp:0.780,pnl:-26.13,ba:235.18,dd:39.73},
  {n:51,ts:1786827900,side:"DOWN",outcome:"DOWN",win:true,et:238.0,bb:235.18,stake:23.52,debit:23.52,avgp:0.760,pnl:6.92,ba:242.10,dd:37.95},
  {n:52,ts:1786830600,side:"DOWN",outcome:"DOWN",win:true,et:218.0,bb:242.10,stake:24.21,debit:24.21,avgp:0.825,pnl:4.79,ba:246.89,dd:36.72},
  {n:53,ts:1786830900,side:"UP",outcome:"DOWN",win:false,et:229.0,bb:246.89,stake:24.69,debit:24.69,avgp:0.793,pnl:-24.69,ba:222.20,dd:43.05},
  {n:54,ts:1786833300,side:"DOWN",outcome:"DOWN",win:true,et:240.0,bb:222.20,stake:22.22,debit:22.22,avgp:0.886,pnl:2.65,ba:224.85,dd:42.37},
  {n:55,ts:1786837200,side:"UP",outcome:"UP",win:true,et:194.0,bb:224.85,stake:22.48,debit:22.48,avgp:0.760,pnl:6.61,ba:231.46,dd:40.68},
  {n:56,ts:1786840800,side:"DOWN",outcome:"DOWN",win:true,et:217.0,bb:231.46,stake:23.15,debit:23.15,avgp:0.784,pnl:5.94,ba:237.40,dd:39.16},
  {n:57,ts:1786843800,side:"UP",outcome:"UP",win:true,et:218.0,bb:237.40,stake:23.74,debit:23.74,avgp:0.803,pnl:5.43,ba:242.83,dd:37.76},
  {n:58,ts:1786849200,side:"DOWN",outcome:"DOWN",win:true,et:208.0,bb:242.83,stake:24.28,debit:24.28,avgp:0.780,pnl:6.38,ba:249.21,dd:36.13},
  {n:59,ts:1786850700,side:"UP",outcome:"UP",win:true,et:247.0,bb:249.21,stake:24.92,debit:24.92,avgp:0.770,pnl:6.93,ba:256.14,dd:34.35},
  {n:60,ts:1786853100,side:"UP",outcome:"UP",win:true,et:183.0,bb:256.14,stake:25.61,debit:25.61,avgp:0.780,pnl:6.73,ba:262.87,dd:32.63},
  {n:61,ts:1786856400,side:"DOWN",outcome:"UP",win:false,et:214.0,bb:262.87,stake:26.29,debit:26.29,avgp:0.766,pnl:-26.29,ba:236.58,dd:39.37},
  {n:62,ts:1786859100,side:"DOWN",outcome:"DOWN",win:true,et:232.0,bb:236.58,stake:23.66,debit:23.66,avgp:0.760,pnl:6.96,ba:243.54,dd:37.58},
  {n:63,ts:1786871400,side:"DOWN",outcome:"DOWN",win:true,et:213.0,bb:243.54,stake:24.35,debit:24.35,avgp:0.829,pnl:4.66,ba:248.20,dd:36.39},
  {n:64,ts:1786909500,side:"DOWN",outcome:"DOWN",win:true,et:198.0,bb:248.20,stake:24.82,debit:24.82,avgp:0.889,pnl:2.88,ba:251.08,dd:35.65},
  {n:65,ts:1786914300,side:"DOWN",outcome:"DOWN",win:true,et:218.0,bb:251.08,stake:25.11,debit:25.11,avgp:0.770,pnl:6.98,ba:258.07,dd:33.86},
  {n:66,ts:1786915800,side:"DOWN",outcome:"DOWN",win:true,et:241.0,bb:258.07,stake:25.81,debit:25.81,avgp:0.830,pnl:4.92,ba:262.99,dd:32.60},
  {n:67,ts:1786923300,side:"UP",outcome:"UP",win:true,et:182.0,bb:262.99,stake:26.30,debit:26.30,avgp:0.920,pnl:2.13,ba:265.12,dd:32.05},
  {n:68,ts:1786936500,side:"DOWN",outcome:"DOWN",win:true,et:198.0,bb:265.12,stake:26.51,debit:26.51,avgp:0.800,pnl:6.17,ba:271.29,dd:30.47},
  {n:69,ts:1786944600,side:"UP",outcome:"UP",win:true,et:221.0,bb:271.29,stake:27.13,debit:27.13,avgp:0.760,pnl:7.98,ba:279.26,dd:28.43},
  {n:70,ts:1786946100,side:"DOWN",outcome:"DOWN",win:true,et:193.0,bb:279.26,stake:27.93,debit:27.93,avgp:0.810,pnl:6.10,ba:285.36,dd:26.87},
  {n:71,ts:1786957800,side:"UP",outcome:"UP",win:true,et:202.0,bb:285.36,stake:28.54,debit:28.54,avgp:0.830,pnl:5.44,ba:290.80,dd:25.47},
  {n:72,ts:1786958100,side:"DOWN",outcome:"DOWN",win:true,et:186.0,bb:290.80,stake:29.08,debit:29.08,avgp:0.970,pnl:0.84,ba:291.64,dd:25.26},
  {n:73,ts:1786958400,side:"DOWN",outcome:"DOWN",win:true,et:183.0,bb:291.64,stake:29.16,debit:29.16,avgp:0.820,pnl:5.96,ba:297.60,dd:23.73},
];

// ──────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────

function fmt$(v, decimals = 2) {
  const sign = v < 0 ? '-' : '';
  return sign + '$' + Math.abs(v).toFixed(decimals);
}

function fmtPct(v, decimals = 1) {
  return v.toFixed(decimals) + '%';
}

function tsToDate(ts) {
  return new Date(ts * 1000);
}

function tsToDateStr(ts) {
  const d = tsToDate(ts);
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  return `${months[d.getUTCMonth()]} ${d.getUTCDate()}`;
}

function tsToDateTimeStr(ts) {
  const d = tsToDate(ts);
  return d.toISOString().replace('T', ' ').substring(0, 16) + ' UTC';
}

function getDayKey(ts) {
  const d = tsToDate(ts);
  return `${d.getUTCFullYear()}-${String(d.getUTCMonth()+1).padStart(2,'0')}-${String(d.getUTCDate()).padStart(2,'0')}`;
}

// ──────────────────────────────────────────────
// State
// ──────────────────────────────────────────────

let currentMode = 'raw';
let charts = {};

// ──────────────────────────────────────────────
// Background particles
// ──────────────────────────────────────────────

function initParticles() {
  const container = document.getElementById('bgParticles');
  const count = 25;
  for (let i = 0; i < count; i++) {
    const p = document.createElement('div');
    p.className = 'particle';
    const size = Math.random() * 3 + 1;
    p.style.width = size + 'px';
    p.style.height = size + 'px';
    p.style.left = Math.random() * 100 + '%';
    p.style.animationDuration = (Math.random() * 15 + 10) + 's';
    p.style.animationDelay = (Math.random() * 10) + 's';
    p.style.opacity = Math.random() * 0.3 + 0.1;
    container.appendChild(p);
  }
}

// ──────────────────────────────────────────────
// Data accessors
// ──────────────────────────────────────────────

function getStrategy(mode) {
  return mode === 'raw' ? SUMMARY.raw_strategy : SUMMARY.sampled_strategy;
}

function getBankroll(mode) {
  return mode === 'raw' ? SUMMARY.raw_bankroll : SUMMARY.sampled_bankroll;
}

function getTrades(mode) {
  return mode === 'raw' ? RAW_BANKROLL : SAMPLED_BANKROLL;
}

// ──────────────────────────────────────────────
// KPI rendering
// ──────────────────────────────────────────────

function renderKPIs(mode) {
  const s = getStrategy(mode);
  const b = getBankroll(mode);

  // Net P&L
  const netEl = document.getElementById('valNetPnl');
  netEl.textContent = fmt$(s.flat_net_pnl);
  netEl.className = 'kpi-value ' + (s.flat_net_pnl >= 0 ? 'positive' : 'negative');
  document.getElementById('subNetPnl').textContent = `${s.resolved_signals} resolved trades @ $${SUMMARY.config.flat_stake} flat`;

  // Win rate
  const wrEl = document.getElementById('valWinRate');
  wrEl.textContent = fmtPct(s.win_rate * 100);
  wrEl.className = 'kpi-value ' + (s.win_rate >= 0.5 ? 'positive' : 'negative');
  document.getElementById('subWinRate').textContent = `${s.wins}W / ${s.losses}L`;

  // Ending balance
  const balEl = document.getElementById('valEndBal');
  balEl.textContent = fmt$(b.ending_balance);
  balEl.className = 'kpi-value ' + (b.ending_balance >= b.starting_balance ? 'positive' : 'negative');
  document.getElementById('subEndBal').textContent = `${fmtPct((b.account_multiple - 1) * 100)} return`;

  // Max drawdown
  document.getElementById('valDrawdown').textContent = fmtPct(b.max_drawdown_pct);
  document.getElementById('valDrawdown').className = 'kpi-value negative';
  document.getElementById('subDrawdown').textContent = `Peak: ${fmt$(b.peak_balance)}`;

  // Signals
  document.getElementById('valSignals').textContent = s.signals.toLocaleString();
  document.getElementById('valSignals').className = 'kpi-value';
  document.getElementById('subSignals').textContent = `of ${s.complete_markets.toLocaleString()} complete markets`;

  // ROI
  const roiEl = document.getElementById('valRoi');
  roiEl.textContent = fmtPct(s.flat_roi_on_debit * 100);
  roiEl.className = 'kpi-value ' + (s.flat_roi_on_debit >= 0 ? 'positive' : 'negative');
  document.getElementById('subRoi').textContent = `On ${fmt$(s.flat_total_debit, 0)} deployed`;
}

// ──────────────────────────────────────────────
// Chart.js global config
// ──────────────────────────────────────────────

const chartColors = {
  primary: '#6366f1',
  primaryLight: 'rgba(99, 102, 241, 0.15)',
  secondary: '#a855f7',
  win: '#22c55e',
  winBg: 'rgba(34, 197, 94, 0.2)',
  loss: '#ef4444',
  lossBg: 'rgba(239, 68, 68, 0.2)',
  up: '#3b82f6',
  down: '#f97316',
  grid: 'rgba(148, 163, 184, 0.06)',
  tick: '#64748b',
  tooltip: 'rgba(17, 18, 54, 0.95)',
};

Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.color = chartColors.tick;

const commonScales = {
  x: {
    grid: { color: chartColors.grid, drawBorder: false },
    ticks: { font: { size: 10, weight: 500 }, maxTicksLimit: 10 },
  },
  y: {
    grid: { color: chartColors.grid, drawBorder: false },
    ticks: { font: { size: 10, weight: 500 } },
  },
};

const commonPlugins = {
  legend: { display: false },
  tooltip: {
    backgroundColor: chartColors.tooltip,
    titleColor: '#f1f5f9',
    bodyColor: '#94a3b8',
    borderColor: 'rgba(99, 102, 241, 0.3)',
    borderWidth: 1,
    padding: 10,
    cornerRadius: 8,
    titleFont: { weight: 600, size: 12 },
    bodyFont: { size: 11 },
    displayColors: false,
  },
};

// ──────────────────────────────────────────────
// Equity Chart
// ──────────────────────────────────────────────

function renderEquityChart(mode) {
  const trades = getTrades(mode);
  const labels = ['Start', ...trades.map(t => `#${t.n}`)];
  const data = [300, ...trades.map(t => t.ba)];

  if (charts.equity) charts.equity.destroy();

  const ctx = document.getElementById('equityChart').getContext('2d');
  const grad = ctx.createLinearGradient(0, 0, 0, 280);
  grad.addColorStop(0, 'rgba(99, 102, 241, 0.25)');
  grad.addColorStop(1, 'rgba(99, 102, 241, 0.01)');

  charts.equity = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        data,
        borderColor: chartColors.primary,
        backgroundColor: grad,
        borderWidth: 2,
        fill: true,
        tension: 0.3,
        pointRadius: 0,
        pointHoverRadius: 5,
        pointHoverBackgroundColor: chartColors.primary,
        pointHoverBorderColor: '#fff',
        pointHoverBorderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { intersect: false, mode: 'index' },
      plugins: {
        ...commonPlugins,
        tooltip: {
          ...commonPlugins.tooltip,
          callbacks: {
            title: (items) => {
              const i = items[0].dataIndex;
              if (i === 0) return 'Starting Balance';
              const t = trades[i - 1];
              return `Trade #${t.n} — ${tsToDateStr(t.ts)}`;
            },
            label: (item) => {
              const val = item.raw;
              const i = item.dataIndex;
              const lines = [`Balance: ${fmt$(val)}`];
              if (i > 0) {
                const t = trades[i - 1];
                lines.push(`P&L: ${fmt$(t.pnl)} ${t.win ? '✓' : '✗'}`);
                lines.push(`Side: ${t.side} → ${t.outcome}`);
              }
              return lines;
            },
          },
        },
      },
      scales: {
        ...commonScales,
        y: {
          ...commonScales.y,
          ticks: {
            ...commonScales.y.ticks,
            callback: v => '$' + v.toFixed(0),
          },
        },
      },
    },
  });

  const b = getBankroll(mode);
  document.getElementById('equityBadge').textContent = `$300 → ${fmt$(b.ending_balance)}`;
}

// ──────────────────────────────────────────────
// P&L Distribution
// ──────────────────────────────────────────────

function renderPnlChart(mode) {
  const trades = getTrades(mode);
  const labels = trades.map(t => `#${t.n}`);
  const data = trades.map(t => t.pnl);
  const colors = trades.map(t => t.win ? chartColors.win : chartColors.loss);

  if (charts.pnl) charts.pnl.destroy();

  charts.pnl = new Chart(document.getElementById('pnlChart'), {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: colors.map(c => c + '99'),
        borderColor: colors,
        borderWidth: 1,
        borderRadius: 3,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        ...commonPlugins,
        tooltip: {
          ...commonPlugins.tooltip,
          callbacks: {
            title: (items) => {
              const t = trades[items[0].dataIndex];
              return `Trade #${t.n} — ${tsToDateStr(t.ts)}`;
            },
            label: (item) => {
              const t = trades[item.dataIndex];
              return [
                `P&L: ${fmt$(t.pnl)}`,
                `Side: ${t.side} | Outcome: ${t.outcome}`,
                `Avg Price: ${t.avgp.toFixed(3)}`,
              ];
            },
          },
        },
      },
      scales: {
        ...commonScales,
        y: {
          ...commonScales.y,
          ticks: {
            ...commonScales.y.ticks,
            callback: v => '$' + v.toFixed(0),
          },
        },
      },
    },
  });
}

// ──────────────────────────────────────────────
// Win/Loss Doughnut
// ──────────────────────────────────────────────

function renderWinLossChart(mode) {
  const b = getBankroll(mode);
  if (charts.winLoss) charts.winLoss.destroy();

  charts.winLoss = new Chart(document.getElementById('winLossChart'), {
    type: 'doughnut',
    data: {
      labels: ['Wins', 'Losses'],
      datasets: [{
        data: [b.wins, b.losses],
        backgroundColor: [chartColors.win + 'cc', chartColors.loss + 'cc'],
        borderColor: ['transparent', 'transparent'],
        borderWidth: 0,
        hoverOffset: 8,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '70%',
      plugins: {
        legend: {
          display: true,
          position: 'bottom',
          labels: {
            color: chartColors.tick,
            font: { size: 11, weight: 500 },
            padding: 16,
            usePointStyle: true,
            pointStyleWidth: 10,
          },
        },
        tooltip: {
          ...commonPlugins.tooltip,
          callbacks: {
            label: (item) => {
              const pct = ((item.raw / (b.wins + b.losses)) * 100).toFixed(1);
              return `${item.label}: ${item.raw} (${pct}%)`;
            },
          },
        },
      },
    },
    plugins: [{
      id: 'centerText',
      beforeDraw(chart) {
        const { ctx, chartArea } = chart;
        const cx = (chartArea.left + chartArea.right) / 2;
        const cy = (chartArea.top + chartArea.bottom) / 2;
        ctx.save();
        ctx.font = '800 28px Inter';
        ctx.fillStyle = '#f1f5f9';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(fmtPct(b.win_rate * 100), cx, cy - 8);
        ctx.font = '500 10px Inter';
        ctx.fillStyle = '#64748b';
        ctx.fillText('WIN RATE', cx, cy + 14);
        ctx.restore();
      },
    }],
  });
}

// ──────────────────────────────────────────────
// Drawdown Chart
// ──────────────────────────────────────────────

function renderDrawdownChart(mode) {
  const trades = getTrades(mode);
  const labels = trades.map(t => `#${t.n}`);
  const data = trades.map(t => -t.dd);

  if (charts.drawdown) charts.drawdown.destroy();

  const ctx = document.getElementById('drawdownChart').getContext('2d');
  const grad = ctx.createLinearGradient(0, 0, 0, 260);
  grad.addColorStop(0, 'rgba(239, 68, 68, 0.01)');
  grad.addColorStop(1, 'rgba(239, 68, 68, 0.3)');

  charts.drawdown = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        data,
        borderColor: chartColors.loss,
        backgroundColor: grad,
        borderWidth: 1.5,
        fill: true,
        tension: 0.3,
        pointRadius: 0,
        pointHoverRadius: 4,
        pointHoverBackgroundColor: chartColors.loss,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        ...commonPlugins,
        tooltip: {
          ...commonPlugins.tooltip,
          callbacks: {
            title: (items) => {
              const t = trades[items[0].dataIndex];
              return `Trade #${t.n}`;
            },
            label: (item) => `Drawdown: ${fmtPct(-item.raw)}`,
          },
        },
      },
      scales: {
        ...commonScales,
        y: {
          ...commonScales.y,
          ticks: {
            ...commonScales.y.ticks,
            callback: v => fmtPct(-v),
          },
        },
      },
    },
  });
}

// ──────────────────────────────────────────────
// Side Distribution
// ──────────────────────────────────────────────

function renderSideChart(mode) {
  const trades = getTrades(mode);
  const upCount = trades.filter(t => t.side === 'UP').length;
  const downCount = trades.filter(t => t.side === 'DOWN').length;

  if (charts.side) charts.side.destroy();

  charts.side = new Chart(document.getElementById('sideChart'), {
    type: 'doughnut',
    data: {
      labels: ['UP', 'DOWN'],
      datasets: [{
        data: [upCount, downCount],
        backgroundColor: [chartColors.up + 'cc', chartColors.down + 'cc'],
        borderWidth: 0,
        hoverOffset: 8,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '70%',
      plugins: {
        legend: {
          display: true,
          position: 'bottom',
          labels: {
            color: chartColors.tick,
            font: { size: 11, weight: 500 },
            padding: 16,
            usePointStyle: true,
            pointStyleWidth: 10,
          },
        },
        tooltip: commonPlugins.tooltip,
      },
    },
    plugins: [{
      id: 'centerTextSide',
      beforeDraw(chart) {
        const { ctx, chartArea } = chart;
        const cx = (chartArea.left + chartArea.right) / 2;
        const cy = (chartArea.top + chartArea.bottom) / 2;
        ctx.save();
        ctx.font = '800 28px Inter';
        ctx.fillStyle = '#f1f5f9';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(`${upCount + downCount}`, cx, cy - 8);
        ctx.font = '500 10px Inter';
        ctx.fillStyle = '#64748b';
        ctx.fillText('TRADES', cx, cy + 14);
        ctx.restore();
      },
    }],
  });
}

// ──────────────────────────────────────────────
// Daily P&L
// ──────────────────────────────────────────────

function renderDailyChart(mode) {
  const trades = getTrades(mode);
  const dailyMap = {};
  trades.forEach(t => {
    const day = getDayKey(t.ts);
    if (!dailyMap[day]) dailyMap[day] = { pnl: 0, wins: 0, losses: 0 };
    dailyMap[day].pnl += t.pnl;
    if (t.win) dailyMap[day].wins++; else dailyMap[day].losses++;
  });

  const days = Object.keys(dailyMap).sort();
  const pnls = days.map(d => dailyMap[d].pnl);
  const colors = pnls.map(v => v >= 0 ? chartColors.win + '99' : chartColors.loss + '99');
  const borders = pnls.map(v => v >= 0 ? chartColors.win : chartColors.loss);

  if (charts.daily) charts.daily.destroy();

  charts.daily = new Chart(document.getElementById('dailyChart'), {
    type: 'bar',
    data: {
      labels: days.map(d => {
        const parts = d.split('-');
        const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
        return `${months[parseInt(parts[1])-1]} ${parseInt(parts[2])}`;
      }),
      datasets: [{
        data: pnls,
        backgroundColor: colors,
        borderColor: borders,
        borderWidth: 1,
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        ...commonPlugins,
        tooltip: {
          ...commonPlugins.tooltip,
          callbacks: {
            title: (items) => days[items[0].dataIndex],
            label: (item) => {
              const d = dailyMap[days[item.dataIndex]];
              return [
                `P&L: ${fmt$(d.pnl)}`,
                `Wins: ${d.wins} | Losses: ${d.losses}`,
              ];
            },
          },
        },
      },
      scales: {
        ...commonScales,
        y: {
          ...commonScales.y,
          ticks: {
            ...commonScales.y.ticks,
            callback: v => '$' + v.toFixed(0),
          },
        },
      },
    },
  });
}

// ──────────────────────────────────────────────
// Status Breakdown
// ──────────────────────────────────────────────

function renderStatusChart(mode) {
  const s = getStrategy(mode);
  const sc = s.status_counts;

  const labelMap = {
    trade: 'Trade Signal',
    no_pullback: 'No Pullback',
    leader_confirm_too_soon_after_pullback: 'Confirm Too Soon',
    leader_confirm_too_early_in_market: 'Too Early in Market',
    opposite_confirmed_first: 'Opposite Confirmed',
  };

  const colorMap = {
    trade: '#6366f1',
    no_pullback: '#64748b',
    leader_confirm_too_soon_after_pullback: '#f59e0b',
    leader_confirm_too_early_in_market: '#ef4444',
    opposite_confirmed_first: '#ec4899',
  };

  const keys = Object.keys(sc).sort((a, b) => sc[b] - sc[a]);
  const labels = keys.map(k => labelMap[k] || k);
  const data = keys.map(k => sc[k]);
  const bgColors = keys.map(k => (colorMap[k] || '#94a3b8') + '99');
  const bdColors = keys.map(k => colorMap[k] || '#94a3b8');

  if (charts.status) charts.status.destroy();

  charts.status = new Chart(document.getElementById('statusChart'), {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: bgColors,
        borderColor: bdColors,
        borderWidth: 1,
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: 'y',
      plugins: {
        ...commonPlugins,
        tooltip: {
          ...commonPlugins.tooltip,
          callbacks: {
            label: (item) => {
              const pct = ((item.raw / s.complete_markets) * 100).toFixed(1);
              return `${item.raw.toLocaleString()} markets (${pct}%)`;
            },
          },
        },
      },
      scales: {
        x: {
          ...commonScales.x,
          ticks: { ...commonScales.x.ticks },
        },
        y: {
          ...commonScales.y,
          ticks: { ...commonScales.y.ticks, font: { size: 11, weight: 500 } },
        },
      },
    },
  });

  document.getElementById('statusBadge').textContent = `${s.complete_markets.toLocaleString()} Complete Markets`;
}

// ──────────────────────────────────────────────
// Trade Table
// ──────────────────────────────────────────────

function renderTradeTable(mode, filter = 'all', search = '') {
  const trades = getTrades(mode);
  let filtered = trades;

  if (filter === 'win') filtered = filtered.filter(t => t.win);
  if (filter === 'loss') filtered = filtered.filter(t => !t.win);
  if (search) {
    const q = search.toLowerCase();
    filtered = filtered.filter(t =>
      t.side.toLowerCase().includes(q) ||
      t.outcome.toLowerCase().includes(q) ||
      tsToDateTimeStr(t.ts).toLowerCase().includes(q) ||
      String(t.n).includes(q)
    );
  }

  const tbody = document.getElementById('tradeTableBody');
  tbody.innerHTML = filtered.map(t => `
    <tr>
      <td>${t.n}</td>
      <td>${tsToDateTimeStr(t.ts)}</td>
      <td><span class="badge ${t.side === 'UP' ? 'badge-up' : 'badge-down'}">${t.side}</span></td>
      <td><span class="badge ${t.outcome === 'UP' ? 'badge-up' : 'badge-down'}">${t.outcome}</span></td>
      <td><span class="badge ${t.win ? 'badge-win' : 'badge-loss'}">${t.win ? 'WIN' : 'LOSS'}</span></td>
      <td>${t.et.toFixed(0)}s</td>
      <td>${fmt$(t.stake)}</td>
      <td>${t.avgp.toFixed(3)}</td>
      <td class="${t.pnl >= 0 ? 'win' : 'loss'}">${fmt$(t.pnl)}</td>
      <td>${fmt$(t.ba)}</td>
      <td class="${t.dd > 15 ? 'loss' : ''}">${fmtPct(t.dd)}</td>
    </tr>
  `).join('');
}

// ──────────────────────────────────────────────
// Footer info
// ──────────────────────────────────────────────

function renderFooterInfo() {
  document.getElementById('infoDateRange').textContent = 'Aug 9 – Aug 17, 2026';
  document.getElementById('infoTotalMarkets').textContent = `${SUMMARY.unique_markets.toLocaleString()} (${SUMMARY.complete_markets.toLocaleString()} complete)`;
  document.getElementById('infoFeeRate').textContent = `${(SUMMARY.config.fee_rate * 100).toFixed(0)}% taker fee`;
  document.getElementById('infoThresholds').textContent =
    `${SUMMARY.config.leader_threshold}/${SUMMARY.config.pullback_threshold}/${SUMMARY.config.confirm_threshold}`;
  const mins = Math.floor(SUMMARY.runtime_seconds / 60);
  const secs = Math.floor(SUMMARY.runtime_seconds % 60);
  document.getElementById('infoRuntime').textContent = `${mins}m ${secs}s`;
  document.getElementById('infoRisk').textContent =
    `${(SUMMARY.config.bankroll_risk_pct * 100).toFixed(0)}% of balance (max $${SUMMARY.config.bankroll_cap})`;
}

// ──────────────────────────────────────────────
// Mode toggle
// ──────────────────────────────────────────────

function setMode(mode) {
  currentMode = mode;
  document.querySelectorAll('.mode-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.mode === mode);
  });
  const slider = document.getElementById('modeSlider');
  slider.classList.toggle('right', mode === 'sampled');

  renderAll(mode);
}

function renderAll(mode) {
  renderKPIs(mode);
  renderEquityChart(mode);
  renderPnlChart(mode);
  renderWinLossChart(mode);
  renderDrawdownChart(mode);
  renderSideChart(mode);
  renderDailyChart(mode);
  renderStatusChart(mode);
  renderTradeTable(mode, document.getElementById('tradeFilter').value, document.getElementById('tradeSearch').value);
}

// ──────────────────────────────────────────────
// Init
// ──────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
  initParticles();
  renderFooterInfo();

  // Mode toggle
  document.querySelectorAll('.mode-btn').forEach(btn => {
    btn.addEventListener('click', () => setMode(btn.dataset.mode));
  });

  // Trade filters
  document.getElementById('tradeFilter').addEventListener('change', () => {
    renderTradeTable(currentMode, document.getElementById('tradeFilter').value, document.getElementById('tradeSearch').value);
  });

  let searchTimeout;
  document.getElementById('tradeSearch').addEventListener('input', () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      renderTradeTable(currentMode, document.getElementById('tradeFilter').value, document.getElementById('tradeSearch').value);
    }, 200);
  });

  // Initial render
  setMode('raw');
});
