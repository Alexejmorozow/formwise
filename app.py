# app.py
import streamlit as st
from jinja2 import Template
import requests
import re
import openai
from io import BytesIO
from datetime import datetime
import base64
import json
from PIL import Image
from weasyprint import HTML
import os

st.set_page_config(page_title="FormWise – Bewerbungs-Generator (Screenshot → Design)", layout="wide")

# ----------------------
# TEMPLATES (CV + Cover)
# (Die Templates, die du angegeben hast, wurden 1:1 integriert)
# ----------------------

MODERN_TECH_TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{{ name }} - CV</title>
<style>
  @page { margin: 1.5cm; }
  body { 
    font-family: 'Inter', 'SF Pro Display', -apple-system, sans-serif; 
    color: #1a1a1a;
    line-height: 1.4;
  }
  .container { display: flex; gap: 30px; }
  .sidebar { 
    width: 35%; 
    background: {{ primary_color }}10;
    padding: 25px;
    border-radius: 12px;
  }
  .main { width: 65%; }
  .name { 
    font-size: 32px; 
    font-weight: 700;
    color: {{ primary_color }};
    margin-bottom: 5px;
  }
  .title { 
    font-size: 18px;
    color: #666;
    margin-bottom: 20px;
  }
  .section { margin-bottom: 25px; }
  .section-title {
    font-size: 16px;
    font-weight: 600;
    color: {{ primary_color }};
    border-bottom: 2px solid {{ primary_color }};
    padding-bottom: 5px;
    margin-bottom: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .skill-bar {
    height: 6px;
    background: #e0e0e0;
    border-radius: 3px;
    margin-bottom: 8px;
  }
  .skill-fill {
    height: 100%;
    background: {{ primary_color }};
    border-radius: 3px;
  }
  .contact-item { margin-bottom: 8px; }
  .job { margin-bottom: 20px; }
  .job-period { 
    color: #666;
    font-size: 12px;
    font-weight: 500;
  }
  .job-company {
    font-weight: 600;
    color: {{ primary_color }};
  }
  .badge {
    display: inline-block;
    background: {{ primary_color }};
    color: white;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 11px;
    margin: 2px;
  }
</style>
</head>
<body>
<div class="container">
  <div class="sidebar">
    <div class="name">{{ name }}</div>
    <div class="title">{{ title }}</div>
    
    <div class="section">
      <div class="section-title">Contact</div>
      <div class="contact-item">{{ contact | replace('\\n','<br>') }}</div>
    </div>
    
    <div class="section">
      <div class="section-title">Skills</div>
      {% for item in skills %}
      <div style="margin-bottom: 10px;">
        <div style="display: flex; justify-content: space-between; font-size: 12px;">
          <span>{{ item.name }}</span>
          <span>{{ item.pct }}%</span>
        </div>
        <div class="skill-bar">
          <div class="skill-fill" style="width: {{ item.pct }}%"></div>
        </div>
      </div>
      {% endfor %}
    </div>
    
    <div class="section">
      <div class="section-title">Languages</div>
      <div>{{ languages }}</div>
    </div>
  </div>
  
  <div class="main">
    <div class="section">
      <div class="section-title">Profile</div>
      <div>{{ profile }}</div>
    </div>
    
    <div class="section">
      <div class="section-title">Experience</div>
      {% for job in experience %}
      <div class="job">
        <div class="job-period">{{ job.period }}</div>
        <div class="job-company">{{ job.company }} | {{ job.role }}</div>
        <ul style="margin-top: 8px;">
          {% for b in job.bullets %}
          <li>{{ b }}</li>
          {% endfor %}
        </ul>
      </div>
      {% endfor %}
    </div>
    
    <div class="section">
      <div class="section-title">Projects</div>
      {% for p in projects %}
      <div style="margin-bottom: 15px;">
        <strong>{{ p.title }}</strong>
        <div style="color: #666; font-size: 14px;">{{ p.desc }}</div>
      </div>
      {% endfor %}
    </div>
  </div>
</div>
</body>
</html>
"""

CORPORATE_TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{{ name }} - Curriculum Vitae</title>
<style>
  @page { margin: 2cm; }
  body { 
    font-family: 'Times New Roman', serif;
    color: #333;
    line-height: 1.3;
  }
  .header {
    text-align: center;
    border-bottom: 3px double {{ primary_color }};
    padding-bottom: 15px;
    margin-bottom: 25px;
  }
  .name {
    font-size: 24px;
    font-weight: bold;
    margin-bottom: 5px;
    color: {{ primary_color }};
  }
  .title {
    font-size: 16px;
    font-style: italic;
    margin-bottom: 10px;
  }
  .section {
    margin-bottom: 20px;
  }
  .section-title {
    font-size: 16px;
    font-weight: bold;
    color: {{ primary_color }};
    border-bottom: 1px solid {{ primary_color }};
    padding-bottom: 3px;
    margin-bottom: 10px;
  }
  .contact-info {
    text-align: center;
    font-size: 12px;
    margin-bottom: 15px;
  }
  .job {
    margin-bottom: 15px;
  }
  .job-header {
    display: flex;
    justify-content: space-between;
    font-weight: bold;
  }
  .job-company {
    color: {{ primary_color }};
  }
  ul {
    margin: 5px 0;
    padding-left: 20px;
  }
  li {
    margin-bottom: 3px;
  }
</style>
</head>
<body>
<div class="header">
  <div class="name">{{ name }}</div>
  <div class="title">{{ title }}</div>
  <div class="contact-info">{{ contact | replace('\\n','<br>') }}</div>
</div>

<div class="section">
  <div class="section-title">Professional Summary</div>
  <div>{{ profile }}</div>
</div>

<div class="section">
  <div class="section-title">Professional Experience</div>
  {% for job in experience %}
  <div class="job">
    <div class="job-header">
      <span class="job-company">{{ job.company }}</span>
      <span>{{ job.period }}</span>
    </div>
    <div style="font-style: italic; margin-bottom: 5px;">{{ job.role }}</div>
    <ul>
      {% for b in job.bullets %}
      <li>{{ b }}</li>
      {% endfor %}
    </ul>
  </div>
  {% endfor %}
</div>

<div class="section">
  <div class="section-title">Education</div>
  <div>{{ education }}</div>
</div>

<div class="section">
  <div class="section-title">Skills & Competencies</div>
  <div>
    {% for item in skills %}
    <strong>{{ item.name }}</strong> ({{ item.pct }}%){% if not loop.last %} | {% endif %}
    {% endfor %}
  </div>
</div>
</body>
</html>
"""

CREATIVE_TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{{ name }}</title>
<style>
  @page { margin: 1cm; }
  body { 
    font-family: 'Helvetica Neue', Arial, sans-serif;
    color: #2c3e50;
    line-height: 1.4;
  }
  .container {
    display: grid;
    grid-template-columns: 1fr 2fr;
    gap: 30px;
  }
  .accent-column {
    background: {{ primary_color }};
    color: white;
    padding: 30px;
  }
  .main-column {
    padding: 30px 30px 30px 0;
  }
  .name {
    font-size: 36px;
    font-weight: 300;
    margin-bottom: 10px;
    line-height: 1.1;
  }
  .title {
    font-size: 16px;
    opacity: 0.9;
    margin-bottom: 30px;
  }
  .section {
    margin-bottom: 25px;
  }
  .section-title {
    font-size: 14px;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 15px;
    font-weight: 600;
  }
  .white-section .section-title {
    border-bottom: 1px solid rgba(255,255,255,0.3);
    padding-bottom: 5px;
  }
  .skill-item {
    margin-bottom: 15px;
  }
  .skill-name {
    display: block;
    margin-bottom: 5px;
  }
  .progress {
    height: 4px;
    background: rgba(255,255,255,0.3);
    border-radius: 2px;
    overflow: hidden;
  }
  .progress-fill {
    height: 100%;
    background: white;
  }
  .job {
    margin-bottom: 20px;
    padding-bottom: 20px;
    border-bottom: 1px solid #ecf0f1;
  }
  .job:last-child {
    border-bottom: none;
  }
  .job-meta {
    color: {{ primary_color }};
    font-size: 12px;
    margin-bottom: 5px;
  }
  .job-role {
    font-weight: 600;
    margin-bottom: 8px;
  }
</style>
</head>
<body>
<div class="container">
  <div class="accent-column">
    <div class="name">{{ name }}</div>
    <div class="title">{{ title }}</div>
    
    <div class="section white-section">
      <div class="section-title">Contact</div>
      <div>{{ contact | replace('\\n','<br>') }}</div>
    </div>
    
    <div class="section white-section">
      <div class="section-title">Skills</div>
      {% for item in skills %}
      <div class="skill-item">
        <span class="skill-name">{{ item.name }}</span>
        <div class="progress">
          <div class="progress-fill" style="width: {{ item.pct }}%"></div>
        </div>
      </div>
      {% endfor %}
    </div>
    
    <div class="section white-section">
      <div class="section-title">Languages</div>
      <div>{{ languages }}</div>
    </div>
  </div>
  
  <div class="main-column">
    <div class="section">
      <div class="section-title">Profile</div>
      <div>{{ profile }}</div>
    </div>
    
    <div class="section">
      <div class="section-title">Experience</div>
      {% for job in experience %}
      <div class="job">
        <div class="job-meta">{{ job.period }} | {{ job.company }}</div>
        <div class="job-role">{{ job.role }}</div>
        <ul>
          {% for b in job.bullets %}
          <li>{{ b }}</li>
          {% endfor %}
        </ul>
      </div>
      {% endfor %}
    </div>
    
    <div class="section">
      <div class="section-title">Education</div>
      <div>{{ education }}</div>
    </div>
  </div>
</div>
</body>
</html>
"""

ACADEMIC_TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{{ name }} - Curriculum Vitae</title>
<style>
  @page { margin: 2.5cm; }
  body { 
    font-family: 'Garamond', 'Times New Roman', serif;
    color: #222;
    line-height: 1.4;
    font-size: 12pt;
  }
  .header {
    text-align: center;
    margin-bottom: 30px;
  }
  .name {
    font-size: 16pt;
    font-weight: bold;
    margin-bottom: 5px;
  }
  .contact {
    font-size: 10pt;
    margin-bottom: 15px;
  }
  .section {
    margin-bottom: 20px;
  }
  .section-title {
    font-size: 12pt;
    font-weight: bold;
    border-bottom: 1px solid #000;
    padding-bottom: 2px;
    margin-bottom: 10px;
  }
  .publication {
    margin-bottom: 8px;
    text-indent: -20px;
    padding-left: 20px;
  }
  .degree {
    margin-bottom: 10px;
  }
  .degree-title {
    font-weight: bold;
  }
  .award {
    margin-bottom: 5px;
  }
</style>
</head>
<body>
<div class="header">
  <div class="name">{{ name }}</div>
  <div class="contact">{{ contact | replace('\\n','<br>') }}</div>
  <div>{{ title }}</div>
</div>

<div class="section">
  <div class="section-title">Education</div>
  <div class="degree">
    <div class="degree-title">{{ education }}</div>
  </div>
</div>

<div class="section">
  <div class="section-title">Research Interests</div>
  <div>{{ profile }}</div>
</div>

<div class="section">
  <div class="section-title">Professional Appointments</div>
  {% for job in experience %}
  <div style="margin-bottom: 10px;">
    <strong>{{ job.role }}</strong><br>
    {{ job.company }}, {{ job.period }}<br>
    <ul>
      {% for b in job.bullets %}
      <li>{{ b }}</li>
      {% endfor %}
    </ul>
  </div>
  {% endfor %}
</div>

<div class="section">
  <div class="section-title">Skills & Methodology</div>
  <div>
    {% for item in skills %}
    {{ item.name }} ({{ item.pct }}%){% if not loop.last %}, {% endif %}
    {% endfor %}
  </div>
</div>

<div class="section">
  <div class="section-title">Languages</div>
  <div>{{ languages }}</div>
</div>

<div class="section">
  <div class="section-title">Selected Projects</div>
  {% for p in projects %}
  <div style="margin-bottom: 8px;">
    <strong>{{ p.title }}</strong>. {{ p.desc }}
  </div>
  {% endfor %}
</div>
</body>
</html>
"""

EXECUTIVE_TEMPLATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{{ name }} - Executive Profile</title>
<style>
  @page { margin: 2cm; }
  body { 
    font-family: 'Georgia', serif;
    color: #1a1a1a;
    line-height: 1.3;
  }
  .letterhead {
    border-bottom: 2px solid {{ primary_color }};
    padding-bottom: 15px;
    margin-bottom: 25px;
  }
  .name {
    font-size: 28px;
    font-weight: bold;
    color: {{ primary_color }};
    margin-bottom: 5px;
  }
  .title {
    font-size: 16px;
    color: #666;
    font-style: italic;
  }
  .contact-bar {
    text-align: right;
    font-size: 11px;
    color: #666;
  }
  .executive-summary {
    background: #f8f9fa;
    padding: 20px;
    border-left: 4px solid {{ primary_color }};
    margin-bottom: 25px;
    font-style: italic;
  }
  .section {
    margin-bottom: 20px;
  }
  .section-title {
    font-size: 14px;
    font-weight: bold;
    color: {{ primary_color }};
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 10px;
    border-bottom: 1px solid #e0e0e0;
    padding-bottom: 3px;
  }
  .achievement {
    margin-bottom: 15px;
  }
  .achievement-title {
    font-weight: bold;
    margin-bottom: 3px;
  }
  .metric {
    color: {{ primary_color }};
    font-weight: bold;
  }
</style>
</head>
<body>
<div class="letterhead">
  <div style="display: flex; justify-content: space-between; align-items: flex-end;">
    <div>
      <div class="name">{{ name }}</div>
      <div class="title">{{ title }}</div>
    </div>
    <div class="contact-bar">{{ contact | replace('\\n','<br>') }}</div>
  </div>
</div>

<div class="executive-summary">
  {{ profile }}
</div>

<div class="section">
  <div class="section-title">Career Highlights & Leadership</div>
  {% for job in experience %}
  <div class="achievement">
    <div style="display: flex; justify-content: space-between; margin-bottom: 5px;">
      <span class="achievement-title">{{ job.role }}</span>
      <span style="color: #666; font-size: 11px;">{{ job.period }}</span>
    </div>
    <div style="color: {{ primary_color }}; margin-bottom: 8px;">{{ job.company }}</div>
    <ul>
      {% for b in job.bullets %}
      <li>{{ b }}</li>
      {% endfor %}
    </ul>
  </div>
  {% endfor %}
</div>

<div class="section">
  <div class="section-title">Core Competencies</div>
  <div style="display: flex; flex-wrap: wrap; gap: 10px;">
    {% for item in skills %}
    <div style="background: {{ primary_color }}; color: white; padding: 5px 12px; border-radius: 15px; font-size: 11px;">
      {{ item.name }} ({{ item.pct }}%)
    </div>
    {% endfor %}
  </div>
</div>

<div class="section">
  <div class="section-title">Education & Credentials</div>
  <div>{{ education }}</div>
</div>
</body>
</html>
"""

# COVER LETTER TEMPLATES
COVER_TECH = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Cover Letter - {{ name }}</title>
<style>
  @page { margin: 2.5cm; }
  body { 
    font-family: 'Inter', -apple-system, sans-serif;
    color: #333;
    line-height: 1.5;
  }
  .header {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    border-bottom: 2px solid {{ primary_color }};
    padding-bottom: 15px;
    margin-bottom: 25px;
  }
  .applicant {
    font-size: 18px;
    font-weight: 600;
    color: {{ primary_color }};
  }
  .date {
    color: #666;
    font-size: 12px;
  }
  .company {
    margin-bottom: 20px;
  }
  .role {
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 5px;
  }
  .paragraph {
    margin-bottom: 15px;
  }
  .signature {
    margin-top: 40px;
  }
  .contact-info {
    font-size: 11px;
    color: #666;
    margin-top: 5px;
  }
</style>
</head>
<body>
<div class="header">
  <div class="applicant">{{ name }}</div>
  <div class="date">{{ date }}</div>
</div>

<div class="company">
  <div class="role">Application: {{ role }}</div>
</div>

<p class="paragraph">{{ para1 }}</p>
<p class="paragraph">{{ para2 }}</p>
<p class="paragraph">{{ para3 }}</p>

<div class="signature">
  <div>Best regards,</div>
  <div style="margin-top: 20px; font-weight: 600;">{{ name }}</div>
  <div class="contact-info">{{ contact | replace('\\n','<br>') }}</div>
</div>
</body>
</html>
"""

COVER_CORPORATE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Motivationsschreiben - {{ name }}</title>
<style>
  @page { margin: 3cm; }
  body { 
    font-family: 'Times New Roman', serif;
    color: #000;
    line-height: 1.4;
    font-size: 12pt;
  }
  .sender {
    text-align: right;
    margin-bottom: 30px;
    font-size: 10pt;
  }
  .recipient {
    margin-bottom: 20px;
  }
  .subject {
    font-weight: bold;
    margin: 25px 0;
  }
  .paragraph {
    margin-bottom: 12px;
    text-align: justify;
  }
  .closing {
    margin-top: 40px;
  }
</style>
</head>
<body>
<div class="sender">
  <div>{{ name }}</div>
  <div>{{ contact | replace('\\n','<br>') }}</div>
  <div>{{ date }}</div>
</div>

<div class="recipient">
  Sehr geehrte Damen und Herren,
</div>

<div class="subject">
  Bewerbung um die Position als {{ role }}
</div>

<p class="paragraph">{{ para1 }}</p>
<p class="paragraph">{{ para2 }}</p>
<p class="paragraph">{{ para3 }}</p>

<div class="closing">
  <p>Mit freundlichen Grüßen,</p>
  <p>{{ name }}</p>
</div>
</body>
</html>
"""

# Template mappings
TEMPLATE_OPTIONS = {
    "Modern Tech": MODERN_TECH_TEMPLATE,
    "Corporate Classic": CORPORATE_TEMPLATE,
    "Creative Minimal": CREATIVE_TEMPLATE,
    "Academic": ACADEMIC_TEMPLATE,
    "Executive": EXECUTIVE_TEMPLATE
}

COVER_OPTIONS = {
    "Modern": COVER_TECH,
    "Formal Corporate": COVER_CORPORATE
}

# ----------------------
# HELPER: Vision-Analyse (Screenshot) via OpenAI Vision (falls verfügbar)
# ----------------------

def get_fallback_style():
    return {
        "primary_color": "#003366",
        "secondary_colors": ["#6b7280", "#4b5563"],
        "color_style": "professional",
        "design_style": "modern",
        "typography": "sans-serif",
        "tone": "formal und professionell",
        "style_keywords": ["professionell", "klar", "seriös"]
    }

def analyze_screenshot_with_vision(api_key: str, image_bytes: bytes):
    """
    Versucht, das übergebene Screenshot-Bild via OpenAI (Vision) zu analysieren.
    Falls fehlschlägt, wird ein Fallback-Style zurückgegeben.
    """
    openai.api_key = api_key
    try:
        # Base64 (Vorsicht: sehr große Strings -> wir verwenden kurzen prompt und rely on model)
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')
        prompt = """
Analysiere diesen Website-Screenshot und gib als JSON zurück:
{
  "primary_color": "#hexcode or null",
  "secondary_colors": ["#hex1", "#hex2"],
  "color_style": "string",
  "design_style": "string",
  "typography": "serif/sans-serif/neutral",
  "tone": "string",
  "style_keywords": ["w1","w2","w3"]
}
Antwort ohne zusätzlichen Text.
"""
        # Hinweis: je nach OpenAI API-Version kann der Umgang mit Bildern variieren.
        # Wir senden Prompt + Bild als Daten-URI in einem einzigen message content (manche Accounts unterstützen das).
        message_content = prompt + "\n\nImage (base64):\n" + image_b64[:200000]  # trim if extremely large

        resp = openai.ChatCompletion.create(
            model="gpt-4-vision-preview",
            messages=[{"role":"user","content": message_content}],
            max_tokens=500,
            temperature=0.0
        )
        text = resp['choices'][0]['message']['content']
        jmatch = re.search(r'\{.*\}', text, re.DOTALL)
        if jmatch:
            return json.loads(jmatch.group(0))
        else:
            return get_fallback_style()
    except Exception as e:
        # Fehlerbehandlung: gib Fallback zurück
        st.warning(f"Analyse fehlgeschlagen (Vision): {e}")
        return get_fallback_style()

# ----------------------
# TEMPLATE & RENDER HELPERS
# ----------------------

def parse_skills(skills_text: str):
    """Parst Skills-Textbox: 'Name:Pct' pro Zeile -> list of dicts"""
    out = []
    for line in skills_text.splitlines():
        line = line.strip()
        if not line:
            continue
        if ':' in line:
            name, pct = line.split(':',1)
            try:
                pct_val = int(re.sub(r'[^0-9]','',pct))
            except:
                pct_val = 75
            out.append({"name": name.strip(), "pct": max(0, min(100, pct_val))})
        else:
            out.append({"name": line, "pct": 75})
    return out

def parse_experience_block(exp_blocks):
    """exp_blocks is list of dicts with period/company/role/bullets_str -> bullets list"""
    out = []
    for b in exp_blocks:
        bullets_list = [s.strip() for s in b.get("bullets","").split(",") if s.strip()]
        out.append({
            "period": b.get("period",""),
            "company": b.get("company",""),
            "role": b.get("role",""),
            "bullets": bullets_list
        })
    return out

def recommend_template_from_style(style):
    s = (style.get("design_style","") + " " + style.get("tone","")).lower()
    if "corporate" in s or "traditional" in s or "conservative" in s:
        return "Corporate Classic"
    if "creative" in s or "artistic" in s:
        return "Creative Minimal"
    if "academic" in s or "research" in s:
        return "Academic"
    if "executive" in s or "leadership" in s:
        return "Executive"
    # default -> tech/modern
    return "Modern Tech"

# ----------------------
# STREAMLIT UI
# ----------------------

st.title("FormWise — Screenshot → Design → Bewerbungs-PDF")
st.markdown("Hochladen → Design analysieren → Template wählen → PDF erzeugen")

# Sidebar: API Key + Upload-Hilfe
with st.sidebar:
    st.header("Konfiguration")
    api_key = st.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY") or "")
    st.markdown("---")
    st.markdown("**Screenshot Analyse**")
    st.markdown("Mache einen Screenshot der Firmenwebsite (Header/Über uns) und lade ihn hoch.")

# Upload / Analyse Column
col_upload, col_preview = st.columns([1,2])

with col_upload:
    uploaded_file = st.file_uploader("Screenshot (png/jpg)", type=["png","jpg","jpeg"])
    if uploaded_file:
        st.image(uploaded_file, caption="Hochgeladenes Bild", use_column_width=True)
        if st.button("🎨 Design analysieren"):
            if not api_key:
                st.error("Bitte OpenAI API Key eingeben (Sidebar).")
            else:
                img_bytes = uploaded_file.getvalue()
                with st.spinner("Analysiere Screenshot..."):
                    style = analyze_screenshot_with_vision(api_key, img_bytes)
                    st.session_state['style_analysis'] = style
                    st.session_state['uploaded_image'] = img_bytes
                    st.success("Design-Analyse fertig.")

with col_preview:
    if 'style_analysis' in st.session_state:
        st.subheader("Analysiertes Design")
        style = st.session_state['style_analysis']
        c1, c2, c3 = st.columns(3)
        with c1:
            st.write("Primärfarbe")
            st.color_picker("", style.get("primary_color","#003366"), disabled=True)
        with c2:
            sec = style.get("secondary_colors",[])
            st.write("Sekundärfarbe 1")
            st.color_picker("", sec[0] if len(sec)>0 else "#6b7280", disabled=True)
        with c3:
            st.write("Sekundärfarbe 2")
            st.color_picker("", sec[1] if len(sec)>1 else "#4b5563", disabled=True)
        st.markdown("**Design-Typ:** " + style.get("design_style",""))
        st.markdown("**Tonalität:** " + style.get("tone",""))
        if style.get("style_keywords"):
            st.markdown("**Keywords:** " + ", ".join(style.get("style_keywords",[])))
    else:
        st.info("Noch keine Analyse. Lade einen Screenshot hoch und klicke auf 'Design analysieren'.")

st.markdown("---")

# Bewerbungsdaten (links input)
st.subheader("Bewerbungsdaten")
col1, col2 = st.columns(2)
with col1:
    name = st.text_input("Name", value=st.session_state.get("name","Max Mustermann"))
    title = st.text_input("Berufsbezeichnung", value=st.session_state.get("title","Organisationsentwickler"))
    contact = st.text_area("Kontakt (mehrzeilig: Adresse, E-Mail, Tel.)", value=st.session_state.get("contact","Musterstrasse 1\n8000 Zürich\nmax.mustermann@email.com\n+41 79 123 45 67"))
    profile = st.text_area("Kurzprofil (1–4 Sätze)", value=st.session_state.get("profile","Organisationsentwickler mit 5+ Jahren Erfahrung in Veränderungsprojekten."))
    education = st.text_input("Ausbildung (Kurz)", value=st.session_state.get("education","MSc Organisationsentwicklung, Universität Zürich"))
with col2:
    # Experience dynamic
    st.markdown("**Berufserfahrung (einfach)**")
    exp_count = st.number_input("Anzahl Jobs", min_value=1, max_value=8, value=2, step=1)
    exp_blocks = []
    for i in range(int(exp_count)):
        st.markdown(f"Job {i+1}")
        period = st.text_input(f"Zeitraum {i+1}", value=st.session_state.get(f"exp_{i}_period", f"201{8+i}-202{0+i}"))
        company = st.text_input(f"Firma {i+1}", value=st.session_state.get(f"exp_{i}_company", f"Beispiel AG {i+1}"))
        role = st.text_input(f"Rolle {i+1}", value=st.session_state.get(f"exp_{i}_role", "Organisationsentwickler"))
        bullets = st.text_area(f"Stichworte / Bulletpoints (Komma getrennt) {i+1}", value=st.session_state.get(f"exp_{i}_bullets","Prozessanalyse, Workshopmoderation"))
        exp_blocks.append({"period": period, "company": company, "role": role, "bullets": bullets})
        # save to session so they persist across reruns
        st.session_state[f"exp_{i}_period"] = period
        st.session_state[f"exp_{i}_company"] = company
        st.session_state[f"exp_{i}_role"] = role
        st.session_state[f"exp_{i}_bullets"] = bullets

    projects_count = st.number_input("Anzahl Projekte", min_value=0, max_value=6, value=1, step=1)
    projects = []
    for i in range(int(projects_count)):
        t = st.text_input(f"Projekt Titel {i+1}", value=st.session_state.get(f"proj_{i}_title", f"Projekt {i+1}"))
        d = st.text_input(f"Projekt Beschreibung {i+1}", value=st.session_state.get(f"proj_{i}_desc","Kurzbeschreibung"))
        projects.append({"title": t, "desc": d})
        st.session_state[f"proj_{i}_title"] = t
        st.session_state[f"proj_{i}_desc"] = d

skills_text = st.text_area("Skills (je Zeile: Name:Prozent)", value=st.session_state.get("skills_text","Change Management:90\nModeration:80\nProjektmanagement:85"))
languages = st.text_input("Sprachen (Kurz)", value=st.session_state.get("languages","Deutsch: Muttersprache | Englisch: verhandlungssicher"))

# persist fields
st.session_state['name'] = name
st.session_state['title'] = title
st.session_state['contact'] = contact
st.session_state['profile'] = profile
st.session_state['education'] = education
st.session_state['skills_text'] = skills_text
st.session_state['languages'] = languages

# Template recommendation & choice
st.markdown("---")
st.subheader("Template-Auswahl")
style = st.session_state.get('style_analysis', get_fallback_style())
recommended = recommend_template_from_style(style)
st.info(f"Empfohlen: **{recommended}** (Analyse)")

template_choice = st.selectbox("Wähle CV-Template", list(TEMPLATE_OPTIONS.keys()), index=list(TEMPLATE_OPTIONS.keys()).index(recommended) if recommended in TEMPLATE_OPTIONS else 0)
cover_choice = st.selectbox("Wähle Cover-Template", list(COVER_OPTIONS.keys()), index=0)

# Preview HTML toggle
show_preview_cols = st.columns([1,1])
with show_preview_cols[0]:
    show_preview = st.checkbox("HTML-Vorschau anzeigen", value=True)
with show_preview_cols[1]:
    generate_both = st.checkbox("CV + Motivationsschreiben generieren", value=True)

# ----------------------
# PDF / HTML RENDER FUNCTION
# ----------------------

def render_template_to_html(template_str, context):
    tpl = Template(template_str)
    return tpl.render(**context)

def render_html_to_pdf_bytes(html_str):
    # WeasyPrint erzeugt bytes
    return HTML(string=html_str).write_pdf()

# ----------------------
# GENERATE BUTTONS
# ----------------------

st.markdown("---")
col_gen_left, col_gen_right = st.columns([1,2])
with col_gen_left:
    if st.button("📄 Generiere PDF(s)"):
        # prepare data
        skills = parse_skills(skills_text)
        experience = parse_experience_block(exp_blocks)
        date_str = datetime.now().strftime("%d.%m.%Y")
        primary_color = style.get("primary_color") if style and style.get("primary_color") else "#003366"
        font_body = "Inter" if style.get("typography","").lower()=="sans-serif" else "Times New Roman"

        common_context = {
            "name": name,
            "title": title,
            "contact": contact,
            "profile": profile,
            "education": education,
            "skills": skills,
            "languages": languages,
            "experience": experience,
            "projects": projects,
            "primary_color": primary_color,
            "date": date_str
        }

        try:
            outputs = []
            # CV
            cv_html = render_template_to_html(TEMPLATE_OPTIONS[template_choice], common_context)
            cv_pdf_bytes = render_html_to_pdf_bytes(cv_html)
            outputs.append(("CV", cv_html, cv_pdf_bytes))

            # Cover
            if generate_both:
                cover_context = {
                    "name": name,
                    "contact": contact,
                    "role": title,
                    "para1": st.session_state.get("cover_para1", f"Mit großem Interesse bewerbe ich mich als {title}."),
                    "para2": st.session_state.get("cover_para2", "Ich bringe Erfahrung in Organisationsentwicklung und Change Management mit."),
                    "para3": st.session_state.get("cover_para3", "Ich freue mich auf ein persönliches Gespräch."),
                    "primary_color": primary_color,
                    "date": date_str
                }
                cover_html = render_template_to_html(COVER_OPTIONS[cover_choice], cover_context)
                cover_pdf_bytes = render_html_to_pdf_bytes(cover_html)
                outputs.append(("Cover", cover_html, cover_pdf_bytes))

            # store in session for preview/download
            st.session_state['last_outputs'] = outputs
            st.success("PDF(s) erfolgreich generiert — weiter unten Vorschau & Download.")
        except Exception as e:
            st.error("Fehler bei PDF-Erzeugung: " + str(e))
            st.stop()

with col_gen_right:
    st.markdown("**Quick Notes:**")
    st.markdown("- Falls WeasyPrint auf dem Host zusätzliche Systemlibs benötigt, melde dich. Ich kann eine pyppeteer-Alternative einbauen.")
    st.markdown("- OpenAI Key wird nur für Screenshot-Analyse benötigt.")

# ----------------------
# SHOW PREVIEW & DOWNLOAD
# ----------------------

if 'last_outputs' in st.session_state:
    outputs = st.session_state['last_outputs']
    for name_out, html_out, pdf_bytes in outputs:
        st.markdown(f"### {name_out} — Vorschau & Download")
        if show_preview:
            # safe preview (als HTML)
            st.subheader("HTML-Vorschau")
            st.components.v1.html(html_out, height=700, scrolling=True)
        # download button
        st.download_button(
            label=f"📥 {name_out} als PDF herunterladen",
            data=pdf_bytes,
            file_name=f"{name.replace(' ','_')}_{name_out}.pdf",
            mime="application/pdf"
        )
        st.markdown("---")

# ----------------------
# HELP / TIPS
# ----------------------
with st.expander("💡 Tipps"):
    st.markdown("""
- Screenshot: erfasse Header / Logo / Über-uns / Karriere-Bereich, hohe Auflösung hilft der Analyse.  
- Wenn Analyse fehlschlägt, wird ein dezentes, seriöses Farbset verwendet.  
- WeasyPrint erzeugt hochwertige, druckfertige PDFs; bei Problemen alternativ pyppeteer möglich.  
- Setze `OPENAI_API_KEY` in Streamlit Secrets oder als Umgebungsvariable.
""")
