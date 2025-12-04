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

# Custom CSS (same as before)

# Initialize database functions (same as before)

# Simple keyword extraction (same as before)

# Platform-specific prompts (same as before)

# AI Content Generation with proper error handling
def generate_content(api_key, platform, product_name, description, audience, tone, keywords):
    # First, try to import OpenAI
    try:
        import openai
    except ImportError:
        st.error("""
        ⚠️ OpenAI package is not installed!
        
        Please add `openai>=1.12.0` to your `requirements.txt` file.
        
        Running in demo mode for now.
        """)
        return generate_demo_content(platform, product_name, description, audience, tone, keywords)
    
    if not api_key:
        st.info("ℹ️ No API key provided. Running in demo mode.")
        return generate_demo_content(platform, product_name, description, audience, tone, keywords)
    
    try:
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
        
        # Check OpenAI version and handle accordingly
        openai_version = openai.__version__
        
        if openai_version.startswith('0.'):
            # Old version (0.x)
            openai.api_key = api_key
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": platform_config['system']},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=800
            )
            content = response.choices[0].message.content
        else:
            # New version (1.x+)
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
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
                "headline": f"Amazing {product_name} - Limited Time Offer!",
                "body": content if content else f"Discover the incredible {product_name}. Perfect for {audience}. Experience the difference today!",
                "cta": "Shop Now",
                "hashtags": keywords[:5] if keywords else ["product", "sale", "new"]
            }
        
        return content_json
    
    except Exception as e:
        st.error(f"Error generating content: {str(e)}")
        st.info("Falling back to demo content.")
        return generate_demo_content(platform, product_name, description, audience, tone, keywords)

def generate_demo_content(platform, product_name, description, audience, tone, keywords):
    """Generate demo content when OpenAI is not available"""
    sample_content = {
        "Google Ads": {
            "headline": f"Amazing {product_name} - 50% Off Today!",
            "body": f"Discover premium {product_name}. Perfect for {audience}. Limited time offer. Shop now!",
            "cta": "Buy Now & Save",
            "hashtags": keywords[:3] if keywords else [product_name.replace(" ", "").lower(), "sale", "deal"]
        },
        "Facebook Ads": {
            "headline": f"Your Search For The Perfect {product_name} Ends Here!",
            "body": f"Tired of ordinary products? Meet our revolutionary {product_name}! Designed specifically for {audience}, this amazing product will transform your experience. With features that actually work and quality you can trust.\n\nWhy choose us?\n✅ Premium Quality\n✅ {tone} Design\n✅ Perfect for {audience}\n✅ Best Value Guaranteed",
            "cta": "Learn More →",
            "hashtags": keywords[:5] if keywords else [product_name.replace(" ", "").lower(), "quality", "innovation", "best", "new"]
        },
        "Instagram": {
            "headline": f"✨ Just Launched: The {product_name} You've Been Waiting For! ✨",
            "body": f"Say hello to our new {product_name}! 🎉\n\nPerfect for {audience}, this is more than just a product - it's a game changer! 💫\n\nWe've designed every detail with {tone.lower()} care to ensure you get the best experience possible.\n\nTag someone who needs this! 👇\n\n#ad #sponsored",
            "cta": "Swipe Up to Shop",
            "hashtags": keywords[:10] if keywords else [product_name.replace(" ", "").lower(), "newproduct", "innovation", "musthave", "trending", "quality", "love", "instagood", "shopping", "deal"]
        },
        "SEO Meta Description": {
            "headline": f"Premium {product_name} | Best for {audience}",
            "body": f"Discover our amazing {product_name} designed for {audience}. Features {tone.lower()} design, premium quality, and exceptional value. Shop now for best deals!",
            "cta": "Learn More & Buy",
            "hashtags": keywords[:3] if keywords else [product_name.replace(" ", "").lower(), "buy", "shop"]
        },
        "Landing Page": {
            "headline": f"Transform Your Experience With Our Premium {product_name}",
            "body": f"Welcome to the future of excellence! Our {product_name} is engineered for {audience} who demand the best.\n\n🌟 Key Benefits:\n• Premium {tone} quality\n• Perfect for {audience}\n• Exceptional value\n• Trusted by thousands\n\nJoin the revolution today!",
            "cta": "Get Started Free",
            "hashtags": keywords[:5] if keywords else [product_name.replace(" ", "").lower(), "premium", "quality", "innovation", "excellence"]
        }
    }
    
    return sample_content.get(platform, sample_content["Facebook Ads"])

# Export functions (conditional imports)
def generate_pdf(content_data):
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=30,
            alignment=1
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#ff7f0e'),
            spaceAfter=12,
            spaceBefore=12
        )
        
        story.append(Paragraph("AI Marketing Content Report", title_style))
        story.append(Spacer(1, 0.3*inch))
        
        data = [
            ['Platform:', content_data['platform']],
            ['Product:', content_data['product_name']],
            ['Generated:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
            ['Tone:', content_data['tone']],
            ['Audience:', content_data['audience']]
        ]
        
        table = Table(data, colWidths=[2*inch, 4*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f2f6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        
        story.append(table)
        story.append(Spacer(1, 0.3*inch))
        
        story.append(Paragraph("Headline", heading_style))
        story.append(Paragraph(content_data['headline'], styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        story.append(Paragraph("Body Content", heading_style))
        story.append(Paragraph(content_data['body'], styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        story.append(Paragraph("Call to Action", heading_style))
        story.append(Paragraph(content_data['cta'], styles['Normal']))
        story.append(Spacer(1, 0.2*inch))
        
        if content_data['hashtags']:
            story.append(Paragraph("Hashtags", heading_style))
            hashtags_text = ' '.join([f"#{tag}" for tag in content_data['hashtags']])
            story.append(Paragraph(hashtags_text, styles['Normal']))
        
        doc.build(story)
        buffer.seek(0)
        return buffer
    except ImportError:
        st.error("ReportLab not installed. PDF export disabled.")
        return None

def generate_docx(content_data):
    try:
        from docx import Document
        from docx.shared import Pt, RGBColor
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        
        doc = Document()
        
        title = doc.add_heading('AI Marketing Content Report', 0)
        title.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        doc.add_paragraph(f"Platform: {content_data['platform']}")
        doc.add_paragraph(f"Product: {content_data['product_name']}")
        doc.add_paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        doc.add_paragraph(f"Tone: {content_data['tone']}")
        doc.add_paragraph(f"Audience: {content_data['audience']}")
        
        doc.add_paragraph()
        
        doc.add_heading('Headline', level=1)
        p = doc.add_paragraph(content_data['headline'])
        p.runs[0].font.size = Pt(14)
        
        doc.add_heading('Body Content', level=1)
        doc.add_paragraph(content_data['body'])
        
        doc.add_heading('Call to Action', level=1)
        p = doc.add_paragraph(content_data['cta'])
        p.runs[0].bold = True
        
        if content_data['hashtags']:
            doc.add_heading('Hashtags', level=1)
            hashtags_text = ' '.join([f"#{tag}" for tag in content_data['hashtags']])
            doc.add_paragraph(hashtags_text)
        
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
    except ImportError:
        st.error("python-docx not installed. DOCX export disabled.")
        return None

# Text export (always works)
def export_as_text(content_data):
    text = f"""AI MARKETING CONTENT REPORT
{'='*50}

Platform: {content_data['platform']}
Product: {content_data['product_name']}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Tone: {content_data['tone']}
Audience: {content_data['audience']}

{'='*50}
HEADLINE:
{content_data['headline']}

{'='*50}
BODY CONTENT:
{content_data['body']}

{'='*50}
CALL TO ACTION:
{content_data['cta']}

"""
    
    if content_data['hashtags']:
        text += f"""{'='*50}
HASHTAGS:
{' '.join([f'#{tag}' for tag in content_data['hashtags']])}
"""
    
    return text.encode('utf-8')

# Authentication and main app functions (same as before)

# Update the export section in generate_content_page():
def generate_content_page():
    # ... (previous code remains the same until export section)
    
    # In the export section, modify like this:
    if 'generated_content' in st.session_state:
        # ... (display content code)
        
        # Export options
        st.markdown("---")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Text export (always available)
            text_data = export_as_text({
                'platform': metadata['platform'],
                'product_name': metadata['product_name'],
                'tone': metadata['tone'],
                'audience': metadata['target_audience'],
                'headline': content['headline'],
                'body': content['body'],
                'cta': content['cta'],
                'hashtags': content.get('hashtags', [])
            })
            st.download_button(
                label="📥 Download as Text",
                data=text_data,
                file_name=f"{metadata['product_name']}_content.txt",
                mime="text/plain",
                use_container_width=True
            )
        
        with col2:
            # PDF export (conditional)
            pdf_buffer = generate_pdf({
                'platform': metadata['platform'],
                'product_name': metadata['product_name'],
                'tone': metadata['tone'],
                'audience': metadata['target_audience'],
                'headline': content['headline'],
                'body': content['body'],
                'cta': content['cta'],
                'hashtags': content.get('hashtags', [])
            })
            if pdf_buffer:
                st.download_button(
                    label="📥 Download as PDF",
                    data=pdf_buffer,
                    file_name=f"{metadata['product_name']}_content.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            else:
                st.info("PDF export requires ReportLab")
        
        with col3:
            # DOCX export (conditional)
            docx_buffer = generate_docx({
                'platform': metadata['platform'],
                'product_name': metadata['product_name'],
                'tone': metadata['tone'],
                'audience': metadata['target_audience'],
                'headline': content['headline'],
                'body': content['body'],
                'cta': content['cta'],
                'hashtags': content.get('hashtags', [])
            })
            if docx_buffer:
                st.download_button(
                    label="📥 Download as DOCX",
                    data=docx_buffer,
                    file_name=f"{metadata['product_name']}_content.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True
                )
            else:
                st.info("DOCX export requires python-docx")
