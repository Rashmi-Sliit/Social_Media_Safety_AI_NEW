import streamlit as st
import pandas as pd

def render_mitigation_dashboard(mitigation_data: dict) -> None:
    """
    Renders the mitigation dashboard with essential fields only.
    Filters out the responsible AI metrics while keeping core mitigation data.
    """
    # Extract only the essential fields we want to display
    essential_fields = {
        "userID": mitigation_data.get("userID"),
        "username": mitigation_data.get("username"),
        "comment_id": mitigation_data.get("comment_id"),
        "toxicity_score": mitigation_data.get("toxicity_score"),
        "label": mitigation_data.get("label"),
        "risk_level": mitigation_data.get("risk_level"),
        "mitigation_action": mitigation_data.get("mitigation_action"),
        "final_status": mitigation_data.get("final_status"),
        "alert_method": mitigation_data.get("alert_method"),
        "user_history_risk": mitigation_data.get("user_history_risk"),
        "trend_priority": mitigation_data.get("trend_priority"),
        "reasoning": mitigation_data.get("reasoning"),
        "recommended_preventive_action": mitigation_data.get("recommended_preventive_action")
    }
    
    # Convert to DataFrame for display
    df = pd.DataFrame([essential_fields])
    st.dataframe(df)

    # Additional statistics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Risk Level", mitigation_data.get("risk_level", "N/A"))
    with col2:
        st.metric("Toxicity Score", f"{mitigation_data.get('toxicity_score', 0.0):.2f}")
    with col3:
        st.metric("Status", mitigation_data.get("final_status", "N/A"))