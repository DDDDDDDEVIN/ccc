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
from typing import Optional, Dict, Any
from flask import current_app, request
from elasticsearch8 import Elasticsearch
from string import Template

# Query templates
date_query = Template('''{
    "range": {
        "created_at": {
            "gte": "${date}T00:00:00",
            "lte": "${date}T23:59:59"
        }
    }
}''')

date_topic_query = Template('''{
    "bool": {
        "must": [
            {"match": {"topic": "${topic}"}},
            {"range": {
                "created_at": {
                    "gte": "${date}T00:00:00",
                    "lte": "${date}T23:59:59"
                }
            }}
        ]
    }
}''')

def main() -> Dict[str, Any]:
    """Return number of posts on a given date and optional topic from ElasticSearch."""
    req = request
    date: Optional[str] = req.headers.get('X-Fission-Params-Date')
    topic: Optional[str] = req.headers.get('X-Fission-Params-Topic')

    if not date:
        current_app.logger.error('Missing required date parameter')
        return {'error': 'Date parameter required'}, 400

    es_client: Elasticsearch = Elasticsearch(
        'https://elasticsearch-master.elastic.svc.cluster.local:9200',
        verify_certs=False,
        ssl_show_warn=False,
        basic_auth=('elastic', 'Mha6ElTaqEWS2mkX')
    )

    try:
        query = json.loads(
            date_topic_query.substitute(date=date, topic=topic)
            if topic else
            date_query.substitute(date=date)
        )

        query_body = {
            "query": query,
            "track_total_hits": True
        }

        res = es_client.search(index='observations*', body=query_body)
        return {
            'post_count': res.get('hits', {}).get('total', {}).get('value', 0),
            'filters': {
                'date': date,
                'topic': topic if topic else 'N/A'
            }
        }

    except Exception as e:
        current_app.logger.error(f'ElasticSearch error: {e}')
        return {'error': 'ElasticSearch query failed'}, 500
