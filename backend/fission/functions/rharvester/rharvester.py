'''
 === Cluster Cloud Computing Project | Team 60 ===
 This function is implemented by Team 60
- Angqi Meng - 1268867
- Yichen Long - 1497321
- Xuan Wu - 1483104
- Zining Zhang - 1508501
- Jingqiu Meng - 1506602
'''
import praw, requests, redis, os, logging
from datetime import datetime
from flask import current_app

def config(k: str) -> str:
    return os.getenv(k) or open(f"/configs/default/reddit-config/{k}").read().strip()

def reddit_client():
    return praw.Reddit(
        client_id=config("REDDIT_CLIENT_ID"),
        client_secret=config("REDDIT_CLIENT_SECRET"),
        user_agent=config("REDDIT_USER_AGENT"),
    )

def get_redis_connection():
    return redis.Redis(
        host='redis-headless.redis.svc.cluster.local',
        port=6379,
        decode_responses=True,
        socket_connect_timeout=2
    )

def load_cursor():
    r = get_redis_connection()
    key = config("REDDIT_CURSOR_KEY")
    ts = r.get(key)
    return float(ts) if ts else 0

def save_cursor(timestamp):
    r = get_redis_connection()
    key = config("REDDIT_CURSOR_KEY")
    r.set(key, str(timestamp))
    current_app.logger.info(f"Saved cursor: {timestamp}")

def harvest_once():
    reddit = reddit_client()
    subreddits = config("REDDIT_SUBREDDITS").replace(",", "+")
    keywords = [k.strip().lower() for k in config("REDDIT_QUERIES").split(",")]
    enqueue_url = config("FISSION_ENQUEUE_URL")

    last_seen = load_cursor()
    max_seen = last_seen
    matched = []

    for post in reddit.subreddit(subreddits).new(limit=100):
        if post.created_utc <= last_seen:
            continue

        if any(kw in post.title.lower() or kw in post.selftext.lower() for kw in keywords):
            matched.append({
                "created_at": datetime.utcfromtimestamp(post.created_utc).isoformat(),
                "text": f"{post.title}\n{post.selftext}".strip(),
                "tags": [post.link_flair_text] if post.link_flair_text else [],
                "source": "reddit",
                "post_id": post.id,
                "user_id": post.author.name if post.author else None,
                "topic": next((kw for kw in keywords if kw in post.title.lower() or kw in post.selftext.lower()), None),
                "subreddit": post.subreddit.display_name
            })


        if post.created_utc > max_seen:
            max_seen = post.created_utc

    if not matched:
        current_app.logger.info("No new matching posts")
        return "DONE"

    try:
        res = requests.post(enqueue_url, json=matched, headers={"Content-Type": "application/json", 'X-Fission-Params-Topic': 'reddit'})
        res.raise_for_status()
        current_app.logger.info(f"Sent {len(matched)} posts to Fission")
        save_cursor(max_seen)
    except Exception as e:
        current_app.logger.error(f"Failed to enqueue: {e}")
        return "ERROR"

    return "OK"

def main():
    result = harvest_once()
    current_app.logger.info(f"Cursor-based Reddit harvester result: {result}")
    return result
