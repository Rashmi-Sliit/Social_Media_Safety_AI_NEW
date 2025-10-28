import streamlit as st
import re
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# ------------------ Email & Validation ------------------
def validate_email(email):
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def send_notification_email(user_data, plan_name):
    """Send email notification to admin."""
    try:
        admin_email = os.getenv('ADMIN_EMAIL')
        from_email = os.getenv('FROM_EMAIL')
        smtp_server = os.getenv('SMTP_HOST')
        smtp_port = int(os.getenv('SMTP_PORT', 587))
        smtp_username = os.getenv('SMTP_USER')
        smtp_password = os.getenv('SMTP_PASS')

        msg = EmailMessage()
        msg.set_content(f"""
        New Pricing Plan Request

        Plan: {plan_name}
        Name: {user_data['name']}
        Email: {user_data['email']}
        Organization: {user_data['organization']}
        Payment Method: {user_data['payment_method']}
        """)

        msg['Subject'] = f'New Pricing Plan Request - {plan_name}'
        msg['From'] = from_email
        msg['To'] = admin_email

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False


# ------------------ Streamlit UI ------------------
def display_pricing_page():
    # Check for success message from form submission
    if st.session_state.get('email_success'):
        st.success("✅ Thank you! Our team will contact you shortly.")
        # Clear the success flag
        del st.session_state.email_success
    
    # 🌈 Custom CSS
    st.markdown("""
    <style>
    :root {
        --bg-main: #FFFFFF;
        --accent: #2563EB;
        --text: #1E293B;
        --card-bg: rgba(37, 99, 235, 0.03);
        --hover: #1D4ED8;
        --success: #16A34A;
        --error: #DC2626;
        --glow: rgba(37, 99, 235, 0.1);
        --border: rgba(37, 99, 235, 0.15);
        --card-shadow: rgba(37, 99, 235, 0.1);
    }

    /* Main container background */
    [data-testid="stAppViewContainer"] {
        background: var(--bg-main) !important;
        color: var(--text);
        min-height: 100vh;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] > div {
        background: var(--bg-main) !important;
        border-right: 1px solid var(--border);
    }
    
    section[data-testid="stSidebar"] {
        background: var(--bg-main) !important;
    }
    
    [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] {
        color: var(--text);
    }
    
    /* Additional sidebar background fixes */
    .st-emotion-cache-1cypcdb, .st-emotion-cache-1dp5vir, div[data-testid="stDecoration"] {
        background: var(--bg-main) !important;
    }
    
    div[data-testid="stSidebarNav"] {
        background: transparent !important;
    }
    
    /* Sidebar navigation buttons */
    [data-testid="stSidebar"] button {
        background-color: transparent !important;
        border: 1px solid var(--accent) !important;
        color: var(--accent) !important;
        transition: all 0.3s ease !important;
    }
    
    [data-testid="stSidebar"] button:hover {
        background-color: var(--hover) !important;
        border-color: transparent !important;
        color: var(--text) !important;
    }
    
    /* Sidebar scrollbar */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        scrollbar-width: thin;
        scrollbar-color: var(--blue-accent) var(--dark-blue);
    }
    
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"]::-webkit-scrollbar {
        width: 6px;
    }
    
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"]::-webkit-scrollbar-track {
        background: var(--dark-blue);
    }
    
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"]::-webkit-scrollbar-thumb {
        background-color: var(--blue-accent);
        border-radius: 3px;
    }
    
    /* Make sidebar elements more visible */
    [data-testid="stSidebar"] .stSelectbox,
    [data-testid="stSidebar"] .stTextInput,
    [data-testid="stSidebar"] .stNumberInput {
        background-color: rgba(26, 54, 93, 0.5) !important;
        border-color: rgba(100, 255, 218, 0.1) !important;
        color: var(--soft-blue) !important;
    }
    
    /* Style all sidebar content */
    [data-testid="stSidebar"] div:not([data-testid="stMarkdownContainer"]) {
        color: var(--soft-blue) !important;
        background: transparent !important;
    }
    
    [data-testid="stSidebar"] label {
        color: var(--blue-accent) !important;
    }
    
    /* Sidebar header styling */
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: var(--blue-accent) !important;
        border-bottom: 1px solid rgba(100, 255, 218, 0.1);
        padding-bottom: 0.5rem;
        margin-bottom: 1rem;
    }
    @keyframes gradientMove {
        0% {background-position: 0% 50%;}
        50% {background-position: 100% 50%;}
        100% {background-position: 0% 50%;}
    }
    .title-text {
        text-align: center;
        font-size: 2.8rem;
        font-weight: bold;
        margin-top: 20px;
        background: -webkit-linear-gradient(var(--text), var(--accent));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 0 30px var(--glow);
        letter-spacing: -0.5px;
    }
    .pricing-card {
        background: var(--card-bg);
        backdrop-filter: blur(20px);
        border-radius: 12px;
        padding: 32px;
        text-align: center;
        box-shadow: 0 8px 32px var(--card-shadow);
        transition: all 0.3s ease-in-out;
        border: 1px solid var(--border);
        height: 100%;
        position: relative;
        overflow: hidden;
    }
    .pricing-card::after {
        content: "";
        position: absolute;
        inset: 0;
        border-radius: 12px;
        padding: 2px;
        background: linear-gradient(
            135deg,
            var(--accent),
            var(--hover)
        );
        -webkit-mask: 
            linear-gradient(#fff 0 0) content-box, 
            linear-gradient(#fff 0 0);
        -webkit-mask-composite: xor;
        mask-composite: exclude;
        opacity: 0;
        transition: opacity 0.3s ease;
    }
    .pricing-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 12px 40px var(--glow);
    }
    .pricing-card:hover::after {
        opacity: 1;
    }
    h2 { 
        color: var(--accent);
        font-weight: 600;
        letter-spacing: 0.5px;
        margin-bottom: 1rem;
    }
    h3 { 
        color: var(--text);
        font-weight: 500;
        letter-spacing: 0.5px;
        margin-bottom: 1.5rem;
    }
    ul { 
        list-style-type: none; 
        padding: 0; 
        text-align: left;
        margin-top: 1.5rem;
    }
    li { 
        margin: 12px 0; 
        color: var(--text);
        opacity: 0.9;
        transition: all 0.3s ease;
        padding-left: 1.5rem;
        position: relative;
    }
    li::before {
        content: "→";
        position: absolute;
        left: 0;
        color: var(--accent);
        opacity: 0;
        transition: opacity 0.3s ease;
    }
    li:hover {
        color: var(--text);
        opacity: 1;
        transform: translateX(5px);
    }
    li:hover::before {
        opacity: 1;
    }
    .stButton > button {
        background: var(--accent) !important;
        border: none !important;
        padding: 12px 24px !important;
        border-radius: 6px !important;
        color: var(--text) !important;
        font-size: 0.95rem !important;
        font-weight: 500 !important;
        cursor: pointer !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
        margin-top: 1.5rem !important;
        box-shadow: 0 4px 12px var(--glow) !important;
    }
    .stButton > button:hover {
        background: var(--hover) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 16px var(--glow) !important;
    }
    .stButton > button:active {
        transform: translateY(0) !important;
    }
    .footer {
        text-align: center;
        margin-top: 50px;
        color: var(--light-blue);
        font-size: 0.9rem;
        transition: color 0.3s ease;
    }
    .footer:hover {
        color: var(--blue-accent);
    }
    table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        color: var(--text);
        margin-top: 24px;
        background: var(--card-bg);
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 8px 32px var(--card-shadow);
        border: 1px solid var(--border);
    }
    th, td {
        border-bottom: 1px solid var(--border);
        padding: 16px;
        text-align: center;
        transition: all 0.3s ease;
    }
    th {
        background: var(--bg-main);
        color: var(--accent);
        font-weight: 600;
        letter-spacing: 0.5px;
        border-bottom: 2px solid var(--border);
    }
    tr:hover {
        background: var(--card-bg);
    }
    td:first-child {
        color: var(--accent);
        font-weight: 500;
    }
    tr:last-child td {
        border-bottom: none;
    }
    /* Feature indicators */
    td:not(:first-child) {
        font-weight: 500;
    }
    td:has(content: "✔") {
        color: var(--success);
    }
    td:has(content: "❌") {
        color: var(--error);
    }
    </style>
    """, unsafe_allow_html=True)

    # 🌟 Title
    st.markdown("<h1 class='title-text'>Choose Your AI Advice Plan</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center; color:#c9d6ff;'>Flexible pricing for every scale — all include API-based analysis</p>", unsafe_allow_html=True)

    # 🧭 Pricing Columns
    col1, col2, col3 = st.columns(3)

    # --- Free Plan ---
    with col1:
        st.markdown("""
        <div class="pricing-card">
            <h2>🌱 Free Plan</h2>
            <h3>$0/month</h3>
            <p><em>Ideal for new users & testing</em></p>
            <ul>
                <li>✔ API analysis access</li>
                <li>❌ Email alerts</li>
                <li>Up to <b>10 single post analyses</b> / month</li>
                <li>Up to <b>5 CSV batch uploads</b> / month</li>
                <li>Basic advice (no detailed explanations)</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Start Free 🚀", key="free_plan"):
            st.success("Redirecting to main dashboard...")
            st.session_state.selected_tab = 0  # 0 for Main Dashboard
            st.rerun()

    # --- Pro Plan ---
    with col2:
        st.markdown("""
        <div class="pricing-card">
            <h2>⚡ Pro Plan</h2>
            <h3>$19.99/month</h3>
            <p><em>Best for regular content moderators</em></p>
            <ul>
                <li>✔ API analysis access</li>
                <li>❌ Email alerts</li>
                <li>Up to <b>200 single analyses</b> / month</li>
                <li>Up to <b>50 CSV batch uploads</b> / month</li>
                <li>Detailed advice & risk reasoning</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Upgrade to Pro 💼", key="pro_plan"):
            st.session_state.selected_plan = "Pro"

    # --- Enterprise Plan ---
    with col3:
        st.markdown("""
        <div class="pricing-card">
            <h2>🏢 Enterprise Plan</h2>
            <h3>Custom Pricing</h3>
            <p><em>For large teams & platforms</em></p>
            <ul>
                <li>✔ API analysis access</li>
                <li>❌ Email alerts</li>
                <li>Unlimited single analyses</li>
                <li>Unlimited CSV uploads</li>
                <li>Priority API processing</li>
                <li>Custom team dashboard</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Contact Sales 🤝", key="enterprise_plan"):
            st.session_state.selected_plan = "Enterprise"

    # 🧾 Registration Form
    if st.session_state.get("selected_plan") in ["Pro", "Enterprise"]:
        st.markdown("---")
        plan = st.session_state.selected_plan
        st.subheader(f"Complete Your {plan} Plan Registration")

        # Add a back button to return to pricing
        if st.button("← Back to Plans"):
            st.session_state.selected_plan = None
            st.rerun()

        with st.form("registration_form", clear_on_submit=True):
            name = st.text_input("Full Name*")
            email = st.text_input("Email*")
            organization = st.text_input("Organization")
            payment_method = st.selectbox("Payment Method*", ["Credit Card", "PayPal", "Bank Transfer"])
            terms = st.checkbox("I agree to the Terms and Conditions*")

            submitted = st.form_submit_button("Submit 🚀")

            if submitted:
                if not all([name, email, terms]):
                    st.error("❌ Please fill in all required fields and accept the terms.")
                elif not validate_email(email):
                    st.error("📧 Invalid email address format.")
                else:
                    user_data = {
                        "name": name,
                        "email": email,
                        "organization": organization,
                        "payment_method": payment_method
                    }
                    if send_notification_email(user_data, plan):
                        # Set a success message in session state
                        st.session_state.email_success = True
                        st.session_state.selected_plan = None
                        st.session_state.selected_tab = 0  # 0 for Main Dashboard
                        st.rerun()
                    else:
                        st.warning("⚠️ Unable to send email notification. Please check SMTP settings.")

    # 🧩 Feature Comparison Table
    st.markdown("---")
    st.subheader("📊 Feature Comparison")

    st.markdown("""
    <table>
        <tr>
            <th>Features</th>
            <th>Free</th>
            <th>Pro</th>
            <th>Enterprise</th>
        </tr>
        <tr><td>API Analysis</td><td>✔</td><td>✔</td><td>✔</td></tr>
        <tr><td>Email Alerts</td><td>❌</td><td>❌</td><td>❌</td></tr>
        <tr><td>Single Post Analysis</td><td>10/month</td><td>200/month</td><td>Unlimited</td></tr>
        <tr><td>CSV Batch Upload</td><td>5/month</td><td>50/month</td><td>Unlimited</td></tr>
        <tr><td>Detailed Advice</td><td>Basic</td><td>✔</td><td>✔</td></tr>
        <tr><td>Priority Support</td><td>Standard</td><td>Priority</td><td>Dedicated 24/7</td></tr>
    </table>
    """, unsafe_allow_html=True)

    # 🌙 Footer
    st.markdown("""
    <div class="footer">
        © 2025 SMS_AI | Built with ❤️ using Streamlit
    </div>
    """, unsafe_allow_html=True)


# ------------------ Run Page ------------------
if __name__ == "__main__":
    display_pricing_page()
