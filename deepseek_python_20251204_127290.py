import streamlit as st
import json
from datetime import datetime
import pandas as pd
from io import BytesIO
import re
import sqlite3
import hashlib
import os
import tempfile
from collections import Counter

# Page configuration
st.set_page_config(
    page_title="AI Marketing Content Generator",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS - simplified
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .content-box {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #1f77b4;
        margin: 10px 0;
    }
    .stButton>button {
        background-color: #1f77b4;
        color: white;
        border-radius: 5px;
        padding: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'username' not in st.session_state:
    st.session_state.username = None

# Database setup
def get_db_path():
    return os.path.join(tempfile.gettempdir(), 'marketing_content.db')

def init_db():
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path, check_same_thread=False)
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      username TEXT UNIQUE NOT NULL,
                      password_hash TEXT NOT NULL)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS generated_content
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
                      platform TEXT NOT NULL,
                      product_name TEXT NOT NULL,
                      body_content TEXT,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Database error: {e}")
        return False

# Initialize database
init_db()

# Database functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, password):
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path, check_same_thread=False)
        c = conn.cursor()
        password_hash = hash_password(password)
        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                  (username, password_hash))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def verify_user(username, password):
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path, check_same_thread=False)
        c = conn.cursor()
        password_hash = hash_password(password)
        c.execute("SELECT id, username FROM users WHERE username=? AND password_hash=?",
                  (username, password_hash))
        user = c.fetchone()
        conn.close()
        return user
    except:
        return None

def save_content(user_id, platform, product_name, body):
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path, check_same_thread=False)
        c = conn.cursor()
        c.execute("INSERT INTO generated_content (user_id, platform, product_name, body_content) VALUES (?, ?, ?, ?)",
                  (user_id, platform, product_name, body))
        conn.commit()
        conn.close()
        return True
    except:
        return False

def get_user_content(user_id):
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path, check_same_thread=False)
        c = conn.cursor()
        c.execute("SELECT id, platform, product_name, body_content, created_at FROM generated_content WHERE user_id=? ORDER BY created_at DESC LIMIT 20", 
                  (user_id,))
        content = c.fetchall()
        conn.close()
        return content
    except:
        return []

# Keyword extraction
def extract_keywords(text, top_n=10):
    try:
        words = re.findall(r'\b[a-z]{3,}\b', text.lower())
        stop_words = set(['the', 'and', 'for', 'with', 'this', 'that'])
        filtered = [word for word in words if word not in stop_words]
        freq = Counter(filtered)
        return [word for word, _ in freq.most_common(top_n)]
    except:
        return []

# Sample content generator (no OpenAI for now)
def generate_sample_content(platform, product_name, description, audience, tone):
    templates = {
        "Google Ads": {
            "headline": f"Amazing {product_name}!",
            "body": f"Discover our premium {product_name}. Perfect for {audience}. Limited offer!",
            "cta": "Shop Now"
        },
        "Facebook Ads": {
            "headline": f"Love {product_name}?",
            "body": f"Our {product_name} is perfect for {audience}. Try it today!",
            "cta": "Learn More"
        },
        "Instagram": {
            "headline": f"✨ New: {product_name} ✨",
            "body": f"Check out our amazing {product_name}! #new #trending",
            "cta": "Shop Now"
        }
    }
    
    content = templates.get(platform, templates["Google Ads"])
    return {
        "headline": content["headline"],
        "body": content["body"],
        "cta": content["cta"],
        "hashtags": ["product", "sale", "new"]
    }

# Login page
def login_page():
    st.markdown("<h1 class='main-header'>🚀 AI Marketing Content Generator</h1>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["Login", "Sign Up"])
    
    with tab1:
        st.subheader("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            if username and password:
                user = verify_user(username, password)
                if user:
                    st.session_state.logged_in = True
                    st.session_state.user_id = user[0]
                    st.session_state.username = user[1]
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid credentials")
    
    with tab2:
        st.subheader("Create Account")
        new_user = st.text_input("New Username")
        new_pass = st.text_input("New Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")
        
        if st.button("Create Account"):
            if new_user and new_pass and confirm:
                if new_pass != confirm:
                    st.error("Passwords don't match")
                elif len(new_pass) < 4:
                    st.error("Password too short")
                else:
                    if create_user(new_user, new_pass):
                        st.success("Account created! Please login.")
                    else:
                        st.error("Username exists")

# Main app
def main_app():
    with st.sidebar:
        st.write(f"Welcome, {st.session_state.username}")
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.rerun()
        
        page = st.radio("Menu", ["Generate", "History", "Keywords"])
    
    if page == "Generate":
        generate_page()
    elif page == "History":
        history_page()
    else:
        keyword_page()

def generate_page():
    st.markdown("<h1 class='main-header'>Generate Content</h1>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        product = st.text_input("Product Name", "Smart Water Bottle")
        description = st.text_area("Description", "A smart bottle that tracks hydration", height=100)
        audience = st.text_input("Target Audience", "Health enthusiasts")
    
    with col2:
        platform = st.selectbox("Platform", ["Google Ads", "Facebook Ads", "Instagram"])
        tone = st.selectbox("Tone", ["Professional", "Friendly", "Urgent"])
    
    if st.button("Generate Content", type="primary"):
        with st.spinner("Generating..."):
            content = generate_sample_content(platform, product, description, audience, tone)
            
            # Save to DB
            save_content(st.session_state.user_id, platform, product, content["body"])
            
            # Display
            st.markdown("### 📝 Result")
            st.markdown(f"**Headline:** {content['headline']}")
            st.markdown(f"**Body:** {content['body']}")
            st.markdown(f"**CTA:** {content['cta']}")
            st.markdown(f"**Hashtags:** {' '.join(['#' + tag for tag in content['hashtags']])}")

def history_page():
    st.markdown("<h1 class='main-header'>Content History</h1>", unsafe_allow_html=True)
    
    history = get_user_content(st.session_state.user_id)
    
    if not history:
        st.info("No content yet")
        return
    
    for item in history:
        with st.expander(f"{item[1]} - {item[2]} ({item[4]})"):
            st.write(item[3])

def keyword_page():
    st.markdown("<h1 class='main-header'>Keyword Extractor</h1>", unsafe_allow_html=True)
    
    text = st.text_area("Enter text", "Smart water bottle with hydration tracking and fitness app sync", height=150)
    
    if st.button("Extract Keywords"):
        keywords = extract_keywords(text)
        st.write("Keywords found:")
        for kw in keywords:
            st.markdown(f"- {kw}")

# Main
def main():
    if not st.session_state.logged_in:
        login_page()
    else:
        main_app()

if __name__ == "__main__":
    main()
