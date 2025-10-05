import streamlit as st
from jinja2 import Template
import requests
from bs4 import BeautifulSoup
import re
import asyncio
import openai
from pyppeteer import launch
from io import BytesIO
import base64
import os
from datetime import datetime
from PIL import Image
import io

st.set_page_config(page_title="FormWise - Screenshot Analysis", layout="centered")

# ----------------------
# BILDANALYSE MIT OPENAI VISION
# ----------------------

def analyze_screenshot_with_vision(api_key, image_bytes):
    """Analysiert Website-Screenshot mit GPT-4 Vision"""
    openai.api_key = api_key
    
    # Bild zu Base64 kodieren
    image_b64 = base64.b64encode(image_bytes).decode('utf-8')
    
    prompt = """
    Analysiere diesen Website-Screenshot und bestimme:
    
    1. **Farbpalette**: 
       - Primärfarbe (Hex-Code)
       - Sekundärfarben (1-2 Hex-Codes)
       - Farbstil (z.B. "corporate blue", "vibrant", "minimal")
    
    2. **Design-Stil**:
       - Modern/Traditional/Minimalistisch/Creative
       - Serif/Sans-serif Typografie
       - Layout (clean, busy, structured, artistic)
    
    3. **Unternehmens-Tonalität**:
       - Formal/Casual/Innovative/Conservative
       - Professional/Friendly/Technical/Creative
    
    Gib die Antwort als JSON:
    {
      "primary_color": "#hexcode",
      "secondary_colors": ["#hex1", "#hex2"],
      "color_style": "string",
      "design_style": "string", 
      "typography": "serif/sans-serif/neutral",
      "tone": "string",
      "style_keywords": ["word1", "word2", "word3"]
    }
    """
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-vision-preview",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=500
        )
        
        # JSON aus Antwort extrahieren
        result_text = response.choices[0].message.content
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        
        if json_match:
            import json
            return json.loads(json_match.group(0))
        else:
            # Fallback
            return {
                "primary_color": "#2563EB",
                "secondary_colors": ["#64748B", "#475569"],
                "color_style": "professional",
                "design_style": "modern",
                "typography": "sans-serif", 
                "tone": "formal und professionell",
                "style_keywords": ["professionell", "modern", "klar"]
            }
            
    except Exception as e:
        st.error(f"Vision API Fehler: {e}")
        return get_fallback_style()

def get_fallback_style():
    """Fallback Style falls Analyse fehlschlägt"""
    return {
        "primary_color": "#2563EB",
        "secondary_colors": ["#64748B", "#475569"],
        "color_style": "professional",
        "design_style": "modern",
        "typography": "sans-serif",
        "tone": "formal und professionell", 
        "style_keywords": ["professionell", "strukturiert", "zuverlässig"]
    }

# ----------------------
# STREAMLIT UI MIT SCREENSHOT UPLOAD
# ----------------------

st.title("📸 FormWise - Screenshot Analyse")

with st.sidebar:
    st.header("🔑 Konfiguration")
    api_key = st.text_input("OpenAI API Key", type="password", 
                           value=os.getenv("OPENAI_API_KEY") or "")
    
    st.header("📷 Website Analyse")
    st.markdown("""
    **So geht's:**
    1. 📸 Mache einen Screenshot der Unternehmens-Website
    2. 📤 Lade das Bild hier hoch  
    3. 🎨 KI analysiert Farben & Design
    4. 📄 Bewerbung wird automatisch angepasst
    """)

# Screenshot Upload Section
st.markdown("## 📸 Website Screenshot Hochladen")

uploaded_file = st.file_uploader(
    "Lade einen Screenshot der Unternehmens-Website hoch",
    type=['png', 'jpg', 'jpeg'],
    help="Mache einen Screenshot der Homepage oder Karriere-Seite"
)

# Vorher/Nachher Vergleich
col1, col2 = st.columns(2)

with col1:
    if uploaded_file is not None:
        # Bild anzeigen
        image = Image.open(uploaded_file)
        st.image(image, caption="Hochgeladener Screenshot", use_column_width=True)
        
        # Analyse starten
        if st.button("🎨 Design analysieren", type="primary") and api_key:
            with st.spinner("KI analysiert Farben und Design..."):
                # Bild in Bytes konvertieren
                img_bytes = uploaded_file.getvalue()
                
                # Vision API aufrufen
                style_analysis = analyze_screenshot_with_vision(api_key, img_bytes)
                
                # Ergebnis speichern
                st.session_state['style_analysis'] = style_analysis
                st.session_state['uploaded_image'] = img_bytes
                
                st.success("✅ Design erfolgreich analysiert!")

with col2:
    # Analyse-Ergebnis anzeigen
    if 'style_analysis' in st.session_state:
        style = st.session_state['style_analysis']
        
        st.markdown("**🎨 Analysierte Farbpalette**")
        
        # Farben visualisieren
        col_color1, col_color2, col_color3 = st.columns(3)
        
        with col_color1:
            st.color_picker("Primärfarbe", style['primary_color'], disabled=True)
            st.caption("Primärfarbe")
            
        with col_color2:
            if len(style['secondary_colors']) > 0:
                st.color_picker("Sekundärfarbe 1", style['secondary_colors'][0], disabled=True)
                st.caption("Sekundärfarbe 1")
                
        with col_color3:
            if len(style['secondary_colors']) > 1:
                st.color_picker("Sekundärfarbe 2", style['secondary_colors'][1], disabled=True)
                st.caption("Sekundärfarbe 2")
        
        # Design-Merkmale anzeigen
        st.markdown("**📊 Design-Merkmale**")
        st.write(f"**Stil:** {style['design_style']}")
        st.write(f"**Typografie:** {style['typography']}")
        st.write(f"**Tonalität:** {style['tone']}")
        
        st.markdown("**🏷️ Stil-Schlüsselwörter**")
        for keyword in style['style_keywords']:
            st.write(f"• {keyword}")

# ----------------------
# BEWERBUNGSDATEN (Unverändert)
# ----------------------

st.markdown("---")
st.markdown("## 👤 Bewerbungsdaten")

col1, col2 = st.columns(2)
with col1:
    name = st.text_input("Name", "Max Mustermann")
    title = st.text_input("Berufsbezeichnung", "Organisationsentwickler")
    contact = st.text_area("Kontakt", "max.mustermann@email.com | +41 79 123 45 67\n8000 Zürich")
    
with col2:
    profile = st.text_area("Kurzprofil", "Organisationsentwickler mit 5+ Jahren Erfahrung in Veränderungsvorhaben.")
    role = st.text_input("Rolle für Anschreiben", "Organisationsentwickler")

# Erfahrung, Skills etc. (wie vorher)
# ... [dein bestehender Code für Erfahrung, Skills, Projekte] ...

# ----------------------
# TEMPLATE AUSWAHL BASIEREND AUF ANALYSE
# ----------------------

def get_recommended_template(style_analysis):
    """Wählt passendes Template basierend auf Design-Analyse"""
    design_style = style_analysis.get('design_style', '').lower()
    tone = style_analysis.get('tone', '').lower()
    
    if 'corporate' in design_style or 'formal' in tone:
        return "Corporate Classic"
    elif 'tech' in design_style or 'modern' in design_style:
        return "Modern Tech" 
    elif 'creative' in design_style or 'artistic' in design_style:
        return "Creative Minimal"
    elif 'academic' in design_style or 'research' in tone:
        return "Academic"
    else:
        return "Modern Tech"  # Default

# Template Auswahl
st.markdown("## 🎨 Design Template")

if 'style_analysis' in st.session_state:
    recommended = get_recommended_template(st.session_state['style_analysis'])
    st.info(f"💡 Empfohlenes Template: **{recommended}** (basierend auf Analyse)")

template_choice = st.selectbox(
    "Wähle ein Design Template",
    ["Modern Tech", "Corporate Classic", "Creative Minimal", "Academic", "Executive"],
    index=0
)

# ----------------------
# PDF GENERIERUNG (angepasst)
# ----------------------

# Hier verwendest du dann die analysierten Farben
if 'style_analysis' in st.session_state:
    style = st.session_state['style_analysis']
    primary_color = style['primary_color']
    font_body = "Helvetica Neue" if style['typography'] == 'sans-serif' else "Georgia"
else:
    # Fallback falls keine Analyse durchgeführt wurde
    primary_color = "#003366"
    font_body = "Helvetica Neue"

# ... [Rest deines Codes für PDF Generierung] ...

st.markdown("---")
if st.button("📄 Bewerbung generieren", type="primary"):
    if not api_key:
        st.error("❌ Bitte OpenAI API Key eingeben")
    else:
        with st.spinner("Generiere Bewerbungsunterlagen..."):
            try:
                # Deine bestehende PDF-Generierung
                # ... [dein Code] ...
                
                st.success("✅ Bewerbungsunterlagen erfolgreich generiert!")
                
            except Exception as e:
                st.error(f"❌ Fehler bei der Generierung: {e}")

# ----------------------
# HILFE & TIPPS
# ----------------------

with st.expander("💡 Tipps für gute Screenshots"):
    st.markdown("""
    **Für beste Ergebnisse:**
    - 📱 **Homepage** der Firma screenshoten
    - 🎯 **Header/Bereich mit Logo** erfassen
    - 🌈 **Farbige Elemente** im Bild haben
    - 📝 **Textbereiche** mit einbeziehen
    - 🔍 **Hohe Qualität** (nicht zu klein/verpixelt)
    
    **Vermeide:**
    - 🚫 Zu dunkle/helle Bilder
    - 🚫 Nur Text ohne Design-Elemente  
    - 🚫 Sehr unruhige Hintergründe
    - 🚫 Persönliche/Login-geschützte Daten
    """)
