import threading
import time
import os
from typing import Any, Dict, List, Optional
import requests

# Simple thread-safe TTL cache
_cache: Dict[str, Dict[str, Any]] = {}
_cache_lock = threading.Lock()
CACHE_TTL = int(os.environ.get("API_CACHE_TTL", "300"))


def cache_get(key: str) -> Optional[Any]:
    with _cache_lock:
        item = _cache.get(key)
        if not item:
            return None
        if time.time() - item["ts"] > CACHE_TTL:
            del _cache[key]
            return None
        return item["value"]


def cache_set(key: str, value: Any) -> None:
    with _cache_lock:
        _cache[key] = {"ts": time.time(), "value": value}


# Reuse a single Session for connection pooling
_session: Optional[requests.Session] = None
_session_lock = threading.Lock()


def session() -> requests.Session:
    global _session
    with _session_lock:
        if _session is None:
            s = requests.Session()
            s.headers.update({"User-Agent": "sms-ai/1.0"})
            _session = s
        return _session


def call_perspective_cached(text: str, api_key: Optional[str]) -> Optional[Dict[str, Any]]:
    """Call Perspective API with caching. Returns parsed JSON or None."""
    if not api_key:
        print("[API Status] ❌ Perspective API call failed: No API key provided")
        return None
    key = f"perspective:{hash(text)}"
    cached = cache_get(key)
    if cached is not None:
        print("[API Status] ✓ Using cached Perspective API result")
        return cached
    try:
        url = "https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze"
        payload = {
            "comment": {"text": text},
            "languages": ["en"],
            "requestedAttributes": {"TOXICITY": {}, "INSULT": {}, "SEVERE_TOXICITY": {}, "PROFANITY": {}}
        }
        resp = session().post(url, params={"key": api_key}, json=payload, timeout=15)
        if resp.status_code == 200:
            print("[API Status] ✓ Perspective API call successful")
            j = resp.json()
            cache_set(key, j)
            return j
        else:
            print(f"[API Status] ❌ Perspective API error: Status {resp.status_code}")
            if resp.status_code == 429:
                print("[API Status] ⚠️ Perspective API rate limit reached")
            error_msg = resp.text if resp.text else "No error message"
            print(f"[API Status] Error details: {error_msg[:200]}")
    except Exception:
        pass
    return None


# Using local text analysis only
