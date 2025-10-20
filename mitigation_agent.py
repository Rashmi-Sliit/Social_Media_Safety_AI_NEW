from typing import Dict, Any
import os
import requests
from email_helper import send_alert
from api_helpers import call_perspective_cached, call_hf_single_cached, call_hf_batch


def call_perspective_toxicity_comment(text: str) -> float:
    key = os.environ.get("PERSPECTIVE_API_KEY")
    if not key:
        return 0.0
    try:
        data = call_perspective_cached(text, key)
        if data:
            val = data.get("attributeScores", {}).get("TOXICITY", {}).get("summaryScore", {}).get("value", 0.0)
            return float(val)
    except Exception:
        pass
    return 0.0


def call_hf_label_classify(comment: str, model: str = "facebook/bart-large-mnli") -> str:
    hf_key = os.environ.get("HUGGINGFACE_API_KEY")
    if not hf_key:
        return ""
    try:
        # Use batch helper for single item to leverage caching
        res = call_hf_batch(model, [comment], hf_key)
        if res and len(res) > 0 and res[0]:
            data = res[0]
            if isinstance(data, dict) and "labels" in data and isinstance(data["labels"], list):
                return data["labels"][0]
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                return data[0].get("label", "")
    except Exception:
        pass
    return ""


def call_hf_toxicity_score(comment: str, model: str = "unitary/toxic-bert") -> float:
    """Call a Hugging Face toxicity model via inference API and return a 0-1 score if available."""
    hf_key = os.environ.get("HUGGINGFACE_API_KEY")
    if not hf_key:
        return 0.0
    try:
        res = call_hf_batch(model, [comment], hf_key)
        if res and len(res) > 0 and res[0]:
            data = res[0]
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                for item in data:
                    lbl = item.get("label", "").lower()
                    if "toxic" in lbl or "toxicity" in lbl:
                        return float(item.get("score", 0.0))
                return float(max((it.get("score", 0.0) for it in data), default=0.0))
            if isinstance(data, dict):
                if "score" in data:
                    return float(data.get("score", 0.0))
    except Exception:
        pass
    return 0.0

# Simple mitigation: compute toxicity, categorize, decide action, and return explainable reasoning

CATEGORY_KEYWORDS = {
    "Cyberbullying": ["disgusting", "idiot", "hate", "stupid", "kill", "you people"],
    "Privacy Leak": ["email", "phone", "ssn", "address"],
    "Scam": ["free", "win", "offer", "bank", "click"],
}


def compute_toxicity(analyzed: Dict[str, Any], risk: Dict[str, Any]) -> float:
    # Combine multiple signals: existing risk_score, Perspective API, HF toxicity model, and local flags
    base = float(risk.get("risk_score", 0.0))
    local = 0.0
    local += 0.1 if analyzed.get("bad_language") else 0.0
    local += 0.2 if analyzed.get("hate_speech") else 0.0
    local = min(local, 1.0)

    # perspective score
    perspective = call_perspective_toxicity_comment(analyzed.get("comment", ""))

    # HF toxicity score
    hf_tox = call_hf_toxicity_score(analyzed.get("comment", ""))

    # weights (can be tuned via env vars)
    p_w = float(os.environ.get("PERSPECTIVE_WEIGHT", 0.5))
    hf_w = float(os.environ.get("HF_TOX_WEIGHT", 0.3))
    local_w = float(os.environ.get("LOCAL_WEIGHT", 0.2))

    # If external APIs are not configured, rely more on local + base risk
    if not os.environ.get("PERSPECTIVE_API_KEY") and not os.environ.get("HUGGINGFACE_API_KEY"):
        p_w = 0.0
        hf_w = 0.0
        local_w = 0.6
        base_w = 0.4
    else:
        base_w = float(os.environ.get("BASE_RISK_WEIGHT", 0.1))

    combined = (p_w * perspective) + (hf_w * hf_tox) + (local_w * local) + (base_w * base)
    # include base risk as small stabilizer if desired
    # normalize by sum of weights
    denom = p_w + hf_w + local_w + base_w
    if denom > 0:
        combined = combined / denom
    combined = min(max(combined, 0.0), 1.0)
    return round(combined, 3)


def categorize(comment: str) -> str:
    # Prefer HF zero-shot category detection if API key present
    hf_key = os.environ.get("HUGGINGFACE_API_KEY")
    if hf_key:
        try:
            label = call_hf_label_classify(comment)
            if label:
                return label
        except Exception:
            pass
    # Fallback to keyword rules
    t = comment.lower()
    for cat, kws in CATEGORY_KEYWORDS.items():
        for k in kws:
            if k in t:
                return cat
    return "Toxic"


def derive_label_from_analyzed(analyzed: Dict[str, Any]) -> str:
    """Derive a reasonable label from analyzed fields when HF label is not available.

    Looks at topic, hate_speech, scam_pattern, pii_detected, sentiment, and bad_language
    to return a normalized label used by downstream mitigation decision logic.
    """
    topic = (analyzed.get("topic") or "").lower()
    if analyzed.get("pii_detected"):
        return "Privacy Leak"
    if analyzed.get("scam_pattern") or "scam" in topic:
        return "Scam"
    if analyzed.get("hate_speech") or analyzed.get("bad_language"):
        # prefer specific bullying/personal attack labels
        if "personal_attack" in topic or "harassment" in topic or "cyberbullying" in topic:
            return "Cyberbullying"
        return "Toxic"
    if topic:
        # Map some known topic names to friendly labels
        if "privacy" in topic:
            return "Privacy Leak"
        if "spam" in topic:
            return "Scam"
        return topic.title()
    # fallback to sentiment-based heuristic
    sent = (analyzed.get("sentiment") or "").lower()
    if sent == "negative":
        return "Toxic"
    return "Other"


def decide_action(toxicity: float, label: str) -> Dict[str, str]:
    """Decide mitigation action based on toxicity and category label."""
    label_lower = (label or "").lower()
    # Privacy Leak requires immediate moderator notification
    if "privacy" in label_lower or "privacy leak" in label_lower:
        return {"mitigation_action": "Notify moderator (privacy)", "final_status": "Flagged", "alert_method": "Email + Dashboard"}
    # Cyberbullying: aggressive policy — if toxic enough, alert and flag
    if "cyberbullying" in label_lower or "personal_attack" in label_lower or "harassment" in label_lower:
        if toxicity >= 0.6:
            return {"mitigation_action": "Immediate block and alert admin", "final_status": "Flagged", "alert_method": "Email + Dashboard"}
        if toxicity >= 0.4:
            return {"mitigation_action": "Add to review queue", "final_status": "Under Review", "alert_method": "Dashboard"}
        return {"mitigation_action": "Show warning to user", "final_status": "Under Review", "alert_method": "Dashboard"}
    # Scam: add to review and possibly escalate
    if "scam" in label_lower:
        if toxicity >= 0.5:
            return {"mitigation_action": "Flag for fraud review", "final_status": "Flagged", "alert_method": "Dashboard"}
        return {"mitigation_action": "Add to review queue", "final_status": "Under Review", "alert_method": "Dashboard"}
    # Default based on toxicity thresholds
    if toxicity >= 0.8:
        return {"mitigation_action": "Alert sent to admin", "final_status": "Flagged", "alert_method": "Email + Dashboard"}
    if toxicity >= 0.5:
        return {"mitigation_action": "Add to review queue", "final_status": "Under Review", "alert_method": "Dashboard"}
    return {"mitigation_action": "No action", "final_status": "Safe", "alert_method": "None"}


def mitigate(analyzed: Dict[str, Any], risk: Dict[str, Any], advice: Dict[str, Any]) -> Dict[str, Any]:
    # If external MITIGATION_AGENT_URL is set, POST combined payload
    url = os.environ.get("MITIGATION_AGENT_URL")
    if url:
        try:
            payload = {**analyzed, **risk, **advice}
            resp = requests.post(url.rstrip("/") + "/mitigate", json=payload, timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception:
            pass
    # Compute toxicity using perspective if available
    perspective_tox = call_perspective_toxicity_comment(analyzed.get("comment", ""))
    toxicity = compute_toxicity(analyzed, risk)
    # blend perspective score into toxicity
    toxicity = round(min(1.0, max(toxicity, perspective_tox)), 3)

    # Use HF to attempt label classification if available; derive label from analyzed fields as a fallback
    hf_label = call_hf_label_classify(analyzed.get("comment", ""))
    generated_label = derive_label_from_analyzed(analyzed)
    # Prefer HF label if available, otherwise use derived generated_label
    label = hf_label or generated_label or "Toxic"
    action = decide_action(toxicity, label)
    reasoning = []
    if analyzed.get("hate_speech"):
        reasoning.append("Contains hate speech")
    if analyzed.get("bad_language"):
        reasoning.append("Bad language detected")
    if analyzed.get("pii_detected"):
        reasoning.append("Possible privacy leak")
    if analyzed.get("scam_pattern"):
        reasoning.append("Possible scam/spam pattern")
    if (analyzed.get("emotion") or "").lower() == "anger":
        reasoning.append("Anger emotion detected")
    if (analyzed.get("sentiment") or "").lower() == "negative":
        reasoning.append("Negative sentiment")
    if risk.get("user_cumulative_risk") and risk["user_cumulative_risk"] > 0.7:
        reasoning.append("User has high cumulative risk")

    out = {
        "userID": analyzed.get("userID"),
        "username": analyzed.get("username"),
        "comment_id": analyzed.get("comment_id"),
        "toxicity_score": toxicity,
        "label": label,
    # removed generated_label field to simplify downstream UI/CSV
        "risk_level": risk.get("risk_level"),
        "mitigation_action": action["mitigation_action"],
        "final_status": action["final_status"],
        "alert_method": action["alert_method"],
        "user_history_risk": risk.get("user_cumulative_risk"),
        "trend_priority": "High" if toxicity > 0.7 else "Medium" if toxicity > 0.4 else "Low",
        "reasoning": "; ".join(reasoning) if reasoning else "No explicit reasons",
        "incident_logged": True,
        "recommended_preventive_action": advice.get("moderation_suggestion", ""),
    }
    # Send email alert for severe actions if SMTP configured
    try:
        if out["mitigation_action"] == "Alert sent to admin":
            subject = f"[Alert] High-risk comment by {out.get('username')}"
            body = f"Comment ID: {out.get('comment_id')}\nUser: {out.get('username')}\nComment: {analyzed.get('comment')}\nReasoning: {out.get('reasoning')}\nAction: {out.get('mitigation_action')}"
            send_alert(subject, body)
    except Exception:
        pass
    return out


if __name__ == "__main__":
    analyzed = {"userID": 101, "username": "rashmi", "comment_id": 1, "comment": "You people are disgusting!", "bad_language": True, "hate_speech": True}
    risk = {"risk_score": 0.85, "risk_level": "High", "user_cumulative_risk": 0.8}
    advice = {"moderation_suggestion": "Place user in review queue for next 24 hours"}
    print(mitigate(analyzed, risk, advice))
