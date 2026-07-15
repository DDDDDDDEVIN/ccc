'''
 === Cluster Cloud Computing Project | Team 60 ===
 This function is implemented by Team 60
- Angqi Meng - 1268867
- Yichen Long - 1497321
- Xuan Wu - 1483104
- Zining Zhang - 1508501
- Jingqiu Meng - 1506602
'''

import json
import logging
import re
import html
from pathlib import Path
from typing import Dict, List, Any, Optional
from flask import current_app, request

CONFIG_BASE = Path("/configs/default/bprocessor-config")


def config(key: str) -> str:
    file_path = CONFIG_BASE / key
    try:
        return file_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        current_app.logger.error(f"Config file '{file_path}' not found")
        raise
    except OSError as e:
        current_app.logger.error(f"Error reading '{file_path}': {e}")
        raise


def load_mapping(config_key: str) -> Dict[str, str]:
    try:
        topic_to_aliases: Dict[str, List[str]] = json.loads(config(config_key))
        # Flatten: every alias (lower‑cased) maps to its canonical topic
        return {
            alias.lower(): topic
            for topic, alias_list in topic_to_aliases.items()
            for alias in alias_list
        }
    except json.JSONDecodeError as e:
        current_app.logger.error(f"'{config_key}' contains invalid JSON: {e}")
    except Exception as e:
        current_app.logger.error(f"load_mapping({config_key}) failed: {e}")
    return {}

# Lazy-load and cache mappings
_state_mapping = None
_topic_mapping = None

def get_state_mapping():
    global _state_mapping
    if _state_mapping is None:
        _state_mapping = load_mapping("STATE_MAPPING")
    return _state_mapping

def get_topic_mapping():
    global _topic_mapping
    if _topic_mapping is None:
        _topic_mapping = load_mapping("TOPIC_MAPPING")
    return _topic_mapping

_TAG_RE = re.compile(r"<[^>]+>")

def clean_content(post: Dict[str, Any]) -> str:
    raw = post.get("content")
    text = html.unescape(raw)
    text = _TAG_RE.sub(" ", text)
    text = " ".join(text.split())
    text = re.sub(r"\s+([?.!,])", r"\1", text)
    return text

def extract_location(post: Dict[str, Any]) -> Optional[str]:
    text = clean_content(post).lower()
    if not text:
        return None
    for alias, state in get_state_mapping().items():
        if re.search(rf"\b{re.escape(alias)}\b", text):
            return state
    return None


def extract_hashtags(post: Dict[str, Any]) -> List[str]:
    tag_objs = post.get("tags", [])
    try:
        return [t.get("name") for t in tag_objs if isinstance(t, dict) and t.get("name")]
    except Exception:
        return []


def extract_topic(post: Dict[str, Any]) -> Optional[str]:
    query = (
        post.get("matched_query")
        or post.get("query")
        or ""
    ).lower()
    return get_topic_mapping().get(query)


def process_post(post: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        created_at = post.get("created_at")
        text = clean_content(post).strip()
        location = extract_location(post)
        tags = extract_hashtags(post)
        topic = extract_topic(post)
        # Identify platform heuristically
        source = "mastodon"
        post_id = post.get("id")
        user_id = post.get("account", {}).get('acct')

        return {
            "created_at": created_at,
            "text": text,
            "location": location,
            "source": source,
            "tags": tags,
            "post_id": post_id,
            "user_id": user_id,
            "topic": topic,
        }
    except Exception as e:
        current_app.logger.warning(f"process_post failed: {e}")
        return None


def main():
    current_app.logger.info("bprocessor started")

    try:
        request_data: List[Dict[str, Any]] = request.get_json(force=True, silent=False)
    except Exception as e:
        current_app.logger.error(f"Could not decode JSON body: {e}")
        return "ERROR"

    if not isinstance(request_data, list):
        current_app.logger.error("Input JSON must be a list of posts")
        return "ERROR"

    current_app.logger.info(f"Received {len(request_data)} posts")

    batch: List[Dict[str, Any]] = [
        transformed
        for post in request_data
        if (transformed := process_post(post))
    ]

    if not batch:
        current_app.logger.info("No valid posts processed")
        return "[]"

    try:
        return json.dumps(batch, ensure_ascii=False)
    except TypeError as e:
        current_app.logger.error(f"JSON serialisation failed: {e}")
        return "ERROR"
