# AI-news-aggregater/scripts/tests/test_e2e.py
"""E2E Tests - 統合テスト"""
import unittest
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, Mock
from datetime import datetime

# スクリプトディレクトリをパスに追加
SCRIPT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPT_DIR))

from fetchers import fetch_hackernews_stories, fetch_reddit_posts, fetch_github_trending
from summarizer import summarize_articles, parse_gemini_response
from scorer import score_articles, calculate_interest_score


class TestE2EDataFlow(unittest.TestCase):
    """データフローのE2Eテスト"""

    def test_full_pipeline_with_mocked_sources(self):
        """フルパイプラインのテスト（モック使用）"""
        # モック記事データを作成
        mock_articles = [
            {
                "id": "test001",
                "title": "Claude Code announces new AI agent features",
                "url": "https://example.com/article1",
                "source": "Hacker News",
                "source_score": 150,
                "comments_count": 42,
                "comments_url": "https://news.ycombinator.com/item?id=12345",
                "summary": None,
                "tags": [],
                "interest_score": 0,
                "matched_keywords": [],
                "created_at": "2026-01-30T10:00:00Z",
                "fetched_at": "2026-01-30T12:00:00Z"
            },
            {
                "id": "test002",
                "title": "New GPT-5 model released by OpenAI",
                "url": "https://example.com/article2",
                "source": "Reddit/MachineLearning",
                "source_score": 200,
                "comments_count": 85,
                "comments_url": "https://reddit.com/r/MachineLearning/...",
                "summary": None,
                "tags": [],
                "interest_score": 0,
                "matched_keywords": [],
                "created_at": "2026-01-30T09:00:00Z",
                "fetched_at": "2026-01-30T12:00:00Z"
            },
            {
                "id": "test003",
                "title": "Python web framework comparison",
                "url": "https://example.com/article3",
                "source": "GitHub Trending",
                "source_score": 1000,
                "comments_count": 50,
                "comments_url": "https://github.com/...",
                "summary": None,
                "tags": [],
                "interest_score": 0,
                "matched_keywords": [],
                "created_at": "2026-01-30T08:00:00Z",
                "fetched_at": "2026-01-30T12:00:00Z"
            }
        ]

        # 設定
        config = {
            "interests": {
                "high": ["Claude", "Anthropic", "Claude Code", "AI agent", "LLM", "MCP"],
                "medium": ["GPT", "OpenAI", "Gemini", "RAG"],
                "low": ["machine learning", "deep learning", "open source"]
            },
            "score_weights": {
                "high": 10,
                "medium": 5,
                "low": 2
            }
        }

        # スコアリング実行
        scored_articles = score_articles(mock_articles, config)

        # 検証
        self.assertEqual(len(scored_articles), 3)

        # Claude Code記事が最高スコアであるべき
        self.assertEqual(scored_articles[0]["id"], "test001")
        self.assertGreater(scored_articles[0]["interest_score"], 0)
        self.assertIn("Claude", scored_articles[0]["matched_keywords"])

        # GPT記事も中程度のスコアがあるべき
        gpt_article = next(a for a in scored_articles if a["id"] == "test002")
        self.assertIn("GPT", gpt_article["matched_keywords"])

    def test_deduplication_logic(self):
        """重複除去のテスト"""
        existing = [
            {"id": "existing001", "title": "Existing Article"}
        ]
        new_articles = [
            {"id": "existing001", "title": "Duplicate"},  # 重複
            {"id": "new001", "title": "New Article"}      # 新規
        ]

        existing_ids = {a["id"] for a in existing}
        unique_new = [a for a in new_articles if a["id"] not in existing_ids]

        self.assertEqual(len(unique_new), 1)
        self.assertEqual(unique_new[0]["id"], "new001")

    def test_article_cleanup(self):
        """古い記事のクリーンアップテスト"""
        from datetime import datetime, timedelta

        now = datetime.utcnow()
        old_date = (now - timedelta(days=10)).isoformat() + "Z"
        recent_date = (now - timedelta(days=3)).isoformat() + "Z"

        articles = [
            {"id": "old", "fetched_at": old_date},
            {"id": "recent", "fetched_at": recent_date}
        ]

        retention_days = 7
        cutoff = now - timedelta(days=retention_days)
        cutoff_str = cutoff.isoformat() + "Z"

        cleaned = [a for a in articles if a.get("fetched_at", "") >= cutoff_str]

        self.assertEqual(len(cleaned), 1)
        self.assertEqual(cleaned[0]["id"], "recent")


class TestE2EScoringEdgeCases(unittest.TestCase):
    """スコアリングのエッジケースE2Eテスト"""

    def test_empty_article_list(self):
        """空の記事リストでもエラーにならない"""
        config = {"interests": {"high": ["test"]}, "score_weights": {"high": 10}}
        result = score_articles([], config)
        self.assertEqual(result, [])

    def test_article_with_none_values(self):
        """None値を含む記事でもエラーにならない"""
        articles = [{
            "id": "test",
            "title": None,
            "summary": None,
            "tags": None,
            "url": "https://test.com"
        }]
        config = {"interests": {"high": ["test"]}, "score_weights": {"high": 10}}

        result = score_articles(articles, config)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["interest_score"], 0)

    def test_unicode_in_keywords(self):
        """日本語キーワードでもマッチング可能"""
        articles = [{
            "id": "test",
            "title": "機械学習の最新トレンド",
            "summary": "ディープラーニングについて",
            "tags": ["AI", "日本語"],
            "url": "https://test.com"
        }]
        config = {
            "interests": {
                "high": ["機械学習", "ディープラーニング"]
            },
            "score_weights": {"high": 10}
        }

        result = score_articles(articles, config)

        self.assertEqual(len(result), 1)
        self.assertGreater(result[0]["interest_score"], 0)


class TestE2ESummarizerParsing(unittest.TestCase):
    """要約パーサーのE2Eテスト"""

    def test_parse_real_like_response(self):
        """実際のGeminiレスポンスに近い形式をパース"""
        response = """
1. summary: Claudeの新しいAIエージェント機能が発表されました。開発者向けの強力なツールセットを提供します。
   tags: Claude, AI Agent, 開発ツール

2. summary: OpenAIがGPT-5を発表。従来モデルより大幅な性能向上を実現しています。
   tags: GPT-5, OpenAI, LLM

3. summary: Pythonのウェブフレームワーク比較記事。Django、FastAPI、Flaskの特徴を解説。
   tags: Python, Web開発, フレームワーク
"""
        results = parse_gemini_response(response, 3)

        self.assertEqual(len(results), 3)
        self.assertIn("Claude", results[0]["tags"])
        self.assertIn("GPT-5", results[1]["tags"])
        self.assertIn("Python", results[2]["tags"])

    def test_parse_malformed_response_gracefully(self):
        """不正な形式でもクラッシュしない"""
        malformed_responses = [
            "",  # 空
            "random text without structure",  # 構造なし
            "1. summary: only summary no tags",  # タグなし
            "1. tags: only tags, no summary",  # 要約なし
        ]

        for response in malformed_responses:
            results = parse_gemini_response(response, 2)
            self.assertEqual(len(results), 2)  # 常に期待数を返す


class TestE2EFetcherFormat(unittest.TestCase):
    """フェッチャーの出力形式E2Eテスト"""

    def test_hackernews_article_format(self):
        """HNフェッチャーが正しい形式を返す"""
        from fetchers.hackernews import parse_story

        raw_story = {
            "id": 12345,
            "title": "Test Article",
            "url": "https://example.com/test",
            "score": 100,
            "descendants": 25,
            "time": 1706600000
        }

        article = parse_story(raw_story)

        # 必須フィールドの存在確認
        required_fields = [
            "id", "title", "url", "source", "source_score",
            "comments_count", "comments_url", "summary", "tags",
            "interest_score", "matched_keywords", "created_at", "fetched_at"
        ]
        for field in required_fields:
            self.assertIn(field, article, f"Missing field: {field}")

        self.assertEqual(article["source"], "Hacker News")

    def test_reddit_article_format(self):
        """Redditフェッチャーが正しい形式を返す"""
        from fetchers.reddit import parse_post

        raw_post = {
            "data": {
                "id": "abc123",
                "title": "Test Post",
                "url": "https://example.com/test",
                "score": 150,
                "num_comments": 30,
                "permalink": "/r/test/comments/abc123/test/",
                "created_utc": 1706600000,
                "is_self": False
            }
        }

        article = parse_post(raw_post, "TestSubreddit")

        required_fields = [
            "id", "title", "url", "source", "source_score",
            "comments_count", "comments_url"
        ]
        for field in required_fields:
            self.assertIn(field, article, f"Missing field: {field}")

        self.assertEqual(article["source"], "Reddit/TestSubreddit")


class TestE2EConfigValidation(unittest.TestCase):
    """設定ファイルの検証E2Eテスト"""

    def test_config_structure(self):
        """config.jsonが正しい構造を持つ"""
        config_path = SCRIPT_DIR.parent / "config.json"

        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            # 必須キーの確認
            self.assertIn("interests", config)
            self.assertIn("score_weights", config)
            self.assertIn("sources", config)

            # interests構造
            interests = config["interests"]
            self.assertIn("high", interests)
            self.assertIn("medium", interests)
            self.assertIn("low", interests)

            # sources構造
            sources = config["sources"]
            self.assertIn("hackernews", sources)
            self.assertIn("reddit", sources)
            self.assertIn("github_trending", sources)


class TestE2EArticlesJsonFormat(unittest.TestCase):
    """articles.jsonフォーマットのE2Eテスト"""

    def test_articles_json_structure(self):
        """articles.jsonが正しい構造を持つ"""
        articles_path = SCRIPT_DIR.parent / "docs" / "data" / "articles.json"

        if articles_path.exists():
            with open(articles_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.assertIn("last_updated", data)
            self.assertIn("articles", data)
            self.assertIsInstance(data["articles"], list)


if __name__ == '__main__':
    unittest.main()
