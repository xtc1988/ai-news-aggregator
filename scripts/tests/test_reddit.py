import unittest
from unittest.mock import patch, Mock
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

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
