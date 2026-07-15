import unittest
from unittest.mock import patch, MagicMock, call
from flask import Flask
import json
#use python -m unittest test.test_end_to_end to run the end to end test
'''
 === Cluster Cloud Computing Project | Team 60 ===
 This test is implemented by Team 60
- Angqi Meng - 1268867
- Yichen Long - 1497321
- Xuan Wu - 1483104
- Zining Zhang - 1508501
- Jingqiu Meng - 1506602
'''
# Import the functions to test
from backend.fission.functions.rharvester.rharvester import main as rharvester
from backend.fission.functions.enqueue.enqueue import main as enqueue
from backend.fission.functions.rprocessor.rprocessor import main as rprocessor
from backend.fission.functions.addobservations.addobservations import main as addobservations

class TestEndToEnd(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test."""
        self.app = Flask(__name__)
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Mock Redis client for enqueue
        self.mock_enqueue_redis = MagicMock()
        self.enqueue_redis_patcher = patch('backend.fission.functions.enqueue.enqueue.redis', autospec=True)
        self.mock_redis = self.enqueue_redis_patcher.start()
        self.mock_redis.StrictRedis.return_value = self.mock_enqueue_redis
        
        # Mock Redis client for rharvester
        self.mock_rharvester_redis = MagicMock()
        self.rharvester_redis_patcher = patch('backend.fission.functions.rharvester.rharvester.get_redis_connection', return_value=self.mock_rharvester_redis)
        self.mock_rharvester_redis = self.rharvester_redis_patcher.start()
        
        # Mock load_mapping for rprocessor
        def load_mapping_side_effect(mapping_type):
            if mapping_type == "STATE_MAPPING":
                return {
                    "sydney": "nsw",
                    "melbourne": "vic",
                    "brisbane": "qld"
                }
            elif mapping_type == "TOPIC_MAPPING":
                return {
                    "election": "election",
                    "vote": "election",
                    "politics": "politics"
                }
            return {}
        self.load_mapping_patcher = patch('backend.fission.functions.rprocessor.rprocessor.load_mapping', side_effect=load_mapping_side_effect)
        self.mock_load_mapping = self.load_mapping_patcher.start()
        
        # Mock Elasticsearch client
        self.mock_es_instance = MagicMock()
        self.mock_es_instance.index.return_value = {"_id": "test-id", "_version": 1, "result": "created"}
        self.es_patcher = patch('backend.fission.functions.addobservations.addobservations.Elasticsearch', return_value=self.mock_es_instance)
        self.mock_es = self.es_patcher.start()
        
        # Mock config function for addobservations
        def addobs_config_side_effect(key):
            config_values = {
                "ES_USERNAME": "user",
                "ES_PASSWORD": "pass"
            }
            return config_values.get(key, "test_value")
        self.addobs_config_patcher = patch('backend.fission.functions.addobservations.addobservations.config', side_effect=addobs_config_side_effect)
        self.mock_addobs_config = self.addobs_config_patcher.start()

        # Mock config function for rharvester
        def rharvester_config_side_effect(key):
            config_values = {
                "REDDIT_CLIENT_ID": "test_client_id",
                "REDDIT_CLIENT_SECRET": "test_client_secret",
                "REDDIT_USER_AGENT": "test_user_agent",
                "REDDIT_SUBREDDITS": "test_subreddit",
                "REDDIT_QUERIES": "test_query",  # This will be used to match posts
                "FISSION_ENQUEUE_URL": "http://test-enqueue-url",
                "REDDIT_CURSOR_KEY": "test_cursor_key"
            }
            return config_values.get(key, "test_value")
        self.rharvester_config_patcher = patch('backend.fission.functions.rharvester.rharvester.config', side_effect=rharvester_config_side_effect)
        self.mock_rharvester_config = self.rharvester_config_patcher.start()

        # Mock Reddit client
        self.mock_reddit_instance = MagicMock()
        self.reddit_patcher = patch('praw.Reddit', return_value=self.mock_reddit_instance)
        self.mock_reddit = self.reddit_patcher.start()

        # Mock requests
        self.requests_patcher = patch('requests.post')
        self.mock_requests = self.requests_patcher.start()
        self.mock_requests.return_value = MagicMock(raise_for_status=lambda: None)

    def tearDown(self):
        """Clean up after each test."""
        self.enqueue_redis_patcher.stop()
        self.rharvester_redis_patcher.stop()
        self.load_mapping_patcher.stop()
        self.es_patcher.stop()
        self.addobs_config_patcher.stop()
        self.rharvester_config_patcher.stop()
        self.reddit_patcher.stop()
        self.requests_patcher.stop()
        self.app_context.pop()

    def test_end_to_end_flow(self):
        """Test the end-to-end flow from harvesting a post to indexing it in Elasticsearch."""
        # Sample input post
        input_post = {
            "text": "Hello from Sydney!",
            "created_at": "2024-01-01T00:00:00Z",
            "post_id": "123",
            "user_id": "testuser",
            "topic": "election",
            "tags": ["election", "vote"],
            "subreddit": "r/sydney"
        }
        
        # Mock Reddit subreddit response
        mock_subreddit = MagicMock()
        mock_post = MagicMock()
        mock_post.created_utc = 1704067200  # 2024-01-01T00:00:00Z
        mock_post.title = "test_query in Sydney!"  # Include the test query in the title
        mock_post.selftext = "Hello from Sydney!"
        mock_post.id = "123"
        mock_post.author = MagicMock(name="testuser")
        mock_post.link_flair_text = "election"
        mock_post.subreddit = MagicMock(display_name="sydney")
        mock_subreddit.new.return_value = [mock_post]
        self.mock_reddit_instance.subreddit.return_value = mock_subreddit
        
        # Mock Redis cursor operations
        self.mock_rharvester_redis.get.return_value = "0"  # Initial cursor value
        self.mock_rharvester_redis.set.return_value = True  # Successful cursor update
        
        # Step 1: Harvest the post using rharvester
        harvest_result = rharvester()
        self.assertEqual(harvest_result, 'OK')
        
        # Step 2: Enqueue the harvested post using enqueue
        with self.app.test_request_context(json=[input_post], headers={'X-Fission-Params-Topic': 'reddit'}):
            enqueue_result = enqueue()
            self.assertEqual(enqueue_result, 'OK')
            
            # Get the actual call arguments
            actual_call = self.mock_enqueue_redis.lpush.call_args
            self.assertIsNotNone(actual_call, "lpush was not called")
            
            # Verify the topic
            self.assertEqual(actual_call.args[0], 'reddit')
            
            # Parse and compare the JSON data
            actual_data = json.loads(actual_call.args[1].decode('utf-8'))
            expected_data = [input_post]
            self.assertEqual(actual_data, expected_data)
        
        # Step 3: Process the post using rprocessor
        with self.app.test_request_context(json=[input_post]):
            processed_result = rprocessor()
            processed_data = json.loads(processed_result)
            self.assertEqual(len(processed_data), 1)
            self.assertEqual(processed_data[0]["location"], "nsw")
            self.assertEqual(processed_data[0]["source"], "reddit")
            self.assertEqual(processed_data[0]["topic"], "election")
        
        # Step 4: Index the processed post using addobservations
        with self.app.test_request_context(json=processed_data):
            indexing_result = addobservations()
            self.assertEqual(indexing_result, 'OK')
            self.mock_es_instance.index.assert_called_once_with(
                index='observations',
                id='123-2024-01-01T00:00:00Z',
                body=processed_data[0]
            )

if __name__ == '__main__':
    unittest.main() 