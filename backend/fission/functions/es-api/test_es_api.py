import requests
import json
import os
from unittest.mock import patch
from es_api import app

def mock_es_response(*args, **kwargs):
    """Mock Elasticsearch responses"""
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code
            self.text = json.dumps(json_data)

        def json(self):
            return self.json_data

        def raise_for_status(self):
            if self.status_code >= 400:
                raise requests.exceptions.HTTPError(f"HTTP {self.status_code}")

    # Mock different responses based on the URL
    url = args[0]
    if '_cluster/health' in url:
        return MockResponse({
            'status': 'green',
            'number_of_nodes': 1,
            'active_shards': 1
        }, 200)
    elif '_cat/indices' in url:
        return MockResponse([
            {'index': 'test_index_1'},
            {'index': 'test_index_2'}
        ], 200)
    elif '_search' in url:
        return MockResponse({
            'hits': {
                'hits': [
                    {'_source': {'test_field': 'test_value', 'data': 'test_data'}}
                ]
            }
        }, 200)
    return MockResponse({}, 404)

@patch('requests.get', side_effect=mock_es_response)
def test_health_endpoint(mock_get):
    """Test the health check endpoint"""
    with app.test_client() as client:
        response = client.get('/es-api/health')
        print("\nTesting /es-api/health endpoint:")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.get_data(as_text=True)}")
        return response.status_code == 200

@patch('requests.get', side_effect=mock_es_response)
def test_indices_endpoint(mock_get):
    """Test the indices endpoint"""
    with app.test_client() as client:
        response = client.get('/es-api/indices')
        print("\nTesting /es-api/indices endpoint:")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.get_data(as_text=True)}")
        return response.status_code == 200

@patch('requests.get', side_effect=mock_es_response)
def test_search_endpoint(mock_get):
    """Test the search endpoint"""
    with app.test_client() as client:
        # Test with sample parameters
        params = {
            'index': 'test_index',
            'field': 'test_field',
            'value': 'test_value',
            'size': 10
        }
        response = client.get('/es-api/search', query_string=params)
        print("\nTesting /es-api/search endpoint:")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.get_data(as_text=True)}")
        return response.status_code == 200

def main():
    """Run all tests"""
    print("Starting ES API tests...")
    
    # Test health endpoint
    health_result = test_health_endpoint()
    print(f"Health endpoint test {'PASSED' if health_result else 'FAILED'}")
    
    # Test indices endpoint
    indices_result = test_indices_endpoint()
    print(f"Indices endpoint test {'PASSED' if indices_result else 'FAILED'}")
    
    # Test search endpoint
    search_result = test_search_endpoint()
    print(f"Search endpoint test {'PASSED' if search_result else 'FAILED'}")
    
    # Print summary
    print("\nTest Summary:")
    print(f"Health endpoint: {'PASSED' if health_result else 'FAILED'}")
    print(f"Indices endpoint: {'PASSED' if indices_result else 'FAILED'}")
    print(f"Search endpoint: {'PASSED' if search_result else 'FAILED'}")

if __name__ == '__main__':
    main() 