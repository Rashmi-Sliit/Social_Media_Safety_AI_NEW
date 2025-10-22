import streamlit as st

def display_about_page():
    # 🎨 Custom CSS with matching colors and animations
    st.markdown("""
    <style>
    :root {
        --bg-main: #0F172A;
        --accent: #2563EB;
        --text: #F8FAFC;
        --card-bg: rgba(37, 99, 235, 0.08);
        --hover: #1E3A8A;
        --glow: rgba(37, 99, 235, 0.1);
        --border: rgba(37, 99, 235, 0.15);
        --card-shadow: rgba(15, 23, 42, 0.15);
    }

    /* Animations */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* Main styles */
    [data-testid="stAppViewContainer"] {
        background: var(--bg-main) !important;
        color: var(--text);
    }

    .title-section {
        text-align: center;
        animation: fadeIn 0.8s ease-out;
        padding: 2rem 0;
    }

    .title-text {
        font-size: 3.2rem;
        font-weight: bold;
        background: linear-gradient(135deg, var(--text), var(--accent));
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 1rem;
    }

    .subtitle-text {
        color: var(--text);
        opacity: 0.9;
        font-size: 1.2rem;
        line-height: 1.6;
        max-width: 800px;
        margin: 0 auto;
    }

    .section-card {
        background: var(--card-bg);
        border-radius: 12px;
        padding: 2rem;
        margin: 1.5rem 0;
        border: 1px solid var(--border);
        box-shadow: 0 8px 32px var(--card-shadow);
        animation: fadeIn 0.8s ease-out;
        backdrop-filter: blur(20px);
    }

    .feature-card {
        background: var(--card-bg);
        border-radius: 10px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid var(--border);
        transition: all 0.3s ease;
    }

    .feature-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px var(--glow);
        border-color: var(--accent);
    }

    .team-card {
        background: var(--card-bg);
        border-radius: 12px;
        padding: 2rem;
        text-align: center;
        border: 1px solid var(--border);
        transition: all 0.3s ease;
    }

    .team-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 40px var(--glow);
        border-color: var(--accent);
    }

    .profile-image {
        width: 120px;
        height: 120px;
        border-radius: 60px;
        margin-bottom: 1rem;
        border: 3px solid var(--accent);
        padding: 3px;
    }

    .social-icons {
        display: flex;
        justify-content: center;
        gap: 1.5rem;
        margin-top: 2rem;
    }

    .social-icon {
        color: var(--accent);
        font-size: 1.5rem;
        transition: all 0.3s ease;
    }

    .social-icon:hover {
        color: var(--text);
        transform: translateY(-3px);
    }

    .section-title {
        color: var(--accent);
        font-size: 1.8rem;
        font-weight: 600;
        margin-bottom: 1.5rem;
        border-bottom: 2px solid var(--border);
        padding-bottom: 0.5rem;
    }
    </style>
    """, unsafe_allow_html=True)

    # 📌 Title Section
    st.markdown("""
    <div class="title-section">
        <h1 class="title-text">About SMS_AI</h1>
        <p class="subtitle-text">
            Advanced AI-powered content moderation and analysis platform that helps make online communication safer and more meaningful through intelligent risk assessment and smart advice generation.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # 🎯 Mission Section
    st.markdown("""
    <div class="section-card">
        <h2 class="section-title">Our Mission</h2>
        <p style="font-size: 1.1rem; line-height: 1.6;">
            At SMS_AI, we're committed to creating a safer digital world through innovative AI technology. 
            Our mission is to empower organizations and individuals with intelligent content moderation tools 
            that help foster healthy online communities while protecting users from harmful content.
            Through advanced machine learning and natural language processing, we're making online 
            communication smarter, safer, and more constructive.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ⭐ Key Features Section
    st.markdown("""
    <div class="section-card">
        <h2 class="section-title">Key Features</h2>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1.5rem;">
            <div class="feature-card">
                <h3 style="color: var(--accent); margin-bottom: 0.5rem;">🤖 AI-Powered Analysis</h3>
                <p>Advanced risk and toxicity detection using state-of-the-art machine learning models</p>
            </div>
            <div class="feature-card">
                <h3 style="color: var(--accent); margin-bottom: 0.5rem;">📊 Batch Processing</h3>
                <p>Efficiently analyze multiple posts and comments through CSV file uploads</p>
            </div>
            <div class="feature-card">
                <h3 style="color: var(--accent); margin-bottom: 0.5rem;">🔌 API Access</h3>
                <p>Seamless integration options for developers with comprehensive API documentation</p>
            </div>
            <div class="feature-card">
                <h3 style="color: var(--accent); margin-bottom: 0.5rem;">💡 Smart Advice</h3>
                <p>Contextual recommendations and insights for better content moderation</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 👥 Team Section
    st.markdown("""
    <div class="section-card">
        <h2 class="section-title">Meet the Team</h2>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 2rem;">
            <div class="team-card">
                <img src="https://source.unsplash.com/random/200x200?face-1" alt="Sarah Chen" class="profile-image">
                <h3 style="color: var(--accent)">Sarah Chen</h3>
                <p style="color: var(--text); opacity: 0.8">AI Research Lead</p>
                <p style="font-size: 0.9rem; margin-top: 0.5rem">Leading our AI model development and research initiatives</p>
            </div>
            <div class="team-card">
                <img src="https://source.unsplash.com/random/200x200?face-2" alt="Michael Ross" class="profile-image">
                <h3 style="color: var(--accent)">Michael Ross</h3>
                <p style="color: var(--text); opacity: 0.8">Backend Developer</p>
                <p style="font-size: 0.9rem; margin-top: 0.5rem">Architecture and API development specialist</p>
            </div>
            <div class="team-card">
                <img src="https://source.unsplash.com/random/200x200?face-3" alt="Emma Taylor" class="profile-image">
                <h3 style="color: var(--accent)">Emma Taylor</h3>
                <p style="color: var(--text); opacity: 0.8">UI/UX Designer</p>
                <p style="font-size: 0.9rem; margin-top: 0.5rem">Creating intuitive and beautiful user experiences</p>
            </div>
            <div class="team-card">
                <img src="https://source.unsplash.com/random/200x200?face-4" alt="David Kim" class="profile-image">
                <h3 style="color: var(--accent)">David Kim</h3>
                <p style="color: var(--text); opacity: 0.8">Product Manager</p>
                <p style="font-size: 0.9rem; margin-top: 0.5rem">Driving product strategy and development</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 📧 Contact Section
    st.markdown("""
    <div class="section-card" style="text-align: center;">
        <h2 class="section-title">Contact Us</h2>
        <p style="font-size: 1.1rem; margin-bottom: 2rem;">
            Have questions? We'd love to hear from you. Send us a message and we'll respond as soon as possible.
        </p>
        <p style="font-size: 1.2rem; color: var(--accent);">
            📧 contact@sms-ai.com
        </p>
        <div class="social-icons">
            <a href="#" class="social-icon">
                <i class="fab fa-linkedin"></i>
            </a>
            <a href="#" class="social-icon">
                <i class="fab fa-github"></i>
            </a>
            <a href="#" class="social-icon">
                <i class="fab fa-twitter"></i>
            </a>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Add Font Awesome for social icons
    st.markdown("""
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css">
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    display_about_page()