"""
update_dashboard.py
毎時実行エントリーポイント
1. ADX計算
2. data/adx_live.json 更新
3. data/adx_history.json 更新（週次）
4. LINE通知判定
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# パス設定
ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

LIVE_JSON    = DATA_DIR / "adx_live.json"
HISTORY_JSON = DATA_DIR / "adx_history.json"
STATE_JSON   = DATA_DIR / "adx_state.json"   # 通知済み週の管理

from adx_calculator import get_live_score, compute_weekly_stats, geo_score
from line_bot import send_line_message, send_weekly_summary


def load_json(path: Path) -> dict | list:
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json(path: Path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  💾 {path.name} 保存完了")


def main():
    print(f"\n{'='*50}")
    print(f"  ADX Monitor  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'='*50}")

    # ── 1. ライブスコア取得 ──────────────────────────────────────────
    print("\n📡 ライブデータ取得中...")
    try:
        live = get_live_score()
    except Exception as e:
        print(f"❌ データ取得エラー: {e}")
        sys.exit(1)

    if not live:
        print("⚠️  データなし（市場クローズ？）")
        sys.exit(0)

    print(f"  週: {live['week']}")
    print(f"  スコア: {live['score']}")
    print(f"  H1avg: {live['h1a']}  H4≥20: {live['h4p20']}%  H4≥30: {live['h4p30']}%")
    print(f"  H1足本数: {live['bars_h1']}  H4足本数: {live['bars_h4']}")

    save_json(LIVE_JSON, live)

    # ── 2. 履歴更新（週1回、週が変わったとき）────────────────────────
    state     = load_json(STATE_JSON)
    last_week = state.get("last_history_week", "")

    if live["week"] != last_week:
        print("\n📅 週次履歴を更新中（新しい週を検出）...")
        try:
            history = compute_weekly_stats(weeks_back=52)
            save_json(HISTORY_JSON, {"weeks": history, "updated_at": live["updated_at"]})
            state["last_history_week"] = live["week"]
        except Exception as e:
            print(f"⚠️  履歴更新エラー（続行）: {e}")
    else:
        print(f"\n📅 履歴はそのまま（{live['week']} は更新済み）")

    # ── 3. LINE通知判定 ──────────────────────────────────────────────
    score = live.get("score")
    last_notified_score = state.get("last_notified_score")
    last_notified_week  = state.get("last_notified_week")

    # 通知条件:
    #   a) スコア≥45 かつ
    #   b) 同じ週で前回通知より+5以上上がったとき、または初回
    should_notify = False
    if score is not None and score >= 45:
        if last_notified_week != live["week"]:
            should_notify = True   # 週が変わって初めてスコア≥45
        elif last_notified_score is None or score >= last_notified_score + 5:
            should_notify = True   # 同週内でスコアが5以上上昇

    print(f"\n🔔 通知判定: score={score}, 閾値45, 通知={'YES' if should_notify else 'NO'}")

    if should_notify:
        ok = send_line_message(live)
        if ok:
            state["last_notified_score"] = score
            state["last_notified_week"]  = live["week"]

    # ── 4. 月曜週次サマリー通知 ─────────────────────────────────────
    now = datetime.now(timezone.utc)
    is_monday = now.weekday() == 0
    is_morning_jst = 0 <= (now.hour + 9) % 24 <= 10   # JST 9:00-10:00 ≈ UTC 0-1

    if is_monday and is_morning_jst and state.get("last_summary_week") != live["week"]:
        print("\n📊 週次サマリー通知（月曜朝）...")
        history = load_json(HISTORY_JSON)
        weeks   = history.get("weeks", [])
        prev    = weeks[-2] if len(weeks) >= 2 else None
        send_weekly_summary(live, prev)
        state["last_summary_week"] = live["week"]

    save_json(STATE_JSON, state)
    print(f"\n✅ 完了")


if __name__ == "__main__":
    main()
