import unittest
from unittest.mock import patch, MagicMock
from flask import Flask
import json
from werkzeug.exceptions import BadRequest
'''
 === Cluster Cloud Computing Project | Team 60 ===
 This test is implemented by Team 60
- Angqi Meng - 1268867
- Yichen Long - 1497321
- Xuan Wu - 1483104
- Zining Zhang - 1508501
- Jingqiu Meng - 1506602
'''
# Import the addobservations function
from backend.fission.functions.addobservations.addobservations import main as addobservations

class TestAddObservations(unittest.TestCase):
    def setUp(self):
        """Set up test environment before each test."""
        self.app = Flask(__name__)
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Mock Elasticsearch client
        self.mock_es_instance = MagicMock()
        self.mock_es_instance.index.return_value = {"_id": "test-id", "_version": 1, "result": "created"}
        self.es_patcher = patch('backend.fission.functions.addobservations.addobservations.Elasticsearch', return_value=self.mock_es_instance)
        self.mock_es = self.es_patcher.start()
        
        # Mock config function to return correct values for username and password
        def config_side_effect(key):
            if key == "ES_USERNAME":
                return "user"
            elif key == "ES_PASSWORD":
                return "pass"
            return "test_value"
        self.config_patcher = patch('backend.fission.functions.addobservations.addobservations.config', side_effect=config_side_effect)
        self.mock_config = self.config_patcher.start()

    def tearDown(self):
        """Clean up after each test."""
        self.es_patcher.stop()
        self.config_patcher.stop()
        self.app_context.pop()

    def test_successful_observation_indexing(self):
        """Test successful indexing of valid observation data."""
        test_data = [{
            "post_id": "123",
            "created_at": "2024-01-01T00:00:00Z",
            "text": "Test observation"
        }]
        
        with self.app.test_request_context(json=test_data):
            # Call the function
            result = addobservations()
            
            # Verify Elasticsearch was called correctly
            self.mock_es_instance.index.assert_called_once_with(
                index='observations',
                id='123-2024-01-01T00:00:00Z',
                body=test_data[0]
            )
            self.assertEqual(result, 'OK')

    def test_invalid_json(self):
        """Test handling of invalid JSON data."""
        with self.app.test_request_context(
            data="invalid json",
            content_type='application/json'
        ):
            # Call the function and expect BadRequest
            with self.assertRaises(BadRequest):
                addobservations()
            self.mock_es_instance.index.assert_not_called()

    def test_elasticsearch_connection_failure(self):
        """Test handling of Elasticsearch connection failure."""
        # Mock Elasticsearch connection failure
        self.mock_es.side_effect = Exception("Connection failed")
        
        test_data = [{
            "post_id": "123",
            "created_at": "2024-01-01T00:00:00Z",
            "text": "Test observation"
        }]
        
        with self.app.test_request_context(json=test_data):
            # Call the function
            result = addobservations()
            
            # Verify error response
            self.assertEqual(result, 'ERROR')
            self.mock_es_instance.index.assert_not_called()

    def test_indexing_failure(self):    
        """Test handling of indexing failure."""
        test_data = [{
            "post_id": "123",
            "created_at": "2024-01-01T00:00:00Z",
            "text": "Test observation"
        }]
        
        # Mock indexing failure
        self.mock_es_instance.index.side_effect = Exception("Indexing failed")
        
        with self.app.test_request_context(json=test_data):
            # Call the function
            result = addobservations()
            
            # Verify error response
            self.assertEqual(result, 'ERROR')
            self.mock_es_instance.index.assert_called_once()

    def test_multiple_observations(self):
        """Test successful indexing of multiple observations."""
        test_data = [
            {
                "post_id": "123",
                "created_at": "2024-01-01T00:00:00Z",
                "text": "Test observation 1"
            },
            {
                "post_id": "456",
                "created_at": "2024-01-01T01:00:00Z",
                "text": "Test observation 2"
            }
        ]
        
        with self.app.test_request_context(json=test_data):
            # Call the function
            result = addobservations()
            
            # Verify Elasticsearch was called for each observation
            self.assertEqual(self.mock_es_instance.index.call_count, 2)
            self.assertEqual(result, 'OK')

if __name__ == '__main__':
    unittest.main() 