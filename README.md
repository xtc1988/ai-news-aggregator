# AI News Aggregator

AI・個人開発関連の情報を自動収集し、AIで要約・整理して表示する自分専用のニュースサイト。

## 機能

- **自動情報収集**: Hacker News、Reddit、GitHub Trendingから記事を取得
- **AI要約**: Google Gemini APIで各記事を日本語要約
- **スコアリング**: 興味キーワードに基づいて自動スコア計算
- **検索・フィルタ**: キーワード検索、ソース別・タグ別・日付別フィルタ
- **完全無料**: GitHub Actions + GitHub Pages で運用

## 技術スタック

| レイヤー | 技術 | 理由 |
|---------|------|------|
| 定期実行 | GitHub Actions | 無料、cron設定が簡単 |
| スクリプト | Python | 標準ライブラリのみで実装可能 |
| AI要約 | Google Gemini API | 無料枠が大きい |
| データ | JSON ファイル | DBなしで運用可能 |
| ホスティング | GitHub Pages | 無料、デプロイが簡単 |
| フロントエンド | 静的HTML + Vanilla JS | ビルド不要、シンプル |

## ディレクトリ構成

```
AI-news-aggregater/
├── .github/
│   └── workflows/
│       └── fetch.yml           # GitHub Actions定期実行
├── scripts/
│   ├── fetch_and_summarize.py  # メインスクリプト
│   ├── fetchers/               # データ取得モジュール
│   │   ├── __init__.py
│   │   └── hackernews.py
│   └── tests/                  # テスト
├── docs/                       # GitHub Pages公開ディレクトリ
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   └── data/
│       └── articles.json
├── config.json                 # 設定ファイル
├── requirements.txt
├── SPEC.md                     # 要件定義・設計書
└── README.md
```

## セットアップ

### 1. リポジトリのフォーク/クローン

```bash
git clone https://github.com/yourusername/AI-news-aggregater.git
cd AI-news-aggregater
```

### 2. Gemini API キーの取得

1. [Google AI Studio](https://aistudio.google.com/app/apikey) でAPIキーを発行
2. リポジトリの Settings > Secrets and variables > Actions に移動
3. `GEMINI_API_KEY` という名前でシークレットを登録

### 3. GitHub Pages の有効化

1. リポジトリの Settings > Pages に移動
2. Source: **Deploy from a branch**
3. Branch: **main**, folder: **/docs**
4. Saveをクリック

### 4. 初回実行

#### 手動実行（GitHub Actions）
1. Actions タブを開く
2. "Fetch and Summarize" ワークフローを選択
3. "Run workflow" をクリック

#### ローカル実行
```bash
# 環境変数を設定
export GEMINI_API_KEY="your-api-key"

# スクリプト実行
python scripts/fetch_and_summarize.py
```

## 設定

### config.json

```json
{
  "interests": {
    "high": ["Claude", "Anthropic", "AI agent", "LLM"],
    "medium": ["GPT", "OpenAI", "RAG"],
    "low": ["machine learning", "startup"]
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
      "subreddits": ["MachineLearning", "LocalLLaMA", "ClaudeAI"],
      "posts_per_subreddit": 25
    },
    "github_trending": {
      "enabled": true
    }
  },
  "gemini": {
    "model": "gemini-1.5-flash",
    "max_articles_per_run": 50
  },
  "retention_days": 7
}
```

### 興味キーワードのカスタマイズ

`interests` セクションを編集して、自分の興味に合わせたキーワードを設定できます。

- `high`: 最も興味のあるキーワード（スコア+10）
- `medium`: 中程度の興味（スコア+5）
- `low`: 軽い興味（スコア+2）

## 定期実行スケジュール

デフォルトでは1日3回実行されます（UTC時間）:

- 0:00 (JST 9:00)
- 8:00 (JST 17:00)
- 16:00 (JST 翌1:00)

`.github/workflows/fetch.yml` の cron 設定を変更して調整できます。

## 情報ソース

| ソース | 取得方法 | 備考 |
|--------|----------|------|
| Hacker News | Firebase API | 無制限 |
| Reddit | JSON API | レート制限あり |
| GitHub Trending | HTMLスクレイピング | 構造変更で壊れる可能性あり |

## 注意事項

- **Gemini API無料枠**: 15 RPM、100万トークン/日
- **GitHub Actions**: パブリックリポジトリは無制限、プライベートは月2000分
- **記事保持期間**: `retention_days` で設定（デフォルト7日）

## ライセンス

MIT License

## 貢献

Issue や Pull Request は歓迎します。
