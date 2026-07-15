'''
 === Cluster Cloud Computing Project | Team 60 ===
 This function is implemented by Team 60
- Angqi Meng - 1268867
- Yichen Long - 1497321
- Xuan Wu - 1483104
- Zining Zhang - 1508501
- Jingqiu Meng - 1506602
'''
import json, logging, re, os
from pathlib import Path
from typing import Dict, List, Any, Optional
from flask import current_app, request

# Default config path
DEFAULT_CONFIG_BASE = Path("/configs/default/bprocessor-config")

# Allow override via environment variable
CONFIG_BASE = Path(os.environ.get("CONFIG_BASE", DEFAULT_CONFIG_BASE))

def config(key: str) -> str:
    file_path = CONFIG_BASE / key
    try:
        return file_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError as e:
        if current_app:
            current_app.logger.error(f"Config file '{file_path}' not found")
        raise
    except OSError as e:
        if current_app:
            current_app.logger.error(f"Error reading '{file_path}': {e}")
        raise

def load_mapping(config_key: str) -> Dict[str, str]:
    try:
        topic_to_aliases: Dict[str, List[str]] = json.loads(config(config_key))
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

def extract_location(post: Dict[str, Any]) -> Optional[str]:
    text = post.get("record", {}).get("text", "").lower()
    if not text:
        return None
    for alias, state in get_state_mapping().items():
        if re.search(rf"\b{re.escape(alias)}\b", text):
            return state
    return None

def extract_hashtags(post: Dict[str, Any]) -> List[str]:
    text = post.get("record", {}).get("text", "")
    return re.findall(r"#\w+", text) if text else []

def extract_topic(post: Dict[str, Any]) -> Optional[str]:
    try:
        query = post.get("matched_query").lower()
        topic = get_topic_mapping().get(query)
    except Exception as e:
        current_app.logger.error("No matched query")
    
    if topic == None:
        current_app.logger.error("Missing topic")
    return topic

def process_post(post: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        return {
            "created_at": post.get("record", {}).get("created_at"),
            "text": post.get("record", {}).get("text", "").strip(),
            "location": extract_location(post),
            "source": "bluesky",
            "tags": extract_hashtags(post),
            "post_id": post.get("uri"),
            "user_id": post.get("author", {}).get("handle"),
            "topic": extract_topic(post),
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

