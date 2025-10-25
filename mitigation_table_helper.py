def filter_mitigation_display(mitigation_data):
    """
    Filter out Responsible AI metrics from mitigation data for display purposes.
    This preserves the original data while controlling what appears in tables.
    """
    if isinstance(mitigation_data, dict):
        # Fields we want to display (all other fields will be filtered out)
        display_fields = {
            "userID", "username", "comment_id", "toxicity_score", "label", 
            "risk_level", "mitigation_action", "final_status", "alert_method", 
            "user_history_risk", "trend_priority", "reasoning", "incident_logged",
            "ai_systems_used", "comment"
        }
        return {k: v for k, v in mitigation_data.items() if k in display_fields}
    return mitigation_data