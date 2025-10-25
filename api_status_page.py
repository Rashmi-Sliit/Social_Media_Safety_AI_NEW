import streamlit as st
import os
from dotenv import load_dotenv
import requests
from datetime import datetime

load_dotenv()

def check_perspective_api():
    api_key = os.getenv('PERSPECTIVE_API_KEY')
    if not api_key:
        return False, "Not Configured", 0, None
    
    # Check API quota/limits
    try:
        # This is a minimal request to check if API is responsive
        url = f"https://commentanalyzer.googleapis.com/v1alpha1/comments:analyze?key={api_key}"
        data = {
            'comment': {'text': 'test message'},
            'requestedAttributes': {'TOXICITY': {}}
        }
        response = requests.post(url, json=data)
        
        # Get remaining quota from headers if available
        quota_remaining = response.headers.get('X-QPS-Remaining', 'Unknown')
        quota_limit = response.headers.get('X-QPS-Limit', 'Unknown')
        
        if response.status_code == 200:
            return True, "Active", quota_remaining, quota_limit
        else:
            return False, f"Error: {response.status_code}", quota_remaining, quota_limit
            
    except Exception as e:
        return False, f"Error: {str(e)}", 0, None

def check_text_analysis_api():
    """Check Azure Text Analytics API status, with local fallback"""
    from api_config import check_api_status
    status = check_api_status()
    azure_status = status.get('azure', {})
    
    return (
        azure_status.get('active', False),
        azure_status.get('status', 'Unknown'),
        azure_status.get('rate_remaining', 'N/A'),
        azure_status.get('rate_limit', 'N/A')
    )

def check_smtp():
    smtp_configured = all([
        os.getenv('SMTP_HOST'),
        os.getenv('SMTP_PORT'),
        os.getenv('SMTP_USER'),
        os.getenv('SMTP_PASS')
    ])
    if smtp_configured:
        return True, "Active", "N/A", "N/A"
    return False, "Not Configured", "N/A", "N/A"

def check_url_safety_api():
    """Check VirusTotal API status"""
    from api_config import check_api_status
    status = check_api_status()
    vt_status = status.get('virustotal', {})
    
    return (
        vt_status.get('active', False),
        vt_status.get('status', 'Unknown'),
        vt_status.get('rate_remaining', 'N/A'),
        vt_status.get('rate_limit', 'N/A')
    )

def check_gemini_api():
    """Check Google's Gemini AI API status"""
    import google.generativeai as genai
    
    api_key = os.getenv('GEMINI_API_KEY')
    model_name = os.getenv('GEMINI_MODEL', 'gemini-pro')
    
    if not api_key:
        return False, "Not Configured", "N/A", "N/A"
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        
        # Test the API with a simple prompt
        response = model.generate_content("Test connection.")
        if response and hasattr(response, 'text'):
            return True, "Active", "Available", model_name
        else:
            return False, "Error: Invalid Response", "N/A", model_name
    except Exception as e:
        return False, f"Error: {str(e)}", "N/A", model_name

def display_api_status_page():
    st.title("🔌 API Status Dashboard")
    st.markdown("Real-time status and health monitoring of all integrated APIs")

    # Get status for all APIs
    perspective_status = check_perspective_api()
    text_analysis_status = check_text_analysis_api()
    smtp_status = check_smtp()
    url_safety_status = check_url_safety_api()
    gemini_status = check_gemini_api()

    # Last checked time
    st.markdown(f"*Last checked: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    st.markdown("---")

    # Display status cards in a grid
    col1, col2 = st.columns(2)

    with col1:
        # Perspective API Card
        with st.container():
            st.markdown(
                f"""
                <div style="padding: 20px; border-radius: 10px; background-color: {'#DCFCE7' if perspective_status[0] else '#FEE2E2'}; margin-bottom: 20px;">
                    <h3 style="color: {'#166534' if perspective_status[0] else '#991B1B'}; margin-bottom: 10px;">
                        {'✅' if perspective_status[0] else '❌'} Perspective API
                    </h3>
                    <p style="color: {'#166534' if perspective_status[0] else '#991B1B'};">
                        <strong>Status:</strong> {perspective_status[1]}<br>
                        <strong>Rate Limit:</strong> {perspective_status[3] or 'N/A'}<br>
                        <strong>Remaining:</strong> {perspective_status[2] or 'N/A'}
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )

        # SMTP/Email Card
        with st.container():
            st.markdown(
                f"""
                <div style="padding: 20px; border-radius: 10px; background-color: {'#DCFCE7' if smtp_status[0] else '#FEE2E2'}; margin-bottom: 20px;">
                    <h3 style="color: {'#166534' if smtp_status[0] else '#991B1B'}; margin-bottom: 10px;">
                        {'✅' if smtp_status[0] else '❌'} Email Service
                    </h3>
                    <p style="color: {'#166534' if smtp_status[0] else '#991B1B'};">
                        <strong>Status:</strong> {smtp_status[1]}<br>
                        <strong>Provider:</strong> {os.getenv('SMTP_HOST', 'Not configured')}<br>
                        <strong>Port:</strong> {os.getenv('SMTP_PORT', 'Not configured')}
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )

    with col2:
        # Gemini API Card
        with st.container():
            st.markdown(
                f"""
                <div style="padding: 20px; border-radius: 10px; background-color: {'#DCFCE7' if gemini_status[0] else '#FEE2E2'}; margin-bottom: 20px;">
                    <h3 style="color: {'#166534' if gemini_status[0] else '#991B1B'}; margin-bottom: 10px;">
                        {'✅' if gemini_status[0] else '❌'} Gemini AI API
                    </h3>
                    <p style="color: {'#166534' if gemini_status[0] else '#991B1B'};">
                        <strong>Status:</strong> {gemini_status[1]}<br>
                        <strong>Model:</strong> {gemini_status[3] or 'N/A'}<br>
                        <strong>Availability:</strong> {gemini_status[2]}
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )

        # Text Analysis API Card
        with st.container():
            st.markdown(
                f"""
                <div style="padding: 20px; border-radius: 10px; background-color: {'#DCFCE7' if text_analysis_status[0] else '#FEE2E2'}; margin-bottom: 20px;">
                    <h3 style="color: {'#166534' if text_analysis_status[0] else '#991B1B'}; margin-bottom: 10px;">
                        {'✅' if text_analysis_status[0] else '❌'} Text Analysis API
                    </h3>
                    <p style="color: {'#166534' if text_analysis_status[0] else '#991B1B'};">
                        <strong>Status:</strong> {text_analysis_status[1]}<br>
                        <strong>Rate Limit:</strong> {text_analysis_status[3] or 'N/A'}<br>
                        <strong>Remaining:</strong> {text_analysis_status[2] or 'N/A'}
                    </p>
                    <p style="color: {'#166534' if text_analysis_status[0] else '#991B1B'}; font-size: 0.9em;">
                        Using Azure Text Analytics with local fallback
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )

        # URL Safety API Card
        with st.container():
            st.markdown(
                f"""
                <div style="padding: 20px; border-radius: 10px; background-color: {'#DCFCE7' if url_safety_status[0] else '#FEE2E2'}; margin-bottom: 20px;">
                    <h3 style="color: {'#166534' if url_safety_status[0] else '#991B1B'}; margin-bottom: 10px;">
                        {'✅' if url_safety_status[0] else '❌'} URL Safety API
                    </h3>
                    <p style="color: {'#166534' if url_safety_status[0] else '#991B1B'};">
                        <strong>Status:</strong> {url_safety_status[1]}<br>
                        <strong>Rate Limit:</strong> {url_safety_status[3] or 'N/A'}<br>
                        <strong>Remaining:</strong> {url_safety_status[2] or 'N/A'}
                    </p>
                    <p style="color: {'#166534' if url_safety_status[0] else '#991B1B'}; font-size: 0.9em;">
                        Using VirusTotal API
                    </p>
                </div>
                """,
                unsafe_allow_html=True
            )

    # Add refresh button
    if st.button("🔄 Refresh Status"):
        st.rerun()

if __name__ == "__main__":
    display_api_status_page()
