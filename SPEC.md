# AI/個人開発ニュースアグリゲーター 要件定義・設計書

## 概要

AI・個人開発関連の情報を自動収集し、AIで要約・整理して表示する自分専用のニュースサイト。

## 要件

### 機能要件

1. **情報収集**
   - 複数ソースから記事/投稿を自動取得
   - 1日2-3回の定期実行
   - 可能な限り多くの記事を取得

2. **AI要約**
   - 各記事を日本語で1-2文に要約
   - 記事にタグを自動付与

3. **スコアリング・並び替え**
   - 興味キーワードに基づいてスコア算出
   - スコアが高い記事が上位に表示される
   - キーワードは設定ファイルで管理

4. **検索・フィルタ**
   - キーワード検索
   - ソース別フィルタ
   - タグ別フィルタ
   - 日付フィルタ

5. **表示**
   - 記事一覧（タイトル、要約、スコア、ソース、日時）
   - 元記事へのリンク
   - コメントページへのリンク（HN/Reddit）

### 非機能要件

- 完全無料で運用
- ユーザー認証不要（自分専用）
- ローカルLLMは使用しない
- GitHub Pages でホスティング

---

## 技術スタック

| レイヤー | 技術 | 理由 |
|---------|------|------|
| 定期実行 | GitHub Actions | 無料、cron設定が簡単 |
| スクリプト | Python | 標準ライブラリのみで実装可能 |
| AI要約 | Google Gemini API (gemini-1.5-flash) | 無料枠が大きい（100万トークン/日） |
| データ | JSON ファイル | DBなしで運用可能 |
| ホスティング | GitHub Pages | 無料、デプロイが簡単 |
| フロントエンド | 静的HTML + Vanilla JS | ビルド不要、シンプル |

---

## 情報ソース

| ソース | 取得方法 | 制限 |
|--------|----------|------|
| Hacker News | Firebase API | 無制限 |
| Reddit | JSON API (.json suffix) | レート制限あり（1req/sec推奨） |
| GitHub Trending | HTMLスクレイピング | 公式APIなし |

### 対象サブレディット
- r/MachineLearning
- r/LocalLLaMA
- r/SideProject
- r/artificial
- r/ClaudeAI

---

## ディレクトリ構成

```
ai-news-aggregator/
├── .github/
│   └── workflows/
│       └── fetch.yml           # GitHub Actions定期実行
├── scripts/
│   └── fetch_and_summarize.py  # メインスクリプト
├── docs/                       # GitHub Pages公開ディレクトリ
│   ├── index.html              # メインページ
│   ├── style.css               # スタイル
│   ├── app.js                  # 検索・フィルタロジック
│   └── data/
│       └── articles.json       # 生成された記事データ
├── config.json                 # 設定ファイル
├── requirements.txt            # Python依存（標準ライブラリのみなら不要）
└── README.md
```

---

## データ構造

### config.json

```json
{
  "interests": {
    "high": ["Claude", "Anthropic", "Claude Code", "cursor", "AI agent", "LLM", "MCP"],
    "medium": ["GPT", "OpenAI", "Gemini", "RAG", "embedding", "prompt engineering"],
    "low": ["machine learning", "deep learning", "open source", "startup"]
  },
  "score_weights": {
    "high": 10,
    "medium": 5,
    "low": 2
  },
  "sources": {
    "hackernews": {
      "enabled": true,
      "top_stories_count": 100
    },
    "reddit": {
      "enabled": true,
      "subreddits": ["MachineLearning", "LocalLLaMA", "SideProject", "artificial", "ClaudeAI"],
      "posts_per_subreddit": 25
    },
    "github_trending": {
      "enabled": true
    }
  },
  "gemini": {
    "model": "gemini-1.5-flash",
    "max_articles_per_run": 50
  }
}
```

### articles.json

```json
{
  "last_updated": "2025-01-30T12:00:00Z",
  "articles": [
    {
      "id": "abc123def456",
      "title": "記事タイトル",
      "url": "https://example.com/article",
      "source": "Hacker News",
      "source_score": 150,
      "comments_count": 42,
      "comments_url": "https://news.ycombinator.com/item?id=12345",
      "summary": "AIによる日本語要約文",
      "tags": ["LLM", "Claude"],
      "interest_score": 25,
      "matched_keywords": ["Claude", "AI agent"],
      "created_at": "2025-01-30T10:00:00Z",
      "fetched_at": "2025-01-30T12:00:00Z"
    }
  ]
}
```

---

## 処理フロー

### 1. 記事取得 (fetch)

```
1. config.json を読み込む
2. 各ソースから記事を取得
   - Hacker News: /v0/topstories.json → 各記事の詳細
   - Reddit: /r/{subreddit}/hot.json
   - GitHub: /trending ページをスクレイピング
3. 重複除去（URLベースでID生成）
4. 既存の articles.json と比較し、新規記事を抽出
```

### 2. 要約 (summarize)

```
1. 新規記事をバッチ化（10件ずつ）
2. Gemini API で要約・タグ付け
   - 入力: タイトル、URL、ソース
   - 出力: 日本語要約（1-2文）、タグ（2-3個）
3. API失敗時はスキップ（要約なしで保存）
```

### 3. スコアリング (score)

```
1. 各記事のタイトル・要約・タグを結合
2. config.json の interests キーワードとマッチング
3. マッチしたキーワードの重みを合算
4. interest_score と matched_keywords を記事に付与
```

### 4. 保存・デプロイ

```
1. 記事を interest_score 降順でソート
2. articles.json に書き出し
3. GitHub Actions が自動コミット・プッシュ
4. GitHub Pages が自動デプロイ
```

---

## フロントエンド仕様

### UI構成

```
+------------------------------------------+
|  AI News Aggregator           [検索ボックス] |
+------------------------------------------+
|  フィルタ: [All] [HN] [Reddit] [GitHub]     |
|  タグ: [LLM] [Claude] [個人開発] ...        |
+------------------------------------------+
|  📰 記事タイトル                    スコア:25 |
|  要約テキストがここに表示される...            |
|  🏷️ LLM, Claude  |  HN  |  2時間前  |  💬42 |
+------------------------------------------+
|  📰 次の記事...                            |
+------------------------------------------+
```

### 検索・フィルタ機能

| 機能 | 実装方法 |
|------|----------|
| キーワード検索 | タイトル・要約・タグを対象に部分一致 |
| ソースフィルタ | source フィールドでフィルタ |
| タグフィルタ | tags 配列に含まれるかチェック |
| 日付フィルタ | created_at でフィルタ（今日/今週/全期間） |

### ソート

- デフォルト: interest_score 降順
- オプション: 日時順、コメント数順、ソーススコア順

---

## GitHub Actions 設定

### .github/workflows/fetch.yml

```yaml
name: Fetch and Summarize

on:
  schedule:
    - cron: '0 0,8,16 * * *'  # UTC 0:00, 8:00, 16:00 (JST 9:00, 17:00, 1:00)
  workflow_dispatch:  # 手動実行用

jobs:
  fetch:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Run fetch script
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: python scripts/fetch_and_summarize.py
      
      - name: Commit and push
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add docs/data/articles.json
          git diff --staged --quiet || git commit -m "Update articles $(date -u +%Y-%m-%dT%H:%M:%SZ)"
          git push
```

---

## セットアップ手順

1. **リポジトリ作成**
   - GitHub で新規リポジトリ作成
   - このディレクトリ構成で初期化

2. **Gemini API キー取得**
   - https://aistudio.google.com/app/apikey でAPIキー発行
   - リポジトリの Settings > Secrets > Actions に `GEMINI_API_KEY` として登録

3. **GitHub Pages 有効化**
   - Settings > Pages
   - Source: Deploy from a branch
   - Branch: main, /docs

4. **初回実行**
   - Actions タブから手動実行（workflow_dispatch）
   - または `python scripts/fetch_and_summarize.py` をローカル実行

---

## 拡張案（将来）

- [ ] RSS フィード対応（技術ブログ等）
- [ ] Discordへの通知
- [ ] 記事の既読管理（LocalStorage）
- [ ] ダークモード
- [ ] 興味キーワードのUI編集
- [ ] 要約の品質向上（記事本文も取得）

---

## 制約・注意事項

- **Reddit API**: User-Agent必須、1リクエスト/秒を推奨
- **GitHub Trending**: 公式APIがないためHTMLパース（構造変更で壊れる可能性）
- **Gemini API無料枠**: 15 RPM、100万トークン/日（超過注意）
- **GitHub Actions**: パブリックリポジトリなら無制限、プライベートは月2000分
- **記事保持期間**: JSONが肥大化するため、古い記事は定期的に削除推奨（例: 7日以上前）
