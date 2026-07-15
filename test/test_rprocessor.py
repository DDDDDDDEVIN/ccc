import unittest
from flask import Flask
from unittest.mock import patch
import json
import os
import tempfile
from pathlib import Path
#use to run the test: python -m unittest test.test_rprocessor
'''
 === Cluster Cloud Computing Project | Team 60 ===
 This test is implemented by Team 60
- Angqi Meng - 1268867
- Yichen Long - 1497321
- Xuan Wu - 1483104
- Zining Zhang - 1508501
- Jingqiu Meng - 1506602
'''
# Set CONFIG_BASE environment variable before importing rprocessor
os.environ["CONFIG_BASE"] = str(Path(tempfile.mkdtemp()) / "rprocessor-config")

class TestRProcessor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Patch load_mapping before importing rprocessor
        cls.load_mapping_patcher = patch(
            'backend.fission.functions.rprocessor.rprocessor.load_mapping',
            side_effect=lambda key: {
                "STATE_MAPPING": {
                    "new south wales": "nsw",
                    "sydney": "nsw",
                    "victoria": "vic",
                    "melbourne": "vic"
                },
                "TOPIC_MAPPING": {
                    "election": "election",
                    "climate": "climate"
                }
            }[key]
        )
        cls.load_mapping_patcher.start()
        global rprocessor, process_post, extract_location, extract_topic
        from backend.fission.functions.rprocessor.rprocessor import main as rprocessor
        from backend.fission.functions.rprocessor.rprocessor import process_post, extract_location, extract_topic

    @classmethod
    def tearDownClass(cls):
        cls.load_mapping_patcher.stop()

    def setUp(self):
        self.app = Flask(__name__)
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_successful_processing(self):
        test_data = [{
            "text": "Hello from Sydney!",
            "created_at": "2024-01-01T00:00:00Z",
            "post_id": "123",
            "user_id": "testuser",
            "topic": "election",
            "tags": ["election", "vote"],
            "subreddit": "r/sydney"
        }]
        with self.app.test_request_context(json=test_data):
            result = rprocessor()
            processed_data = json.loads(result)
            self.assertEqual(len(processed_data), 1)
            self.assertEqual(processed_data[0]["location"], "nsw")
            self.assertEqual(processed_data[0]["source"], "reddit")
            self.assertEqual(processed_data[0]["topic"], "election")
            self.assertEqual(processed_data[0]["tags"], ["election", "vote"])

    def test_invalid_json(self):
        with self.app.test_request_context(
            data="invalid json",
            content_type='application/json'
        ):
            result = rprocessor()
            self.assertEqual(result, "ERROR")

    def test_empty_posts(self):
        with self.app.test_request_context(json=[]):
            result = rprocessor()
            self.assertEqual(result, "[]")

    def test_process_post_with_location(self):
        post = {
            "text": "Hello from Melbourne!",
            "created_at": "2024-01-01T00:00:00Z",
            "post_id": "123",
            "user_id": "testuser",
            "topic": "election",
            "tags": [],
            "subreddit": "r/melbourne"
        }
        result = process_post(post)
        self.assertIsNotNone(result)
        self.assertEqual(result["location"], "vic")

    def test_process_post_with_topic(self):
        post = {
            "text": "Hello",
            "created_at": "2024-01-01T00:00:00Z",
            "post_id": "123",
            "user_id": "testuser",
            "topic": "climate",
            "tags": [],
            "subreddit": "r/australia"
        }
        result = process_post(post)
        self.assertIsNotNone(result)
        self.assertEqual(result["topic"], "climate")

    def test_process_post_with_subreddit_location(self):
        post = {
            "text": "Hello",
            "created_at": "2024-01-01T00:00:00Z",
            "post_id": "123",
            "user_id": "testuser",
            "topic": "election",
            "tags": [],
            "subreddit": "r/sydney"
        }
        result = process_post(post)
        self.assertIsNotNone(result)
        self.assertEqual(result["location"], "nsw")

if __name__ == '__main__':
    unittest.main() 