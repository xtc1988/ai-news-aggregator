"""Tests for GitHub Trending fetcher"""
import pytest
from unittest.mock import Mock, patch
from bs4 import BeautifulSoup
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fetchers.github_trending import (
    generate_id,
    parse_repo_row,
    fetch_github_trending,
    GITHUB_TRENDING_URL
)


class TestGenerateId:
    def test_generate_id_returns_12_chars(self):
        """IDは12文字のハッシュを返す"""
        result = generate_id("https://github.com/test/repo")
        assert len(result) == 12

    def test_generate_id_consistent(self):
        """同じURLは同じIDを返す"""
        url = "https://github.com/test/repo"
        assert generate_id(url) == generate_id(url)

    def test_generate_id_different_urls(self):
        """異なるURLは異なるIDを返す"""
        id1 = generate_id("https://github.com/test/repo1")
        id2 = generate_id("https://github.com/test/repo2")
        assert id1 != id2


class TestParseRepoRow:
    @pytest.fixture
    def sample_html(self):
        """サンプルのGitHub Trendingリポジトリ行HTML"""
        return """
        <article class="Box-row">
            <h2>
                <a href="/openai/gpt-4">openai / gpt-4</a>
            </h2>
            <p>GPT-4 implementation</p>
            <a href="/openai/gpt-4/stargazers">1,234</a>
            <span class="d-inline-block float-sm-right">456 stars today</span>
        </article>
        """

    def test_parse_repo_row_valid(self, sample_html):
        """有効なHTML行を正しくパースする"""
        soup = BeautifulSoup(sample_html, "html.parser")
        row = soup.select_one("article.Box-row")
        result = parse_repo_row(row)

        assert result is not None
        assert result["title"] == "[GitHub] openai/gpt-4"
        assert result["url"] == "https://github.com/openai/gpt-4"
        assert result["source"] == "GitHub Trending"
        assert result["source_score"] == 1234
        assert result["comments_count"] == 456
        assert result["summary"] == "GPT-4 implementation"

    def test_parse_repo_row_no_h2(self):
        """h2がない場合はNoneを返す"""
        html = "<article class='Box-row'><p>No h2</p></article>"
        soup = BeautifulSoup(html, "html.parser")
        row = soup.select_one("article.Box-row")
        result = parse_repo_row(row)
        assert result is None

    def test_parse_repo_row_no_href(self):
        """hrefがない場合はNoneを返す"""
        html = "<article class='Box-row'><h2><a>No href</a></h2></article>"
        soup = BeautifulSoup(html, "html.parser")
        row = soup.select_one("article.Box-row")
        result = parse_repo_row(row)
        assert result is None

    def test_parse_repo_row_no_description(self):
        """説明がない場合もパースできる"""
        html = """
        <article class="Box-row">
            <h2><a href="/test/repo">test / repo</a></h2>
        </article>
        """
        soup = BeautifulSoup(html, "html.parser")
        row = soup.select_one("article.Box-row")
        result = parse_repo_row(row)

        assert result is not None
        assert result["summary"] is None


class TestFetchGithubTrending:
    @patch('fetchers.github_trending.requests.get')
    def test_fetch_github_trending_success(self, mock_get):
        """正常なレスポンスを処理できる"""
        mock_response = Mock()
        mock_response.text = """
        <html>
            <article class="Box-row">
                <h2><a href="/test/repo">test / repo</a></h2>
                <p>Test description</p>
            </article>
        </html>
        """
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = fetch_github_trending()

        assert len(result) == 1
        assert result[0]["title"] == "[GitHub] test/repo"
        mock_get.assert_called_once()

    @patch('fetchers.github_trending.requests.get')
    def test_fetch_github_trending_network_error(self, mock_get):
        """ネットワークエラー時は空リストを返す"""
        mock_get.side_effect = Exception("Network error")

        result = fetch_github_trending()

        assert result == []

    @patch('fetchers.github_trending.requests.get')
    def test_fetch_github_trending_empty_page(self, mock_get):
        """空のページでも正常に処理"""
        mock_response = Mock()
        mock_response.text = "<html></html>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        result = fetch_github_trending()

        assert result == []
