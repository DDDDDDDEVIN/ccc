'''
 === Cluster Cloud Computing Project | Team 60 ===
 This function is implemented by Team 60
- Angqi Meng - 1268867
- Yichen Long - 1497321
- Xuan Wu - 1483104
- Zining Zhang - 1508501
- Jingqiu Meng - 1506602
'''
import logging
import json
from typing import Dict, List, Any
from flask import current_app, request
from elasticsearch8 import Elasticsearch


def config(k: str) -> str:
    with open(f'/configs/default/addobservations-config/{k}', 'r') as f:
        return f.read().strip()

def main() -> str:
    """Process and index weather observation data into Elasticsearch.

    Handles:
    - Elasticsearch client initialization with security credentials
    - Suppression of SSL warnings for self-signed certificates
    - Bulk indexing of observation records
    - Document ID generation using station ID and timestamp
    - Request payload validation and logging

    Returns:
        'ok' on successful processing of all observations

    Raises:
        JSONDecodeError: If invalid JSON payload received
        ElasticsearchException: For indexing failures
    """
    # Initialize Elasticsearch client
    try:
        es_client: Elasticsearch = Elasticsearch(
            'https://elasticsearch-master.elastic.svc.cluster.local:9200',
            verify_certs=False,
            ssl_show_warn=False,
            basic_auth=(config("ES_USERNAME"), config("ES_PASSWORD"))
        )
        current_app.logger.info(f"Elastic Search connection established")
    except Exception as e:
        current_app.logger.error(f"Elastic Search connection failed")

    # Validate and parse request payload
    request_data: List[Dict[str, Any]] = request.get_json(force=True)
    current_app.logger.info(f'Processing {len(request_data)} observations')

    # Index each observation
    for observation in request_data:
        doc_id: str = f'{observation["post_id"]}-{observation["created_at"]}'
        try:
            index_response: Dict[str, Any] = es_client.index(
                index='observations',
                id=doc_id,
                body=observation
            )
            current_app.logger.info(
                f'Indexed observation {doc_id} - '
                f'Version: {index_response["_version"]}'
            )
        except Exception as e:
            current_app.logger.error(f"store observations failed")
            return "ERROR"

    return 'OK'
