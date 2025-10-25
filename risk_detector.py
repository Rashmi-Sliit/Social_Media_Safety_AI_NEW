from typing import Dict, Any, List
import os
import json
import numpy as np
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
from collections import defaultdict

# Initialize BERT model for toxicity classification
try:
    tokenizer = AutoTokenizer.from_pretrained("unitary/toxic-bert")
    model = AutoModelForSequenceClassification.from_pretrained("unitary/toxic-bert")
    BERT_AVAILABLE = True
except Exception:
    print("Warning: BERT model initialization failed. Will use basic scoring.")
    BERT_AVAILABLE = False

try:
    from pyod.models.iforest import IForest
    PYOD_AVAILABLE = True
except Exception:
    PYOD_AVAILABLE = False

# Weights for manual scoring (fallback)
WEIGHTS = {
    "bad_language": 0.25,
    "hate_speech": 0.35,
    "pii_detected": 0.35,
    "scam_pattern": 0.4,
    "emotion_anger": 0.3,
    "sentiment_negative": 0.1,
}

def _bool(flag: Any) -> bool:
    """Coerce various flag values to boolean safely."""
    return bool(flag)

def _bert_toxicity_score(text: str) -> float:
    """Get toxicity score using BERT model."""
    if not BERT_AVAILABLE or not text:
        return 0.0
    
    try:
        # Tokenize and prepare input
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512, padding=True)
        
        # Get model prediction
        with torch.no_grad():
            outputs = model(**inputs)
            scores = torch.nn.functional.softmax(outputs.logits, dim=1)
            
            # Model output format: [non-toxic, toxic]
            toxic_score = scores[0][1].item()  # Get toxic class probability
        
        return round(toxic_score, 3)
    except Exception as e:
        print(f"BERT scoring error: {e}")
        return 0.0

def _build_feature_vector(analyzed: Dict[str, Any]) -> List[float]:
    """Build feature vector for anomaly detection."""
    return [
        1.0 if _bool(analyzed.get("bad_language")) else 0.0,
        1.0 if _bool(analyzed.get("hate_speech")) else 0.0,
        1.0 if _bool(analyzed.get("pii_detected")) else 0.0,
        1.0 if _bool(analyzed.get("scam_pattern")) else 0.0,
        1.0 if analyzed.get("emotion") == "anger" else 0.0,
        1.0 if analyzed.get("sentiment") == "negative" else 0.0,
    ]

def _compute_manual_score(analyzed: Dict[str, Any]) -> float:
    """Compute risk score using manual weights."""
    numerator = 0.0
    numerator += WEIGHTS["bad_language"] if _bool(analyzed.get("bad_language")) else 0.0
    numerator += WEIGHTS["hate_speech"] if _bool(analyzed.get("hate_speech")) else 0.0
    numerator += WEIGHTS["pii_detected"] if _bool(analyzed.get("pii_detected")) else 0.0
    numerator += WEIGHTS["scam_pattern"] if _bool(analyzed.get("scam_pattern")) else 0.0
    numerator += WEIGHTS["emotion_anger"] if analyzed.get("emotion") == "anger" else 0.0
    numerator += WEIGHTS["sentiment_negative"] if analyzed.get("sentiment") == "negative" else 0.0

    total_weight = sum(WEIGHTS.values()) or 1.0
    raw_score = numerator / total_weight
    return round(min(max(raw_score, 0.0), 1.0), 3)

def compute_risk(analyzed: Dict[str, Any], user_history_risk: float = None) -> Dict[str, Any]:
    """
    Compute risk score and assessment using local BERT model.
    
    Args:
        analyzed: Content analyzer output dictionary
        user_history_risk: Optional previous risk score for the user
    
    Returns:
        Dictionary with risk assessment including score, level, reasons
    """
    # Initialize reasons list for risk factors
    reasons = []
    
    # Get comment text
    text = analyzed.get("comment", "")
    
    # Get BERT-based toxicity score
    bert_score = _bert_toxicity_score(text)
    
    # Get manual weighted score as fallback/complement
    manual_score = _compute_manual_score(analyzed)
    
    # Compute final risk score with balanced distribution
    if BERT_AVAILABLE and bert_score > 0:
        # When BERT is available, use weighted combination of scores
        bert_weight = 0.6  # Balanced weight for BERT score
        manual_weight = 0.4  # Increased manual weight for better distribution
        
        # Combine scores with enhanced scaling for better distribution
        combined_score = bert_score * bert_weight + manual_score * manual_weight
        
        # Apply stronger scaling to ensure higher scores
        # Scale up more aggressively for toxic content
        if bert_score > 0.5 or manual_score > 0.5:
            combined_score = combined_score * 1.4  # Stronger boost for potentially toxic content
        elif 0.3 <= combined_score <= 0.7:
            combined_score = combined_score * 1.25  # Moderate boost for mid-range
        
        score = round(min(max(combined_score, manual_score), 1.0), 3)
        risk_score_source = "bert_enhanced"
    else:
        # Fallback to manual scoring with enhanced scaling
        score = min(manual_score * 1.3, 1.0)  # Scale up manual scores more aggressively
        risk_score_source = "manual"

    # Build human-readable reasons
    if bert_score >= 0.7:
        reasons.append("bert_toxic_high")
    if _bool(analyzed.get("hate_speech")):
        reasons.append("hate_speech")
    if _bool(analyzed.get("bad_language")):
        reasons.append("bad_language")
    if _bool(analyzed.get("pii_detected")):
        reasons.append("pii_detected")
    if _bool(analyzed.get("scam_pattern")):
        reasons.append("scam_pattern")
    if analyzed.get("emotion") == "anger":
        reasons.append("emotion:anger")
    if analyzed.get("sentiment") == "negative":
        reasons.append("sentiment:negative")

    # Compute user cumulative risk (simple running average if provided)
    if user_history_risk is not None:
        try:
            cumulative = round((float(user_history_risk) + score) / 2.0, 3)
        except Exception:
            cumulative = score
    else:
        cumulative = score

    # Map to risk levels with adjusted thresholds for better high-risk detection
    if score >= 0.65:  # High risk threshold - lowered for better detection
        level = "High"
    elif score >= 0.4:  # Medium risk threshold - adjusted for better spread
        level = "Medium"
    else:
        level = "Low"
    
    # Force higher risk level for serious issues
    if _bool(analyzed.get("hate_speech")) or _bool(analyzed.get("pii_detected")):
        if level == "Low":
            level = "Medium"
            score = max(score, 0.4)  # Boost to medium
        # Force high risk for serious combinations
        if analyzed.get("hate_speech") and analyzed.get("pii_detected"):
            level = "High"
            score = max(score, 0.65)  # Ensure high risk score
        # Also escalate to high if multiple flags are present
        elif sum([
            _bool(analyzed.get("hate_speech")),
            _bool(analyzed.get("pii_detected")),
            _bool(analyzed.get("scam_pattern")),
            _bool(analyzed.get("bad_language")),
            analyzed.get("emotion") == "anger",
            analyzed.get("sentiment") == "negative"
        ]) >= 3:  # If 3 or more risk factors
            level = "High"
            score = max(score, 0.65)  # Ensure high risk score

    # Deterministic anomaly rules
    anomaly_flag = False
    if _bool(analyzed.get("hate_speech")) and _bool(analyzed.get("bad_language")):
        anomaly_flag = True
    if _bool(analyzed.get("pii_detected")) and score >= 0.4:
        anomaly_flag = True
    if cumulative >= 0.9:
        anomaly_flag = True
    
    # Build output dictionary
    out = {
        "userID": analyzed.get("userID"),
        "username": analyzed.get("username"),
        "comment_id": analyzed.get("comment_id"),
        "comment": analyzed.get("comment"),
        "risk_score": score,
        "risk_level": level,
        "risk_reason": "; ".join(reasons) if reasons else "",
        "anomaly_flag": anomaly_flag,
        "user_cumulative_risk": cumulative,
        "risk_score_source": risk_score_source
    }

    # Attach BERT score if available
    if BERT_AVAILABLE:
        out["bert_toxicity"] = bert_score

    # Optional: PyOD anomaly detection
    if os.environ.get("USE_PYOD") and PYOD_AVAILABLE:
        try:
            features_path = os.environ.get("PYOD_FEATURES_PATH")
            if features_path and os.path.exists(features_path):
                with open(features_path, "r", encoding="utf-8") as fh:
                    historical = json.load(fh)
                if isinstance(historical, list) and len(historical) >= 2:
                    detector = IForest()
                    detector.fit(historical)
                    current = [_build_feature_vector(analyzed)]
                    pred = detector.predict(current)
                    if len(pred) > 0 and int(pred[0]) == 1:
                        out["anomaly_flag"] = True
                        out["risk_reason"] = (out["risk_reason"] + "; pyod_anomaly") if out["risk_reason"] else "pyod_anomaly"
        except Exception:
            pass

    return out

if __name__ == "__main__":
    # Quick demo
    sample = {
        "userID": 101,
        "username": "test_user",
        "comment_id": 1,
        "comment": "This is a test comment with some negative content!",
        "bad_language": False,
        "hate_speech": False,
        "pii_detected": False,
        "scam_pattern": False,
        "sentiment": "negative",
        "emotion": "anger"
    }
    result = compute_risk(sample)
    print(json.dumps(result, indent=2))