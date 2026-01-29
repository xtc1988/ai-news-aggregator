import unittest
from unittest.mock import patch, Mock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

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
        mock_response_ids.raise_for_status = Mock()

        mock_response_item = Mock()
        mock_response_item.json.return_value = {
            "id": 1,
            "title": "Test",
            "url": "https://test.com",
            "score": 100,
            "descendants": 10,
            "time": 1706600000
        }
        mock_response_item.raise_for_status = Mock()

        mock_get.side_effect = [mock_response_ids] + [mock_response_item] * 3

        results = fetch_hackernews_stories(limit=3)
        self.assertEqual(len(results), 3)

if __name__ == '__main__':
    unittest.main()
