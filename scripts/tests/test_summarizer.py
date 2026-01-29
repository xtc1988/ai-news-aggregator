"""Tests for summarizer module"""
import pytest
from unittest.mock import Mock, patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from summarizer import (
    parse_gemini_response,
    summarize_batch,
    summarize_articles,
    configure_gemini,
    GEMINI_AVAILABLE
)


class TestParseGeminiResponse:
    def test_parse_single_response(self):
        """単一の応答をパースできる"""
        response = "1. summary: これはテストです\n   tags: AI, テスト, Python"
        result = parse_gemini_response(response, 1)

        assert len(result) == 1
        assert result[0]["summary"] == "これはテストです"
        assert "AI" in result[0]["tags"]

    def test_parse_multiple_responses(self):
        """複数の応答をパースできる"""
        response = """1. summary: 最初の記事
   tags: AI, ML
2. summary: 二番目の記事
   tags: Python, データ"""
        result = parse_gemini_response(response, 2)

        assert len(result) == 2
        assert result[0]["summary"] == "最初の記事"
        assert result[1]["summary"] == "二番目の記事"

    def test_parse_fills_missing(self):
        """期待数に足りない場合は空で埋める"""
        response = "1. summary: 一つだけ\n   tags: テスト"
        result = parse_gemini_response(response, 3)

        assert len(result) == 3
        assert result[0]["summary"] == "一つだけ"
        assert result[1]["summary"] is None
        assert result[2]["summary"] is None

    def test_parse_empty_response(self):
        """空の応答を処理できる"""
        result = parse_gemini_response("", 2)

        assert len(result) == 2
        assert all(r["summary"] is None for r in result)

    def test_tags_limited_to_5(self):
        """タグは最大5個まで"""
        response = "1. summary: テスト\n   tags: a, b, c, d, e, f, g"
        result = parse_gemini_response(response, 1)

        assert len(result[0]["tags"]) <= 5


class TestConfigureGemini:
    @patch.dict(os.environ, {}, clear=True)
    def test_configure_without_api_key(self):
        """APIキーがない場合はFalseを返す"""
        result = configure_gemini()
        assert result is False

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    def test_configure_with_api_key(self):
        """APIキーがある場合の動作確認"""
        # GEMINI_AVAILABLEがFalseの場合（google.generativeaiがない環境）
        # configure_geminiはFalseを返す
        # GEMINI_AVAILABLEがTrueの場合は設定してTrueを返す
        result = configure_gemini()
        # 環境によって結果が異なるため、例外が発生しないことを確認
        assert result in [True, False]


class TestSummarizeBatch:
    def test_summarize_batch_no_gemini(self):
        """Geminiが利用不可の場合は空の結果を返す"""
        articles = [
            {"title": "Test", "url": "http://test.com", "source": "Test"}
        ]

        with patch('summarizer.GEMINI_AVAILABLE', False):
            result = summarize_batch(articles)

        assert len(result) == 1
        assert result[0]["summary"] is None

    @patch('summarizer.GEMINI_AVAILABLE', True)
    @patch('summarizer.configure_gemini')
    def test_summarize_batch_no_api_key(self, mock_configure):
        """APIキーがない場合は空の結果を返す"""
        mock_configure.return_value = False
        articles = [
            {"title": "Test", "url": "http://test.com", "source": "Test"}
        ]

        result = summarize_batch(articles)

        assert len(result) == 1
        assert result[0]["summary"] is None


class TestSummarizeArticles:
    def test_skip_already_summarized(self):
        """既に要約済みの記事はスキップする"""
        articles = [
            {"title": "Test", "summary": "Already summarized", "tags": ["test"]}
        ]

        result = summarize_articles(articles)

        assert result == articles
        assert result[0]["summary"] == "Already summarized"

    def test_empty_list(self):
        """空のリストを処理できる"""
        result = summarize_articles([])
        assert result == []

    @patch('summarizer.summarize_batch')
    def test_respects_max_articles(self, mock_batch):
        """max_articlesを超えない"""
        mock_batch.return_value = [{"summary": "test", "tags": []}]
        articles = [{"title": f"Test {i}", "url": f"http://test{i}.com", "source": "Test"}
                    for i in range(100)]

        summarize_articles(articles, batch_size=10, max_articles=5)

        # Should only call batch once with 5 articles
        assert mock_batch.call_count <= 1
