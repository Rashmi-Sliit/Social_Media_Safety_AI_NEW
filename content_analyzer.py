import re
import random
import os
import json
import requests
from typing import Dict, Any, List, Tuple
from api_helpers import call_hf_batch, call_perspective_cached

# Optional imports for improved models (dynamic to avoid static resolution errors)
VADER_AVAILABLE = False
SBERT_AVAILABLE = False
TRANSFORMERS_AVAILABLE = False
_vader = None
_sbert_model = None
try:
    import importlib
    vader_mod = importlib.import_module("vaderSentiment.vaderSentiment")
    SentimentIntensityAnalyzer = getattr(vader_mod, "SentimentIntensityAnalyzer")
    _vader = SentimentIntensityAnalyzer()
    VADER_AVAILABLE = True
except Exception:
    VADER_AVAILABLE = False

try:
    import importlib
    st_mod = importlib.import_module("sentence_transformers")
    SentenceTransformer = getattr(st_mod, "SentenceTransformer")
    _sbert_model = SentenceTransformer('all-MiniLM-L6-v2')
    SBERT_AVAILABLE = True
except Exception:
    SBERT_AVAILABLE = False

try:
    import importlib
    transformers_mod = importlib.import_module("transformers")
    pipeline = getattr(transformers_mod, "pipeline")
    TRANSFORMERS_AVAILABLE = True
except Exception:
    TRANSFORMERS_AVAILABLE = False

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


def call_huggingface_model(model: str, payload: Any) -> Any:
    """Generic call to Hugging Face Inference API for a given model name.
    Returns the JSON-decoded response or None on failure.
    Requires HUGGINGFACE_API_KEY in env.
    """
    # Use api_helpers batch/single cached calls where appropriate
    hf_key = os.environ.get("HUGGINGFACE_API_KEY")
    if not hf_key or not model:
        return None
    # For single-call convenience, use call_hf_batch on single-item list and return first
    try:
        res = call_hf_batch(model, [payload.get("inputs") if isinstance(payload, dict) else payload], hf_key)
        if res and len(res) > 0:
            return res[0]
    except Exception:
        pass
    return None

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
    # Prefer sentence-transformers if available
    if SBERT_AVAILABLE:
        try:
            emb = _sbert_model.encode([text])[0]
            # emb may be numpy array
            try:
                lst = emb.tolist()
            except Exception:
                lst = list(emb)
            return [float(x) for x in lst]
        except Exception:
            pass
    # Fallback to random embedding
    random.seed(hash(text) & 0xffffffff)
    return [round(random.random(), 3) for _ in range(dim)]


def contains_bad_word(text: str) -> bool:
    words = re.findall(r"\w+", text.lower())
    return any(w in BAD_WORDS for w in words)


def detect_hate(text: str) -> bool:
    # Use a simple heuristic and optionally a transformer zero-shot classifier
    t = text.lower()
    # if explicit patterns match, flag
    if any(re.search(p, t) for p in HATE_PATTERNS):
        return True
    # if bad words present, flag
    if contains_bad_word(text):
        return True
    # detect direct threats toward a person (e.g., "I'll destroy your account", "I will kill you")
    # look for second-person references and violent verbs
    if re.search(r"\byou\b", t):
        for v in VIOLENT_VERBS:
            if v in t:
                return True
    # also detect first-person threats directed at 'you'
    if re.search(r"\b(i\s*(will|'ll|am going to)\s+(kill|destroy|ruin|attack|harm))\b", t):
        return True
    # Optionally use HF zero-shot to detect "hate speech" label
    if TRANSFORMERS_AVAILABLE:
        try:
            classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
            res = classifier(text, candidate_labels=["hate speech", "not hate speech"], multi_label=False)
            if res and res.get("labels") and res.get("scores"):
                label = res["labels"][0]
                score = res["scores"][0]
                if label == "hate speech" and score > 0.6:
                    return True
        except Exception:
            pass
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
    # Phrase-based detection: look for scam-like ngrams
    t = text.lower()
    scam_phrases = ["free money", "click here", "bank account", "wire transfer", "claim prize", "limited offer"]
    for p in scam_phrases:
        if p in t:
            return True
    # Detect URLs or bare domains (e.g., scam.com) as potentially malicious
    if URL_REGEX.search(text):
        # if domain contains suspicious keywords or no context, flag as potential scam
        m = URL_REGEX.search(text)
        domain = m.group(0).lower() if m else ""
        if "scam" in domain or "free" in domain or "win" in domain:
            return True
        # otherwise, flag links as suspicious by default
        return True
    # fallback keyword match
    words = set(re.findall(r"\w+", t))
    if words & SCAM_KEYWORDS:
        return True
    # Optional HF classifier for scams
    if TRANSFORMERS_AVAILABLE:
        try:
            classifier = pipeline("text-classification", model="mrm8488/distilroberta-finetuned-financial-sentiment")
            res = classifier(text)
            # simplistic: if model returns label containing 'scam' or 'fraud' consider true
            if isinstance(res, list) and len(res) > 0:
                lab = res[0].get("label", "").lower()
                if "scam" in lab or "fraud" in lab:
                    return True
        except Exception:
            pass
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
    # Fallback to HF sentiment if available
    if TRANSFORMERS_AVAILABLE:
        try:
            sentiment_pipe = pipeline("sentiment-analysis")
            res = sentiment_pipe(text)
            if isinstance(res, list) and len(res) > 0:
                lbl = res[0].get("label", "").lower()
                if "pos" in lbl or "positive" in lbl:
                    return "positive", "joy"
                if "neg" in lbl or "negative" in lbl:
                    return "negative", "sadness"
        except Exception:
            pass
    # last-resort keyword fallback
    t = text.lower()
    if any(w in t for w in ["love", "great", "happy"]):
        return "positive", "joy"
    if any(w in t for w in ["hate", "disgusting", "stupid", "idiot", "kill"]):
        return "negative", "anger"
    return "neutral", "neutral"


def topic_classify(text: str) -> str:
    # Use HF zero-shot for topic classification if available
    if TRANSFORMERS_AVAILABLE:
        try:
            classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
            candidate_labels = ["personal_attack", "harassment", "spam", "safety", "privacy", "scam", "general"]
            res = classifier(text, candidate_labels)
            if res and res.get("labels") and res.get("scores"):
                return res["labels"][0]
        except Exception:
            pass
    # Fallback rule-based
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
        except Exception:
            pass

    # Optionally call HuggingFace models for sentiment/emotion/summary/topic
    hf_key = os.environ.get("HUGGINGFACE_API_KEY")
    if hf_key:
        # sentiment model
        sent_out = call_huggingface_model("distilbert-base-uncased-finetuned-sst-2-english", {"inputs": comment})
        if sent_out:
            # HF classification returns e.g. [{label: 'POSITIVE', score: 0.99}]
            try:
                lbl = sent_out[0].get("label", "")
                sentiment = "positive" if "POS" in lbl.upper() else "negative" if "NEG" in lbl.upper() else sentiment
            except Exception:
                pass
        # summarization omitted (disabled)
        # emotion/topic could be added similarly with dedicated models

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
    """Process a batch of rows and return list of analyzed outputs. Uses HF and SBERT where available for efficiency.
    """
    comments = [str(r.get("comment", "")) for r in rows]
    embeddings = None
    if embed:
        try:
            if SBERT_AVAILABLE:
                embs = _sbert_model.encode(comments)
                # embs is iterable of arrays
                embeddings = []
                for e in embs:
                    try:
                        lst = e.tolist()
                    except Exception:
                        lst = list(e)
                    embeddings.append([float(x) for x in lst])
        except Exception:
            embeddings = None

    # Use batched HF calls for topic/sentiment enrichment if HF key present
    hf_key = os.environ.get("HUGGINGFACE_API_KEY")
    hf_model = os.environ.get("HF_TOPIC_MODEL", "facebook/bart-large-mnli")
    hf_topic_outputs = None
    if hf_key:
        try:
            hf_topic_outputs = call_hf_batch(hf_model, comments, hf_key)
        except Exception:
            hf_topic_outputs = None

    results = []
    for i, r in enumerate(rows):
        res = analyze_row(r, embed=False)
        # attach embedding
        if embed:
            if embeddings:
                res["user_history_embedding"] = embeddings[i]
            else:
                res["user_history_embedding"] = simple_embedding(res.get("comment", ""))
        # map HF topic output if available
        if hf_topic_outputs and i < len(hf_topic_outputs) and hf_topic_outputs[i]:
            try:
                # zero-shot returns labels/scores
                out = hf_topic_outputs[i]
                if isinstance(out, dict) and "labels" in out and isinstance(out["labels"], list):
                    res["topic"] = out["labels"][0]
            except Exception:
                pass
        results.append(res)
    return results


if __name__ == "__main__":
    # quick demo
    sample = {"userID": 101, "username": "rashmi", "comment_id": 1, "comment": "You people are disgusting!"}
    print(analyze_row(sample))
