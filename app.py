import streamlit as st
from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa
import io

env = Environment(loader=FileSystemLoader("templates"))

def render_pdf(template_name, context):
    template = env.get_template(template_name)
    html = template.render(context)
    pdf_bytes = io.BytesIO()
    pisa.CreatePDF(io.StringIO(html), dest=pdf_bytes)
    return pdf_bytes.getvalue(), html

st.set_page_config(page_title="Formwise – Bewerbungsgenerator", layout="wide")
st.title("💼 Formwise – Bewerbungsgenerator (EBP-Edition)")

with st.sidebar:
    st.header("📋 Persönliche Angaben")
    name = st.text_input("Name", "Alexej Morozow")
    email = st.text_input("E-Mail", "alex.moroz@example.com")
    phone = st.text_input("Telefon", "+41 79 123 45 67")
    address = st.text_input("Adresse", "Zürich, Schweiz")

    st.header("🎯 Position")
    position = st.text_input("Bewerbung als", "Organisationsentwickler")
    company = st.text_input("Unternehmen", "EBP")
    website = st.text_input("Unternehmens-URL", "https://www.ebp.global/ch-de")

st.divider()
st.subheader("🧾 Lebenslauf")

col1, col2 = st.columns(2)
with col1:
    education = st.text_area("Ausbildung", "MAS Organisationsentwicklung, Universität Zürich\nBSc Sozialpädagogik, HSLU")
    experience = st.text_area("Berufserfahrung", "Teamleiter, Wohnheim Zürich\nSozialpädagoge, Stiftung XY")
with col2:
    skills = st.text_area("Fähigkeiten", "Organisationsanalyse, Change Management, Kommunikation")
    languages = st.text_area("Sprachen", "Deutsch (C2)\nEnglisch (C1)\nFranzösisch (B2)")

st.divider()
st.subheader("💬 Motivationsschreiben")
motivation_text = st.text_area("Text deines Motivationsschreibens",
"""Sehr geehrte Damen und Herren,

Mit grossem Interesse bewerbe ich mich als Organisationsentwickler bei EBP...
""")

if st.button("📄 Bewerbung generieren"):
    ctx_cv = {
        "name": name, "email": email, "phone": phone, "address": address,
        "education": education, "experience": experience,
        "skills": skills, "languages": languages,
        "company": company, "position": position
    }
    ctx_cover = {
        "name": name, "email": email, "phone": phone, "address": address,
        "motivation_text": motivation_text,
        "company": company, "position": position
    }
    cv_pdf, cv_html = render_pdf("cv_template.html", ctx_cv)
    cover_pdf, cover_html = render_pdf("cover_template.html", ctx_cover)

    st.success("✅ Bewerbung erfolgreich erstellt!")
    st.subheader("📄 Vorschau – Lebenslauf")
    st.components.v1.html(cv_html, height=800, scrolling=True)
    st.subheader("📄 Vorschau – Motivationsschreiben")
    st.components.v1.html(cover_html, height=800, scrolling=True)
    st.download_button("⬇️ Lebenslauf herunterladen", data=cv_pdf, file_name="Lebenslauf.pdf")
    st.download_button("⬇️ Motivationsschreiben herunterladen", data=cover_pdf, file_name="Motivationsschreiben.pdf")
