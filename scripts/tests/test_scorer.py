"""Tests for scorer module"""
import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scorer import calculate_interest_score, score_articles


class TestCalculateInterestScore:
    @pytest.fixture
    def sample_interests(self):
        return {
            "high": ["AI", "machine learning"],
            "medium": ["Python", "automation"],
            "low": ["news", "update"]
        }

    @pytest.fixture
    def sample_weights(self):
        return {"high": 10, "medium": 5, "low": 2}

    def test_high_priority_match(self, sample_interests, sample_weights):
        """高優先度キーワードのマッチ"""
        article = {"title": "AI revolution", "summary": "", "tags": []}
        score, matched = calculate_interest_score(article, sample_interests, sample_weights)

        assert score == 10
        assert "AI" in matched

    def test_multiple_matches(self, sample_interests, sample_weights):
        """複数のキーワードマッチ"""
        article = {
            "title": "AI with Python",
            "summary": "Machine learning automation",
            "tags": []
        }
        score, matched = calculate_interest_score(article, sample_interests, sample_weights)

        # AI(10) + machine learning(10) + Python(5) + automation(5) = 30
        assert score == 30
        assert len(matched) >= 2

    def test_no_match(self, sample_interests, sample_weights):
        """マッチなし"""
        article = {"title": "Cooking recipes", "summary": "", "tags": []}
        score, matched = calculate_interest_score(article, sample_interests, sample_weights)

        assert score == 0
        assert matched == []

    def test_case_insensitive(self, sample_interests, sample_weights):
        """大文字小文字を無視"""
        article = {"title": "ai and PYTHON", "summary": "", "tags": []}
        score, matched = calculate_interest_score(article, sample_interests, sample_weights)

        assert score > 0
        assert len(matched) >= 1

    def test_tags_contribute_to_score(self, sample_interests, sample_weights):
        """タグもスコアに寄与する"""
        article = {"title": "Something", "summary": "", "tags": ["AI", "Python"]}
        score, matched = calculate_interest_score(article, sample_interests, sample_weights)

        assert score == 15  # AI(10) + Python(5)

    def test_summary_contributes_to_score(self, sample_interests, sample_weights):
        """要約もスコアに寄与する"""
        article = {"title": "Title", "summary": "AI is amazing", "tags": []}
        score, matched = calculate_interest_score(article, sample_interests, sample_weights)

        assert score == 10
        assert "AI" in matched

    def test_no_duplicate_keywords(self, sample_interests, sample_weights):
        """重複キーワードは一度だけカウント"""
        article = {"title": "AI AI AI", "summary": "AI", "tags": ["AI"]}
        score, matched = calculate_interest_score(article, sample_interests, sample_weights)

        # Should only count AI once per text field search
        assert "AI" in matched


class TestScoreArticles:
    def test_sort_by_score(self):
        """スコア降順でソート"""
        config = {
            "interests": {"high": ["critical"], "medium": ["normal"]},
            "score_weights": {"high": 10, "medium": 5}
        }
        articles = [
            {"title": "This is normal news", "summary": "", "tags": []},
            {"title": "This is critical news", "summary": "", "tags": []},
        ]

        result = score_articles(articles, config)

        assert result[0]["title"] == "This is critical news"
        assert result[0]["interest_score"] > result[1]["interest_score"]

    def test_default_weights(self):
        """デフォルトの重みを使用"""
        config = {"interests": {"high": ["test"]}}
        articles = [{"title": "test article", "summary": "", "tags": []}]

        result = score_articles(articles, config)

        assert result[0]["interest_score"] == 10  # default high weight

    def test_empty_config(self):
        """空の設定でも動作"""
        config = {}
        articles = [{"title": "test", "summary": "", "tags": []}]

        result = score_articles(articles, config)

        assert result[0]["interest_score"] == 0

    def test_matched_keywords_stored(self):
        """マッチしたキーワードが保存される"""
        config = {
            "interests": {"high": ["AI", "ML"]},
            "score_weights": {"high": 10}
        }
        articles = [{"title": "AI and ML", "summary": "", "tags": []}]

        result = score_articles(articles, config)

        assert "AI" in result[0]["matched_keywords"]
        assert "ML" in result[0]["matched_keywords"]

    def test_empty_articles(self):
        """空のリストを処理"""
        config = {"interests": {"high": ["test"]}}
        result = score_articles([], config)
        assert result == []
