'''
 === Cluster Cloud Computing Project | Team 60 ===
 This function is implemented by Team 60
- Angqi Meng - 1268867
- Yichen Long - 1497321
- Xuan Wu - 1483104
- Zining Zhang - 1508501
- Jingqiu Meng - 1506602
'''
import logging, os, requests
from datetime import datetime
from atproto import Client
import redis
from flask import current_app
from dateutil.parser import parse

def get_redis_connection():
    return redis.Redis(
        host='redis-headless.redis.svc.cluster.local',
        port=6379,
        decode_responses=True,
        socket_connect_timeout=2
    )

def load_cursor(query):
    try:
        r = get_redis_connection()
        return r.get(f"bsky:{query}:cursor")
    except redis.RedisError as e:
        current_app.logger.error(f"Redis error when loading cursor: {e}")
        return None

def save_cursor(query: str, cursor: str):
    r = get_redis_connection()
    r.set(f"bsky:{query}:cursor", cursor)
    current_app.logger.info(f"Saved cursor: {cursor}")

def config(k: str) -> str:
    with open(f'/configs/default/bluesky-config/{k}', 'r') as f:
        return f.read().strip()

def harvest_old() -> str:
    username = config('BSKY_USERNAME')
    app_password = config('BSKY_PASSWORD')
    queries = [q.strip() for q in config('BSKY_QUERIES').split(',')]
    start_date_str = config('BSKY_START_DATE')
    enqueue_url = config('FISSION_ENQUEUE_URL')
    election_start = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))

    max_posts = 100
    post_batch = int(config("BSKY_BATCH_SIZE"))

    if not username or not app_password:
        current_app.logger.error("Missing credentials")
        return "ERROR"

    try:
        client = Client()
        client.login(username, app_password)
        current_app.logger.info("login succeed")
    except Exception as e:
        current_app.logger.error(f"login failed: {e}")
        return "ERROR"

    seen = set()
    all_filtered = []
    stop = False

    for query in queries:
        cursor = load_cursor(query)
        try:
            current_app.logger.info(f"Querying BlueSky with cursor={cursor}, query='{query}'")
            result = client.app.bsky.feed.search_posts({
                'q': query,
                'limit': max_posts,
                'cursor': cursor,
                'sort': 'latest'
            })
            current_app.logger.info(f"Received {len(result.posts)} posts from BlueSky")
        except Exception as e:
            current_app.logger.error(f"search_posts() failed: {e}", exc_info=True)
            continue
        
        for post in result.posts:
            try:
                created_str = post.record.created_at
                if not created_str:
                    continue
                created = parse(created_str)

                if created < election_start:
                    stop = True
                    break

                if post.uri not in seen:
                    seen.add(post.uri)
                    post_dict = post.dict()
                    post_dict["matched_query"] = query
                    all_filtered.append(post_dict)
            except Exception as e:
                current_app.logger.warning(f"Skipping post due to validation error: {e}")
                continue
        next_cursor = result.cursor if result else None
        if next_cursor and not stop:
            save_cursor(query, next_cursor)
        else:
            current_app.logger.info(f"Reached end of historical range for query:{query}")
            continue

        if stop:
            break

    if not all_filtered:
        current_app.logger.info("No qualifying posts after start date")
        return "OK"

    for i in range(0, len(all_filtered), post_batch):
        chunk = all_filtered[i:i + post_batch]
        

        try:
            res = requests.post(
                url=enqueue_url,
                headers={
                    'Content-Type': 'application/json',
                    'X-Fission-Params-Topic': 'bluesky'
                },
                json=chunk
            )
            
            res.raise_for_status()
            current_app.logger.info(f"Sent batch of {len(chunk)} posts")
        except Exception as e:
            current_app.logger.error(f"Failed to send posts: {e}", exc_info=True)

    return "OK"

def main():
    result = harvest_old()
    current_app.logger.info(f"Harvester result: {result}")
    return result
