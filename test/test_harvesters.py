import unittest
from unittest.mock import patch, MagicMock
import os
from datetime import datetime
import json
import sys
import importlib.util
from flask import Flask
from pathlib import Path

# use python -m unittest test/test_harvesters.py -v to run the test
'''
 === Cluster Cloud Computing Project | Team 60 ===
 This test is implemented by Team 60
- Angqi Meng - 1268867
- Yichen Long - 1497321
- Xuan Wu - 1483104
- Zining Zhang - 1508501
- Jingqiu Meng - 1506602
'''
# Import the harvester functions using direct file imports
def import_from_file(relative_path):
    """Import a module from a relative path."""
    # Get the absolute path of the project root
    project_root = Path(__file__).parent.parent
    # Construct the full path
    full_path = project_root / relative_path
    # Get the module name from the path
    module_name = Path(relative_path).stem
    
    spec = importlib.util.spec_from_file_location(module_name, full_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

# Import the harvester modules
bharvester = import_from_file('backend/fission/functions/bharvester-h/bharvester-h.py')
mharvester = import_from_file('backend/fission/functions/mharvester/mharvester.py')
rharvester = import_from_file('backend/fission/functions/rharvester/rharvester.py')
class TestHarvesters(unittest.TestCase):
    def setUp(self):
        # Mock environment variables and config files
        self.config_patcher = patch('builtins.open', MagicMock())
        self.mock_open = self.config_patcher.start()
        
        # Mock Redis
        self.mock_redis_instance = MagicMock()
        self.mock_redis_instance.get.return_value = None
        self.mock_redis_instance.sismember.return_value = False
        self.mock_redis_instance.sadd.return_value = None
        self.mock_redis_instance.expire.return_value = None
        # Patch get_redis_connection in both modules
        mharvester.get_redis_connection = MagicMock(return_value=self.mock_redis_instance)
        rharvester.get_redis_connection = MagicMock(return_value=self.mock_redis_instance)
        bharvester.get_redis_connection = MagicMock(return_value=self.mock_redis_instance)

        # Patch network dependencies directly on modules
        self.mock_requests = MagicMock()
        self.mock_requests.post.return_value.status_code = 200
        self.mock_requests.post.return_value.raise_for_status.return_value = None
        self.mock_requests.get.return_value.status_code = 200
        self.mock_requests.get.return_value.json.return_value = [{
            'id': '123',
            'content': 'Test post',
            'created_at': '2024-01-01T00:00:00Z'
        }]
        mharvester.requests = self.mock_requests
        rharvester.requests = self.mock_requests
        bharvester.requests = self.mock_requests

        # Patch Bluesky Client for bharvester
        self.mock_client = MagicMock()
        self.mock_client.login.return_value = None
        mock_post_data = MagicMock()
        mock_post_data.record.created_at = '2024-01-02T00:00:00Z'
        mock_post_data.uri = 'test-uri'
        mock_post_data.dict.return_value = {'text': 'Test post'}
        mock_result = MagicMock()
        mock_result.posts = [mock_post_data]
        mock_result.cursor = 'next-cursor'
        self.mock_client.app.bsky.feed.search_posts.return_value = mock_result
        bharvester.Client = MagicMock(return_value=self.mock_client)

        # Set up Flask app context for current_app usage
        self.app = Flask(__name__)
        self.app_context = self.app.app_context()
        self.app_context.push()

        # Mock PRAW
        self.mock_praw = MagicMock()
        mock_submission = MagicMock()
        mock_submission.created_utc = datetime.now().timestamp()
        mock_submission.title = 'Test election post'
        mock_submission.selftext = 'Test content'
        mock_submission.link_flair_text = 'Politics'
        mock_submission.subreddit.display_name = 'testsub'
        mock_submission.id = '123'
        mock_submission.author.name = 'testuser'
        self.mock_praw.Reddit.return_value.subreddit.return_value.new.return_value = [mock_submission]
        rharvester.praw = self.mock_praw

    def tearDown(self):
        self.config_patcher.stop()
        self.app_context.pop()

    def test_bluesky_harvester(self):
        # Mock config file content
        self.mock_open.return_value.__enter__.return_value.read.side_effect = [
            'testuser',  # BSKY_USERNAME
            'testpass',  # BSKY_PASSWORD
            'election,politics',  # BSKY_QUERIES
            '2024-01-01T00:00:00Z',  # BSKY_START_DATE
            'http://test-enqueue',  # FISSION_ENQUEUE_URL
            '10'  # BSKY_BATCH_SIZE
        ]
        result = bharvester.harvest_old()
        self.assertEqual(result, 'OK')

    def test_mastodon_harvester(self):
        # Mock config file content
        self.mock_open.return_value.__enter__.return_value.read.side_effect = [
            'https://mastodon.test',  # MASTODON_BASE_URL
            'test-token',  # MASTODON_TOKEN
            'election,politics',  # HASHTAGS
            'http://test-enqueue',  # FISSION_ENQUEUE_URL
            '10',  # MAX_POST
            'seen:key'  # SEEN_KEY
        ]
        result = mharvester.main()
        self.assertIn('Total unique posts sent: 2', result)

    def test_reddit_harvester(self):
        # Mock environment variables
        os.environ['REDDIT_CLIENT_ID'] = 'test-client'
        os.environ['REDDIT_CLIENT_SECRET'] = 'test-secret'
        os.environ['REDDIT_USER_AGENT'] = 'test-agent'
        os.environ['REDDIT_SUBREDDITS'] = 'testsub'
        os.environ['REDDIT_QUERIES'] = 'election'
        os.environ['REDDIT_CURSOR_KEY'] = 'reddit:cursor'
        os.environ['FISSION_ENQUEUE_URL'] = 'http://test-enqueue'
        result = rharvester.harvest_once()
        self.assertEqual(result, 'OK')

if __name__ == '__main__':
    unittest.main() 