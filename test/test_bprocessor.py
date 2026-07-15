import unittest
from flask import Flask
from unittest.mock import patch
import json
#use to run the test: python -m unittest test.test_bprocessor
'''
 === Cluster Cloud Computing Project | Team 60 ===
 This test is implemented by Team 60
- Angqi Meng - 1268867
- Yichen Long - 1497321
- Xuan Wu - 1483104
- Zining Zhang - 1508501
- Jingqiu Meng - 1506602
'''
class TestBProcessor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Patch load_mapping before importing bprocessor
        cls.load_mapping_patcher = patch(
            'backend.fission.functions.bprocessor.bprocessor.load_mapping',
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
        global bprocessor, process_post, extract_location, extract_hashtags, extract_topic
        from backend.fission.functions.bprocessor.bprocessor import main as bprocessor
        from backend.fission.functions.bprocessor.bprocessor import process_post, extract_location, extract_hashtags, extract_topic

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
            "record": {
                "text": "Hello from Sydney! #election",
                "created_at": "2024-01-01T00:00:00Z"
            },
            "uri": "test-uri",
            "author": {"handle": "testuser"},
            "matched_query": "election"
        }]
        with self.app.test_request_context(json=test_data):
            result = bprocessor()
            processed_data = json.loads(result)
            self.assertEqual(len(processed_data), 1)
            self.assertEqual(processed_data[0]["location"], "nsw")
            self.assertEqual(processed_data[0]["source"], "bluesky")
            self.assertEqual(processed_data[0]["topic"], "election")
            self.assertEqual(processed_data[0]["tags"], ["#election"])

    def test_invalid_json(self):
        with self.app.test_request_context(
            data="invalid json",
            content_type='application/json'
        ):
            result = bprocessor()
            self.assertEqual(result, "ERROR")

    def test_empty_posts(self):
        with self.app.test_request_context(json=[]):
            result = bprocessor()
            self.assertEqual(result, "[]")

    def test_simple_post_processing(self):
        post = {
            "record": {
                "text": "Hello from Melbourne!",
                "created_at": "2024-01-01T00:00:00Z"
            },
            "uri": "test-uri",
            "author": {"handle": "testuser"},
            "matched_query": "election"
        }
        result = process_post(post)
        self.assertIsNotNone(result)
        self.assertEqual(result["location"], "vic")
        self.assertEqual(result["source"], "bluesky")
        self.assertEqual(result["topic"], "election")

if __name__ == '__main__':
    unittest.main() 