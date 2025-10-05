# app.py
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

st.set_page_config(page_title="FormWise - EBP Template", layout="centered")

# ----------------------
# Templates (HTML)
# ----------------------
CV_TEMPLATE = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{{ name }} - CV</title>
<style>
  @page { margin: 2cm; }
  body { font-family: {{ font_body }} , Arial, sans-serif; color: #111; }
  h1 { color: {{ primary_color }}; font-size: 28px; margin-bottom:6px; }
  h2 { color: {{ primary_color }}; font-size:14px; margin:12px 0 6px 0; border-bottom:1px solid {{ primary_color }}; padding-bottom:4px; width:100%; }
  .header { display:flex; justify-content:space-between; align-items:center; }
  .contact { font-size:12px; color:#222; }
  .container { display:flex; gap:24px; margin-top:12px; }
  .left { width:28%; }
  .right { width:72%; }
  .section { margin-bottom:10px; }
  .skill-bar { height:9px; background:#e6eef6; border-radius:5px; overflow:hidden; margin-bottom:6px; }
  .skill-fill { height:100%; background:{{ primary_color }}; }
  ul { margin-top:6px; }
  li { margin-bottom:6px; }
  .muted { color:#444; font-size:12px; }
  footer { position:fixed; bottom:1.5cm; left:2cm; right:2cm; font-size:10px; color:#666; text-align:center; }
</style>
</head>
<body>
<div class="header">
  <div>
    <h1>{{ name }}</h1>
    <div class="muted">{{ title }}</div>
  </div>
  <div class="contact">
    {{ contact }}
  </div>
</div>

<div class="container">
  <div class="left">
    <div class="section">
      <h2>Fähigk</h2>
      {% for item in skills %}
      <div class="skill-bar"><div class="skill-fill" style="width:{{ item.pct }}%"></div></div>
      <div class="muted" style="margin-bottom:8px;">{{ item.name }}</div>
      {% endfor %}
    </div>

    <div class="section">
      <h2>Sprachen</h2>
      <div class="muted">{{ languages }}</div>
    </div>

    <div class="section">
      <h2>Ausbildung</h2>
      <div class="muted">{{ education }}</div>
    </div>
  </div>

  <div class="right">
    <div class="section">
      <h2>Profil</h2>
      <div>{{ profile }}</div>
    </div>

    <div class="section">
      <h2>Berufserfahrung</h2>
      {% for job in experience %}
      <strong>{{ job.period }} – {{ job.company }} – {{ job.role }}</strong>
      <ul>
      {% for b in job.bullets %}
        <li>{{ b }}</li>
      {% endfor %}
      </ul>
      {% endfor %}
    </div>

    <div class="section">
      <h2>Projekte</h2>
      <ul>
      {% for p in projects %}
        <li><strong>{{ p.title }}</strong> — {{ p.desc }}</li>
      {% endfor %}
      </ul>
    </div>
  </div>
</div>

<footer>Erstellt mit FormWise · {{ date }}</footer>
</body>
</html>
"""

COVER_TEMPLATE = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{{ name }} - Motivationsschr</title>
<style>
  @page { margin: 2cm; }
  body { font-family: {{ font_body }}, Arial, sans-serif; color:#111; line-height:1.5; }
  .header { color: {{ primary_color }}; font-size:18px; margin-bottom:8px; }
  .meta { font-size:12px; color:#333; margin-bottom:18px; }
  p { margin-bottom:12px; }
  footer { position:fixed; bottom:1.5cm; left:2cm; right:2cm; font-size:10px; color:#666; text-align:center; }
</style>
</head>
<body>
<div class="header">Bewerbung als {{ role }}</div>
<div class="meta">
  {{ name }} · {{ contact }}<br>
  Datum: {{ date }}
</div>

<p>Sehr geehrte Damen und Herren,</p>

<p>{{ para1 }}</p>
<p>{{ para2 }}</p>
<p>{{ para3 }}</p>

<p>Freundliche Grüsse,</p>
<p>{{ name }}</p>

<footer>FormWise · personalisiert für EBP</footer>
</body>
</html>
"""

# ----------------------
# Helper: web scrape + color extraction + openai call
# ----------------------

def extract_hex_colors_from_css(css_text):
    # find hex color codes in css
    hexes = re.findall(r'#(?:[0-9a-fA-F]{3}){1,2}', css_text)
    # filter and return unique
    seen = []
    for h in hexes:
        hh = h.lower()
        if hh not in seen:
            seen.append(hh)
    return seen

def fetch_site_text_and_css(url, timeout=8):
    try:
        r = requests.get(url, timeout=timeout, headers={'User-Agent':'Mozilla/5.0'})
        html = r.text
        soup = BeautifulSoup(html, 'html.parser')
        # collect inline styles
        css_text = ""
        for style in soup.find_all('style'):
            css_text += style.get_text() + "\n"
        # collect linked stylesheets
        for link in soup.find_all('link', rel='stylesheet'):
            href = link.get('href')
            if href:
                href_full = href if href.startswith('http') else requests.compat.urljoin(url, href)
                try:
                    rr = requests.get(href_full, timeout=5, headers={'User-Agent':'Mozilla/5.0'})
                    css_text += rr.text + "\n"
                except:
                    pass
        # pick some text (about, mission, career)
        candidates = []
        for sel in ['meta[name=description]', 'h1', 'h2', 'p', 'section', 'article']:
            for el in soup.select(sel):
                txt = el.get_text(separator=' ', strip=True)
                if len(txt) > 40:
                    candidates.append(txt)
        body_text = "\n\n".join(candidates[:6])
        return body_text, css_text
    except Exception as e:
        return "", ""

def ask_openai_for_style(api_key, sample_text, sample_css):
    openai.api_key = api_key
    prompt = f"""
Analysiere die folgende Firmenseite. Gib als JSON nur diese Felder:
- main_color: Hexcode (z.B. #003366) oder null
- secondary_color: Hexcode oder null
- style_keywords: Liste (3) kurze Adjektive
- typography_hint: 'serif' | 'sans-serif' | 'neutral'
- tone_hint: kurzer Satz, z.B. 'formal und technisch'

Hier sind Auszüge aus Text und CSS:
TEXT:
{sample_text[:3000]}

CSS:
{sample_css[:4000]}
"""
    resp = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}],
        max_tokens=300,
        temperature=0.0
    )
    text = resp['choices'][0]['message']['content']
    # try extract JSON within
    try:
        import json
        # find first { ... }
        jmatch = re.search(r'\{.*\}', text, re.DOTALL)
        if jmatch:
            jtxt = jmatch.group(0)
            out = json.loads(jtxt)
            return out
    except Exception as e:
        pass
    # fallback
    return {
        "main_color": None,
        "secondary_color": None,
        "style_keywords": ["seriös","klar","neutral"],
        "typography_hint": "sans-serif",
        "tone_hint": "formal und fachlich"
    }

# ----------------------
# PDF rendering (pyppeteer)
# ----------------------
async def html_to_pdf_bytes(html_str):
    browser = await launch(args=['--no-sandbox'])
    page = await browser.newPage()
    await page.setContent(html_str, waitUntil='networkidle0')
    pdf_bytes = await page.pdf(format='A4', printBackground=True, margin={'top': '20mm','bottom':'20mm','left':'20mm','right':'20mm'})
    await browser.close()
    return pdf_bytes

def render_pdf(html):
    # run pyppeteer loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    pdf_bytes = loop.run_until_complete(html_to_pdf_bytes(html))
    return pdf_bytes

# ----------------------
# Streamlit UI
# ----------------------
st.title("FormWise – EBP CV & Cover (Demo)")

with st.sidebar:
    st.header("Setup")
    api_key = st.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY") or "")
    st.markdown("Wenn du die Firma analysieren willst, gib die URL ein und klick 'Analysieren'.")

st.markdown("## Nutzdaten")
col1, col2 = st.columns(2)
with col1:
    name = st.text_input("Name", "Max Mustermann")
    title = st.text_input("Berufsbezeichnung", "Organisationsentwickler")
    contact = st.text_area("Kontakt (Tel, Mail, Ort)", "max.mustermann@email.com | +41 79 123 45 67\n8000 Zürich")
with col2:
    profile = st.text_area("Kurzprofil", "Organisationsentwickler mit 5+ Jahren Erfahrung in Veränderungsvorhaben.")
    role = st.text_input("Rolle für Cover", "Organisationsentwickler")

st.markdown("## Erfahrung (einfach für Demo)")
exp_count = st.slider("Anzahl Jobs", 1, 6, 2)
experience = []
for i in range(exp_count):
    st.markdown(f"### Job {i+1}")
    colA, colB = st.columns([2,4])
    with colA:
        period = st.text_input(f"Zeitraum {i+1}", f"202{i}-202{4+i}")
        company = st.text_input(f"Firma {i+1}", f"Beispiel AG {i+1}")
    with colB:
        role_i = st.text_input(f"Rolle {i+1}", "Organisationsentwickler")
        bullets = st.text_area(f"Stichworte {i+1} (Komma getrennt)", "Prozessanalyse, Workshopmoderation")
    experience.append({
        "period": period,
        "company": company,
        "role": role_i,
        "bullets": [b.strip() for b in bullets.split(",") if b.strip()]
    })

st.markdown("## Projekte")
proj_count = st.slider("Anzahl Projekte", 0, 4, 1)
projects = []
for i in range(proj_count):
    t = st.text_input(f"Projekt Titel {i+1}", f"Projekt {i+1}")
    d = st.text_input(f"Projekt Beschr {i+1}", "Kurzbeschreibung")
    projects.append({"title": t, "desc": d})

st.markdown("## Skills / Sonst")
skills_raw = st.text_area("Skills (Name:Prozent, neue Zeile)", "Change Management:90\nModeration:80\nProjektmgmt:85")
skills = []
for line in skills_raw.splitlines():
    if ":" in line:
        name_s, pct = line.split(":",1)
        try:
            p = int(re.sub(r'[^0-9]','',pct))
        except:
            p = 75
        skills.append({"name": name_s.strip(), "pct": p})

languages = st.text_input("Sprachen", "Deutsch: Mutterspr | Englisch: verhandelbar")
education = st.text_input("Letzte Ausbildung", "MSc Organisationsentwicklung, Uni Zürich")

st.markdown("----")
st.markdown("## Firmenanalyse (optional)")
colA, colB = st.columns([3,1])
with colA:
    company_url = st.text_input("Firmen URL", "https://www.ebp.global/ch-de")
with colB:
    if st.button("Analysieren"):
        if not api_key:
            st.error("API Key fehlt")
        else:
            with st.spinner("Webseite lesen & Stil ermitteln..."):
                txt, css = fetch_site_text_and_css(company_url)
                style = ask_openai_for_style(api_key, txt, css)
                st.session_state['style'] = style
                st.success("Fertig: Stil ermittelt")

style = st.session_state.get('style', None)
if style:
    st.markdown("**Stil (von KI)**")
    st.json(style)
else:
    st.info("Keine Firmeninfo geladen. Fallback Stil wird genutzt.")

# choose font & colors
primary_color = style.get('main_color') if style and style.get('main_color') else "#003366"
font_body = "Helvetica Neue" if (style and style.get('typography_hint') == 'sans-serif') else "Georgia"

# render html
date_str = datetime.now().strftime("%d.%m.%Y")
cv_html = Template(CV_TEMPLATE).render(
    name=name, title=title, contact=contact.replace("\n","<br>"),
    skills=skills, languages=languages, education=education,
    profile=profile, experience=experience, projects=projects,
    primary_color=primary_color, font_body=font_body, date=date_str
)

cover_paras = {
    "para1": st.text_area("Cover Text 1", "Mit grossem Interesse habe ich Ihre Ausschreibung gelesen. Die Arbeitsweise und Werte von EBP sprechen mich an."),
    "para2": st.text_area("Cover Text 2", "Ich bringe Erfahrung in Change Management, Stakeholderarbeit und nachhaltiger Implementierung mit."),
    "para3": st.text_area("Cover Text 3", "Ich freue mich auf ein Gespräch, um mögliche Beitrag zu erläutern.")
}

cover_html = Template(COVER_TEMPLATE).render(
    name=name, contact=contact.replace("\n"," | "), role=role,
    para1=cover_paras['para1'], para2=cover_paras['para2'], para3=cover_paras['para3'],
    primary_color=primary_color, font_body=font_body, date=date_str
)

st.markdown("----")
st.markdown("### Vorschau (HTML)")

tab1, tab2 = st.tabs(["CV (HTML)","Motivation (HTML)"])
with tab1:
    st.components.v1.html(cv_html, height=700, scrolling=True)
with tab2:
    st.components.v1.html(cover_html, height=700, scrolling=True)

st.markdown("----")
if st.button("PDF erzeugen & Download"):
    with st.spinner("Generiere PDF (Chromium wird ggf. geladen, das kann kurz dauern)..."):
        try:
            cv_pdf = render_pdf(cv_html)
            cover_pdf = render_pdf(cover_html)
            # combine: simply offer two files; user can merge locally
            st.download_button("CV herunterladen (PDF)", data=cv_pdf, file_name=f"{name.replace(' ','_')}_CV.pdf", mime="application/pdf")
            st.download_button("Motivationsschr herunterladen (PDF)", data=cover_pdf, file_name=f"{name.replace(' ','_')}_Motivationsschr.pdf", mime="application/pdf")
            st.success("PDFs bereit")
        except Exception as e:
            st.error(f"PDF Fehler: {e}")
            st.exception(e)

st.markdown("----")
st.markdown("### Hinweise zur Produktion & Deployment")
st.markdown("""
- Setze `OPENAI_API_KEY` in Streamlit Secrets (oder gib im Sidebar ein).
- Erster PDF-Export lädt Chromium (pyppeteer) → kann 30–120s dauern.
- Auf Streamlit Cloud: funktioniert, kann aber Startzeit verlängern. Alternativ lokal testen.
""")
