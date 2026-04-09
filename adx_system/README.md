# ADX Monitor — セットアップガイド

XAUUSD ADXスコアをリアルタイム監視し、LINE通知とWebダッシュボードで確認できるシステムです。

---

## ファイル構成

```
your-repo/
├── .github/
│   └── workflows/
│       └── adx_monitor.yml     ← GitHub Actions（毎時実行）
├── data/                        ← 自動生成（コミット不要）
│   ├── adx_live.json
│   ├── adx_history.json
│   └── adx_state.json
├── adx_calculator.py            ← ADX計算エンジン
├── line_bot.py                  ← LINE通知
├── update_dashboard.py          ← メイン実行スクリプト
├── requirements.txt
└── index.html                   ← ダッシュボード（GitHub Pages）
```

---

## セットアップ手順

### 1. GitHubリポジトリ作成

```bash
# 新しいリポジトリを作成（Private OK）
git init adx-monitor
cd adx-monitor
# 全ファイルをコピーして
git add .
git commit -m "Initial setup"
git remote add origin https://github.com/あなたのユーザー名/adx-monitor.git
git push -u origin main
```

### 2. GitHub Pages 有効化

1. リポジトリ → **Settings** → **Pages**
2. Source: **Deploy from a branch**
3. Branch: `main` / folder: `/ (root)`
4. Save → URLが発行される（例: `https://username.github.io/adx-monitor/`）

### 3. LINE Messaging API 設定

#### LINE Developers でBotを作る

1. https://developers.line.biz/ にアクセス
2. **新しいプロバイダー** を作成
3. **Messaging API チャネル** を作成
4. チャネル設定 → **Messaging API** タブ
5. **チャネルアクセストークン（長期）** を発行 → コピー

#### 自分のLINEをBotと友達にする

- チャネル設定の **QRコード** をスキャン → 友達追加

#### ブロードキャストをオンにする（友達全員に通知）

- または **User ID** を取得してプッシュ送信でもOK

### 4. GitHub Secrets にトークンを登録

1. リポジトリ → **Settings** → **Secrets and variables** → **Actions**
2. **New repository secret** をクリック
3. Name: `LINE_CHANNEL_ACCESS_TOKEN`
4. Value: コピーしたトークンをペースト
5. **Add secret**

### 5. GitHub Actions を有効化

1. リポジトリ → **Actions** タブ
2. **I understand my workflows, go ahead and enable them**
3. `ADX Monitor` ワークフローが表示される
4. **Run workflow** → **Run workflow** で手動テスト実行

---

## 動作確認チェックリスト

- [ ] Actions → 最初の手動実行が成功
- [ ] `data/adx_live.json` がコミットされる
- [ ] `data/adx_history.json` がコミットされる
- [ ] GitHub Pages の URL でダッシュボードが表示される
- [ ] LINEにテスト通知が届く（score≥45のときのみ）

---

## 通知閾値の変更

`update_dashboard.py` の以下の行を変更:

```python
# デフォルト: スコア≥45で通知
if score is not None and score >= 45:
```

`line_bot.py` の以下の行も変更:

```python
if not force and (score is None or score < 45):
```

---

## よくあるエラー

| エラー | 原因 | 対処 |
|--------|------|------|
| `LINE送信失敗: 401` | トークンが間違い | Secrets を再確認 |
| `yfinance エラー` | 市場クローズ時 | 翌営業日に再実行 |
| `Permission denied` | Actions権限不足 | repo Settings → Actions → Workflow permissions → Read and write |
| データが空 | 週末・祝日 | 正常（バーが少ないとスキップ） |

---

## カスタマイズ

### 複数銘柄追加（EURUSD等）

`adx_calculator.py` の `SYMBOL` を変更、または複数を並列実行。

### MT5連動（Phase 2）

MT5のEA → HTTPでこのシステムのAPIを叩く or CSVに書き出してActionsが読み込む形で連動可能。

---

## コスト

| 項目 | コスト |
|------|--------|
| GitHub Actions | **無料** (public repo) / 月2000分 (private) |
| GitHub Pages | **無料** |
| LINE Messaging API | **無料** (月200通まで broadcast) |
| yfinance | **無料** |
| **合計** | **¥0** |
