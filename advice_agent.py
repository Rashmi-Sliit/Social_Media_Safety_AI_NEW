from typing import Dict, Any, Optional
import os
import requests
import json
import time


import google.generativeai as genai
import json

def setup_gemini():
    """Setup Gemini API with credentials and specified model"""
    api_key = os.environ.get("GEMINI_API_KEY")
    model_name = os.environ.get("GEMINI_MODEL", "gemini-pro")
    
    if not api_key:
        print("[API Status] ❌ Gemini API call failed: No API key provided")
        return None
        
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        print(f"[API Status] ✓ Gemini API initialized with model: {model_name}")
        return model
    except Exception as e:
        print(f"[API Status] ❌ Failed to setup Gemini API: {e}")
        return None

def _build_prompt(risk_out: Dict[str, Any], mitigation_out: Dict[str, Any] = None) -> str:
    """Build a structured prompt for Gemini API to analyze content and generate advice"""
    comment = (mitigation_out or {}).get('comment') or risk_out.get('comment', '')
    risk_score = float(risk_out.get('risk_score', 0) or 0)
    risk_level = risk_out.get('risk_level', 'Low')
    
    prompt = f"""You are an AI moderation assistant. Analyze this social media comment and provide structured advice.

Comment to analyze: "{comment}"
Risk Score: {risk_score} (on a scale of 0.0 to 1.0)
Risk Level: {risk_level}

Respond with a JSON object containing exactly these three fields:
- "advice": (string) Clear, specific recommendations for handling this content
- "moderation_suggestion": (string) Step-by-step actions for moderators
- "trend": (string) Brief analysis of behavior patterns and potential trends

Risk level guidelines:
- Low (0.0-0.3): Monitor only
- Medium (0.3-0.7): Review required
- High (0.7-1.0): Immediate action needed

Format your entire response as a valid JSON object like this:
{{
  "advice": "string with specific advice",
  "moderation_suggestion": "string with clear steps",
  "trend": "string describing patterns"
}}

Do not include any text outside the JSON object."""
    return prompt


def _parse_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    # Try direct parse
    try:
        return json.loads(text)
    except Exception:
        # Extract first {...} substring
        s = text.find("{")
        e = text.rfind("}")
        if s != -1 and e != -1 and e > s:
            try:
                return json.loads(text[s:e+1])
            except Exception:
                return None
    return None


def call_external_advice_api(risk_out: Dict[str, Any], mitigation_out: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
    """Generate advice using Google's Gemini API.
    Falls back to local processing if Gemini is not available.
    """
    model = setup_gemini()
    if not model:
        return None
        
    prompt = _build_prompt(risk_out, mitigation_out)
    
    try:
        print("[API Status] 🤖 Generating advice with Gemini AI...")
        
        response = model.generate_content(prompt)
        if not response:
            print("[API Status] ❌ Gemini API returned empty response")
            return None
            
        # Extract JSON from response
        text = response.text
        parsed = _parse_json_from_text(text)
        if parsed and all(k in parsed for k in ["advice", "moderation_suggestion", "trend"]):
            print("[API Status] ✓ Successfully generated advice with Gemini AI")
            return parsed
        else:
            print("[API Status] ⚠️ Gemini response missing required fields")
            return None
            
    except Exception as e:
        print(f"[API Status] ❌ Gemini API error: {e}")
        return None
    
    return None


def builtin_advice(payload: Dict[str, Any]) -> Dict[str, Any]:
    # deterministic fallback
    score = payload.get("risk_score", 0) or 0
    level = (payload.get("risk_level") or "Low").title()
    reason = (payload.get("risk_reason") or "").lower()
    # Prefer label provided by mitigation agent; fall back to top-level label
    label = ((payload.get("mitigation") or {}).get("label") or (payload.get("label") or "")).lower()
    def has_any(text: str, kws: list) -> bool:
        return any(k in text for k in kws if k)

    advice_parts = []
    suggestion_parts = []
    trend = "No significant harmful trend detected."

    # High risk: more granular handling
    if level == "High":
        if has_any(reason, ["pii", "personal", "address", "ssn", "dob"]) or has_any(label, ["pii", "privacy"]):
            advice_parts.append("Contains sensitive personal information — redact or remove personal identifiers immediately.")
            suggestion_parts.append("Quarantine content; notify privacy/compliance team; consider account action")
            trend = "Personal data exposure trend — immediate privacy review recommended."

        elif has_any(reason, ["scam", "fraud", "phish", "phishing"]) or has_any(label, ["scam", "fraud"]):
            advice_parts.append("Likely fraudulent/scam content. Do not engage; remove or block suspicious links and attachments.")
            suggestion_parts.append("Escalate to fraud review; block URLs and preserve evidence for investigation")
            trend = "Fraudulent activity trending upwards."

        elif has_any(reason, ["hate", "harass", "slur", "abuse"]) or has_any(label, ["hate", "harassment", "cyberbullying"]):
            advice_parts.append("Hateful or abusive language detected. Enforce community standards and consider sanctions.")
            suggestion_parts.append("Flag for moderator review; consider temporary suspension for repeat offenders")
            trend = "Spike in abusive language; consider targeted moderation."

        elif has_any(reason, ["self-harm", "suicid", "harm"]):
            advice_parts.append("Content indicates potential self-harm risk. Prioritize user safety and escalate to support teams.")
            suggestion_parts.append("Alert safety team; provide crisis resources and follow emergency protocols")
            trend = "Self-harm content requires urgent attention."

        else:
            advice_parts.append("High risk content. Recommend removal and a deeper investigation of the user/context.")
            suggestion_parts.append("Immediate moderator review and preserve context for audits")
            trend = "High-severity incidents detected."

    # Medium risk: guidance and soft actions
    elif level == "Medium":
        if has_any(reason, ["pii", "privacy", "personal"]) or has_any(label, ["pii", "privacy"]):
            advice_parts.append("Possible personal data exposure. Suggest redaction and inform the affected user when appropriate.")
            suggestion_parts.append("Queue for privacy check; offer user guidance to remove sensitive details")
            trend = "Occasional privacy leaks observed."

        elif has_any(reason, ["scam", "promo", "advert"]) or has_any(label, ["spam", "scam", "promotion"]):
            advice_parts.append("Potentially promotional or suspicious content. Limit distribution and warn the poster.")
            suggestion_parts.append("Add to review queue; throttle visibility or tag as promotional")
            trend = "Promotional/suspicious posts are intermittent."

        elif has_any(reason, ["hate", "harass", "insult"]) or has_any(label, ["harassment", "hate"]):
            advice_parts.append("Borderline offensive language. Encourage rephrasing and apply a soft warning.")
            suggestion_parts.append("Show a warning to the user and suggest edits; monitor for repeat behavior")
            trend = "Occasional offensive language detected."

        else:
            advice_parts.append("Content may be questionable — recommend manual review and guidance to the author.")
            suggestion_parts.append("Manual review; consider educational nudges rather than punitive action")
            trend = "No strong trend but monitor for escalation."

    # Low risk: promote education and monitoring
    else:
        if score > 0.7:
            # Low label but high score — anomaly
            advice_parts.append("Low-labeled content but unusually high risk score — perform a quick manual spot-check.")
            suggestion_parts.append("Spot-check by moderator; review recent activity for patterns")
            trend = "Anomalous high-scoring, low-labeled content detected."
        else:
            advice_parts.append("Content appears safe. Encourage positive and explanatory behavior where helpful.")
            suggestion_parts.append("No action needed; consider lightweight educational nudges")
            trend = "No significant harmful trend detected."

    # Compose deterministic outputs
    advice_text = " ".join(advice_parts) if advice_parts else "No specific advice."
    moderation_suggestion = "; ".join(suggestion_parts) if suggestion_parts else "No action needed"

    # Add confidence note based on score
    if score >= 0.8:
        trend = f"{trend} (high confidence)"
    elif score >= 0.5:
        trend = f"{trend} (moderate confidence)"
    else:
        trend = f"{trend} (low confidence)"

    return {"advice": advice_text, "moderation_suggestion": moderation_suggestion, "trend": trend}


def generate_advice(risk_out: Dict[str, Any], mitigation_out: Dict[str, Any] = None) -> Dict[str, Any]:
    """Generate moderation advice using Gemini API with risk score-based enhancement"""
    
    # Get advice from Gemini API
    gemini_response = call_external_advice_api(risk_out, mitigation_out)
    
    # Check for URL safety
    try:
        url_checks = find_and_check_urls_in_text((mitigation_out or {}).get('comment', '') or risk_out.get('comment', ''))
        urls_safe = True if not url_checks else all(bool(v) for v in url_checks.values())
    except Exception:
        urls_safe = False
    
    risk_score = float(risk_out.get('risk_score', 0) or 0)
    
    # Default values for the response
    response_data = {
        "userID": risk_out.get("userID"),
        "username": risk_out.get("username"),
        "comment_id": risk_out.get("comment_id"),
        "advice": "",
        "moderation_suggestion": "No specific moderation action needed",  # Default string value
        "trend": "No significant trend detected",  # Default string value
        "label": (mitigation_out or {}).get("label") or risk_out.get("label") or "Unclassified",
        "urls_safe": urls_safe,
        "predicted_behavior_risk": round(min(1.0, risk_score + 0.15), 3),
        "source": "local"
    }
    
    if gemini_response and isinstance(gemini_response, dict):
        # Ensure all values are strings
        advice = str(gemini_response.get('advice', ''))
        moderation = str(gemini_response.get('moderation_suggestion', response_data["moderation_suggestion"]))
        trend = str(gemini_response.get('trend', response_data["trend"]))
        
        # Enhance advice with risk score context
        if risk_score >= 0.7:
            advice = f"🚨 HIGH RISK - Immediate Action Required: {advice}"
        elif risk_score >= 0.4:
            advice = f"⚠️ MEDIUM RISK - Monitor Closely: {advice}"
            
        response_data.update({
            "advice": advice,
            "moderation_suggestion": moderation,
            "trend": trend,
            "source": "gemini"
        })
    else:
        # If Gemini fails, generate a basic response based on risk score
        if risk_score >= 0.7:
            response_data["advice"] = "🚨 HIGH RISK: Immediate review required. Content may violate community guidelines."
            response_data["moderation_suggestion"] = "Review immediately and take appropriate action based on content severity."
        elif risk_score >= 0.4:
            response_data["advice"] = "⚠️ MEDIUM RISK: Content requires monitoring and review."
            response_data["moderation_suggestion"] = "Add to moderation queue for review."
        else:
            response_data["advice"] = "✅ LOW RISK: Content appears to be within community guidelines."
            response_data["moderation_suggestion"] = "No immediate action required."
    
    return response_data

    # Fallback to deterministic local advice
    local = builtin_advice(payload)
    return {
        "userID": risk_out.get("userID"),
        "username": risk_out.get("username"),
        "comment_id": risk_out.get("comment_id"),
        "advice": local.get("advice"),
        
        "trend": local.get("trend"),
        # expose label from mitigation (if available) or risk label
        "label": (mitigation_out or {}).get("label") or risk_out.get("label"),
        # boolean column indicating whether URLs in the comment are safe
        "urls_safe": urls_safe,
        "predicted_behavior_risk": round(min(1.0, (risk_out.get("risk_score", 0) or 0) + 0.15), 3),
        "source": "builtin-free",
    }


def check_url_safety(url: str) -> bool:
    """Check a URL using the Google Safe Browsing Lookup API (v4).

    Uses the SAFE_BROWSING_API_KEY environment variable. Returns True if the
    URL is considered safe (no threats found) and False if unsafe or on
    detection of a malicious/threatening classification.

    Note: The Google Safe Browsing API is free with quota limits for small
    projects. If you prefer an alternative free service, you can integrate
    with PhishTank (https://phishtank.org/developer_info.php) similarly.

    Error handling: network issues or missing API key return False (treat as
    unsafe by default so callers can take conservative action).
    """
    key = os.environ.get("SAFE_BROWSING_API_KEY")
    if not key:
        # No API key configured; be conservative and return False (unsafe)
        return False

    # Build the Safe Browsing v4 lookup request
    url_api = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={key}"
    payload = {
        "client": {"clientId": "sms_ai", "clientVersion": "1.0"},
        "threatInfo": {
            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "UNWANTED_SOFTWARE", "POTENTIALLY_HARMFUL_APPLICATION"],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}],
        },
    }
    try:
        r = requests.post(url_api, json=payload, timeout=8)
        if r.status_code not in (200, 201):
            return False
        j = r.json()
        # If 'matches' key exists and is non-empty, the URL is unsafe
        matches = j.get("matches")
        if matches:
            return False
        return True
    except Exception:
        # On any exception, return False to be conservative
        return False


def find_and_check_urls_in_text(text: str) -> Dict[str, bool]:
    """Extracts URLs from text and returns a map url->is_safe (bool).

    Uses a simple regex to find URLs. For each URL found it calls
    check_url_safety(). If no URLs are found returns an empty dict.
    """
    import re
    debug = bool(os.environ.get("URL_CHECK_DEBUG"))

    def dbg(*args):
        if debug:
            try:
                print("[URL_CHECK_DEBUG]", *args)
            except Exception:
                pass

    # Basic deobfuscation: hxxp/hxxps -> http/https, [.] -> . , (dot) -> .
    t = (text or "").replace("hxxp://", "http://").replace("hxxps://", "https://")
    t = t.replace("[.]", ".").replace("(dot)", ".")

    # Tolerant regex to match many URL-like patterns (with/without scheme, with common ports and paths)
    url_re = re.compile(
        r"(?:(?:https?://)|(?:http?://))?[\w\-]+(?:\.[\w\-]+)+(?:[:0-9]{0,6})?(?:/[^\s]*)?", re.IGNORECASE
    )

    found = []
    for m in url_re.finditer(t):
        candidate = m.group(0)
        # skip short false-positives
        if len(candidate) < 4:
            continue
        # heuristics: must contain at least one dot and a letter
        if "." in candidate and re.search(r"[a-zA-Z]", candidate):
            found.append(candidate)

    dbg("raw found:", found)

    # Normalize and strip trailing punctuation
    results = {}
    for u in found:
        norm = u.strip().rstrip('.,;:')
        if not norm.lower().startswith(("http://", "https://")):
            norm = "http://" + norm
        dbg("checking:", norm)
        try:
            results[norm] = check_url_safety(norm)
            dbg(norm, "->", results[norm])
        except Exception as e:
            dbg("error checking url", norm, e)
            results[norm] = False
    return results


# Example usage:
if __name__ == "__main__":
    # quick demo (requires SAFE_BROWSING_API_KEY env var)
    test_url = "http://example.com"
    safe = check_url_safety(test_url)
    print(f"URL {test_url} safe: {safe}")
