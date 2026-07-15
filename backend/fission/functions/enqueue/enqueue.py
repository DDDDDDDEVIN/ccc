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
from typing import Dict, Any, Optional
from flask import current_app, request
import redis


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def main() -> str:
    """Message queue producer for Redis streaming.

    Handles:
    - Redis connection pooling
    - JSON payload serialization
    - Topic-based message routing via headers
    - Message size logging

    Returns:
        'OK' with HTTP 200 on successful enqueue

    Raises:
        redis.RedisError: For connection/operation failures
        JSONDecodeError: If invalid payload received
    """
    logger.info("enqueue started")
    
    # Extract routing parameters
    topic: Optional[str] = request.headers.get('X-Fission-Params-Topic')
    
    try:
        json_data: Dict[str, Any] = request.get_json()
        logger.info("Successfully get json data")
    except Exception as e:
        logger.error("Get json failure")
        return {"error": "Invalid JSON payload"}, 400

    if not isinstance(json_data, list):
        logger.error("Invalid payload: not a list")
        return {"error": "Expected a list of JSON objects"}, 400

    # Initialize Redis client with type annotation
    redis_client: redis.StrictRedis = redis.StrictRedis(
        host='redis-headless.redis.svc.cluster.local',
        socket_connect_timeout=5,
        decode_responses=False
    )
    
    # Publish message to queue
    redis_client.lpush(
        topic,
        json.dumps(json_data).encode('utf-8')
    )
    
    # Structured logging with message metrics
    logger.info(
        f'Enqueued to {topic} topic - '
        f'Payload size: {len(json_data)} bytes'
    )
    
    return 'OK'