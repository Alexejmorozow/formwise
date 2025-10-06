import streamlit as st
from jinja2 import Template
import openai
import pdfkit
from io import BytesIO
import base64
import os
import json
from PIL import Image
import re

st.set_page_config(page_title="FormWise – Bewerbungsgenerator", layout="wide")

# -----------------------
# GPT-4 Vision Analyse
# -----------------------
def analyze_screenshot_with_vision(api_key, image_bytes):
    openai.api_key = api_key
    image_b64 = base64.b64encode(image_bytes).decode('utf-8')
    prompt = """
    Analysiere diesen Screenshot und gib ein JSON zurück mit:
    {
      "primary_color": "#hexcode",
      "secondary_colors": ["#hex1", "#hex2"],
      "design_style": "modern/professional/creative",
      "typography": "sans-serif/serif",
      "tone": "formal/casual",
      "style_keywords": ["word1","word2"]
    }
    """
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-vision-preview",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                ]
            }],
            max_tokens=400
        )
        text = response.choices[0].message.content
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
    except Exception:
        pass
    return {
        "primary_color": "#003366",
        "secondary_colors": ["#006699", "#CCCCCC"],
        "design_style": "corporate",
        "typography": "sans-serif",
        "tone": "formal",
        "style_keywords": ["modern", "clean", "professional"]
    }

# -----------------------
# PDF Generator
# -----------------------
def render_pdf(template_path, context):
    with open(template_path, "r", encoding="utf-8") as f:
        html = Template(f.read()).render(**context)
    pdf_bytes = pdfkit.from_string(html, False)
    return BytesIO(pdf_bytes), html

# -----------------------
# UI
# -----------------------
st.title("📄 FormWise – Bewerbungsgenerator")

with st.sidebar:
    st.header("🔑 Einstellungen")
    api_key = st.text_input("OpenAI API Key", type="password")
    st.markdown("---")
    uploaded_file = st.file_uploader("📷 Screenshot der Firmenwebsite", type=["png", "jpg", "jpeg"])

if uploaded_file and api_key:
    image = Image.open(uploaded_file)
    st.image(image, caption="Hochgeladener Screenshot", use_column_width=True)
    if st.button("🎨 Design analysieren"):
        with st.spinner("Analysiere Website-Design..."):
            result = analyze_screenshot_with_vision(api_key, uploaded_file.getvalue())
            st.session_state["style"] = result
            st.success("Analyse abgeschlossen!")
            st.json(result)

# -----------------------
# Eingabedaten
# -----------------------
st.header("👤 Bewerbungsdaten")

col1, col2 = st.columns(2)
with col1:
    name = st.text_input("Name", "Alexej Morozow")
    title = st.text_input("Titel", "Organisationsentwickler")
    contact = st.text_area("Kontakt", "alexej.morozow@email.com | Zürich")
    profile = st.text_area("Profil", "Erfahrener Organisationsentwickler mit Fokus auf Change Management.")
with col2:
    role = st.text_input("Rolle", "Organisationsentwickler")
    experiences = st.text_area("Erfahrungen (je Zeile)", "EBP – Change Projekte\nPwC – Organisationsberatung").split("\n")
    skills = st.text_area("Fähigkeiten (je Zeile)", "Kommunikation\nAgiles Arbeiten\nModeration").split("\n")

# -----------------------
# Bewerbungsbrief
# -----------------------
st.header("💬 Anschreiben")
intro = st.text_area("Einleitung", "Mit großem Interesse habe ich Ihre Ausschreibung gelesen ...")
body = st.text_area("Hauptteil", "Ich bringe langjährige Erfahrung in Veränderungsprozessen mit ...")
closing = st.text_area("Schluss", "Ich freue mich auf ein persönliches Gespräch.")

# -----------------------
# PDF Generierung
# -----------------------
if st.button("📄 PDF generieren"):
    style = st.session_state.get("style", {
        "primary_color": "#003366",
        "typography": "sans-serif"
    })
    context_cv = {
        "name": name,
        "title": title,
        "contact": contact,
        "profile": profile,
        "experiences": experiences,
        "skills": skills,
        "primary_color": style["primary_color"],
        "font": "Helvetica Neue" if style["typography"] == "sans-serif" else "Georgia"
    }
    context_cover = {
        "name": name,
        "role": role,
        "intro": intro,
        "body": body,
        "closing": closing,
        "primary_color": style["primary_color"],
        "font": "Helvetica Neue" if style["typography"] == "sans-serif" else "Georgia"
    }

    with st.spinner("Erstelle PDFs..."):
        cv_pdf, cv_html = render_pdf("templates/cv_template.html", context_cv)
        cover_pdf, cover_html = render_pdf("templates/cover_template.html", context_cover)

        st.success("✅ PDFs erstellt!")

        st.download_button("📥 Lebenslauf herunterladen", data=cv_pdf, file_name="Lebenslauf.pdf", mime="application/pdf")
        st.download_button("📥 Anschreiben herunterladen", data=cover_pdf, file_name="Anschreiben.pdf", mime="application/pdf")

        with st.expander("👁️ Lebenslauf Vorschau"):
            st.markdown(cv_html, unsafe_allow_html=True)
        with st.expander("👁️ Anschreiben Vorschau"):
            st.markdown(cover_html, unsafe_allow_html=True)
