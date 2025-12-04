import streamlit as st
from openai import OpenAI  # Updated for OpenAI v1.x
import json
from datetime import datetime
import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
import spacy
from collections import Counter
import re
import sqlite3
import hashlib
import os
import tempfile
import sys

# Page configuration
st.set_page_config(
    page_title="AI Marketing Content Generator",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS (keep your existing CSS)

# Database initialization with proper path handling
def get_db_path():
    """Get database path that works in both local and Streamlit Cloud"""
    if 'STREAMLIT_SHARING_MODE' in os.environ or 'STREAMLIT_DEPLOYMENT_MODE' in os.environ:
        # On Streamlit Cloud, use a persistent directory
        return os.path.join(tempfile.gettempdir(), 'marketing_content.db')
    else:
        # Local development
        return 'marketing_content.db'

def init_db():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path, check_same_thread=False)
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  username TEXT UNIQUE NOT NULL,
                  email TEXT UNIQUE NOT NULL,
                  password_hash TEXT NOT NULL,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    
    # Generated content table
    c.execute('''CREATE TABLE IF NOT EXISTS generated_content
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  platform TEXT NOT NULL,
                  product_name TEXT NOT NULL,
                  product_description TEXT,
                  target_audience TEXT,
                  brand_tone TEXT,
                  keywords TEXT,
                  headline TEXT,
                  body_content TEXT,
                  cta TEXT,
                  hashtags TEXT,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # Sessions table
    c.execute('''CREATE TABLE IF NOT EXISTS sessions
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  session_token TEXT UNIQUE,
                  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  expires_at TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    conn.commit()
    conn.close()

# Initialize database
init_db()

# Database helper functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, email, password):
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path, check_same_thread=False)
        c = conn.cursor()
        password_hash = hash_password(password)
        c.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                  (username, email, password_hash))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False
    except Exception as e:
        st.error(f"Database error: {str(e)}")
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
    except Exception as e:
        st.error(f"Database error: {str(e)}")
        return None

def save_content_to_db(user_id, platform, product_name, description, audience, tone, 
                       keywords, headline, body, cta, hashtags):
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path, check_same_thread=False)
        c = conn.cursor()
        c.execute("""INSERT INTO generated_content 
                     (user_id, platform, product_name, product_description, target_audience, 
                      brand_tone, keywords, headline, body_content, cta, hashtags)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                  (user_id, platform, product_name, description, audience, tone,
                   json.dumps(keywords), headline, body, cta, json.dumps(hashtags)))
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Error saving content: {str(e)}")

def get_user_content_history(user_id, limit=50):
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path, check_same_thread=False)
        c = conn.cursor()
        c.execute("""SELECT id, platform, product_name, headline, body_content, 
                     cta, hashtags, created_at FROM generated_content 
                     WHERE user_id=? ORDER BY created_at DESC LIMIT ?""", (user_id, limit))
        content = c.fetchall()
        conn.close()
        return content
    except Exception as e:
        st.error(f"Database error: {str(e)}")
        return []

def delete_content(content_id, user_id):
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path, check_same_thread=False)
        c = conn.cursor()
        c.execute("DELETE FROM generated_content WHERE id=? AND user_id=?", (content_id, user_id))
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Database error: {str(e)}")

# Load spaCy model with Streamlit Cloud compatibility
@st.cache_resource(show_spinner="Loading NLP model...")
def load_spacy_model():
    try:
        # Try to load the model
        nlp = spacy.load("en_core_web_sm")
        return nlp
    except OSError:
        # If model not found, provide clear instructions
        st.error("""
        ⚠️ **spaCy model not found!**
        
        Please add this to your `requirements.txt`:
        ```
        https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.7.1/en_core_web_sm-3.7.1.tar.gz
        ```
        
        Or run this command locally:
        ```bash
        python -m spacy download en_core_web_sm
        ```
        """)
        # Return a simple tokenizer as fallback
        return None

nlp = load_spacy_model()

# NLP Keyword Extraction with fallback
def extract_keywords(text, top_n=10):
    if nlp is None:
        # Simple fallback keyword extraction without spaCy
        words = re.findall(r'\b[a-z]{3,}\b', text.lower())
        stop_words = set(['the', 'and', 'for', 'with', 'this', 'that', 'have', 'from'])
        keywords = [word for word in words if word not in stop_words]
        freq = Counter(keywords)
        return [word for word, _ in freq.most_common(top_n)]
    
    try:
        doc = nlp(text.lower())
        
        # Extract nouns and adjectives
        keywords = []
        for token in doc:
            if token.pos_ in ['NOUN', 'ADJ', 'PROPN'] and not token.is_stop and len(token.text) > 2:
                keywords.append(token.lemma_)
        
        # Count frequency
        keyword_freq = Counter(keywords)
        
        # Get top keywords
        top_keywords = [word for word, freq in keyword_freq.most_common(top_n)]
        
        return top_keywords
    except Exception as e:
        st.error(f"Error in keyword extraction: {str(e)}")
        return []

# Platform-specific prompts (keep your existing prompts)

# AI Content Generation - UPDATED FOR OpenAI v1.x
def generate_content(api_key, platform, product_name, description, audience, tone, keywords):
    if not api_key:
        st.error("API key is required")
        return None
    
    try:
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        platform_config = PLATFORM_PROMPTS[platform]
        
        prompt = f"""
{platform_config['instructions']}

Product Information:
- Name: {product_name}
- Description: {description}
- Target Audience: {audience}
- Brand Tone: {tone}
- Keywords: {', '.join(keywords)}

Return the response in the following JSON format:
{{
    "headline": "compelling headline",
    "body": "main content body",
    "cta": "call to action",
    "hashtags": ["hashtag1", "hashtag2", "hashtag3"]
}}
"""
        
        response = client.chat.completions.create(
            model="gpt-4",  # or "gpt-3.5-turbo" for lower cost
            messages=[
                {"role": "system", "content": platform_config['system']},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=800
        )
        
        content = response.choices[0].message.content
        
        # Parse JSON response
        try:
            content_json = json.loads(content)
        except json.JSONDecodeError:
            # Fallback if not JSON
            content_json = {
                "headline": "Check out our amazing product!",
                "body": content,
                "cta": "Shop Now",
                "hashtags": keywords[:5] if keywords else ["product", "sale", "new"]
            }
        
        return content_json
    
    except Exception as e:
        st.error(f"Error generating content: {str(e)}")
        return None

# Keep your existing PDF, DOCX, and other functions (they should work as-is)

# Authentication and main app functions remain the same...

# Add this at the end to handle Streamlit Cloud deployment
if __name__ == "__main__":
    # Clear any existing session state issues
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    
    # Initialize other session variables if they don't exist
    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = None
    if 'username' not in st.session_state:
        st.session_state['username'] = None
    
    # Initialize database
    try:
        init_db()
    except Exception as e:
        st.warning(f"Database initialization note: {str(e)}")
    
    # Run the main function
    main()