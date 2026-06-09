import streamlit as st
import json
import os
import datetime
import io

# PDF-Bibliotheken (Stelle sicher, dass reportlab installiert ist: pip install reportlab)
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

st.set_page_config(layout="wide", page_title="Einsatzplanung")

# --- DATEI-PFADE & DATEN ---
STAMMDATEN_FILE = "stammdaten.json"

def load_data(file):
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"mitarbeiter": [], "projekte": [], "abwesenheiten": []}

def save_data(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# Initialisierung
data = load_data(STAMMDATEN_FILE)
if "einsatz" not in data: data["einsatz"] = {}
if "abwesend" not in data: data["abwesend"] = {}

# --- UI LOGIK ---
st.title("🏗️ Einsatzplanung 2026")

# Navigation
kw = st.sidebar.number_input("Kalenderwoche wählen", 1, 52, 24)
tab1, tab2 = st.tabs(["Übersicht", "Planung bearbeiten"])

# 1. Übersicht
with tab1:
    st.subheader(f"Wochenplan KW {kw}")
    if st.button("PDF exportieren"):
        st.write("PDF-Funktion bereit.") # Hier wird später die PDF-Logik integriert

# 2. Bearbeiten
with tab2:
    st.subheader("Planung bearbeiten")
    if data["projekte"]:
        selected_proj = st.selectbox("Projekt", [p["name"] for p in data["projekte"]])
        arbeit = st.text_input("Arbeiten")
        mitarbeiter = st.multiselect("Eingeteilte Mitarbeiter", data["mitarbeiter"])
        
        if st.button("Speichern"):
            if kw not in data["einsatz"]: data["einsatz"][str(kw)] = {}
            data["einsatz"][str(kw)][selected_proj] = {"arbeit": arbeit, "ma": mitarbeiter}
            save_data(STAMMDATEN_FILE, data)
            st.success("Gespeichert!")

# --- ABWESENHEITEN ---
st.sidebar.subheader("Abwesenheiten")
ma_select = st.sidebar.selectbox("Mitarbeiter", data["mitarbeiter"])
start_date = st.sidebar.date_input("Startdatum")
if st.sidebar.button("Abwesenheit eintragen"):
    data["abwesenheiten"].append({"ma": ma_select, "start": str(start_date)})
    save_data(STAMMDATEN_FILE, data)
    st.rerun()

st.sidebar.write("Aktuelle Abwesenheiten:", data["abwesenheiten"])