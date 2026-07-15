import unittest
from unittest.mock import patch, MagicMock
from flask import Flask
import json
#use to run the test: python -m unittest test.test_enqueue
'''
 === Cluster Cloud Computing Project | Team 60 ===
 This test is implemented by Team 60
- Angqi Meng - 1268867
- Yichen Long - 1497321
- Xuan Wu - 1483104
- Zining Zhang - 1508501
- Jingqiu Meng - 1506602
'''
# Import the enqueue function
from backend.fission.functions.enqueue.enqueue import main as enqueue

# use python -m unittest test/test_enqueue.py -v to run the test
class TestEnqueue(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test."""
        self.app = Flask(__name__)
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Mock Redis client
        self.redis_patcher = patch('redis.StrictRedis')
        self.mock_redis = self.redis_patcher.start()
        self.mock_redis_instance = MagicMock()
        self.mock_redis.return_value = self.mock_redis_instance

    def tearDown(self):
        """Clean up after each test."""
        self.redis_patcher.stop()
        self.app_context.pop()

    def test_successful_enqueue(self):
        """Test successful enqueue of valid JSON data."""
        test_data = [{"id": 1, "text": "test"}]
        
        with self.app.test_request_context(
            json=test_data,
            headers={'X-Fission-Params-Topic': 'test-topic'}
        ):
            # Call the function
            result = enqueue()
            
            # Verify Redis was called correctly
            self.mock_redis_instance.lpush.assert_called_once_with(
                'test-topic',
                json.dumps(test_data).encode('utf-8')
            )
            self.assertEqual(result, 'OK')

    def test_invalid_json(self):
        """Test handling of invalid JSON data."""
        with self.app.test_request_context(
            data="invalid json",
            content_type='application/json',
            headers={'X-Fission-Params-Topic': 'test-topic'}
        ):
            # Call the function
            result, status_code = enqueue()
            
            # Verify error response
            self.assertEqual(status_code, 400)
            self.assertEqual(result, {"error": "Invalid JSON payload"})
            self.mock_redis_instance.lpush.assert_not_called()

    def test_non_list_json(self):
        """Test handling of non-list JSON data."""
        test_data = {"not": "a list"}
        
        with self.app.test_request_context(
            json=test_data,
            headers={'X-Fission-Params-Topic': 'test-topic'}
        ):
            # Call the function
            result, status_code = enqueue()
            
            # Verify error response
            self.assertEqual(status_code, 400)
            self.assertEqual(result, {"error": "Expected a list of JSON objects"})
            self.mock_redis_instance.lpush.assert_not_called()

    def test_missing_topic(self):
        """Test handling of missing topic header."""
        test_data = [{"id": 1, "text": "test"}]
        
        with self.app.test_request_context(
            json=test_data
        ):
            # Call the function
            result = enqueue()
            
            # Verify Redis was called with None topic
            self.mock_redis_instance.lpush.assert_called_once_with(
                None,
                json.dumps(test_data).encode('utf-8')
            )
            self.assertEqual(result, 'OK')

if __name__ == '__main__':
    unittest.main() 