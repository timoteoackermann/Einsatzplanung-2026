import streamlit as st
import json
import os
import datetime
import io
import glob

# PDF-Bibliotheken importieren
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Setzt das Layout auf "Wide" für maximale Übersicht
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
        with open(STAMMDATEN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "projekte" not in data:
                data["projekte"] = [
                    {"nummer": "2026-01", "name": "Baustelle Hauptstraße"},
                    {"nummer": "2026-02", "name": "Projekt Nordstadt"}
                ]
            if "mitarbeiter" not in data:
                data["mitarbeiter"] = [
                    "Tobias Wagner", "Alexander Weber", "Christian Schmidt", 
                    "Dennis Müller", "Stefan Becker", "Michael Hofmann"
                ]
            if "abwesenheiten" not in data:
                data["abwesenheiten"] = []
            return data
    else:
        return {
            "mitarbeiter": [
                "Tobias Wagner", "Alexander Weber", "Christian Schmidt", 
                "Dennis Müller", "Stefan Becker", "Michael Hofmann"
            ],
            "projekte": [
                {"nummer": "2026-01", "name": "Baustelle Hauptstraße"},
                {"nummer": "2026-02", "name": "Projekt Nordstadt"}
            ],
            "abwesenheiten": []
        }

def save_stammdaten(data):
    with open(STAMMDATEN_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

stammdaten = load_stammdaten()
MITARBEITER_POOL = sorted(stammdaten["mitarbeiter"])

# --- HELFER: ABWESENHEITS-BERECHNUNG ---
def get_effective_absences(tag_name, tag_date, week_data):
    absent_display = []
    seen = set()
    
    if tag_date:
        for entry in stammdaten.get("abwesenheiten", []):
            ma = entry["mitarbeiter"]
            try:
                start_d = datetime.date.fromisoformat(entry["start"])
                end_d = datetime.date.fromisoformat(entry["ende"])
                if start_d <= tag_date <= end_d:
                    if ma in MITARBEITER_POOL and ma not in seen:
                        typ = entry.get("typ", "Ganztägig")
                        suffix = " (VM)" if "Vormittags" in typ else (" (NM)" if "Nachmittags" in typ else "")
                        absent_display.append(f"{ma}{suffix}")
                        seen.add(ma)
            except:
                pass
                
    for ma in week_data.get("abwesend", {}).get(tag_name, []):
        if ma in MITARBEITER_POOL and ma not in seen:
            absent_display.append(ma)
            seen.add(ma)
            
    return sorted(absent_display)

def get_kw_date_range_str(wochentage_daten):
    try:
        start_date = wochentage_daten[0]["date"]
        end_date = wochentage_daten[-1]["date"]
        return f"{start_date.strftime('%d.%m.%y')} – {end_date.strftime('%d.%m.%y')}"
    except:
        return ""

# --- POP-UP DIALOG FÜR MANUELLE ZEITRÄUME ---
@st.dialog("📅 Abwesenheiten & Zeiträume verwalten")
def manage_absences_dialog(ma_name):
    st.markdown(f"### 👤 {ma_name}")
    st.write("Hinterlege hier Urlaube, Lehrgänge oder halbtägige Abwesenheiten.")
    
    st.markdown("**🆕 Neuen Zeitraum hinzufügen:**")
    range_input = st.date_input("Zeitraum auswählen (Klick auf Start- und Endtag):", value=(), key=f"input_range_{ma_name}")
    
    typ_input = st.radio(
        "Umfang der Abwesenheit:",
        options=["Ganztägig", "Vormittags (erst ab Mittags einsatzbereit)", "Nachmittags (ab Mittags abwesend)"],
        index=0,
        key=f"input_typ_{ma_name}"
    )
    
    if st.button("Zeitraum speichern", key=f"btn_save_range_{ma_name}", type="primary"):
        if len(range_input) == 2:
            start_str = range_input[0].isoformat()
            ende_str = range_input[1].isoformat()
            
            stammdaten["abwesenheiten"].append({
                "mitarbeiter": ma_name,
                "start": start_str,
                "ende": ende_str,
                "typ": typ_input
            })
            save_stammdaten(stammdaten)
            st.success("Zeitraum erfolgreich hinterlegt!")
            st.rerun()
        else:
            st.error("Bitte wähle einen vollständigen Zeitraum (Start- UND Enddatum) aus!")
            
    st.markdown("---")
    st.markdown("**🗂️ Gespeicherte Zeiträume:**")
    
    ma_absences = [a for a in stammdaten.get("abwesenheiten", []) if a["mitarbeiter"] == ma_name]
    if not ma_absences:
        st.info("Keine eingetragenen Zeiträume vorhanden.")
    else:
        for idx, abw in enumerate(ma_absences):
            col_text, col_del = st.columns([4, 1])
            try:
                start_formatted = datetime.date.fromisoformat(abw["start"]).strftime("%d.%m.%Y")
                end_formatted = datetime.date.fromisoformat(abw["ende"]).strftime("%d.%m.%Y")
                typ_anzeige = ab