"""
line_bot.py
LINE Messaging API を使ったADXスコア通知
"""

import os
import json
import requests
from datetime import datetime, timezone

LINE_API_URL     = "https://api.line.me/v2/bot/message/broadcast"
LINE_CHANNEL_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")

# スコア帯の定義
SCORE_LEVELS = [
    (75, "🔥🔥🔥 EXPLOSIVE", "#FF4400"),
    (60, "⚡ 最強週",        "#00FFB3"),
    (45, "✅ 強い週",         "#00D97E"),
    (30, "🟡 良い週",         "#FFD700"),
    (18, "⬜ OK週",           "#888888"),
    (0,  "❌ 見送り",          "#444444"),
]

def get_score_label(score: float | None) -> tuple[str, str]:
    if score is None:
        return "— データなし", "#444444"
    for threshold, label, color in SCORE_LEVELS:
        if score >= threshold:
            return label, color
    return "❌ 見送り", "#444444"


def build_flex_message(data: dict) -> dict:
    score      = data.get("score")
    h1a        = data.get("h1a", 0)
    h4p20      = data.get("h4p20", 0)
    h4p30      = data.get("h4p30", 0)
    week       = data.get("week", "")
    updated_at = data.get("updated_at", "")
    bars_h1    = data.get("bars_h1", 0)

    label, color = get_score_label(score)
    score_str    = str(int(score)) if score is not None else "—"

    # 進捗バーの長さ（0〜100px相当）
    def bar_pct(v, mn=0, mx=100):
        return max(0, min(100, int((v - mn) / (mx - mn) * 100)))

    h1a_pct  = bar_pct(h1a, 10, 40)
    h4p20_pct = bar_pct(h4p20, 0, 100)
    h4p30_pct = bar_pct(h4p30, 0, 100)

    # 更新時刻フォーマット
    try:
        dt = datetime.fromisoformat(updated_at).astimezone()
        time_str = dt.strftime("%m/%d %H:%M JST")
    except Exception:
        time_str = updated_at[:16] if updated_at else "—"

    return {
        "type": "flex",
        "altText": f"[ADX Monitor] {week} スコア: {score_str} {label}",
        "contents": {
            "type": "bubble",
            "size": "kilo",
            "styles": {
                "body": {"backgroundColor": "#060b10"}
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "paddingAll": "16px",
                "spacing": "sm",
                "contents": [
                    # ヘッダー
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "contents": [
                            {
                                "type": "text",
                                "text": "ADX MONITOR",
                                "size": "xxs",
                                "color": "#2a4a60",
                                "flex": 1,
                            },
                            {
                                "type": "text",
                                "text": time_str,
                                "size": "xxs",
                                "color": "#2a4a60",
                                "align": "end",
                            }
                        ]
                    },
                    {
                        "type": "text",
                        "text": f"XAUUSD  {week}",
                        "size": "xs",
                        "color": "#5a8aaa",
                        "margin": "xs",
                    },
                    # スコア大表示
                    {
                        "type": "box",
                        "layout": "vertical",
                        "backgroundColor": "#0a1828",
                        "cornerRadius": "8px",
                        "paddingAll": "12px",
                        "margin": "md",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "horizontal",
                                "contents": [
                                    {
                                        "type": "text",
                                        "text": "相場点数",
                                        "size": "xs",
                                        "color": "#3a5a70",
                                        "flex": 1,
                                    },
                                    {
                                        "type": "text",
                                        "text": score_str,
                                        "size": "xxl",
                                        "color": color if color != "#444444" else "#555555",
                                        "weight": "bold",
                                        "align": "end",
                                    }
                                ]
                            },
                            {
                                "type": "text",
                                "text": label,
                                "size": "sm",
                                "color": color if color != "#444444" else "#555555",
                                "align": "end",
                                "margin": "xs",
                            }
                        ]
                    },
                    # 3指標
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "md",
                        "spacing": "xs",
                        "contents": [
                            _metric_row("H1 avgADX", f"{h1a:.2f}", h1a_pct, "#44aaff"),
                            _metric_row("H4 ≥20%",   f"{h4p20:.0f}%", h4p20_pct, "#ffd700"),
                            _metric_row("H4 ≥30%",   f"{h4p30:.0f}%", h4p30_pct, "#ff88cc"),
                        ]
                    },
                    # フッター
                    {
                        "type": "text",
                        "text": f"H1足 {bars_h1}本 集計 | (H1×H4≥20×H4≥30)^1/3",
                        "size": "xxs",
                        "color": "#1e3040",
                        "margin": "md",
                        "wrap": True,
                    }
                ]
            }
        }
    }


def _metric_row(label: str, value: str, pct: int, color: str) -> dict:
    return {
        "type": "box",
        "layout": "vertical",
        "contents": [
            {
                "type": "box",
                "layout": "horizontal",
                "contents": [
                    {"type": "text", "text": label, "size": "xxs", "color": "#3a5a70", "flex": 2},
                    {"type": "text", "text": value, "size": "xxs", "color": color, "align": "end", "weight": "bold"},
                ]
            },
            {
                "type": "box",
                "layout": "horizontal",
                "height": "4px",
                "backgroundColor": "#0d1e2e",
                "cornerRadius": "2px",
                "contents": [
                    {
                        "type": "box",
                        "layout": "vertical",
                        "backgroundColor": color,
                        "width": f"{pct}%",
                        "contents": []
                    }
                ]
            }
        ]
    }


def send_line_message(data: dict, force: bool = False) -> bool:
    """
    force=False のときはスコア≥45のみ通知
    force=True  のときは常に通知（手動確認用）
    """
    if not LINE_CHANNEL_TOKEN:
        print("⚠️  LINE_CHANNEL_ACCESS_TOKEN が未設定")
        return False

    score = data.get("score")
    if not force and (score is None or score < 45):
        label, _ = get_score_label(score)
        print(f"通知スキップ: score={score} ({label}) — 閾値45未満")
        return False

    payload  = {"messages": [build_flex_message(data)]}
    headers  = {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_TOKEN}",
    }

    resp = requests.post(LINE_API_URL, headers=headers,
                         data=json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    if resp.status_code == 200:
        label, _ = get_score_label(score)
        print(f"✅ LINE送信成功: score={score} ({label})")
        return True
    else:
        print(f"❌ LINE送信失敗: {resp.status_code} {resp.text}")
        return False


# ── 週次サマリー通知（毎週月曜朝用）─────────────────────────────────
def send_weekly_summary(current: dict, prev_week: dict | None = None) -> bool:
    score_now  = current.get("score")
    score_prev = prev_week.get("score") if prev_week else None
    week       = current.get("week", "")

    if score_prev is not None:
        diff = score_now - score_prev if score_now else 0
        trend = f"前週比 {'↑' if diff > 0 else '↓'}{abs(diff):.0f}"
    else:
        trend = "初回集計"

    label, _ = get_score_label(score_now)

    summary_data = {
        **current,
        "week": f"週次サマリー {week}",
    }
    return send_line_message(summary_data, force=True)


if __name__ == "__main__":
    # テスト送信
    test_data = {
        "week":       "2026-W14",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "h1a":        25.5,
        "h4p20":      80.0,
        "h4p30":      40.0,
        "score":      52.3,
        "bars_h1":    38,
        "bars_h4":    10,
    }
    print("=== テスト通知 ===")
    send_line_message(test_data, force=True)
