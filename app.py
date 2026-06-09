import streamlit as st
import json
import os
import datetime
import io
import glob

# PDF-Bibliotheken importieren
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import Image

# Setzt das Layout auf "Wide"
st.set_page_config(layout="wide", page_title="Mitarbeitereinsatzplanung", page_icon="🏗️")

# --- 0. PASSWORT-SCHUTZ ---
PASSWORD = "Bauleitung2026"

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🏗️ Login Einsatzplanung")
    eingabe = st.text_input("Bitte Passwort eingeben:", type="password")
    if st.button("Einloggen"):
        if eingabe == PASSWORD:
            st.session_state.authenticated = True
            st.success("Erfolgreich eingeloggt!")
            st.rerun()
        else:
            st.error("Falsches Passwort!")
    st.stop()

# --- 1. STAMMDATEN-VERWALTUNG (MITARBEITER) ---
STAMMDATEN_FILE = "stammdaten.json"

def load_stammdaten():
    if os.path.exists(STAMMDATEN_FILE):
        with open(STAMMDATEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return {
            "mitarbeiter": [
                "Tobias Wagner", "Alexander Weber", "Christian Schmidt", 
                "Dennis Müller", "Stefan Becker", "Michael Hofmann"
            ]
        }

def save_stammdaten(data):
    with open(STAMMDATEN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

stammdaten = load_stammdaten()
MITARBEITER_POOL = sorted(stammdaten["mitarbeiter"])

# --- 2. GENERIERUNG DES MONATSKALENDERS (JAHR 2026) ---
MONATE_NAMEN = [
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember"
]

wochen_pro_monat = {m: [] for m in MONATE_NAMEN}
kw_zu_monat_mapping = {}

for kw in range(1, 54):
    mo = datetime.date.fromisocalendar(2026, kw, 1)
    do = datetime.date.fromisocalendar(2026, kw, 4)
    so = datetime.date.fromisocalendar(2026, kw, 7)
    
    monat_name = MONATE_NAMEN[do.month - 1]
    anzeige_text = f"KW {kw:02d} ({mo.strftime('%d.%m.')} – {so.strftime('%d.%m.')})"
    kw_key = f"KW {kw}"
    
    wochen_pro_monat[monat_name].append({
        "kw_text": kw_key,
        "anzeige": anzeige_text
    })
    kw_zu_monat_mapping[kw_key] = monat_name

heute = datetime.date.today()
iso_jahr, iso_kw, _ = heute.isocalendar()
aktuelle_start_kw = f"KW {iso_kw}" if iso_jahr == 2026 else "KW 24"

if "kw_auswahl" not in st.session_state:
    st.session_state.kw_auswahl = aktuelle_start_kw
if "selected_month" not in st.session_state:
    st.session_state.selected_month = kw_zu_monat_mapping.get(st.session_state.kw_auswahl, "Juni")

# --- 3. PROJEKT- & WOCHENDATEN-VERWALTUNG ---
def get_filename(kw):
    return f"planung_{kw.lower().replace(' ', '_')}.json"

def load_data(kw):
    filename = get_filename(kw)
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return {
            "projekte": ["Baustelle Hauptstraße", "Projekt Nordstadt"],
            "einsatz": {},
            "abwesend": {n: [] for n in ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag"]}
        }

def save_data(kw, data):
    with open(get_filename(kw), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_wochentage_mit_datum(kw_text):
    try:
        kw_num = int(kw_text.replace("KW", "").strip())
        namen = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag"]
        tage_liste = []
        for i, name in enumerate(namen, start=1):
            tag_datum = datetime.date.fromisocalendar(2026, kw_num, i)
            tage_liste.append({
                "name": name,
                "anzeige": f"{name} ({tag_datum.strftime('%d.%m.')})"
            })
        return tage_liste
    except:
        return [{"name": n, "anzeige": n} for n in ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag"]]

# --- PDF GENERIERUNGS-FUNKTION ---
def create_pdf(data, wochentage_daten, kw_text):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=landscape(A4), 
        rightMargin=20, 
        leftMargin=