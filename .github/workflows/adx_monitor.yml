"""
adx_calculator.py
XAUUSD ADX Weekly Score Engine
幾何平均スコア: (H1_avgADX正規化 × H4≥20% × H4≥30%)^(1/3)
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
import json
import os

SYMBOL    = "GC=F"   # yfinance: Gold Futures (XAUUSD相当)
H1_PERIOD = 28
H4_PERIOD = 28

# ── ADX計算 ─────────────────────────────────────────────────────────
def calc_adx(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high  = df["High"]
    low   = df["Low"]
    close = df["Close"]

    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs()
    ], axis=1).max(axis=1)

    plus_dm  = high.diff().clip(lower=0)
    minus_dm = (-low.diff()).clip(lower=0)
    mask = plus_dm < minus_dm;  plus_dm[mask]  = 0
    mask = minus_dm < high.diff().clip(lower=0); minus_dm[mask] = 0

    def smooth(s, n):
        out = [np.nan] * len(s)
        vals = s.values
        # first valid sum
        first = next((i for i, v in enumerate(vals) if not np.isnan(v)), None)
        if first is None: return pd.Series(out, index=s.index)
        acc = 0; cnt = 0
        for i in range(first, min(first+n, len(vals))):
            if not np.isnan(vals[i]): acc += vals[i]; cnt += 1
        if cnt < n: return pd.Series(out, index=s.index)
        out[first+n-1] = acc
        for i in range(first+n, len(vals)):
            if np.isnan(vals[i]): out[i] = np.nan
            else: out[i] = out[i-1] - out[i-1]/n + vals[i]
        return pd.Series(out, index=s.index)

    atr14  = smooth(tr,       period)
    pDM14  = smooth(plus_dm,  period)
    mDM14  = smooth(minus_dm, period)

    pDI = 100 * pDM14 / atr14
    mDI = 100 * mDM14 / atr14
    dx  = 100 * (pDI - mDI).abs() / (pDI + mDI)
    adx = smooth(dx, period)
    return pd.Series(adx, index=df.index)


# ── 週次統計を計算 ──────────────────────────────────────────────────
def compute_weekly_stats(weeks_back: int = 52) -> list[dict]:
    end   = datetime.now(timezone.utc)
    start = end - timedelta(weeks=weeks_back + 4)   # バッファ込み

    # H1足
    df_h1 = yf.download(SYMBOL, start=start, end=end, interval="1h",
                         progress=False, auto_adjust=True)
    # H4足（yfinanceに4h直接ないのでH1から再サンプル）
    df_h4 = df_h1.resample("4h").agg({
        "Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"
    }).dropna()

    adx_h1 = calc_adx(df_h1, H1_PERIOD)
    adx_h4 = calc_adx(df_h4, H4_PERIOD)

    # 週番号を付与
    df_h1["adx"] = adx_h1
    df_h4["adx"] = adx_h4
    df_h1["week"] = df_h1.index.to_period("W").astype(str)
    df_h4["week"] = df_h4.index.to_period("W").astype(str)

    results = []
    for wk, grp_h1 in df_h1.groupby("week"):
        grp_h4 = df_h4[df_h4["week"] == wk]
        h1_vals = grp_h1["adx"].dropna()
        h4_vals = grp_h4["adx"].dropna()

        if len(h1_vals) < 5 or len(h4_vals) < 3:
            continue

        h1a    = float(h1_vals.mean())
        h4p20  = float((h4_vals >= 20).mean() * 100)
        h4p30  = float((h4_vals >= 30).mean() * 100)
        score  = geo_score(h1a, h4p20, h4p30)

        results.append({
            "week":   wk,
            "ws":     str(grp_h1.index[0].date()),
            "h1a":    round(h1a,  2),
            "h4p20":  round(h4p20, 1),
            "h4p30":  round(h4p30, 1),
            "score":  round(score, 1) if score is not None else None,
        })

    return sorted(results, key=lambda x: x["week"])


# ── 幾何平均スコア ───────────────────────────────────────────────────
def geo_score(h1a: float, h4p20: float, h4p30: float) -> float | None:
    if any(v is None for v in [h1a, h4p20, h4p30]):
        return None
    h1norm = max(0.0, min(100.0, (h1a - 10) / (40 - 10) * 100))
    a = max(0.1, h1norm)
    b = max(0.1, h4p20)
    c = max(0.1, h4p30)
    return (a * b * c) ** (1/3)


# ── 現在週のライブスコア ─────────────────────────────────────────────
def get_live_score() -> dict:
    end   = datetime.now(timezone.utc)
    start = end - timedelta(days=10)

    df_h1 = yf.download(SYMBOL, start=start, end=end, interval="1h",
                         progress=False, auto_adjust=True)
    df_h4 = df_h1.resample("4h").agg({
        "Open":"first","High":"max","Low":"min","Close":"last","Volume":"sum"
    }).dropna()

    adx_h1 = calc_adx(df_h1, H1_PERIOD)
    adx_h4 = calc_adx(df_h4, H4_PERIOD)

    # 今週のみ
    this_week = end.strftime("%Y-W%W")
    h1_this = adx_h1[adx_h1.index.to_period("W").astype(str) == this_week].dropna()
    h4_this = adx_h4[adx_h4.index.to_period("W").astype(str) == this_week].dropna()

    if len(h1_this) == 0:
        return {}

    h1a   = float(h1_this.mean())
    h4p20 = float((h4_this >= 20).mean() * 100) if len(h4_this) else 0.0
    h4p30 = float((h4_this >= 30).mean() * 100) if len(h4_this) else 0.0
    score = geo_score(h1a, h4p20, h4p30)

    return {
        "week":      this_week,
        "updated_at": end.isoformat(),
        "h1a":        round(h1a,   2),
        "h4p20":      round(h4p20, 1),
        "h4p30":      round(h4p30, 1),
        "score":      round(score,  1) if score else None,
        "bars_h1":    len(h1_this),
        "bars_h4":    len(h4_this),
    }


if __name__ == "__main__":
    print("=== Live Score ===")
    live = get_live_score()
    print(json.dumps(live, indent=2, ensure_ascii=False))

    print("\n=== Weekly History (last 8 weeks) ===")
    hist = compute_weekly_stats(weeks_back=8)
    for row in hist:
        print(f"  {row['week']}  score={row['score']:5.1f}  "
              f"h1a={row['h1a']:5.2f}  h4p20={row['h4p20']:5.1f}%  h4p30={row['h4p30']:5.1f}%")
