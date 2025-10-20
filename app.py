import streamlit as st
import pandas as pd
import io
import os
from dotenv import load_dotenv
load_dotenv()
from typing import Dict, Any, List
try:
    import altair as alt
    _ALT_AVAILABLE = True
except Exception:
    alt = None
    _ALT_AVAILABLE = False

from content_analyzer import analyze_row, analyze_batch
from risk_detector import compute_risk
from advice_agent import generate_advice
from mitigation_agent import mitigate
from email_helper import send_alert

st.set_page_config(page_title="Social Media Safety AI", page_icon="🛡️", layout="wide")

st.markdown("""
<link rel=\"preconnect\" href=\"https://fonts.googleapis.com\">
<link rel=\"preconnect\" href=\"https://fonts.gstatic.com\" crossorigin>
<link href=\"https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap\" rel=\"stylesheet\">
<style>
  :root { --electric:#00FFFF; --purple:#6A0DAD; --neon:#39FF14; --jet:#0D0D0D; }
  html, body, [class^=\"css\"] { font-family: 'Inter', sans-serif; }
  .stApp { background: linear-gradient(120deg, rgba(0,255,255,0.10), rgba(106,13,173,0.10), rgba(57,255,20,0.10)); background-size: 200% 200%; animation: moveBg 16s ease infinite; }
  @keyframes moveBg { 0%{background-position:0% 50%} 50%{background-position:100% 50%} 100%{background-position:0% 50%} }
  .ai-title { font-size: 42px; font-weight: 800; color: #E6F7FF; text-shadow: 0 0 8px var(--electric), 0 0 20px rgba(0,255,255,0.3); }
  .subtitle { color: #BFBFBF; margin-top: -10px; }
  .glass-card { background: rgba(13,13,13,0.65); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 14px 16px; box-shadow: 0 10px 28px rgba(0,0,0,0.35), 0 0 12px rgba(0,255,255,0.06); }
  .glow-border { border: 1px solid rgba(0,255,255,0.3); box-shadow: 0 0 10px rgba(0,255,255,0.2) inset, 0 0 16px rgba(0,255,255,0.1); border-radius: 12px; }
  .gradient-btn button { background: linear-gradient(90deg, var(--purple), var(--electric)); border: 0; color: #fff; font-weight: 700; border-radius: 12px; padding: 0.6rem 1.2rem; transition: transform .2s ease, box-shadow .2s ease; }
  .gradient-btn button:hover { transform: translateY(-1px); box-shadow: 0 8px 24px rgba(0,255,255,0.25); }
  .stTabs [data-baseweb=\"tab-list\"] { gap: 12px; }
  .stTabs [data-baseweb=\"tab\"] { background: rgba(13,13,13,0.55); border-radius: 999px; padding: 8px 16px; color: #D8D8D8; border: 1px solid rgba(255,255,255,0.08); }
  .stTabs [aria-selected=\"true\"] { border: 1px solid rgba(0,255,255,0.4); color: #fff; box-shadow: 0 0 10px rgba(0,255,255,0.15); }
  section[data-testid=\"stSidebar\"] { background: rgba(13,13,13,0.85) !important; border-right: 1px solid rgba(255,255,255,0.06); }
  .side-item { padding: 8px 10px; border-radius: 10px; margin-bottom: 6px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.06); color:#E6F7FF; }
  .ai-pulse { width:10px;height:10px;border-radius:50%; background: var(--neon); box-shadow: 0 0 12px rgba(57,255,20,0.9); animation: pulse 1.6s infinite ease-in-out; display:inline-block; margin-bottom:-2px; }
  @keyframes pulse { 0%{transform:scale(0.9); opacity:.8} 50%{transform:scale(1.2); opacity:1} 100%{transform:scale(0.9); opacity:.8} }
  .df-wrap { padding: 8px; border-radius: 12px; }
  .big-metric {font-size: 28px; font-weight: 800; color:#E6F7FF}
  .subtext {color: #9AA0A6;}
  .risk-high {background:#2a0e0e;color:#ffb4b4;}
  .risk-medium {background:#2a250e;color:#ffd58a;}
  .risk-low {background:#0e2a17;color:#9dffb1;}
</style>
""", unsafe_allow_html=True)

st.sidebar.markdown("### 🧭 Controls")
st.sidebar.markdown("<div class='side-item'>Use controls below to customize analysis and display.</div>", unsafe_allow_html=True)
st.sidebar.markdown("---")

# Performance controls
st.sidebar.markdown("#### ⚙️ Performance")
sample_limit = st.sidebar.number_input("Max rows to process", min_value=1, value=500, step=50)
batch_size_ui = st.sidebar.slider("Batch size", min_value=8, max_value=256, value=64, step=8)
use_embeddings = st.sidebar.toggle("Use embeddings (slower)", value=False)
fast_mode = st.sidebar.toggle("Fast mode (skip external API calls)", value=True, help="Temporarily disables external API calls during this run to speed up processing.")

# Filters
st.sidebar.markdown("#### 🧭 Filters")
filter_levels = st.sidebar.multiselect("Show risk levels", ["High", "Medium", "Low"], default=["High", "Medium", "Low"])
min_risk = st.sidebar.slider("Min risk score", 0.0, 1.0, 0.0, 0.05)
user_search = st.sidebar.text_input("Search username contains")

st.sidebar.markdown("**AI Status:** <span class='ai-pulse'></span> <span style='margin-left:6px;'>Active</span>", unsafe_allow_html=True)
st.sidebar.markdown("---")
admin_alerts_open = st.sidebar.button("🚨 Open Admin Alerts Dashboard")

# Quick test for email settings (uses send_alert; will try SendGrid first if configured)
if st.sidebar.button("📬 Test Email Settings"):
    test_subj = "[Test] SMS_AI email settings"
    test_body = "This is a test email from your SMS_AI instance. If you received this, SendGrid/SMTP is configured."
    ok, err = send_alert(test_subj, test_body)
    if ok:
        st.sidebar.success("Test email sent to admin address.")
    else:
        st.sidebar.error(f"Test failed — {err or 'check SENDGRID_API_KEY or SMTP settings in .env and environment variables.'}")

# Quick test for advice generation (uses ADVICE_API_PROVIDER / ADVICE_AGENT_URL or builtin)
if st.sidebar.button("🧠 Test Advice (use last analysis)"):
    sample_risk = None
    if st.session_state.get('last_risk'):
        sample_risk = st.session_state.get('last_risk')
        sample_mitig = st.session_state.get('last_mitigate')
    else:
        st.sidebar.info("No previous analysis found; using a default sample.")
        sample_risk = {"userID": 1, "username": "test", "comment_id": 1, "risk_score": 0.8, "risk_level": "High", "risk_reason": "hate speech"}
        sample_mitig = {}
    with st.sidebar.spinner("Generating advice..."):
        try:
            advice = generate_advice(sample_risk, sample_mitig)
            st.sidebar.success("Advice generated (see details)")
            with st.sidebar.expander("Advice JSON"):
                st.json(advice)
        except Exception as e:
            st.sidebar.error(f"Advice generation failed: {e}")

st.markdown("<div class='ai-title'>🧠 Social Media Safety AI</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Analyze social media content for safety and risk assessment</div>", unsafe_allow_html=True)

# Analysis mode selection
analysis_mode = st.radio(
    "Choose analysis mode:",
    ["📝 Single Post Analysis", "📊 CSV Batch Analysis"],
    horizontal=True
)

if analysis_mode == "📝 Single Post Analysis":
    st.markdown("### 📝 Single Post Analysis")
    st.markdown("Enter a post or comment to analyze through our AI safety pipeline.")
    
    # User input form
    with st.form("post_analysis_form"):
        col1, col2 = st.columns(2)
        with col1:
            user_id = st.number_input("User ID", min_value=1, value=1, step=1)
            username = st.text_input("Username", value="user123")
        with col2:
            comment_id = st.number_input("Comment ID", min_value=1, value=1, step=1)
        
        post_text = st.text_area(
            "Post/Comment Text", 
            placeholder="Enter the post or comment you want to analyze...",
            height=100
        )
        
        analyze_post = st.form_submit_button("🔍 Analyze Post", use_container_width=True)
    
    # Show results if user just submitted OR if we have saved results in session_state
    if (analyze_post and post_text.strip()) or st.session_state.get("show_results"):
        # If this run just submitted the form, perform analysis and persist to session_state
        if analyze_post and post_text.strip():
            # Process single post through the pipeline
            with st.spinner("Analyzing post through AI pipeline..."):
                # Create row data for analysis
                row_data = {
                    "userID": user_id,
                    "username": username,
                    "comment_id": comment_id,
                    "comment": post_text.strip()
                }

                # Run through the analysis pipeline
                analyzed = analyze_row(row_data, embed=bool(use_embeddings))
                risk_out = compute_risk(analyzed)
                mitigate_out = mitigate(analyzed, risk_out, {})
                # Ensure comment text is available to the advice generator so URL checks run
                risk_for_advice = {**risk_out, "comment": row_data.get("comment")}
                advice_out = generate_advice(risk_for_advice, mitigation_out=mitigate_out)

                # Persist to session state so subsequent reruns (like clicking send) keep showing results
                st.session_state['last_analyzed'] = analyzed
                st.session_state['last_risk'] = risk_out
                st.session_state['last_mitigate'] = mitigate_out
                st.session_state['last_advice'] = advice_out
                st.session_state['last_post_text'] = post_text
                st.session_state['last_user_id'] = user_id
                st.session_state['last_username'] = username
                st.session_state['show_results'] = True
        # Load from session state for display when user interacts (button clicks cause rerun)
        analyzed = st.session_state.get('last_analyzed')
        risk_out = st.session_state.get('last_risk')
        mitigate_out = st.session_state.get('last_mitigate')
        advice_out = st.session_state.get('last_advice')
        post_text = st.session_state.get('last_post_text', '')
        user_id = st.session_state.get('last_user_id', user_id)
        username = st.session_state.get('last_username', username)

        # Display results with improved frontend-style UI
        st.success("✅ Analysis Complete!")

        # Create tabs for results
        result_tabs = st.tabs(["📝 Content Analysis", "🛡️ Risk Assessment", "💡 Advice", "🧯 Mitigation"])

        # --- Content Analysis Tab ---
        with result_tabs[0]:
            st.subheader("Content Analysis")
            st.markdown("<div class='df-wrap glow-border'>", unsafe_allow_html=True)
            # Top preview and compact metadata cards
            st.markdown(f"### 🔎 Preview\n{post_text[:400]}{'...' if len(post_text) > 400 else ''}")
            # compact card row for metadata
            meta_html = f'''<div style="display:flex;gap:12px;margin-top:10px;"> 
                <div style="flex:1;padding:10px;border-radius:10px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.04);"> <strong>User</strong><br>{username}</div>
                <div style="flex:1;padding:10px;border-radius:10px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.04);"> <strong>User ID</strong><br>{user_id}</div>
                <div style="flex:1;padding:10px;border-radius:10px;background:linear-gradient(90deg,#fffbfb,#f0fcff);border:1px solid rgba(255,255,255,0.04);"> <strong>Sentiment</strong><br>{analyzed.get('sentiment','Unknown').title()}</div>
                <div style="flex:1;padding:10px;border-radius:10px;background:linear-gradient(90deg,#fff8ff,#f7f0ff);border:1px solid rgba(255,255,255,0.04);"> <strong>Emotion</strong><br>{analyzed.get('emotion','Unknown').title()}</div>
                <div style="flex:1;padding:10px;border-radius:10px;background:linear-gradient(90deg,#f8fff6,#f0fff0);border:1px solid rgba(255,255,255,0.04);"> <strong>Topic</strong><br>{analyzed.get('topic','Unknown').title()}</div>
            </div>'''
            st.markdown(meta_html, unsafe_allow_html=True)

            # Full analysis in expander (keeps UI clean)
            with st.expander("Show full content analysis (raw)"):
                st.json(analyzed)
            st.markdown("</div>", unsafe_allow_html=True)

        # --- Risk Assessment Tab ---
        with result_tabs[1]:
            st.subheader("Risk Assessment")
            st.markdown("<div class='df-wrap glow-border'>", unsafe_allow_html=True)
            # Score and level
            risk_score = float(risk_out.get("risk_score", 0) or 0)
            risk_level = risk_out.get("risk_level", "Low")
            r_col1, r_col2 = st.columns([2,1])
            with r_col1:
                # Big gauge-like presentation using metric and progress
                if risk_level == "High":
                    st.metric(label="Risk Level", value=f"🚨 {risk_level}", delta=f"{risk_score:.3f}")
                elif risk_level == "Medium":
                    st.metric(label="Risk Level", value=f"⚠️ {risk_level}", delta=f"{risk_score:.3f}")
                else:
                    st.metric(label="Risk Level", value=f"✅ {risk_level}", delta=f"{risk_score:.3f}")
                st.progress(min(max(risk_score, 0.0), 1.0))
                st.caption("Higher progress means higher estimated risk")
            with r_col2:
                # compact user info card row
                info_html = f'''<div style="display:flex;gap:8px;align-items:center;"> 
                    <div style="flex:1;padding:8px;border-radius:10px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.04);"> <strong>User ID</strong><br>{risk_out.get('userID', user_id)}</div>
                    <div style="flex:2;padding:8px;border-radius:10px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.04);"> <strong>Username</strong><br>{risk_out.get('username', username)}</div>
                    <div style="flex:1;padding:8px;border-radius:10px;background:rgba(255,50,50,0.06);border:1px solid rgba(255,50,50,0.06);"> <strong>Anomaly</strong><br>{str(risk_out.get('anomaly_flag', False))}</div>
                </div>'''
                st.markdown(info_html, unsafe_allow_html=True)
                st.markdown("**User cumulative risk**")
                st.metric("Cumulative", f"{risk_out.get('user_cumulative_risk', 0):.3f}")
                st.markdown("**Contributing factors**")
                factors = risk_out.get("factors") or []
                if factors:
                    for f in factors[:6]:
                        st.info(f)
                else:
                    st.write("No explicit factors provided")

            # More details
            with st.expander("Show full risk output (raw)"):
                st.json(risk_out)
            st.markdown("</div>", unsafe_allow_html=True)

        # --- Advice Tab ---
        with result_tabs[2]:
            st.subheader("AI Advice")
            st.markdown("<div class='df-wrap glow-border'>", unsafe_allow_html=True)
            advice_text = advice_out.get("advice") or advice_out.get("summary") or "No advice available"
            mod_sugg = advice_out.get("moderation_suggestion") or "No suggestion available"
            pred_beh = advice_out.get("predicted_behavior_risk")

            st.markdown(f"### 💡 Recommendation\n{advice_text}")
            st.markdown(f"**Moderation suggestion:** {mod_sugg}")
            if pred_beh is not None:
                st.metric("Predicted behavior risk", f"{float(pred_beh):.3f}")

            # Suggested actions list
            actions = advice_out.get("suggested_actions") or advice_out.get("actions") or []
            if actions:
                for a in actions:
                    st.write(f"- {a}")
            else:
                st.write("No explicit action list provided")

            with st.expander("Show full advice output (raw)"):
                st.json(advice_out)
            st.markdown("</div>", unsafe_allow_html=True)

        # --- Mitigation Tab ---
        with result_tabs[3]:
            st.subheader("Mitigation Decision")
            st.markdown("<div class='df-wrap glow-border'>", unsafe_allow_html=True)
            final_status = mitigate_out.get("final_status", "Unknown")
            mitigation_action = mitigate_out.get("mitigation_action", "No action")
            label = mitigate_out.get("label", "")

            st.markdown(f"**Label:** {label}")
            if final_status == "Flagged":
                st.error(f"🚨 Status: {final_status}")
                st.markdown(f"**Action:** {mitigation_action}")
            elif final_status == "Under Review":
                st.warning(f"⚠️ Status: {final_status}")
                st.markdown(f"**Action:** {mitigation_action}")
            else:
                st.success(f"✅ Status: {final_status}")
                st.markdown(f"**Action:** {mitigation_action}")

            # Mitigation metadata as styled cards
            mit_html = f'''<div style="display:flex;gap:12px;margin-top:8px;"> 
                <div style="flex:1;padding:10px;border-radius:10px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.04);"> <strong>Toxicity</strong><br>{mitigate_out.get('toxicity_score', mitigate_out.get('toxicity', 'N/A'))}</div>
                <div style="flex:1;padding:10px;border-radius:10px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.04);"> <strong>Username</strong><br>{mitigate_out.get('username', username)}</div>
                <div style="flex:1;padding:10px;border-radius:10px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.04);"> <strong>User ID</strong><br>{mitigate_out.get('userID', user_id)}</div>
                <div style="flex:1;padding:10px;border-radius:10px;background:linear-gradient(90deg,#ff3c3c22,#ffb4b422);border:1px solid rgba(255,60,60,0.06);"> <strong>Final Status</strong><br>{mitigate_out.get('final_status', final_status)}</div>
                <div style="flex:1;padding:10px;border-radius:10px;background:linear-gradient(90deg,#6A0DAD22,#00FFFF22);border:1px solid rgba(106,13,173,0.06);"> <strong>Trend Priority</strong><br>{mitigate_out.get('trend_priority', mitigate_out.get('priority', 'N/A'))}</div>
                <div style="flex:1;padding:10px;border-radius:10px;background:linear-gradient(90deg,#39FF1422,#00FFFF22);border:1px solid rgba(57,255,20,0.06);"> <strong>Alert Method</strong><br>{mitigate_out.get('alert_method', mitigate_out.get('alert_channel', 'N/A'))}</div>
            </div>'''
            st.markdown(mit_html, unsafe_allow_html=True)

            with st.expander("Show full mitigation output (raw)"):
                st.json(mitigate_out)

            # Only show send-alert button when final_status is Flagged
            if (mitigate_out and mitigate_out.get("final_status") == "Flagged"):
                st.markdown("<div style='margin-top:10px'>", unsafe_allow_html=True)
                if st.button("📧 Send alert to admin (Email)"):
                    # Use persisted mitigate_out from session state to avoid losing data on rerun
                    m = st.session_state.get('last_mitigate', mitigate_out)
                    subj = f"[Alert] Flagged comment by {m.get('username', username)}"
                    body = f"Comment ID: {m.get('comment_id')}\nUser: {m.get('username')}\nUser ID: {m.get('userID')}\nLabel: {m.get('label')}\nToxicity: {m.get('toxicity_score')}\nAction: {m.get('mitigation_action')}\nReasoning: {m.get('reasoning')}"
                    ok, err = send_alert(subj, body)
                    if ok:
                        st.success("Alert email sent to admin.")
                    else:
                        st.error(f"Failed to send alert — {err or 'check SMTP or SENDGRID settings in .env and environment variables.'}")
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("</div>", unsafe_allow_html=True)
    
    elif analyze_post and not post_text.strip():
        st.error("Please enter some text to analyze.")

else:
    # CSV Analysis Mode (existing functionality)
    st.markdown("### 📊 CSV Batch Analysis")
    st.markdown("Upload a CSV with columns: userID, username, comment_id, comment")
    
    uploaded_file = st.file_uploader("Choose CSV file", type=["csv"])

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
        except Exception as e:
            st.error(f"Failed to read CSV: {e}")
            st.stop()

        required = {"userID", "username", "comment_id", "comment"}
        if not required.issubset(set(df.columns)):
            st.error(f"CSV must contain columns: {required}")
            st.stop()

        total_comments = len(df)
        total_users = df["userID"].nunique()

        st.sidebar.metric("Total comments", total_comments)
        st.sidebar.metric("Total users", total_users)

        # Process rows in batches for scalability
        BATCH_SIZE = int(batch_size_ui)
        analyzed_list: List[Dict[str, Any]] = []
        risk_list: List[Dict[str, Any]] = []
        advice_list: List[Dict[str, Any]] = []
        mitigation_list: List[Dict[str, Any]] = []

        # simple user cumulative risk map
        user_risk_map = {}

        # Optional speed limit
        if len(df) > sample_limit:
            df = df.head(sample_limit)

        # Temporarily disable external APIs for speed
        restore_env = {}
        if fast_mode:
            for key in ["HUGGINGFACE_API_KEY", "PERSPECTIVE_API_KEY"]:
                if key in os.environ:
                    restore_env[key] = os.environ[key]
                    os.environ.pop(key, None)

        progress = st.progress(0)
        rows = []
        for idx, row in df.iterrows():
            rows.append({"userID": row["userID"], "username": row["username"], "comment_id": row["comment_id"], "comment": row["comment"]})
            # when batch is full or last row, process batch
            if len(rows) >= BATCH_SIZE or idx == len(df) - 1:
                batch_out = analyze_batch(rows, embed=bool(use_embeddings))
                for i, analyzed in enumerate(batch_out):
                    prev = user_risk_map.get(analyzed["userID"])
                    risk_out = compute_risk(analyzed, user_history_risk=prev)
                    user_risk_map[analyzed["userID"]] = risk_out["user_cumulative_risk"]

                    # compute mitigation first so advice can reference the mitigation label and reasoning
                    mitigate_out = mitigate(analyzed, risk_out, {})
                    # Pass the comment into the advice generator so URL safety checks run
                    risk_for_advice = {**risk_out, "comment": analyzed.get("comment")}
                    advice_out = generate_advice(risk_for_advice, mitigation_out=mitigate_out)

                    analyzed_list.append(analyzed)
                    risk_list.append(risk_out)
                    advice_list.append(advice_out)
                    mitigation_list.append(mitigate_out)

                progress.progress(int((idx + 1) / total_comments * 100))
                rows = []

        progress.empty()

        # Restore API keys if disabled
        if restore_env:
            for k, v in restore_env.items():
                os.environ[k] = v

        # Convert to DataFrames for display
        df_analyzed = pd.DataFrame(analyzed_list)
        df_risk = pd.DataFrame(risk_list)
        df_advice = pd.DataFrame(advice_list)
        df_mitig = pd.DataFrame(mitigation_list)

        # Apply sidebar filters
        if not df_risk.empty:
            mask = df_risk["risk_level"].isin(filter_levels) & (df_risk["risk_score"] >= min_risk)
            if user_search:
                mask = mask & df_risk["username"].astype(str).str.contains(user_search, case=False, na=False)
            df_risk = df_risk[mask]
            ids = set(df_risk["comment_id"].tolist())
            if not df_advice.empty:
                df_advice = df_advice[df_advice["comment_id"].isin(ids)]
            if not df_mitig.empty:
                df_mitig = df_mitig[df_mitig["comment_id"].isin(ids)]
            if not df_analyzed.empty:
                df_analyzed = df_analyzed[df_analyzed["comment_id"].isin(ids)]

        # Overview
        st.header("Overview")
        col1, col2, col3 = st.columns(3)
        high_risk_count = df_risk[df_risk["risk_level"] == "High"].shape[0]
        flagged_users = df_mitig[df_mitig["final_status"] == "Flagged"]["userID"].nunique()
        category_counts = df_mitig["label"].value_counts().to_dict()

        col1.metric("High-risk comments", high_risk_count)
        col2.metric("Flagged users", flagged_users)
        with col3:
            st.write("Category distribution")
            cat_series = pd.Series(category_counts)
            try:
                if _ALT_AVAILABLE and not cat_series.empty:
                    chart = alt.Chart(cat_series.reset_index().rename(columns={"index":"label",0:"count"})).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
                        x=alt.X("label:N", sort='-y'), y="count:Q",
                        color=alt.Color("label:N", scale=alt.Scale(range=['#00FFFF','#6A0DAD','#39FF14','#FF7A00','#FF3CAC']))
                    ).properties(height=240)
                    st.altair_chart(chart, use_container_width=True)
                else:
                    st.bar_chart(cat_series)
            except Exception:
                st.bar_chart(cat_series)

        # Tabs for agents
        tabs = st.tabs(["📝 Content Analyzer", "🛡️ Risk Detector", "💡 Advice Agent", "🧯 Mitigation Agent"]) 

        with tabs[0]:
            st.subheader("Content Analyzer")
            st.markdown("<div class='df-wrap glow-border'>", unsafe_allow_html=True)
            st.dataframe(df_analyzed, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
            colA, colB = st.columns(2)
            with colA:
                st.markdown("**Emotions**")
                if not df_analyzed.empty and "emotion" in df_analyzed:
                    try:
                        emotion_counts = df_analyzed["emotion"].value_counts().reset_index()
                        emotion_counts.columns = ["emotion","count"]
                        if _ALT_AVAILABLE:
                            emo_chart = alt.Chart(emotion_counts).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
                                x=alt.X("emotion:N", sort='-y'), y="count:Q",
                                color=alt.Color("emotion:N", scale=alt.Scale(range=['#6A0DAD','#00FFFF','#39FF14','#FF3CAC','#FFA500']))
                            )
                            st.altair_chart(emo_chart, use_container_width=True)
                        else:
                            st.bar_chart(emotion_counts.set_index("emotion")['count'])
                    except Exception:
                        st.bar_chart(df_analyzed["emotion"].value_counts())
                else:
                    st.info("No emotion data available.")
            with colB:
                st.markdown("**Language flags**")
                try:
                    counts = pd.DataFrame({"flag": ["bad_language","hate_speech"], "count": [int(df_analyzed.get("bad_language", pd.Series(dtype=int)).sum() if not df_analyzed.empty else 0), int(df_analyzed.get("hate_speech", pd.Series(dtype=int)).sum() if not df_analyzed.empty else 0)]})
                    if _ALT_AVAILABLE:
                        flag_chart = alt.Chart(counts).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
                            x="flag:N", y="count:Q", color=alt.Color("flag:N", scale=alt.Scale(range=['#FF3CAC','#39FF14']))
                        )
                        st.altair_chart(flag_chart, use_container_width=True)
                    else:
                        st.bar_chart(counts.set_index("flag")['count'])
                except Exception:
                    st.bar_chart(pd.Series({"bad_language":0,"hate_speech":0}))

        with tabs[1]:
            st.subheader("Risk Detector")
            st.markdown("<div class='df-wrap glow-border'>", unsafe_allow_html=True)
            st.dataframe(df_risk, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
            colR1, colR2 = st.columns(2)
            with colR1:
                st.markdown("**Risk levels**")
                try:
                    rl = df_risk["risk_level"].value_counts().reset_index()
                    rl.columns = ["risk_level","count"]
                    if _ALT_AVAILABLE:
                        rl_chart = alt.Chart(rl).mark_arc(innerRadius=40).encode(theta="count:Q", color=alt.Color("risk_level:N", scale=alt.Scale(range=['#FF3CAC','#FFD166','#39FF14'])))
                        st.altair_chart(rl_chart, use_container_width=True)
                    else:
                        st.bar_chart(rl.set_index("risk_level")['count'])
                except Exception:
                    st.bar_chart(df_risk["risk_level"].value_counts())
            with colR2:
                st.markdown("**Top risky users**")
                top_users = df_risk.groupby("userID")["risk_score"].mean().sort_values(ascending=False).head(10)
                try:
                    tu = top_users.reset_index().rename(columns={"risk_score":"avg_risk"})
                    if _ALT_AVAILABLE:
                        tu_chart = alt.Chart(tu).mark_line(point=True).encode(x=alt.X("userID:O"), y="avg_risk:Q", color=alt.value('#00FFFF'))
                        st.altair_chart(tu_chart, use_container_width=True)
                    else:
                        st.line_chart(tu.set_index("userID")['avg_risk'])
                except Exception:
                    st.line_chart(top_users)

        with tabs[2]:
            st.subheader("Advice Agent")
            st.markdown("<div class='df-wrap glow-border'>", unsafe_allow_html=True)
            # Create a display copy so we can add a friendly 'URL Safe' column while
            # preserving all original columns in `df_advice`.
            try:
                df_advice_display = df_advice.copy()
                if "urls_safe" in df_advice_display.columns:
                    # Keep original boolean values; also add a readable column name
                    df_advice_display["URL Safe"] = df_advice_display["urls_safe"].astype(bool)
                
                    df_advice_display["URL Safe"] = False
                # Remove internal/display columns we don't want shown in the Advice tab
                try:
                    df_advice_display = df_advice_display.drop(columns=[c for c in ["source", "label"] if c in df_advice_display.columns])
                except Exception:
                    # fallback: ignore drop errors
                    pass
            except Exception:
                # If copying fails for any reason, fall back to the original DataFrame
                df_advice_display = df_advice

            # If URL Safe is present, show it with colored badges via pandas Styler
            try:
                if "URL Safe" in df_advice_display.columns:
                    def _style_url_safe(v):
                        # v is boolean
                        try:
                            if bool(v):
                                return 'background-color: #c6efce; color: #006400; font-weight: 600; text-align: center;'
                            else:
                                return 'background-color: #f8d7da; color: #721c24; font-weight: 600; text-align: center;'
                        except Exception:
                            return ''

                    styled = df_advice_display.style.applymap(_style_url_safe, subset=["URL Safe"])
                    st.dataframe(styled, use_container_width=True)
                else:
                    st.dataframe(df_advice_display, use_container_width=True)
            except Exception:
                # Fallback to plain display if styling fails
                st.dataframe(df_advice_display, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
            colA1, colA2 = st.columns(2)
            with colA1:
                st.markdown("**Predicted behavior risk**")
                try:
                    pbr = df_advice[["comment_id","predicted_behavior_risk"]].copy()
                    if _ALT_AVAILABLE:
                        pbr_chart = alt.Chart(pbr).mark_area(opacity=0.4, color='#6A0DAD').encode(x=alt.X("comment_id:O", sort=None), y="predicted_behavior_risk:Q")
                        st.altair_chart(pbr_chart, use_container_width=True)
                    else:
                        st.line_chart(pbr.set_index("comment_id")['predicted_behavior_risk'])
                except Exception:
                    st.line_chart(df_advice.get("predicted_behavior_risk", pd.Series(dtype=float)))
            with colA2:
                st.markdown("**Moderation suggestions**")
                try:
                    ms = df_advice["moderation_suggestion"].value_counts().reset_index()
                    ms.columns = ["suggestion","count"]
                    if _ALT_AVAILABLE:
                        ms_chart = alt.Chart(ms).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(x=alt.X("suggestion:N", sort='-y'), y="count:Q", color=alt.Color("suggestion:N", scale=alt.Scale(scheme='tableau20')))
                        st.altair_chart(ms_chart, use_container_width=True)
                    else:
                        st.bar_chart(ms.set_index("suggestion")['count'])
                except Exception:
                    st.bar_chart(df_advice.get("moderation_suggestion", pd.Series(dtype=str)).value_counts())

        with tabs[3]:
            st.subheader("Mitigation Agent")
            st.markdown("<div class='df-wrap glow-border'>", unsafe_allow_html=True)
            st.dataframe(df_mitig, use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Category distribution
            st.markdown("**Category distribution**")
            try:
                lab = df_mitig["label"].value_counts().reset_index()
                lab.columns = ["label","count"]
                if _ALT_AVAILABLE:
                    lab_chart = alt.Chart(lab).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(x=alt.X("label:N", sort='-y'), y="count:Q", color=alt.Color("label:N", scale=alt.Scale(scheme='turbo')))
                    st.altair_chart(lab_chart, use_container_width=True)
                else:
                    st.bar_chart(lab.set_index("label")['count'])
            except Exception:
                st.bar_chart(df_mitig.get("label", pd.Series(dtype=str)).value_counts())
            
            # Admin Alerts Dashboard section within Mitigation tab
            st.markdown("---")
            st.header("🚨 Admin Alerts Dashboard")
            colA, colB = st.columns([3,1])
            with colA:
                flagged = df_mitig[df_mitig["final_status"] == "Flagged"] if not df_mitig.empty else pd.DataFrame()
                st.markdown("<div class='df-wrap glow-border'>", unsafe_allow_html=True)
                st.dataframe(flagged if not flagged.empty else pd.DataFrame(columns=["userID","username","comment_id","label","mitigation_action"]), use_container_width=True)
                st.markdown("</div>", unsafe_allow_html=True)
            with colB:
                st.markdown("<div class='gradient-btn'>", unsafe_allow_html=True)
                if st.button("Send All Alerts"):
                    try:
                        flagged_df = df_mitig[df_mitig["final_status"] == "Flagged"] if not df_mitig.empty else pd.DataFrame()
                    except Exception:
                        flagged_df = pd.DataFrame()

                    if flagged_df.empty:
                        st.info("No flagged items to send alerts for.")
                    else:
                        sent = 0
                        failed = []
                        with st.spinner(f"Sending {len(flagged_df)} alerts..."):
                            for idx, row in flagged_df.iterrows():
                                subj = f"[Alert] Flagged comment by {row.get('username') or row.get('userID')}"
                                body_lines = [
                                    f"Comment ID: {row.get('comment_id')}",
                                    f"User: {row.get('username')}",
                                    f"User ID: {row.get('userID')}",
                                    f"Label: {row.get('label')}",
                                    f"Toxicity: {row.get('toxicity_score', row.get('toxicity', 'N/A'))}",
                                    f"Action: {row.get('mitigation_action')}",
                                    f"Reasoning: {row.get('reasoning') or ''}",
                                    f"Original comment:\n{row.get('comment') or ''}",
                                ]
                                body = "\n".join(body_lines)
                                ok, err = send_alert(subj, body)
                                if ok:
                                    sent += 1
                                else:
                                    failed.append({"row_index": int(idx), "error": err})

                        st.success(f"Attempted to send {len(flagged_df)} alerts — {sent} succeeded, {len(failed)} failed.")
                        if failed:
                            with st.expander("Show failed sends"):
                                for f in failed:
                                    st.write(f"Row {f['row_index']}: {f['error']}")
                st.markdown("</div>", unsafe_allow_html=True)

            # Backend workflow button (global, shows backend flow for first row of CSV)
            st.markdown("<div class='gradient-btn'>", unsafe_allow_html=True)
            if st.button("🧠 Show backend workflow for first row"):
                st.markdown("### Content Analyzer Output")
                st.json(analyzed_list[0])
                st.markdown("### Risk Detector Output")
                st.json(risk_list[0])
                st.markdown("### Advice Agent Output")
                st.json(advice_list[0])
                st.markdown("### Mitigation Agent Output")
                st.json(mitigation_list[0])
            st.markdown("</div>", unsafe_allow_html=True)

        # Download final mitigation outputs
        st.download_button("Download final report (CSV)", data=df_mitig.to_csv(index=False), file_name="mitigation_report.csv")

    else:
        st.info("Please upload a CSV file to begin.")
