'''
 === Cluster Cloud Computing Project | Team 60 ===
 This function is implemented by Team 60
- Angqi Meng - 1268867
- Yichen Long - 1497321
- Xuan Wu - 1483104
- Zining Zhang - 1508501
- Jingqiu Meng - 1506602
'''

import os
import requests
from redis import Redis
from flask import current_app

def get_redis_connection():
    return Redis(
        host='redis-headless.redis.svc.cluster.local',
        port=6379,
        decode_responses=True,
        socket_connect_timeout=2
    )

def config(k: str) -> str:
    with open(f'/configs/default/mastodon-config/{k}', 'r') as f:
        return f.read().strip()

def main():
    current_app.logger.propagate = False
    
    base_url = config('MASTODON_BASE_URL')
    token = config('MASTODON_TOKEN')
    hashtags = config('HASHTAGS').split(',')
    enqueue_url = config('FISSION_ENQUEUE_URL')
    limit = int(config('MAX_POST'))
    seen_key = config('SEEM_KEY')

    current_app.logger.info("Configuration loaded successfully.")

    try:
        redis = get_redis_connection()
        current_app.logger.info("Redis connection established.")
    except Exception as e:
        current_app.logger.error(f"Redis connection failed: {e}")
        return "ERROR"

    headers = {"Authorization": f"Bearer {token}"}


    total_sent = 0

    for tag in hashtags:
        tag = tag.strip()
        if not tag:
            continue

        cursor_key = f"mastodon:cursor:{tag}"
        since_id = redis.get(cursor_key)

        params = {"limit": limit}
        if since_id:
            params["since_id"] = since_id

        url = f"{base_url}/api/v1/timelines/tag/{tag}"
        try:
            res = requests.get(url, headers=headers, params=params)
            res.raise_for_status()
            posts = res.json()
        except Exception as e:
            current_app.logger.error(f"Error fetching posts for #{tag}: {e}")
            continue

        if not posts:
            current_app.logger.info(f"No new posts found for #{tag}")
            continue

        # Update since_id for this tag
        new_max = max(int(p["id"]) for p in posts)
        redis.set(cursor_key, str(new_max))

        # Deduplication: only keep unseen posts
        unique_posts = []
        for post in posts:
            post_id = post["id"]
            if not redis.sismember(seen_key, post_id):
                redis.sadd(seen_key, post_id)
                redis.expire(seen_key, 86400)
                post['matched_query'] = tag
                unique_posts.append(post)

        if unique_posts:
            try:
                res = requests.post(
                    url=enqueue_url,
                    headers={
                        'Content-Type': 'application/json',
                        'X-Fission-Params-Topic': 'mastodon'
                        },
                    json=unique_posts
                )
                res.raise_for_status()
                current_app.logger.info(f"Sent {len(unique_posts)} posts for tag #{tag}")
                total_sent += len(unique_posts)
            except Exception as e:
                current_app.logger.error(f"Error sending posts to enqueue for #{tag}: {e}")
    return f"Total unique posts sent: {total_sent}"
