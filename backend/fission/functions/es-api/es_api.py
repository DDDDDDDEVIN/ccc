import requests
import os
import logging
from flask import Flask, request, jsonify

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Get Elasticsearch configuration from environment variables or use defaults
ES_URL = os.getenv('ES_URL', 'https://localhost:9200')
ES_USER = os.getenv('ES_USER', 'elastic')
ES_PASSWORD = os.getenv('ES_PASSWORD', 'Mha6ElTaqEWS2mkX')

HEADERS = {
    "Accept": "application/vnd.elasticsearch+json; compatible-with=8",
    "Content-Type": "application/vnd.elasticsearch+json; compatible-with=8",
}

def get_es_connection():
    """
    Return Elasticsearch connection configuration dictionary
    """
    return {
        'url': ES_URL,
        'auth': (ES_USER, ES_PASSWORD),
        'headers': HEADERS,
        'verify': False,  # Disable SSL verify if self-signed certs are used
        'timeout': 60
    }

@app.route('/es-api/indices', methods=['GET'])
def list_indices():
    """
    List all indices in Elasticsearch cluster.
    """
    try:
        logger.info("Received request to list indices")
        es_config = get_es_connection()
        resp = requests.get(
            f"{es_config['url']}/_cat/indices?format=json",
            auth=es_config['auth'],
            headers=es_config['headers'],
            verify=es_config['verify'],
            timeout=es_config['timeout']
        )
        resp.raise_for_status()
        data = resp.json()
        indices = [item["index"] for item in data]
        return jsonify({
            'status': 'success',
            'data': indices
        })
    except Exception as e:
        logger.error(f"Error listing indices: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"Cannot retrieve index list: {str(e)}"
        }), 500

@app.route('/es-api/scroll_search', methods=['GET'])
def scroll_search():
    """
    Search documents using Elasticsearch scroll API.
    Supports two modes:
    1) Term query: when field and value are provided (for first request)
    2) Match_all query: when no field or value provided (for first request)
    For subsequent requests, use scroll_id to fetch next batches.
    """
    try:
        index = request.args.get('index')
        field = request.args.get('field')
        value = request.args.get('value')
        scroll = request.args.get('scroll', '1m')
        scroll_id = request.args.get('scroll_id')

        es_config = get_es_connection()

        if scroll_id:
            # Continue scroll with scroll_id to fetch next batch, POST request
            url = f"{es_config['url']}/_search/scroll"
            payload = {
                "scroll": scroll,
                "scroll_id": scroll_id
            }
            resp = requests.post(url, auth=es_config['auth'], headers=es_config['headers'], json=payload,
                                 verify=es_config['verify'], timeout=es_config['timeout'])
        else:
            # First request, start scroll context with query
            if not index:
                return jsonify({'status': 'error', 'message': 'Missing required parameter: index'}), 400

            url = f"{es_config['url']}/{index}/_search?scroll={scroll}"
            if field and value:
                query = {
                    "term": {
                        field: {
                            "value": value
                        }
                    }
                }
            else:
                # No field/value given, return all docs
                query = {
                    "match_all": {}
                }

            payload = {
                "size": 1000,
                "query": query
            }

            resp = requests.post(url, auth=es_config['auth'], headers=es_config['headers'], json=payload,
                                 verify=es_config['verify'], timeout=es_config['timeout'])

        resp.raise_for_status()
        resp_json = resp.json()

        hits = resp_json.get("hits", {}).get("hits", [])
        scroll_id = resp_json.get("_scroll_id", None)

        return jsonify({
            'status': 'success',
            'scroll_id': scroll_id,
            'data': [hit["_source"] for hit in hits]
        })

    except Exception as e:
        logger.error(f"Error in scroll_search: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/es-api/health', methods=['GET'])
def health_check():
    """
    Check Elasticsearch cluster health status.
    """
    try:
        logger.info("Received health check request")
        es_config = get_es_connection()
        resp = requests.get(
            f"{es_config['url']}/_cluster/health",
            auth=es_config['auth'],
            headers=es_config['headers'],
            verify=es_config['verify'],
            timeout=es_config['timeout']
        )
        resp.raise_for_status()
        return jsonify({
            'status': 'success',
            'data': resp.json()
        })
    except Exception as e:
        logger.error(f"Error checking health: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def main():
    """
    Main function for Fission or other serverless frameworks.
    """
    return app

if __name__ == '__main__':
    # Run the Flask app on all interfaces at port 8888
    app.run(host='0.0.0.0', port=8888)
