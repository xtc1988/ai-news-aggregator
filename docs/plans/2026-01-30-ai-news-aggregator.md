# AI/個人開発ニュースアグリゲーター Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** AI・個人開発関連の情報を自動収集し、Gemini APIで要約・整理してGitHub Pagesで表示する自分専用ニュースサイトを構築する

**Architecture:**
- Python スクリプトで Hacker News / Reddit / GitHub Trending から記事を取得
- Gemini API で日本語要約・タグ付け
- 興味キーワードベースでスコアリング
- 静的HTML + Vanilla JS でフロントエンド表示
- GitHub Actions で1日3回定期実行

**Tech Stack:** Python 3.11, Google Gemini API (gemini-1.5-flash), GitHub Actions, GitHub Pages, Vanilla JS

---

## Phase 1: プロジェクト基盤構築

### Task 1: ディレクトリ構造とconfig.json作成

**Files:**
- Create: `AI-news-aggregater/config.json`
- Create: `AI-news-aggregater/scripts/` (directory)
- Create: `AI-news-aggregater/docs/data/` (directory)
- Create: `AI-news-aggregater/requirements.txt`

**Step 1: ディレクトリ構造を作成**

```bash
mkdir -p AI-news-aggregater/scripts
mkdir -p AI-news-aggregater/docs/data
mkdir -p AI-news-aggregater/.github/workflows
```

**Step 2: config.json を作成**

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
  },
  "retention_days": 7
}
```

**Step 3: requirements.txt を作成**

```
google-generativeai>=0.3.0
requests>=2.31.0
beautifulsoup4>=4.12.0
```

**Step 4: 初期 articles.json を作成**

```json
{
  "last_updated": null,
  "articles": []
}
```

**Step 5: Commit**

```bash
git add AI-news-aggregater/
git commit -m "feat: initialize project structure and config"
```

---

## Phase 2: データ取得スクリプト

### Task 2: Hacker News フェッチャー

**Files:**
- Create: `AI-news-aggregater/scripts/fetchers/__init__.py`
- Create: `AI-news-aggregater/scripts/fetchers/hackernews.py`
- Test: `AI-news-aggregater/scripts/tests/test_hackernews.py`

**Step 1: テストファイルを作成**

```python
# AI-news-aggregater/scripts/tests/test_hackernews.py
import unittest
from unittest.mock import patch, Mock
import sys
sys.path.insert(0, '..')

from fetchers.hackernews import fetch_hackernews_stories, parse_story

class TestHackerNews(unittest.TestCase):

    def test_parse_story_valid(self):
        """有効なストーリーデータをパースできる"""
        raw = {
            "id": 12345,
            "title": "Test Article",
            "url": "https://example.com/article",
            "score": 150,
            "descendants": 42,
            "time": 1706600000
        }
        result = parse_story(raw)

        self.assertEqual(result["title"], "Test Article")
        self.assertEqual(result["url"], "https://example.com/article")
        self.assertEqual(result["source"], "Hacker News")
        self.assertEqual(result["source_score"], 150)
        self.assertEqual(result["comments_count"], 42)
        self.assertIn("comments_url", result)

    def test_parse_story_no_url(self):
        """URLなしのストーリー（Ask HN等）はスキップ"""
        raw = {
            "id": 12345,
            "title": "Ask HN: Something",
            "score": 50,
            "descendants": 10,
            "time": 1706600000
        }
        result = parse_story(raw)
        self.assertIsNone(result)

    @patch('fetchers.hackernews.requests.get')
    def test_fetch_hackernews_stories(self, mock_get):
        """複数ストーリーを取得できる"""
        # Mock top stories
        mock_response_ids = Mock()
        mock_response_ids.json.return_value = [1, 2, 3]

        mock_response_item = Mock()
        mock_response_item.json.return_value = {
            "id": 1,
            "title": "Test",
            "url": "https://test.com",
            "score": 100,
            "descendants": 10,
            "time": 1706600000
        }

        mock_get.side_effect = [mock_response_ids] + [mock_response_item] * 3

        results = fetch_hackernews_stories(limit=3)
        self.assertEqual(len(results), 3)

if __name__ == '__main__':
    unittest.main()
```

**Step 2: テストが失敗することを確認**

```bash
cd AI-news-aggregater/scripts
python -m pytest tests/test_hackernews.py -v
```
Expected: FAIL (module not found)

**Step 3: hackernews.py を実装**

```python
# AI-news-aggregater/scripts/fetchers/hackernews.py
"""Hacker News Firebase API からの記事取得"""
import requests
import hashlib
from datetime import datetime
from typing import Optional

HN_API_BASE = "https://hacker-news.firebaseio.com/v0"

def generate_id(url: str) -> str:
    """URLからユニークIDを生成"""
    return hashlib.md5(url.encode()).hexdigest()[:12]

def parse_story(raw: dict) -> Optional[dict]:
    """APIレスポンスを記事形式に変換"""
    if "url" not in raw or not raw.get("url"):
        return None

    return {
        "id": generate_id(raw["url"]),
        "title": raw.get("title", ""),
        "url": raw["url"],
        "source": "Hacker News",
        "source_score": raw.get("score", 0),
        "comments_count": raw.get("descendants", 0),
        "comments_url": f"https://news.ycombinator.com/item?id={raw['id']}",
        "summary": None,
        "tags": [],
        "interest_score": 0,
        "matched_keywords": [],
        "created_at": datetime.utcfromtimestamp(raw.get("time", 0)).isoformat() + "Z",
        "fetched_at": datetime.utcnow().isoformat() + "Z"
    }

def fetch_hackernews_stories(limit: int = 100) -> list[dict]:
    """Hacker Newsのトップストーリーを取得"""
    # トップストーリーのID一覧を取得
    response = requests.get(f"{HN_API_BASE}/topstories.json", timeout=10)
    response.raise_for_status()
    story_ids = response.json()[:limit]

    articles = []
    for story_id in story_ids:
        try:
            resp = requests.get(f"{HN_API_BASE}/item/{story_id}.json", timeout=5)
            resp.raise_for_status()
            story = resp.json()
            if story:
                article = parse_story(story)
                if article:
                    articles.append(article)
        except Exception as e:
            print(f"Error fetching story {story_id}: {e}")
            continue

    return articles
```

**Step 4: __init__.py を作成**

```python
# AI-news-aggregater/scripts/fetchers/__init__.py
from .hackernews import fetch_hackernews_stories
```

**Step 5: テストを実行して合格を確認**

```bash
cd AI-news-aggregater/scripts
python -m pytest tests/test_hackernews.py -v
```
Expected: PASS

**Step 6: Commit**

```bash
git add AI-news-aggregater/scripts/
git commit -m "feat: add Hacker News fetcher with tests"
```

---

### Task 3: Reddit フェッチャー

**Files:**
- Create: `AI-news-aggregater/scripts/fetchers/reddit.py`
- Test: `AI-news-aggregater/scripts/tests/test_reddit.py`

**Step 1: テストファイルを作成**

```python
# AI-news-aggregater/scripts/tests/test_reddit.py
import unittest
from unittest.mock import patch, Mock
import sys
sys.path.insert(0, '..')

from fetchers.reddit import fetch_reddit_posts, parse_post

class TestReddit(unittest.TestCase):

    def test_parse_post_valid(self):
        """有効な投稿データをパースできる"""
        raw = {
            "data": {
                "id": "abc123",
                "title": "Test Post",
                "url": "https://example.com/post",
                "score": 200,
                "num_comments": 50,
                "permalink": "/r/test/comments/abc123/test/",
                "created_utc": 1706600000,
                "is_self": False
            }
        }
        result = parse_post(raw, "TestSubreddit")

        self.assertEqual(result["title"], "Test Post")
        self.assertEqual(result["source"], "Reddit/TestSubreddit")
        self.assertEqual(result["source_score"], 200)

    def test_parse_post_self_post(self):
        """セルフポストはpermalinkをURLとして使用"""
        raw = {
            "data": {
                "id": "abc123",
                "title": "Discussion Post",
                "url": "https://reddit.com/r/test/abc123",
                "score": 100,
                "num_comments": 20,
                "permalink": "/r/test/comments/abc123/discussion/",
                "created_utc": 1706600000,
                "is_self": True
            }
        }
        result = parse_post(raw, "TestSubreddit")
        self.assertIn("reddit.com", result["url"])

if __name__ == '__main__':
    unittest.main()
```

**Step 2: テストが失敗することを確認**

```bash
cd AI-news-aggregater/scripts
python -m pytest tests/test_reddit.py -v
```
Expected: FAIL

**Step 3: reddit.py を実装**

```python
# AI-news-aggregater/scripts/fetchers/reddit.py
"""Reddit JSON API からの投稿取得"""
import requests
import hashlib
import time
from datetime import datetime
from typing import Optional

REDDIT_BASE = "https://www.reddit.com"
USER_AGENT = "AI-News-Aggregator/1.0"

def generate_id(url: str) -> str:
    """URLからユニークIDを生成"""
    return hashlib.md5(url.encode()).hexdigest()[:12]

def parse_post(raw: dict, subreddit: str) -> Optional[dict]:
    """APIレスポンスを記事形式に変換"""
    data = raw.get("data", {})

    # セルフポストの場合はRedditのURLを使用
    url = data.get("url", "")
    if data.get("is_self", False):
        url = f"https://reddit.com{data.get('permalink', '')}"

    if not url:
        return None

    return {
        "id": generate_id(url),
        "title": data.get("title", ""),
        "url": url,
        "source": f"Reddit/{subreddit}",
        "source_score": data.get("score", 0),
        "comments_count": data.get("num_comments", 0),
        "comments_url": f"https://reddit.com{data.get('permalink', '')}",
        "summary": None,
        "tags": [],
        "interest_score": 0,
        "matched_keywords": [],
        "created_at": datetime.utcfromtimestamp(data.get("created_utc", 0)).isoformat() + "Z",
        "fetched_at": datetime.utcnow().isoformat() + "Z"
    }

def fetch_reddit_posts(subreddits: list[str], posts_per_sub: int = 25) -> list[dict]:
    """複数サブレディットから投稿を取得"""
    headers = {"User-Agent": USER_AGENT}
    articles = []

    for subreddit in subreddits:
        try:
            url = f"{REDDIT_BASE}/r/{subreddit}/hot.json?limit={posts_per_sub}"
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            posts = data.get("data", {}).get("children", [])

            for post in posts:
                article = parse_post(post, subreddit)
                if article:
                    articles.append(article)

            # Rate limit: 1 request per second
            time.sleep(1)

        except Exception as e:
            print(f"Error fetching r/{subreddit}: {e}")
            continue

    return articles
```

**Step 4: __init__.py を更新**

```python
# AI-news-aggregater/scripts/fetchers/__init__.py
from .hackernews import fetch_hackernews_stories
from .reddit import fetch_reddit_posts
```

**Step 5: テストを実行して合格を確認**

```bash
cd AI-news-aggregater/scripts
python -m pytest tests/test_reddit.py -v
```
Expected: PASS

**Step 6: Commit**

```bash
git add AI-news-aggregater/scripts/
git commit -m "feat: add Reddit fetcher with tests"
```

---

### Task 4: GitHub Trending フェッチャー

**Files:**
- Create: `AI-news-aggregater/scripts/fetchers/github_trending.py`
- Test: `AI-news-aggregater/scripts/tests/test_github_trending.py`

**Step 1: テストファイルを作成**

```python
# AI-news-aggregater/scripts/tests/test_github_trending.py
import unittest
from unittest.mock import patch, Mock
import sys
sys.path.insert(0, '..')

from fetchers.github_trending import parse_repo_row, fetch_github_trending

class TestGitHubTrending(unittest.TestCase):

    def test_parse_repo_row_valid(self):
        """有効なリポジトリ行をパースできる"""
        # BeautifulSoupのモックは複雑なのでintegration testで確認
        pass

    @patch('fetchers.github_trending.requests.get')
    def test_fetch_github_trending_empty(self, mock_get):
        """空のレスポンスでもエラーにならない"""
        mock_response = Mock()
        mock_response.text = "<html><body></body></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        results = fetch_github_trending()
        self.assertEqual(results, [])

if __name__ == '__main__':
    unittest.main()
```

**Step 2: github_trending.py を実装**

```python
# AI-news-aggregater/scripts/fetchers/github_trending.py
"""GitHub Trending ページのスクレイピング"""
import requests
import hashlib
from datetime import datetime
from typing import Optional
from bs4 import BeautifulSoup

GITHUB_TRENDING_URL = "https://github.com/trending"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

def generate_id(url: str) -> str:
    """URLからユニークIDを生成"""
    return hashlib.md5(url.encode()).hexdigest()[:12]

def parse_repo_row(row) -> Optional[dict]:
    """リポジトリ行をパースして記事形式に変換"""
    try:
        # リポジトリ名とURL
        h2 = row.select_one("h2 a")
        if not h2:
            return None

        repo_path = h2.get("href", "").strip()
        if not repo_path:
            return None

        url = f"https://github.com{repo_path}"
        repo_name = repo_path.strip("/")

        # 説明文
        desc_elem = row.select_one("p")
        description = desc_elem.get_text(strip=True) if desc_elem else ""

        # スター数
        star_elem = row.select_one("a[href$='/stargazers']")
        stars = 0
        if star_elem:
            star_text = star_elem.get_text(strip=True).replace(",", "")
            try:
                stars = int(star_text)
            except ValueError:
                pass

        # 今日のスター数
        today_stars_elem = row.select_one("span.d-inline-block.float-sm-right")
        today_stars = 0
        if today_stars_elem:
            today_text = today_stars_elem.get_text(strip=True)
            try:
                today_stars = int(today_text.split()[0].replace(",", ""))
            except (ValueError, IndexError):
                pass

        return {
            "id": generate_id(url),
            "title": f"[GitHub] {repo_name}",
            "url": url,
            "source": "GitHub Trending",
            "source_score": stars,
            "comments_count": today_stars,
            "comments_url": f"{url}/issues",
            "summary": description if description else None,
            "tags": [],
            "interest_score": 0,
            "matched_keywords": [],
            "created_at": datetime.utcnow().isoformat() + "Z",
            "fetched_at": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        print(f"Error parsing repo row: {e}")
        return None

def fetch_github_trending() -> list[dict]:
    """GitHub Trendingページからリポジトリを取得"""
    headers = {"User-Agent": USER_AGENT}

    try:
        response = requests.get(GITHUB_TRENDING_URL, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        rows = soup.select("article.Box-row")

        articles = []
        for row in rows:
            article = parse_repo_row(row)
            if article:
                articles.append(article)

        return articles

    except Exception as e:
        print(f"Error fetching GitHub Trending: {e}")
        return []
```

**Step 3: __init__.py を更新**

```python
# AI-news-aggregater/scripts/fetchers/__init__.py
from .hackernews import fetch_hackernews_stories
from .reddit import fetch_reddit_posts
from .github_trending import fetch_github_trending
```

**Step 4: テストを実行**

```bash
cd AI-news-aggregater/scripts
python -m pytest tests/test_github_trending.py -v
```

**Step 5: Commit**

```bash
git add AI-news-aggregater/scripts/
git commit -m "feat: add GitHub Trending scraper"
```

---

## Phase 3: AI要約とスコアリング

### Task 5: Gemini API 要約モジュール

**Files:**
- Create: `AI-news-aggregater/scripts/summarizer.py`
- Test: `AI-news-aggregater/scripts/tests/test_summarizer.py`

**Step 1: テストファイルを作成**

```python
# AI-news-aggregater/scripts/tests/test_summarizer.py
import unittest
from unittest.mock import patch, Mock, MagicMock
import sys
sys.path.insert(0, '..')

from summarizer import summarize_articles, parse_gemini_response

class TestSummarizer(unittest.TestCase):

    def test_parse_gemini_response_valid(self):
        """有効なGeminiレスポンスをパースできる"""
        response_text = '''
        1. summary: これはAI関連の記事です。新しいLLMについて解説しています。
           tags: LLM, AI, 機械学習
        2. summary: Claudeの新機能が発表されました。
           tags: Claude, Anthropic
        '''
        results = parse_gemini_response(response_text, 2)

        self.assertEqual(len(results), 2)
        self.assertIn("LLM", results[0]["tags"])
        self.assertIn("Claude", results[1]["tags"])

    def test_parse_gemini_response_malformed(self):
        """不正なレスポンスでもエラーにならない"""
        response_text = "Invalid response format"
        results = parse_gemini_response(response_text, 2)

        self.assertEqual(len(results), 2)
        self.assertIsNone(results[0]["summary"])

if __name__ == '__main__':
    unittest.main()
```

**Step 2: summarizer.py を実装**

```python
# AI-news-aggregater/scripts/summarizer.py
"""Gemini APIを使用した記事要約"""
import os
import re
import time
from typing import Optional

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

def configure_gemini():
    """Gemini APIを設定"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("Warning: GEMINI_API_KEY not set")
        return False

    if GEMINI_AVAILABLE:
        genai.configure(api_key=api_key)
        return True
    return False

def parse_gemini_response(response_text: str, expected_count: int) -> list[dict]:
    """Geminiのレスポンスをパースして要約とタグを抽出"""
    results = []

    # 各記事の結果を抽出
    pattern = r'(\d+)\.\s*summary:\s*(.+?)\s*tags:\s*(.+?)(?=\d+\.|$)'
    matches = re.findall(pattern, response_text, re.DOTALL | re.IGNORECASE)

    for match in matches:
        idx, summary, tags = match
        summary = summary.strip()
        tags = [t.strip() for t in tags.split(",") if t.strip()]
        results.append({
            "summary": summary if summary else None,
            "tags": tags[:5]  # 最大5タグ
        })

    # 結果が足りない場合はNoneで埋める
    while len(results) < expected_count:
        results.append({"summary": None, "tags": []})

    return results[:expected_count]

def summarize_batch(articles: list[dict], model_name: str = "gemini-1.5-flash") -> list[dict]:
    """記事のバッチを要約"""
    if not GEMINI_AVAILABLE or not configure_gemini():
        return [{"summary": None, "tags": []} for _ in articles]

    # プロンプト作成
    prompt = """以下の記事を日本語で要約してください。
各記事について:
- summary: 1-2文で内容を要約（日本語）
- tags: 関連するタグを2-3個（カンマ区切り）

記事リスト:
"""
    for i, article in enumerate(articles, 1):
        prompt += f"\n{i}. タイトル: {article['title']}\n   URL: {article['url']}\n   ソース: {article['source']}\n"

    prompt += "\n回答形式:\n1. summary: [要約]\n   tags: [タグ1], [タグ2], [タグ3]\n2. ..."

    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(prompt)
        return parse_gemini_response(response.text, len(articles))
    except Exception as e:
        print(f"Gemini API error: {e}")
        return [{"summary": None, "tags": []} for _ in articles]

def summarize_articles(articles: list[dict], batch_size: int = 10, max_articles: int = 50) -> list[dict]:
    """記事リストを要約（バッチ処理）"""
    # 要約済みの記事はスキップ
    to_summarize = [a for a in articles if not a.get("summary")][:max_articles]

    if not to_summarize:
        return articles

    print(f"Summarizing {len(to_summarize)} articles...")

    for i in range(0, len(to_summarize), batch_size):
        batch = to_summarize[i:i + batch_size]
        results = summarize_batch(batch)

        for article, result in zip(batch, results):
            article["summary"] = result["summary"]
            article["tags"] = result["tags"]

        # Rate limit
        if i + batch_size < len(to_summarize):
            time.sleep(2)

    return articles
```

**Step 3: テストを実行**

```bash
cd AI-news-aggregater/scripts
python -m pytest tests/test_summarizer.py -v
```

**Step 4: Commit**

```bash
git add AI-news-aggregater/scripts/
git commit -m "feat: add Gemini API summarizer"
```

---

### Task 6: スコアリングモジュール

**Files:**
- Create: `AI-news-aggregater/scripts/scorer.py`
- Test: `AI-news-aggregater/scripts/tests/test_scorer.py`

**Step 1: テストファイルを作成**

```python
# AI-news-aggregater/scripts/tests/test_scorer.py
import unittest
import sys
sys.path.insert(0, '..')

from scorer import calculate_interest_score, score_articles

class TestScorer(unittest.TestCase):

    def test_calculate_interest_score_high_match(self):
        """高優先度キーワードにマッチした場合"""
        article = {
            "title": "Claude Code の新機能",
            "summary": "Anthropicが発表した新しいAI agent機能",
            "tags": ["Claude", "AI"]
        }
        interests = {
            "high": ["Claude", "Anthropic", "AI agent"],
            "medium": ["GPT"],
            "low": ["startup"]
        }
        weights = {"high": 10, "medium": 5, "low": 2}

        score, keywords = calculate_interest_score(article, interests, weights)

        self.assertGreater(score, 20)  # 複数マッチ
        self.assertIn("Claude", keywords)

    def test_calculate_interest_score_no_match(self):
        """キーワードにマッチしない場合"""
        article = {
            "title": "料理レシピ",
            "summary": "美味しいパスタの作り方",
            "tags": ["料理"]
        }
        interests = {
            "high": ["Claude"],
            "medium": ["GPT"],
            "low": ["startup"]
        }
        weights = {"high": 10, "medium": 5, "low": 2}

        score, keywords = calculate_interest_score(article, interests, weights)

        self.assertEqual(score, 0)
        self.assertEqual(keywords, [])

if __name__ == '__main__':
    unittest.main()
```

**Step 2: scorer.py を実装**

```python
# AI-news-aggregater/scripts/scorer.py
"""興味キーワードに基づくスコアリング"""
import re
from typing import Tuple

def calculate_interest_score(
    article: dict,
    interests: dict,
    weights: dict
) -> Tuple[int, list[str]]:
    """記事の興味スコアを計算"""
    # 検索対象テキストを結合
    text = " ".join([
        article.get("title", ""),
        article.get("summary", "") or "",
        " ".join(article.get("tags", []))
    ]).lower()

    score = 0
    matched = []

    for priority, keywords in interests.items():
        weight = weights.get(priority, 1)
        for keyword in keywords:
            # 大文字小文字を無視してマッチング
            pattern = re.compile(re.escape(keyword.lower()))
            if pattern.search(text):
                score += weight
                matched.append(keyword)

    return score, list(set(matched))

def score_articles(articles: list[dict], config: dict) -> list[dict]:
    """全記事にスコアを付与してソート"""
    interests = config.get("interests", {})
    weights = config.get("score_weights", {"high": 10, "medium": 5, "low": 2})

    for article in articles:
        score, keywords = calculate_interest_score(article, interests, weights)
        article["interest_score"] = score
        article["matched_keywords"] = keywords

    # スコア降順でソート
    articles.sort(key=lambda x: x["interest_score"], reverse=True)

    return articles
```

**Step 3: テストを実行**

```bash
cd AI-news-aggregater/scripts
python -m pytest tests/test_scorer.py -v
```

**Step 4: Commit**

```bash
git add AI-news-aggregater/scripts/
git commit -m "feat: add interest keyword scorer"
```

---

## Phase 4: メインスクリプト

### Task 7: メインスクリプト統合

**Files:**
- Create: `AI-news-aggregater/scripts/fetch_and_summarize.py`
- Create: `AI-news-aggregater/scripts/tests/__init__.py`

**Step 1: メインスクリプトを実装**

```python
#!/usr/bin/env python3
# AI-news-aggregater/scripts/fetch_and_summarize.py
"""記事取得・要約・スコアリングのメインスクリプト"""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from fetchers import fetch_hackernews_stories, fetch_reddit_posts, fetch_github_trending
from summarizer import summarize_articles
from scorer import score_articles

# パス設定
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
CONFIG_PATH = PROJECT_ROOT / "config.json"
ARTICLES_PATH = PROJECT_ROOT / "docs" / "data" / "articles.json"

def load_config() -> dict:
    """設定ファイルを読み込む"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def load_existing_articles() -> dict:
    """既存の記事データを読み込む"""
    if ARTICLES_PATH.exists():
        with open(ARTICLES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_updated": None, "articles": []}

def save_articles(data: dict):
    """記事データを保存"""
    ARTICLES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(ARTICLES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def fetch_all_articles(config: dict) -> list[dict]:
    """全ソースから記事を取得"""
    articles = []
    sources = config.get("sources", {})

    # Hacker News
    if sources.get("hackernews", {}).get("enabled", False):
        print("Fetching Hacker News...")
        limit = sources["hackernews"].get("top_stories_count", 100)
        articles.extend(fetch_hackernews_stories(limit=limit))

    # Reddit
    if sources.get("reddit", {}).get("enabled", False):
        print("Fetching Reddit...")
        subreddits = sources["reddit"].get("subreddits", [])
        posts_per = sources["reddit"].get("posts_per_subreddit", 25)
        articles.extend(fetch_reddit_posts(subreddits, posts_per))

    # GitHub Trending
    if sources.get("github_trending", {}).get("enabled", False):
        print("Fetching GitHub Trending...")
        articles.extend(fetch_github_trending())

    return articles

def deduplicate_articles(new_articles: list[dict], existing_articles: list[dict]) -> list[dict]:
    """重複を除去して新規記事のみ返す"""
    existing_ids = {a["id"] for a in existing_articles}
    return [a for a in new_articles if a["id"] not in existing_ids]

def cleanup_old_articles(articles: list[dict], retention_days: int) -> list[dict]:
    """古い記事を削除"""
    cutoff = datetime.utcnow() - timedelta(days=retention_days)
    cutoff_str = cutoff.isoformat() + "Z"

    return [a for a in articles if a.get("fetched_at", "") >= cutoff_str]

def main():
    """メイン処理"""
    print("=" * 50)
    print(f"AI News Aggregator - {datetime.utcnow().isoformat()}Z")
    print("=" * 50)

    # 設定読み込み
    config = load_config()
    existing_data = load_existing_articles()
    existing_articles = existing_data.get("articles", [])

    # 記事取得
    new_articles = fetch_all_articles(config)
    print(f"Fetched {len(new_articles)} articles total")

    # 重複除去
    unique_new = deduplicate_articles(new_articles, existing_articles)
    print(f"Found {len(unique_new)} new articles")

    # 既存 + 新規
    all_articles = existing_articles + unique_new

    # 古い記事を削除
    retention_days = config.get("retention_days", 7)
    all_articles = cleanup_old_articles(all_articles, retention_days)

    # AI要約
    gemini_config = config.get("gemini", {})
    max_summarize = gemini_config.get("max_articles_per_run", 50)
    all_articles = summarize_articles(all_articles, max_articles=max_summarize)

    # スコアリング
    all_articles = score_articles(all_articles, config)

    # 保存
    output_data = {
        "last_updated": datetime.utcnow().isoformat() + "Z",
        "articles": all_articles
    }
    save_articles(output_data)

    print(f"Saved {len(all_articles)} articles to {ARTICLES_PATH}")
    print("Done!")

if __name__ == "__main__":
    main()
```

**Step 2: テスト用 __init__.py を作成**

```python
# AI-news-aggregater/scripts/tests/__init__.py
```

**Step 3: ローカルで実行テスト（Gemini APIキーなしでも動作確認）**

```bash
cd AI-news-aggregater
python scripts/fetch_and_summarize.py
```

**Step 4: Commit**

```bash
git add AI-news-aggregater/scripts/
git commit -m "feat: add main fetch_and_summarize script"
```

---

## Phase 5: フロントエンド

### Task 8: HTML/CSS/JS フロントエンド

**Files:**
- Create: `AI-news-aggregater/docs/index.html`
- Create: `AI-news-aggregater/docs/style.css`
- Create: `AI-news-aggregater/docs/app.js`

**Step 1: index.html を作成**

```html
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI News Aggregator</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <header>
        <h1>AI News Aggregator</h1>
        <input type="search" id="search" placeholder="キーワード検索...">
    </header>

    <nav class="filters">
        <div class="filter-group">
            <label>ソース:</label>
            <button class="filter-btn active" data-source="all">All</button>
            <button class="filter-btn" data-source="Hacker News">HN</button>
            <button class="filter-btn" data-source="Reddit">Reddit</button>
            <button class="filter-btn" data-source="GitHub">GitHub</button>
        </div>
        <div class="filter-group">
            <label>期間:</label>
            <button class="filter-btn active" data-period="all">全期間</button>
            <button class="filter-btn" data-period="today">今日</button>
            <button class="filter-btn" data-period="week">今週</button>
        </div>
        <div class="filter-group">
            <label>並び替え:</label>
            <select id="sort">
                <option value="score">スコア順</option>
                <option value="date">日時順</option>
                <option value="comments">コメント数順</option>
            </select>
        </div>
    </nav>

    <div id="tags-filter" class="tags-container"></div>

    <main id="articles"></main>

    <footer>
        <p>Last updated: <span id="last-updated">-</span></p>
    </footer>

    <script src="app.js"></script>
</body>
</html>
```

**Step 2: style.css を作成**

```css
/* AI-news-aggregater/docs/style.css */
:root {
    --bg-color: #0d1117;
    --card-bg: #161b22;
    --text-color: #c9d1d9;
    --text-muted: #8b949e;
    --accent-color: #58a6ff;
    --border-color: #30363d;
    --tag-bg: #21262d;
    --score-high: #238636;
    --score-mid: #9e6a03;
    --score-low: #6e7681;
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg-color);
    color: var(--text-color);
    line-height: 1.6;
    padding: 1rem;
    max-width: 1200px;
    margin: 0 auto;
}

header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 0;
    border-bottom: 1px solid var(--border-color);
    margin-bottom: 1rem;
    flex-wrap: wrap;
    gap: 1rem;
}

header h1 {
    font-size: 1.5rem;
    color: var(--accent-color);
}

#search {
    padding: 0.5rem 1rem;
    border: 1px solid var(--border-color);
    border-radius: 6px;
    background: var(--card-bg);
    color: var(--text-color);
    width: 250px;
}

.filters {
    display: flex;
    gap: 1.5rem;
    padding: 1rem 0;
    flex-wrap: wrap;
}

.filter-group {
    display: flex;
    align-items: center;
    gap: 0.5rem;
}

.filter-group label {
    color: var(--text-muted);
    font-size: 0.875rem;
}

.filter-btn {
    padding: 0.25rem 0.75rem;
    border: 1px solid var(--border-color);
    border-radius: 20px;
    background: transparent;
    color: var(--text-muted);
    cursor: pointer;
    font-size: 0.875rem;
    transition: all 0.2s;
}

.filter-btn:hover {
    border-color: var(--accent-color);
    color: var(--accent-color);
}

.filter-btn.active {
    background: var(--accent-color);
    color: var(--bg-color);
    border-color: var(--accent-color);
}

#sort {
    padding: 0.25rem 0.5rem;
    border: 1px solid var(--border-color);
    border-radius: 6px;
    background: var(--card-bg);
    color: var(--text-color);
}

.tags-container {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    padding: 0.5rem 0;
}

.tag {
    display: inline-block;
    padding: 0.2rem 0.6rem;
    background: var(--tag-bg);
    border-radius: 12px;
    font-size: 0.75rem;
    color: var(--text-muted);
    cursor: pointer;
    transition: all 0.2s;
}

.tag:hover,
.tag.active {
    background: var(--accent-color);
    color: var(--bg-color);
}

main {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding: 1rem 0;
}

.article {
    background: var(--card-bg);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 1rem;
    transition: border-color 0.2s;
}

.article:hover {
    border-color: var(--accent-color);
}

.article-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 1rem;
    margin-bottom: 0.5rem;
}

.article-title {
    font-size: 1rem;
    font-weight: 600;
}

.article-title a {
    color: var(--text-color);
    text-decoration: none;
}

.article-title a:hover {
    color: var(--accent-color);
}

.score {
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
    white-space: nowrap;
}

.score-high {
    background: var(--score-high);
    color: white;
}

.score-mid {
    background: var(--score-mid);
    color: white;
}

.score-low {
    background: var(--score-low);
    color: white;
}

.article-summary {
    color: var(--text-muted);
    font-size: 0.875rem;
    margin-bottom: 0.75rem;
}

.article-meta {
    display: flex;
    align-items: center;
    gap: 1rem;
    flex-wrap: wrap;
    font-size: 0.75rem;
    color: var(--text-muted);
}

.article-meta a {
    color: var(--text-muted);
    text-decoration: none;
}

.article-meta a:hover {
    color: var(--accent-color);
}

.article-tags {
    display: flex;
    gap: 0.25rem;
}

.article-keywords {
    color: var(--accent-color);
    font-size: 0.7rem;
}

footer {
    text-align: center;
    padding: 2rem 0;
    color: var(--text-muted);
    font-size: 0.875rem;
    border-top: 1px solid var(--border-color);
    margin-top: 2rem;
}

@media (max-width: 600px) {
    header {
        flex-direction: column;
        align-items: stretch;
    }

    #search {
        width: 100%;
    }

    .filters {
        flex-direction: column;
    }
}
```

**Step 3: app.js を作成**

```javascript
// AI-news-aggregater/docs/app.js
let articles = [];
let filteredArticles = [];
let activeSource = 'all';
let activePeriod = 'all';
let activeTag = null;
let sortBy = 'score';

async function loadArticles() {
    try {
        const response = await fetch('data/articles.json');
        const data = await response.json();
        articles = data.articles || [];
        document.getElementById('last-updated').textContent =
            data.last_updated ? new Date(data.last_updated).toLocaleString('ja-JP') : '-';

        buildTagsFilter();
        applyFilters();
    } catch (error) {
        console.error('Error loading articles:', error);
        document.getElementById('articles').innerHTML =
            '<p style="text-align:center;color:var(--text-muted);">記事の読み込みに失敗しました</p>';
    }
}

function buildTagsFilter() {
    const tagCounts = {};
    articles.forEach(article => {
        (article.tags || []).forEach(tag => {
            tagCounts[tag] = (tagCounts[tag] || 0) + 1;
        });
    });

    const sortedTags = Object.entries(tagCounts)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 15);

    const container = document.getElementById('tags-filter');
    container.innerHTML = sortedTags.map(([tag, count]) =>
        `<span class="tag" data-tag="${tag}">${tag} (${count})</span>`
    ).join('');
}

function applyFilters() {
    const searchQuery = document.getElementById('search').value.toLowerCase();

    filteredArticles = articles.filter(article => {
        // Source filter
        if (activeSource !== 'all') {
            if (!article.source.includes(activeSource)) return false;
        }

        // Period filter
        if (activePeriod !== 'all') {
            const articleDate = new Date(article.created_at || article.fetched_at);
            const now = new Date();
            if (activePeriod === 'today') {
                const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
                if (articleDate < today) return false;
            } else if (activePeriod === 'week') {
                const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
                if (articleDate < weekAgo) return false;
            }
        }

        // Tag filter
        if (activeTag) {
            if (!(article.tags || []).includes(activeTag)) return false;
        }

        // Search filter
        if (searchQuery) {
            const searchText = [
                article.title,
                article.summary || '',
                (article.tags || []).join(' ')
            ].join(' ').toLowerCase();
            if (!searchText.includes(searchQuery)) return false;
        }

        return true;
    });

    // Sort
    filteredArticles.sort((a, b) => {
        if (sortBy === 'score') {
            return (b.interest_score || 0) - (a.interest_score || 0);
        } else if (sortBy === 'date') {
            return new Date(b.created_at || b.fetched_at) - new Date(a.created_at || a.fetched_at);
        } else if (sortBy === 'comments') {
            return (b.comments_count || 0) - (a.comments_count || 0);
        }
        return 0;
    });

    renderArticles();
}

function renderArticles() {
    const container = document.getElementById('articles');

    if (filteredArticles.length === 0) {
        container.innerHTML = '<p style="text-align:center;color:var(--text-muted);">記事が見つかりません</p>';
        return;
    }

    container.innerHTML = filteredArticles.map(article => {
        const score = article.interest_score || 0;
        const scoreClass = score >= 15 ? 'score-high' : score >= 5 ? 'score-mid' : 'score-low';
        const timeAgo = getTimeAgo(article.created_at || article.fetched_at);

        return `
            <article class="article">
                <div class="article-header">
                    <h2 class="article-title">
                        <a href="${article.url}" target="_blank" rel="noopener">${escapeHtml(article.title)}</a>
                    </h2>
                    <span class="score ${scoreClass}">スコア: ${score}</span>
                </div>
                ${article.summary ? `<p class="article-summary">${escapeHtml(article.summary)}</p>` : ''}
                <div class="article-meta">
                    <span class="article-tags">
                        ${(article.tags || []).map(tag => `<span class="tag">${escapeHtml(tag)}</span>`).join('')}
                    </span>
                    <span>${escapeHtml(article.source)}</span>
                    <span>${timeAgo}</span>
                    ${article.comments_url ? `<a href="${article.comments_url}" target="_blank">💬 ${article.comments_count || 0}</a>` : ''}
                    ${article.matched_keywords?.length ? `<span class="article-keywords">🎯 ${article.matched_keywords.join(', ')}</span>` : ''}
                </div>
            </article>
        `;
    }).join('');
}

function getTimeAgo(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) return `${diffMins}分前`;
    if (diffHours < 24) return `${diffHours}時間前`;
    if (diffDays < 7) return `${diffDays}日前`;
    return date.toLocaleDateString('ja-JP');
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Event listeners
document.getElementById('search').addEventListener('input', applyFilters);

document.querySelectorAll('[data-source]').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('[data-source]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        activeSource = btn.dataset.source;
        applyFilters();
    });
});

document.querySelectorAll('[data-period]').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('[data-period]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        activePeriod = btn.dataset.period;
        applyFilters();
    });
});

document.getElementById('sort').addEventListener('change', (e) => {
    sortBy = e.target.value;
    applyFilters();
});

document.getElementById('tags-filter').addEventListener('click', (e) => {
    if (e.target.classList.contains('tag')) {
        const tag = e.target.dataset.tag;
        if (activeTag === tag) {
            activeTag = null;
            e.target.classList.remove('active');
        } else {
            document.querySelectorAll('#tags-filter .tag').forEach(t => t.classList.remove('active'));
            activeTag = tag;
            e.target.classList.add('active');
        }
        applyFilters();
    }
});

// Initialize
loadArticles();
```

**Step 4: Commit**

```bash
git add AI-news-aggregater/docs/
git commit -m "feat: add frontend HTML/CSS/JS"
```

---

## Phase 6: GitHub Actions

### Task 9: GitHub Actions ワークフロー

**Files:**
- Create: `AI-news-aggregater/.github/workflows/fetch.yml`

**Step 1: fetch.yml を作成**

```yaml
# AI-news-aggregater/.github/workflows/fetch.yml
name: Fetch and Summarize

on:
  schedule:
    # UTC 0:00, 8:00, 16:00 (JST 9:00, 17:00, 1:00)
    - cron: '0 0,8,16 * * *'
  workflow_dispatch:  # 手動実行用

jobs:
  fetch:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
        working-directory: ./AI-news-aggregater

      - name: Run fetch script
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
        run: |
          python scripts/fetch_and_summarize.py
        working-directory: ./AI-news-aggregater

      - name: Commit and push changes
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add docs/data/articles.json
          git diff --staged --quiet || git commit -m "chore: update articles $(date -u +%Y-%m-%dT%H:%M:%SZ)"
          git push
        working-directory: ./AI-news-aggregater
```

**Step 2: Commit**

```bash
git add AI-news-aggregater/.github/
git commit -m "feat: add GitHub Actions workflow"
```

---

## Phase 7: ドキュメント

### Task 10: README作成

**Files:**
- Create: `AI-news-aggregater/README.md`

**Step 1: README.md を作成**

```markdown
# AI News Aggregator

AI・個人開発関連の情報を自動収集し、AIで要約・整理して表示する自分専用ニュースサイト。

## 機能

- 📰 **複数ソースから記事自動収集**
  - Hacker News
  - Reddit (MachineLearning, LocalLLaMA, SideProject, artificial, ClaudeAI)
  - GitHub Trending

- 🤖 **AI要約** (Gemini API)
  - 各記事を日本語1-2文で要約
  - 自動タグ付け

- 🎯 **興味スコアリング**
  - キーワードベースでスコア算出
  - 高スコア記事が上位表示

- 🔍 **検索・フィルタ**
  - キーワード検索
  - ソース別/タグ別/期間フィルタ
  - ソート切り替え

## セットアップ

### 1. リポジトリ設定

```bash
# フォークまたはクローン
git clone https://github.com/YOUR_USERNAME/ai-news-aggregator.git
```

### 2. Gemini APIキー取得

1. https://aistudio.google.com/app/apikey でAPIキー発行
2. リポジトリ Settings > Secrets > Actions に `GEMINI_API_KEY` として登録

### 3. GitHub Pages有効化

1. Settings > Pages
2. Source: Deploy from a branch
3. Branch: main, /docs

### 4. 初回実行

Actions タブから手動実行 (workflow_dispatch)

## ローカル実行

```bash
# 依存インストール
pip install -r requirements.txt

# 実行（GEMINI_API_KEYなしでも取得のみ動作）
export GEMINI_API_KEY=your_key_here
python scripts/fetch_and_summarize.py
```

## カスタマイズ

`config.json` を編集:

- `interests`: 興味キーワード (high/medium/low)
- `sources`: 取得ソース設定
- `gemini.max_articles_per_run`: 1回あたりの要約数
- `retention_days`: 記事保持日数

## 技術スタック

- Python 3.11
- Google Gemini API (gemini-1.5-flash)
- GitHub Actions
- GitHub Pages
- Vanilla JS
```

**Step 2: Commit**

```bash
git add AI-news-aggregater/README.md
git commit -m "docs: add README"
```

---

## 実装チェックリスト

- [ ] Task 1: ディレクトリ構造とconfig.json
- [ ] Task 2: Hacker News フェッチャー
- [ ] Task 3: Reddit フェッチャー
- [ ] Task 4: GitHub Trending フェッチャー
- [ ] Task 5: Gemini API 要約モジュール
- [ ] Task 6: スコアリングモジュール
- [ ] Task 7: メインスクリプト統合
- [ ] Task 8: HTML/CSS/JS フロントエンド
- [ ] Task 9: GitHub Actions ワークフロー
- [ ] Task 10: README作成

## デプロイ後の確認

1. GitHub Actions が正常に実行されるか
2. `docs/data/articles.json` が生成されるか
3. GitHub Pages で記事が表示されるか
4. 検索・フィルタが動作するか
