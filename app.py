import streamlit as st
import json
import os
import datetime
import io

# Layout-Einstellungen
st.set_page_config(layout="wide", page_title="Einsatzplanung")

# --- 1. DATENMANAGEMENT ---
STAMMDATEN_FILE = "stammdaten.json"

def load_data():
    if os.path.exists(STAMMDATEN_FILE):
        with open(STAMMDATEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"mitarbeiter": ["Max Mustermann", "Erika Musterfrau"], "projekte": ["Projekt A"]}

def save_data(data):
    with open(STAMMDATEN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- 2. HAUPTPROGRAMM ---
st.title("Mitarbeitereinsatzplanung")

data = load_data()

# Einfache Anzeige der Daten zur Überprüfung
st.subheader("Mitarbeiter")
st.write(data["mitarbeiter"])

st.subheader("Projekte")
st.write(data["projekte"])

# Test-Button zum Speichern
if st.button("Daten zurücksetzen"):
    default_data = {
        "mitarbeiter": ["Max Mustermann", "Erika Musterfrau"],
        "projekte": ["Projekt A"]
    }
    save_data(default_data)
    st.success("Daten wurden zurückgesetzt!")
    st.rerun()

st.info("Wenn du diesen Text siehst, läuft das Grundgerüst fehlerfrei.")