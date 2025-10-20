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
        return None
    key = f"perspective:{hash(text)}"
    cached = cache_get(key)
    if cached is not None:
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
            j = resp.json()
            cache_set(key, j)
            return j
    except Exception:
        pass
    return None


def call_hf_single_cached(model: str, payload: Any, hf_key: Optional[str]) -> Optional[Any]:
    """Call HF Inference API for a single input with caching."""
    if not hf_key or not model:
        return None
    text_key = ""
    try:
        # make a cache key from payload conservatively
        if isinstance(payload, dict) and "inputs" in payload:
            text_key = str(payload.get("inputs"))
        else:
            text_key = str(payload)
    except Exception:
        text_key = str(payload)
    key = f"hf:{model}:{hash(text_key)}"
    cached = cache_get(key)
    if cached is not None:
        return cached
    try:
        url = f"https://api-inference.huggingface.co/models/{model}"
        headers = {"Authorization": f"Bearer {hf_key}"}
        resp = session().post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            j = resp.json()
            cache_set(key, j)
            return j
    except Exception:
        pass
    return None


def call_hf_batch(model: str, texts: List[str], hf_key: Optional[str]) -> List[Optional[Any]]:
    """Call HF Inference API in batch for a list of texts. Caches per-text responses.

    Returns list aligned with `texts` containing parsed responses or None.
    """
    if not hf_key or not model:
        return [None] * len(texts)
    results: List[Optional[Any]] = [None] * len(texts)
    to_call_indices = []
    payload_texts = []
    for i, t in enumerate(texts):
        k = f"hf:{model}:{hash(t)}"
        c = cache_get(k)
        if c is not None:
            results[i] = c
        else:
            to_call_indices.append(i)
            payload_texts.append(t)

    if not to_call_indices:
        return results

    # Try batched call
    try:
        url = f"https://api-inference.huggingface.co/models/{model}"
        headers = {"Authorization": f"Bearer {hf_key}"}
        resp = session().post(url, headers=headers, json={"inputs": payload_texts}, timeout=60)
        if resp.status_code == 200:
            j = resp.json()
            # If HF returns single object for batched inputs or list
            if isinstance(j, list):
                for k, idx in enumerate(to_call_indices):
                    out = j[k] if k < len(j) else None
                    results[idx] = out
                    cache_set(f"hf:{model}:{hash(payload_texts[k])}", out)
            else:
                # single object returned; apply same to all
                for idx, txt in zip(to_call_indices, payload_texts):
                    results[idx] = j
                    cache_set(f"hf:{model}:{hash(txt)}", j)
            return results
    except Exception:
        pass

    # Fallback: call individually
    for k_idx, idx in enumerate(to_call_indices):
        txt = payload_texts[k_idx]
        try:
            url = f"https://api-inference.huggingface.co/models/{model}"
            headers = {"Authorization": f"Bearer {hf_key}"}
            resp = session().post(url, headers=headers, json={"inputs": txt}, timeout=30)
            if resp.status_code == 200:
                out = resp.json()
                results[idx] = out
                cache_set(f"hf:{model}:{hash(txt)}", out)
            else:
                results[idx] = None
        except Exception:
            results[idx] = None

    return results
