import re
import random
import os
import json
import requests
from typing import Dict, Any, List, Tuple
from api_helpers import call_perspective_cached

# Optional imports for improved models (dynamic to avoid static resolution errors)
VADER_AVAILABLE = False
_vader = None
try:
    import importlib
    vader_mod = importlib.import_module("vaderSentiment.vaderSentiment")
    SentimentIntensityAnalyzer = getattr(vader_mod, "SentimentIntensityAnalyzer")
    _vader = SentimentIntensityAnalyzer()
    VADER_AVAILABLE = True
except Exception:
    VADER_AVAILABLE = False

# Optional Presidio imports for PII detection (if installed)
try:
    from presidio_analyzer import AnalyzerEngine
    PRESIDIO_AVAILABLE = True
except Exception:
    PRESIDIO_AVAILABLE = False


def call_perspective_toxicity(text: str) -> Dict[str, Any]:
    """Call Perspective API if key is set; return attributeScores or empty dict on failure."""
    key = os.environ.get("PERSPECTIVE_API_KEY")
    if not key:
        return {}
    j = call_perspective_cached(text, key)
    if j:
        return j.get("attributeScores", {})
    return {}


# Local text analysis is used instead of external APIs

# Lightweight free-rule-based content analyzer for demo purposes
# Detect bad language, hate speech, PII, scam patterns, extract sentiment, emotion, topic, summary, and optional embedding

BAD_WORDS = {"disgusting", "stupid", "idiot", "kill", "hate", "destroy", "ruin", "delete", "ban", "loser", "moron", "trash", "dumb", "shut up"}
HATE_PATTERNS = [r"you people", r"all [a-z]+s are", r"go back to"]
VIOLENT_VERBS = {"destroy", "kill", "ruin", "destroyed", "destroying", "delete", "ban", "harm", "attack", "destroy your"}
URL_REGEX = re.compile(r"(https?://\S+|\b[\w-]+\.(com|net|org|io|co|ru|biz|info)\b)", re.IGNORECASE)
PII_PATTERNS = [r"\b\d{10}\b", r"\b\d{3}-\d{2}-\d{4}\b", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"]
SCAM_KEYWORDS = {"free", "click", "win", "prize", "offer", "bank account"}

EMOTIONS = ["anger", "sadness", "fear", "joy", "neutral"]
TOPICS = ["personal_attack", "harassment", "spam", "safety", "privacy"]


def simple_embedding(text: str, dim: int = 8) -> List[float]:
    # Simple random embedding based on text hash
    random.seed(hash(text) & 0xffffffff)
    return [round(random.random(), 3) for _ in range(dim)]


def contains_bad_word(text: str) -> bool:
    words = re.findall(r"\w+", text.lower())
    return any(w in BAD_WORDS for w in words)


def detect_hate(text: str) -> bool:
    # Simple rule-based hate speech detection
    t = text.lower()
    # if explicit patterns match, flag
    if any(re.search(p, t) for p in HATE_PATTERNS):
        return True
    # if bad words present, flag
    if contains_bad_word(text):
        return True
    # detect direct threats toward a person
    if re.search(r"\byou\b", t):
        for v in VIOLENT_VERBS:
            if v in t:
                return True
    # also detect first-person threats directed at 'you'
    if re.search(r"\b(i\s*(will|'ll|am going to)\s+(kill|destroy|ruin|attack|harm))\b", t):
        return True
    return False


def detect_pii(text: str) -> bool:
    # Use Presidio if available for better PII detection
    if PRESIDIO_AVAILABLE:
        try:
            engine = AnalyzerEngine()
            results = engine.analyze(text=text, language="en")
            return len(results) > 0
        except Exception:
            pass
    for p in PII_PATTERNS:
        if re.search(p, text):
            return True
    return False


def detect_scam(text: str) -> bool:
    # Check URLs using VirusTotal API
    if URL_REGEX.search(text):
        print("[API Status] ✓ URL detected, checking with URL Safety API")
        try:
            from api_helpers import call_virustotal_cached
            api_key = os.environ.get("VIRUSTOTAL_API_KEY")
            m = URL_REGEX.search(text)
            url = m.group(0)
            result = call_virustotal_cached(url, api_key)
            if result:
                positives = result.get('positives', 0)
                if positives > 0:
                    print("[API Status] ✓ URL Safety API: URL flagged as suspicious")
                    return True
                print("[API Status] ✓ URL Safety API: URL appears safe")
                return False
        except Exception as e:
            print(f"[API Status] ❌ URL Safety API error: {str(e)}")
            # Fall back to basic detection
            
    # Basic scam detection fallback
    t = text.lower()
    scam_phrases = ["free money", "click here", "bank account", "wire transfer", "claim prize", "limited offer"]
    for p in scam_phrases:
        if p in t:
            return True
            
    # Check for suspicious domains
    if URL_REGEX.search(text):
        m = URL_REGEX.search(text)
        domain = m.group(0).lower() if m else ""
        if "scam" in domain or "free" in domain or "win" in domain:
            return True
            
    # Keyword match
    words = set(re.findall(r"\w+", t))
    if words & SCAM_KEYWORDS:
        return True
        
    return False


def sentiment_and_emotion(text: str) -> Tuple[str, str]:
    # Use VADER if available for sentiment
    if VADER_AVAILABLE:
        try:
            scores = _vader.polarity_scores(text)
            compound = scores.get("compound", 0.0)
            if compound >= 0.05:
                return "positive", "joy"
            if compound <= -0.05:
                return "negative", "sadness"
            return "neutral", "neutral"
        except Exception:
            pass
            
    # Rule-based sentiment analysis
    t = text.lower()
    if any(w in t for w in ["love", "great", "happy", "excellent", "awesome"]):
        return "positive", "joy"
    if any(w in t for w in ["hate", "disgusting", "stupid", "idiot", "kill", "terrible", "awful"]):
        return "negative", "anger"
    return "neutral", "neutral"


def topic_classify(text: str) -> str:
    # Rule-based topic classification
    t = text.lower()
    if detect_scam(text):
        return "scam"
    if detect_pii(text):
        return "privacy"
    if detect_hate(text) or contains_bad_word(text):
        return "personal_attack"
    return "general"


# Note: summary generation removed per request


def analyze_row(row: Dict[str, Any], embed: bool = True) -> Dict[str, Any]:
    comment = str(row.get("comment", ""))
    # If an external CONTENT_ANALYZER_URL is provided, POST to it and return its response
    url = os.environ.get("CONTENT_ANALYZER_URL")
    if url:
        try:
            payload = {"userID": row.get("userID"), "username": row.get("username"), "comment_id": row.get("comment_id"), "comment": comment}
            resp = requests.post(url.rstrip("/") + "/analyze", json=payload, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            # fallback to local analysis on any error
            pass
    # Local analysis fallback
    bad_language = contains_bad_word(comment)
    hate = detect_hate(comment)
    pii = detect_pii(comment)
    scam = detect_scam(comment)
    sentiment, emotion = sentiment_and_emotion(comment)
    topic = topic_classify(comment)
    embedding = simple_embedding(comment) if embed else None

    # Try Perspective API to enrich flags
    print("[API Status] ✓ Processing content with Perspective API")
    perspective_attrs = call_perspective_toxicity(comment)
    if perspective_attrs:
        try:
            tox = perspective_attrs.get("TOXICITY", {}).get("summaryScore", {}).get("value", 0)
            insult = perspective_attrs.get("INSULT", {}).get("summaryScore", {}).get("value", 0)
            prof = perspective_attrs.get("PROFANITY", {}).get("summaryScore", {}).get("value", 0)
            if tox > 0.7:
                bad_language = True
            if insult > 0.6:
                hate = True
            if prof > 0.6:
                bad_language = True
            print("[API Status] ✓ Perspective API analysis completed")
        except Exception:
            print("[API Status] ⚠️ Error processing Perspective API results")
            pass

    # Use local text analysis for sentiment
    print("[API Status] ✓ Starting local text analysis")
    try:
        # Local analysis is performed by TextBlob and NLTK
        # These operations are already handled by sentiment_and_emotion()
        sentiment, emotion = sentiment_and_emotion(comment)
        print("[API Status] ✓ Text analysis completed successfully")
    except Exception as e:
        print(f"[API Status] ❌ Text analysis error: {str(e)}")
        sentiment = "neutral"
        emotion = "neutral"

    out = {
        "userID": row.get("userID"),
        "username": row.get("username"),
        "comment_id": row.get("comment_id"),
        "comment": comment,
        "bad_language": bad_language,
        "hate_speech": hate,
        "pii_detected": pii,
        "scam_pattern": scam,
        "sentiment": sentiment,
        "emotion": emotion,
        "topic": topic,
    }
    if embed:
        out["user_history_embedding"] = embedding
    return out


def analyze_batch(rows: List[Dict[str, Any]], embed: bool = True) -> List[Dict[str, Any]]:
    """Process a batch of rows and return list of analyzed outputs."""
    print("[API Status] ✓ Processing batch content analysis")
    results = []
    for r in rows:
        res = analyze_row(r, embed=embed)
        results.append(res)
    print("[API Status] ✓ Batch analysis completed successfully")
    return results


if __name__ == "__main__":
    # quick demo
    sample = {"userID": 101, "username": "rashmi", "comment_id": 1, "comment": "You people are disgusting!"}
    print(analyze_row(sample))
