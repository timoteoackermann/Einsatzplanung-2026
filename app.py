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
    st.title("Login Einsatzplanung")
    eingabe = st.text_input("Bitte Passwort eingeben:", type="password")
    if st.button("Einloggen"):
        if eingabe == PASSWORD:
            st.session_state.authenticated = True
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
                return json.load(f)
        except:
            pass
    return {
        "mitarbeiter": ["Tobias Wagner", "Alexander Weber", "Christian Schmidt", "Dennis Müller", "Stefan Becker", "Michael Hofmann"],
        "projekte": [{"nummer": "2026-01", "name": "Baustelle Hauptstraße"}, {"nummer": "2026-02", "name": "Projekt Nordstadt"}],
        "abwesenheiten": []
    }

def save_stammdaten(data):
    with open(STAMMDATEN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

stammdaten = load_stammdaten()
MITARBEITER_POOL = sorted(stammdaten["mitarbeiter"])

# --- HELFER & DIALOGE ---
@st.dialog("📅 Abwesenheiten verwalten")
def manage_absences_dialog(ma_name):
    st.write(f"Verwaltung für: {ma_name}")
    range_input = st.date_input("Zeitraum:", value=())
    typ_input = st.radio("Umfang:", ["Ganztägig", "Vormittags", "Nachmittags"])
    if st.button("Speichern"):
        if len(range_input) == 2:
            stammdaten["abwesenheiten"].append({
                "mitarbeiter": ma_name,
                "start": range_input[0].isoformat(),
                "ende": range_input[1].isoformat(),
                "typ": typ_input
            })
            save_stammdaten(stammdaten)
            st.rerun()

# --- 2. LOGIK ---
def get_filename(kw):
    return f"planung_{kw.lower().replace(' ', '_')}.json"

def load_data(kw):
    filename = get_filename(kw)
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"projekte": [], "einsatz": {}, "abwesend": {}}

def save_data(kw, data):
    with open(get_filename(kw), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# Initialisierung
if "kw_auswahl" not in st.session_state:
    iso_jahr, iso_kw, _ = datetime.date.today().isocalendar()
    st.session_state.kw_auswahl = f"KW {iso_kw}"

# Navigation & UI
st.sidebar.title("Navigation")
kw_input = st.sidebar.text_input("Kalenderwoche (z.B. KW 24):", value=st.session_state.kw_auswahl)
st.session_state.kw_auswahl = kw_input
data = load_data(kw_input)

# Hauptbereich
st.title(f"Planung für {kw_input}")

if st.sidebar.button("Speichern"):
    save_data(kw_input, data)
    st.success("Gespeichert!")

# Einfaches Beispiel-Interface zum Testen
st.write("Projekte dieser Woche:", data["projekte"])
neues_projekt = st.text_input("Projekt hinzufügen (Name):")
if st.button("Projekt hinzufügen"):
    data["projekte"].append(neues_projekt)
    save_data(kw_input, data)
    st.rerun()