import streamlit as st
import json
import os

# Layout
st.set_page_config(layout="wide", page_title="Einsatzplanung")

# --- DATEI-PFADE ---
STAMMDATEN_FILE = "stammdaten.json"

# --- DATEN LADE & SPEICHER FUNKTIONEN ---
def load_stammdaten():
    if os.path.exists(STAMMDATEN_FILE):
        with open(STAMMDATEN_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "mitarbeiter": ["Tobias Wagner", "Alexander Weber"],
        "projekte": [{"nummer": "2026-01", "name": "Baustelle Hauptstraße"}]
    }

def save_stammdaten(data):
    with open(STAMMDATEN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- PROGRAMM-LOGIK ---
stammdaten = load_stammdaten()

st.title("🏗️ Stammdatenverwaltung")

# Mitarbeiter-Bereich
st.subheader("Mitarbeiter-Pool")
col1, col2 = st.columns([3, 1])
with col1:
    neuer_ma = st.text_input("Name eines neuen Mitarbeiters:")
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Hinzufügen"):
        if neuer_ma and neuer_ma not in stammdaten["mitarbeiter"]:
            stammdaten["mitarbeiter"].append(neuer_ma)
            save_stammdaten(stammdaten)
            st.rerun()

st.write("Aktuelle Liste:", stammdaten["mitarbeiter"])

# Projekt-Bereich
st.subheader("Projekt-Pool")
p_nr = st.text_input("Projektnummer (z.B. 2026-02):")
p_name = st.text_input("Projektname:")

if st.button("Projekt speichern"):
    if p_nr and p_name:
        stammdaten["projekte"].append({"nummer": p_nr, "name": p_name})
        save_stammdaten(stammdaten)
        st.success("Projekt hinzugefügt!")
        st.rerun()

st.write("Aktuelle Projekte:", stammdaten["projekte"])