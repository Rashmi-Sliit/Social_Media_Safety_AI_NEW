from typing import Dict, Any, List, Tuple
import os
import requests
import json
from datetime import datetime
from email_helper import send_alert
from api_helpers import call_perspective_cached

# Responsible AI configuration
RESPONSIBLE_AI_CONFIG = {
    "bias_detection": True,
    "fairness_metrics": True,
    "transparency_level": "high",
    "decision_logging": True,
    "ethical_guidelines": [
        "Avoid discriminatory outcomes",
        "Protect user privacy",
        "Ensure transparent decisions",
        "Provide appeal mechanisms",
        "Consider context and intent"
    ]
}

def log_decision_metrics(decision: Dict[str, Any]) -> None:
    """Log decisions for accountability and bias monitoring"""
    try:
        timestamp = datetime.now().isoformat()
        metrics_path = "responsible_ai_metrics.json"
        
        # Load existing metrics
        metrics = []
        if os.path.exists(metrics_path):
            with open(metrics_path, 'r') as f:
                metrics = json.load(f)
                
        # Add new decision data
        metrics.append({
            "timestamp": timestamp,
            "decision": decision,
            "bias_indicators": check_bias_indicators(decision),
            "fairness_score": calculate_fairness_score(decision),
            "ethical_compliance": verify_ethical_compliance(decision)
        })
        
        # Keep last 1000 decisions for analysis
        metrics = metrics[-1000:]
        
        with open(metrics_path, 'w') as f:
            json.dump(metrics, f, indent=2)
    except Exception as e:
        print(f"Failed to log decision metrics: {e}")

def check_bias_indicators(decision: Dict[str, Any]) -> List[str]:
    """Check for potential bias in decisions"""
    bias_indicators = []
    
    # Check for disproportionate actions
    if decision.get("toxicity_score", 0) > 0.7:
        reasoning = decision.get("reasoning", "").lower()
        # Check for culturally specific terms or context
        cultural_terms = ["accent", "dialect", "cultural", "traditional"]
        if any(term in reasoning for term in cultural_terms):
            bias_indicators.append("Potential cultural bias in high toxicity score")
    
    return bias_indicators

def calculate_fairness_score(decision: Dict[str, Any]) -> float:
    """Calculate a fairness score for the decision"""
    score = 1.0
    
    # Check decision consistency
    if decision.get("toxicity_score", 0) > 0.8 and decision.get("mitigation_action") != "Alert sent to admin":
        score -= 0.2  # Inconsistent severe case handling
        
    # Check for context consideration
    if "User has concerning history" in decision.get("reasoning", ""):
        score -= 0.1  # Potential over-reliance on historical data
        
    return max(0.0, score)

def verify_ethical_compliance(decision: Dict[str, Any]) -> Dict[str, Any]:
    """Verify compliance with ethical guidelines"""
    compliance = {
        "compliant": True,
        "warnings": [],
        "suggestions": []
    }
    
    # Check privacy protection
    if "privacy" in decision.get("label", "").lower() and decision.get("alert_method") != "Email + Dashboard":
        compliance["compliant"] = False
        compliance["warnings"].append("Privacy issues must be escalated properly")
    
    # Check transparency
    if not decision.get("reasoning"):
        compliance["warnings"].append("Decision lacks explanation")
        
    # Check for appeal path
    if decision.get("final_status") == "Flagged" and "appeal" not in decision.get("recommended_preventive_action", "").lower():
        compliance["suggestions"].append("Consider adding appeal process information")
    
    # Check for context consideration
    if decision.get("toxicity_score", 0) > 0.9 and len(decision.get("reasoning", "").split()) < 10:
        compliance["warnings"].append("High severity cases need more detailed reasoning")
        
    return compliance


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


# Removed HuggingFace label classification in favor of local analysis


# Removed in favor of Perspective API and local analysis

# Import Gemini AI for advanced reasoning
import google.generativeai as genai

def setup_gemini():
    """Initialize Gemini AI with API key"""
    api_key = os.environ.get("GEMINI_API_KEY")
    model_name = os.environ.get("GEMINI_MODEL", "gemini-pro")
    if not api_key:
        print("[API Status] ❌ Gemini API not configured")
        return None
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        print(f"[API Status] ✓ Gemini initialized for reasoning generation")
        return model
    except Exception as e:
        print(f"[API Status] ❌ Gemini setup failed: {e}")
        return None

def generate_reasoning(comment: str, toxicity: float, analyzed: Dict[str, Any]) -> str:
    """Generate detailed reasoning about content toxicity using Gemini AI"""
    model = setup_gemini()
    if not model:
        # Fallback to basic reasoning if Gemini is not available
        return _generate_basic_reasoning(analyzed)
        
    prompt = f"""Analyze this social media comment and explain why it might be toxic or concerning.
    Comment: "{comment}"
    Toxicity Score: {toxicity}
    
    Consider these aspects in your analysis:
    - Hate speech or offensive language
    - Personal attacks or bullying
    - Privacy concerns
    - Scam indicators
    - Emotional tone
    - Potential harm or threats
    
    Return a concise, comma-separated list of reasons why this content might be problematic.
    Format: "Reason 1, Reason 2, Reason 3"
    If content appears safe, return "Content appears safe and within community guidelines"
    """
    
    try:
        response = model.generate_content(prompt)
        if response and response.text:
            reasoning = response.text.strip().strip('"')  # Remove quotes if present
            print(f"[API Status] ✓ Generated reasoning using Gemini AI")
            return reasoning
    except Exception as e:
        print(f"[API Status] ❌ Gemini reasoning generation failed: {e}")
    
    return _generate_basic_reasoning(analyzed)

def _generate_basic_reasoning(analyzed: Dict[str, Any]) -> str:
    """Fallback function for basic reasoning when Gemini is unavailable"""
    reasons = []
    if analyzed.get("hate_speech"):
        reasons.append("Contains hate speech")
    if analyzed.get("bad_language"):
        reasons.append("Contains inappropriate language")
    if analyzed.get("pii_detected"):
        reasons.append("Contains potential privacy information")
    if analyzed.get("scam_pattern"):
        reasons.append("Shows patterns of potential scam")
    if (analyzed.get("emotion") or "").lower() == "anger":
        reasons.append("Displays angry or aggressive tone")
    if (analyzed.get("sentiment") or "").lower() == "negative":
        reasons.append("Shows negative sentiment")
    return "; ".join(reasons) if reasons else "No explicit concerns identified"

# Category keywords for basic classification
CATEGORY_KEYWORDS = {
    "Cyberbullying": ["disgusting", "idiot", "hate", "stupid", "kill", "you people"],
    "Privacy Leak": ["email", "phone", "ssn", "address"],
    "Scam": ["free", "win", "offer", "bank", "click"],
}


def compute_toxicity(analyzed: Dict[str, Any], risk: Dict[str, Any]) -> float:
    # Combine multiple signals: existing risk_score, Perspective API, and local flags
    base = float(risk.get("risk_score", 0.0))
    local = 0.0
    local += 0.1 if analyzed.get("bad_language") else 0.0
    local += 0.2 if analyzed.get("hate_speech") else 0.0
    local = min(local, 1.0)

    # perspective score
    perspective = call_perspective_toxicity_comment(analyzed.get("comment", ""))

    # weights (can be tuned via env vars)
    p_w = float(os.environ.get("PERSPECTIVE_WEIGHT", 0.6))
    local_w = float(os.environ.get("LOCAL_WEIGHT", 0.3))
    base_w = float(os.environ.get("BASE_RISK_WEIGHT", 0.1))

    # If Perspective API is not configured, rely more on local + base risk
    if not os.environ.get("PERSPECTIVE_API_KEY"):
        p_w = 0.0
        local_w = 0.7
        base_w = 0.3

    combined = (p_w * perspective) + (local_w * local) + (base_w * base)
    # normalize by sum of weights
    denom = p_w + local_w + base_w
    if denom > 0:
        combined = combined / denom
    combined = min(max(combined, 0.0), 1.0)
    return round(combined, 3)


def categorize(comment: str) -> str:
    # Use keyword rules for basic categorization
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
    """
    Mitigate potentially harmful content with responsible AI principles.
    
    Implements:
    - Bias detection and mitigation
    - Fairness metrics
    - Decision transparency
    - Ethical compliance
    - Appeal mechanisms
    """
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
            
    # Add transparency context
    analyzed["ai_systems_used"] = []
    if os.environ.get("PERSPECTIVE_API_KEY"):
        analyzed["ai_systems_used"].append("Perspective API")
    if os.environ.get("GEMINI_API_KEY"):
        analyzed["ai_systems_used"].append("Gemini AI")
    # Compute toxicity using perspective if available
    toxicity = compute_toxicity(analyzed, risk)

    # Use local analysis to derive label
    label = derive_label_from_analyzed(analyzed)
    action = decide_action(toxicity, label)
    
    # Generate detailed reasoning using Gemini AI
    comment = analyzed.get("comment", "")
    reasoning = generate_reasoning(comment, toxicity, analyzed)
    
    # Add user risk context if high
    if risk.get("user_cumulative_risk") and risk["user_cumulative_risk"] > 0.7:
        reasoning = f"{reasoning}, User has concerning history with high cumulative risk"

    # Create initial output dictionary
    out = {
        "userID": analyzed.get("userID"),
        "username": analyzed.get("username"),
        "comment_id": analyzed.get("comment_id"),
        "toxicity_score": toxicity,
        "label": label,
        "risk_level": risk.get("risk_level"),
        "mitigation_action": action["mitigation_action"],
        "final_status": action["final_status"],
        "alert_method": action["alert_method"],
        "user_history_risk": risk.get("user_cumulative_risk"),
        "trend_priority": "High" if toxicity > 0.7 else "Medium" if toxicity > 0.4 else "Low",
        "reasoning": reasoning,
        "incident_logged": True,
        "recommended_preventive_action": advice.get("moderation_suggestion", ""),
        "ai_systems_used": analyzed.get("ai_systems_used", [])
    }
    
    # Add responsible AI components after initial dictionary is created
    responsible_ai_data = {
        "decision_transparency": {
            "factors_considered": [
                "Content toxicity",
                "User history",
                "Context analysis",
                "Pattern recognition"
            ],
            "appeal_process": (
                "To appeal this decision, please contact our moderation team "
                "with your comment ID and any additional context that may help review your case."
            ),
        }
    }
    
    # Add ethical review and metrics
    responsible_ai_data.update({
        "ethical_review": verify_ethical_compliance(out),
        "bias_indicators": check_bias_indicators(out),
        "fairness_score": calculate_fairness_score(out)
    })
    
    # Update the output dictionary with responsible AI data
    out.update(responsible_ai_data)
    
    # Log the decision metrics if enabled
    if RESPONSIBLE_AI_CONFIG["decision_logging"]:
        log_decision_metrics(out)
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
