import streamlit as st
import time
import pandas as pd

# -------------------------------
# Page config and global styles
# -------------------------------
st.set_page_config(page_title="🛡️ Social Media Safety AI", page_icon="🧠", layout="wide", initial_sidebar_state="expanded")

# Load Google Fonts
st.markdown(
    """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap" rel="stylesheet">
<style>
  :root {
    --electric: #00FFFF;
    --purple: #6A0DAD;
    --neon: #39FF14;
    --jet: #0D0D0D;
  }
  html, body, [class^="css"]  {
    font-family: 'Inter', sans-serif;
  }
  /* Animated background gradient */
  .stApp {
    background: linear-gradient(120deg, rgba(0,255,255,0.12), rgba(106,13,173,0.12), rgba(57,255,20,0.12));
    background-size: 200% 200%;
    animation: moveBg 16s ease infinite;
  }
  @keyframes moveBg { 0% {background-position: 0% 50%} 50% {background-position: 100% 50%} 100% {background-position: 0% 50%} }

  /* Glowing header */
  .ai-title { font-size: 42px; font-weight: 800; color: #E6F7FF; text-shadow: 0 0 8px var(--electric), 0 0 20px rgba(0, 255, 255, 0.3); }
  .subtitle { color: #BFBFBF; margin-top: -12px; }

  /* Cards */
  .glass-card { background: rgba(13,13,13,0.65); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 18px 18px; box-shadow: 0 10px 30px rgba(0,0,0,0.35), 0 0 12px rgba(0,255,255,0.06); }
  .glow-border { border: 1px solid rgba(0,255,255,0.3); box-shadow: 0 0 10px rgba(0,255,255,0.2) inset, 0 0 16px rgba(0,255,255,0.1); border-radius: 12px; }

  /* Buttons */
  .gradient-btn button { 
    background: linear-gradient(90deg, var(--purple), var(--electric));
    border: 0; color: #fff; font-weight: 700; border-radius: 12px; padding: 0.6rem 1.2rem; transition: transform .2s ease, box-shadow .2s ease;
  }
  .gradient-btn button:hover { transform: translateY(-1px); box-shadow: 0 8px 24px rgba(0,255,255,0.25); }

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] { gap: 12px; }
  .stTabs [data-baseweb="tab"] { background: rgba(13,13,13,0.55); border-radius: 999px; padding: 8px 16px; color: #D8D8D8; border: 1px solid rgba(255,255,255,0.08); }
  .stTabs [aria-selected="true"] { border: 1px solid rgba(0,255,255,0.4); color: #fff; box-shadow: 0 0 10px rgba(0,255,255,0.15); }

  /* Sidebar */
  section[data-testid="stSidebar"] { background: rgba(13,13,13,0.85) !important; border-right: 1px solid rgba(255,255,255,0.06); }
  .side-item { padding: 8px 10px; border-radius: 10px; margin-bottom: 6px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); }

  /* AI Pulse Indicator */
  .ai-pulse { width:10px;height:10px;border-radius:50%; background: var(--neon); box-shadow: 0 0 12px rgba(57,255,20,0.9); animation: pulse 1.6s infinite ease-in-out; display:inline-block; margin-bottom:-2px; }
  @keyframes pulse { 0%{transform:scale(0.9); opacity:.8} 50%{transform:scale(1.2); opacity:1} 100%{transform:scale(0.9); opacity:.8} }

  .metric-big { font-size:30px; font-weight:800; color:#E6F7FF }
  .metric-sub { color:#9AA0A6; }

  /* Dataframe glow wrapper */
  .df-wrap { padding: 8px; border-radius: 12px; }
</style>
    """,
    unsafe_allow_html=True,
)

# -------------------------------
# Sidebar Navigation
# -------------------------------
st.sidebar.markdown("### 🧭 Navigation")
st.sidebar.markdown(
    """
<div class="side-item">📝 Content Analyzer</div>
<div class="side-item">🛡️ Risk Detector</div>
<div class="side-item">🧯 Mitigation Agent</div>
<div class="side-item">💡 Advice Agent</div>
<div class="side-item">🚨 Admin Alerts</div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown("---")
dark_mode = st.sidebar.toggle("🌙 Dark Mode", value=True)
st.sidebar.markdown("**AI Status:** <span class='ai-pulse'></span> <span style='margin-left:6px;'>Active</span>", unsafe_allow_html=True)

# -------------------------------
# Header
# -------------------------------
st.markdown("<div class='ai-title'>🧠 Social Media Safety AI</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Futuristic AI control center UI with glowing analytics</div>", unsafe_allow_html=True)

# -------------------------------
# Top Row Metrics (demo values)
# -------------------------------
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown("<div class='glass-card'><div class='metric-big'>128</div><div class='metric-sub'>Comments Processed</div></div>", unsafe_allow_html=True)
with col2:
    st.markdown("<div class='glass-card'><div class='metric-big'>23</div><div class='metric-sub'>High-risk Comments</div></div>", unsafe_allow_html=True)
with col3:
    st.markdown("<div class='glass-card'><div class='metric-big'>7</div><div class='metric-sub'>Flagged Users</div></div>", unsafe_allow_html=True)
with col4:
    st.markdown("<div class='glass-card'><div class='metric-big'>92%</div><div class='metric-sub'>Automation Coverage</div></div>", unsafe_allow_html=True)

# -------------------------------
# Mitigation Dashboard Only
# -------------------------------
st.markdown("#### 🧯 Mitigation Agent Dashboard")
st.markdown("<div class='glass-card glow-border'>Real-time mitigation decisions, actions, and reasoning.</div>", unsafe_allow_html=True)

# Demo placeholder DataFrame for mitigation
demo_mitigation_df = pd.DataFrame({
    "userID": [1, 2, 3, 4, 5],
    "username": ["alice", "bob", "carol", "david", "eve"],
    "comment": ["You are stupid", "Click here for free prize", "I love this!", "This is amazing", "You people are disgusting"],
    "risk_level": ["High", "Medium", "Low", "Low", "High"],
    "toxicity": [0.85, 0.52, 0.08, 0.12, 0.92],
    "label": ["Cyberbullying", "Scam", "Safe", "Safe", "Cyberbullying"],
    "final_status": ["Flagged", "Under Review", "Safe", "Safe", "Flagged"],
    "mitigation_action": ["Immediate block and alert admin", "Add to review queue", "No action", "No action", "Immediate block and alert admin"]
})

# Display mitigation data
st.markdown("**Recent Mitigation Decisions**")
st.markdown("<div class='df-wrap glow-border'>", unsafe_allow_html=True)
st.dataframe(demo_mitigation_df, use_container_width=True)
st.markdown("</div>", unsafe_allow_html=True)

# Mitigation statistics
col1, col2, col3, col4 = st.columns(4)
with col1:
    flagged_count = len(demo_mitigation_df[demo_mitigation_df["final_status"] == "Flagged"])
    st.markdown(f"<div class='glass-card'><div class='metric-big'>{flagged_count}</div><div class='metric-sub'>Flagged Posts</div></div>", unsafe_allow_html=True)
with col2:
    review_count = len(demo_mitigation_df[demo_mitigation_df["final_status"] == "Under Review"])
    st.markdown(f"<div class='glass-card'><div class='metric-big'>{review_count}</div><div class='metric-sub'>Under Review</div></div>", unsafe_allow_html=True)
with col3:
    safe_count = len(demo_mitigation_df[demo_mitigation_df["final_status"] == "Safe"])
    st.markdown(f"<div class='glass-card'><div class='metric-big'>{safe_count}</div><div class='metric-sub'>Safe Posts</div></div>", unsafe_allow_html=True)
with col4:
    avg_toxicity = demo_mitigation_df["toxicity"].mean()
    st.markdown(f"<div class='glass-card'><div class='metric-big'>{avg_toxicity:.2f}</div><div class='metric-sub'>Avg Toxicity</div></div>", unsafe_allow_html=True)

# Mitigation action breakdown
st.markdown("**Mitigation Action Breakdown**")
action_counts = demo_mitigation_df["mitigation_action"].value_counts()
st.bar_chart(action_counts)

# Risk level distribution
st.markdown("**Risk Level Distribution**")
risk_counts = demo_mitigation_df["risk_level"].value_counts()
st.bar_chart(risk_counts)

# Live mitigation examples
st.markdown("**Live Mitigation Examples**")
with st.expander("View Recent Mitigation Decisions"):
    for idx, row in demo_mitigation_df.iterrows():
        if row["final_status"] == "Flagged":
            st.error(f"🚨 **{row['username']}**: {row['comment'][:50]}... → {row['mitigation_action']}")
        elif row["final_status"] == "Under Review":
            st.warning(f"⚠️ **{row['username']}**: {row['comment'][:50]}... → {row['mitigation_action']}")
        else:
            st.success(f"✅ **{row['username']}**: {row['comment'][:50]}... → {row['mitigation_action']}")

# Integration code example
st.markdown("**Integration Example**")
st.code("""
# Example integration point for mitigation dashboard:
# from mitigation_agent import mitigate
# from content_analyzer import analyze_row
# from risk_detector import compute_risk
# 
# # Process a comment through the pipeline
# analyzed = analyze_row({"userID": 1, "username": "user", "comment_id": 1, "comment": "text"})
# risk = compute_risk(analyzed)
# mitigation = mitigate(analyzed, risk, {})
# 
# # Display in dashboard
# st.dataframe(pd.DataFrame([mitigation]))
""", language="python")

# -------------------------------
# Workflow Button and Progress Demo
# -------------------------------
st.markdown("---")
st.markdown("### Workflow")
workflow_btn = st.container()
with workflow_btn:
    colA, colB = st.columns([1,4])
    with colA:
        st.markdown("<div class='gradient-btn'>", unsafe_allow_html=True)
        run = st.button("▶ Run Demo Workflow")
        st.markdown("</div>", unsafe_allow_html=True)
    with colB:
        if run:
            prog = st.progress(0, text="Initializing...")
            for i in range(1, 101):
                time.sleep(0.01)
                prog.progress(i, text=f"Processing... {i}%")
            st.success("Workflow complete. Replace with real pipeline calls.")

# Note: This dashboard is a UI shell. Integrate your backend by replacing placeholders with real data.


