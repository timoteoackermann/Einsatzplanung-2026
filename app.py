import streamlit as st
import json
import os
import datetime
import io
import glob

# PDF-Bibliotheken importieren
try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
except ImportError:
    st.error("Bitte installiere ReportLab im Terminal: pip install reportlab")
    st.stop()

# Layout
st.set_page_config(layout="wide", page_title="Mitarbeitereinsatzplanung", page_icon="🏗️")

# --- 0. PASSWORT-SCHUTZ ---
PASSWORD = "Bauleitung2026"

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    col_login_logo, col_login_title = st.columns([1, 8])
    with col_login_logo:
        if os.path.exists("logo.png"):
            st.image("logo.png", width=120)
    with col_login_title:
        st.title("Login Einsatzplanung")
        
    eingabe = st.text_input("Bitte Passwort eingeben:", type="password")
    if st.button("Einloggen"):
        if eingabe == PASSWORD:
            st.session_state.authenticated = True
            st.success("Erfolgreich eingeloggt!")
            st.rerun()
        else:
            st.error("Falsches Passwort!")
    st.stop()

# --- 1. STAMMDATEN-VERWALTUNG ---
STAMMDATEN_FILE = "stammdaten.json"

def load_stammdaten():
    if os.path.exists(STAMMDATEN_FILE):
        try:
            with open(STAMMDATEN_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "projekte" not in data: