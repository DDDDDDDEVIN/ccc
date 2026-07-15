import unittest
from unittest.mock import patch, MagicMock
from flask import Flask
import json
import os
import tempfile
from pathlib import Path
#use to run the test: python -m unittest test.test_mprocessor
'''
 === Cluster Cloud Computing Project | Team 60 ===
 This test is implemented by Team 60
- Angqi Meng - 1268867
- Yichen Long - 1497321
- Xuan Wu - 1483104
- Zining Zhang - 1508501
- Jingqiu Meng - 1506602
'''
# Import the mprocessor function
from backend.fission.functions.mprocessor.mprocessor import main as mprocessor
from backend.fission.functions.mprocessor.mprocessor import process_post, extract_location, extract_hashtags, extract_topic, clean_content

class TestMProcessor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Create a temporary directory for config files
        cls.temp_dir = tempfile.mkdtemp()
        CONFIG_DIR = Path(cls.temp_dir) / "mprocessor-config"
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        # Write config files in the format expected by the processor
        (CONFIG_DIR / "STATE_MAPPING").write_text(json.dumps({
            "new south wales": "nsw",
            "sydney": "nsw",
            "victoria": "vic",
            "melbourne": "vic"
        }))
        (CONFIG_DIR / "TOPIC_MAPPING").write_text(json.dumps({
            "election": "election",
            "climate": "climate"
        }))
        os.environ["CONFIG_BASE"] = str(CONFIG_DIR)
        global mprocessor, process_post, extract_location, extract_hashtags, extract_topic, clean_content
        from backend.fission.functions.mprocessor.mprocessor import main as mprocessor
        from backend.fission.functions.mprocessor.mprocessor import process_post, extract_location, extract_hashtags, extract_topic, clean_content

    @classmethod
    def tearDownClass(cls):
        # Clean up temporary directory
        import shutil
        shutil.rmtree(cls.temp_dir)

    def setUp(self):
        """Set up test environment before each test."""
        self.app = Flask(__name__)
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Mock config function
        self.config_patcher = patch('backend.fission.functions.mprocessor.mprocessor.config')
        self.mock_config = self.config_patcher.start()
        
        # Mock config values
        self.mock_config.side_effect = lambda key: {
            "STATE_MAPPING": json.dumps({
                "nsw": ["new south wales", "sydney"],
                "vic": ["victoria", "melbourne"]
            }),
            "TOPIC_MAPPING": json.dumps({
                "election": ["election", "vote"],
                "climate": ["climate", "weather"]
            })
        }.get(key, "")

    def tearDown(self):
        """Clean up after each test."""
        self.config_patcher.stop()
        self.app_context.pop()

    def test_successful_processing(self):
        """Test successful processing of valid Mastodon posts."""
        test_data = [{
            "content": "Hello from Sydney!",
            "created_at": "2024-01-01T00:00:00Z",
            "id": "123",
            "account": {"acct": "testuser"},
            "matched_query": "election",
            "tags": [{"name": "election"}, {"name": "vote"}]
        }]
        
        with self.app.test_request_context(json=test_data):
            result = mprocessor()
            processed_data = json.loads(result)
            
            self.assertEqual(len(processed_data), 1)
            self.assertEqual(processed_data[0]["location"], "nsw")
            self.assertEqual(processed_data[0]["source"], "mastodon")
            self.assertEqual(processed_data[0]["topic"], "election")
            self.assertEqual(processed_data[0]["tags"], ["election", "vote"])

    def test_invalid_json(self):
        """Test handling of invalid JSON data."""
        with self.app.test_request_context(
            data="invalid json",
            content_type='application/json'
        ):
            result = mprocessor()
            self.assertEqual(result, "ERROR")

    def test_empty_posts(self):
        """Test handling of empty posts list."""
        with self.app.test_request_context(json=[]):
            result = mprocessor()
            self.assertEqual(result, "[]")

    def test_clean_content(self):
        """Test HTML content cleaning."""
        test_content = "<p>Hello <b>from</b> <a href='#'>Melbourne</a>!</p>"
        cleaned = clean_content({"content": test_content})
        self.assertEqual(cleaned, "Hello from Melbourne!")

    def test_process_post_with_location(self):
        """Test process_post function with location extraction."""
        post = {
            "content": "Hello from Melbourne!",
            "created_at": "2024-01-01T00:00:00Z",
            "id": "123",
            "account": {"acct": "testuser"},
            "matched_query": "election",
            "tags": []
        }
        
        result = process_post(post)
        self.assertIsNotNone(result)
        self.assertEqual(result["location"], "vic")

    def test_process_post_with_hashtags(self):
        """Test process_post function with hashtag extraction."""
        post = {
            "content": "Hello",
            "created_at": "2024-01-01T00:00:00Z",
            "id": "123",
            "account": {"acct": "testuser"},
            "matched_query": "election",
            "tags": [{"name": "election"}, {"name": "vote"}]
        }
        
        result = process_post(post)
        self.assertIsNotNone(result)
        self.assertEqual(result["tags"], ["election", "vote"])

    def test_process_post_with_topic(self):
        """Test process_post function with topic extraction."""
        post = {
            "content": "Hello",
            "created_at": "2024-01-01T00:00:00Z",
            "id": "123",
            "account": {"acct": "testuser"},
            "matched_query": "climate",
            "tags": []
        }
        
        result = process_post(post)
        self.assertIsNotNone(result)
        self.assertEqual(result["topic"], "climate")

if __name__ == '__main__':
    unittest.main() 