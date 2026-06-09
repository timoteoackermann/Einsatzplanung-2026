import streamlit as st
import json
import os
import datetime

# Setzt das Layout auf "Wide"
st.set_page_config(layout="wide", page_title="Mitarbeitereinsatzplanung", page_icon="🏗️")

# --- 0. PASSWORT-SCHUTZ ---
PASSWORD = "Bauleitung2026"  # <-- Hier dein gewünschtes Passwort eintragen!

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
    st.stop()  # Stoppt die App hier, falls nicht eingeloggt

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

# --- 2. DATUMSLOGIK FÜR DIE KW (JAHR 2026) ---
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

# --- 4. SEITENLEISTE (NAVIGATION & VERWALTUNG) ---
st.sidebar.header("🗓️ Verwaltung")
kw_auswahl = st.sidebar.selectbox("Kalenderwoche wählen", [f"KW {i}" for i in range(1, 53)], index=23)

WOCHENTAGE_DATEN = get_wochentage_mit_datum(kw_auswahl)

if 'current_kw' not in st.session_state or st.session_state.current_kw != kw_auswahl:
    st.session_state.current_kw = kw_auswahl
    st.session_state.data = load_data(kw_auswahl)

data = st.session_state.data

st.sidebar.markdown("---")

with st.sidebar.expander("👥 Mitarbeiter-Pool verwalten"):
    st.write("Aktuelles Team:")
    for ma in MITARBEITER_POOL:
        col_ma_name, col_ma_del = st.columns([4, 1])
        col_ma_name.write(f"• {ma}")
        if col_ma_del.button("🗑️", key=f"del_ma_{ma}"):
            stammdaten["mitarbeiter"].remove(ma)
            save_stammdaten(stammdaten)
            st.rerun()
            
    neuer_ma = st.text_input("Neuer Mitarbeiter Name:", key="add_ma_input")
    if st.button("➕ Mitarbeiter hinzufügen"):
        if neuer_ma and neuer_ma not in stammdaten["mitarbeiter"]:
            stammdaten["mitarbeiter"].append(neuer_ma)
            save_stammdaten(stammdaten)
            st.rerun()

st.sidebar.markdown("---")

with st.sidebar.expander("🏗️ Baustellen dieser Woche verwalten"):
    st.write("Aktive Projekte in dieser KW:")
    for prj in list(data["projekte"]):
        col_prj_name, col_prj_del = st.columns([4, 1])
        col_prj_name.write(f"• {prj}")
        if col_prj_del.button("🗑️", key=f"del_prj_{prj}"):
            data["projekte"].remove(prj)
            if prj in data["einsatz"]:
                del data["einsatz"][prj]
            save_data(kw_auswahl, data)
            st.rerun()
            
    neues_projekt = st.text_input("Neue Baustelle hinzufügen:", key="add_prj_input")
    if st.button("➕ Baustelle hinzufügen"):
        if neues_projekt and neues_projekt not in data["projekte"]:
            data["projekte"].append(neues_projekt)
            save_data(kw_auswahl, data)
            st.rerun()

if st.sidebar.button("🚪 Logout"):
    st.session_state.authenticated = False
    st.rerun()

# --- 5. HAUPTBEREICH & MODUS-AUSWAHL ---
st.title(f"🏗️ Einsatzplanung — {kw_auswahl}")

modus = st.radio("Ansicht wählen:", ["👀 Kompakte Wochenübersicht", "✍️ Planungs-Modus (Bearbeiten)"], horizontal=True)

# --- 6. LOGIK: DOPPELBELEGUNGEN PRÜFEN ---
belegte_mitarbeiter = {t["name"]: {} for t in WOCHENTAGE_DATEN}
for prj in data["projekte"]:
    for t in WOCHENTAGE_DATEN:
        tag = t["name"]
        eingeteilt = data["einsatz"].get(prj, {}).get(tag, {}).get("mitarbeiter", [])
        for mitarbeiter in eingeteilt:
            if mitarbeiter not in belegte_mitarbeiter[tag]:
                belegte_mitarbeiter[tag][mitarbeiter] = []
            belegte_mitarbeiter[tag][mitarbeiter].append(prj)

# --- 7. MODUS A: KOMPAKTE WOCHENÜBERSICHT ---
if modus == "👀 Kompakte Wochenübersicht":
    st.markdown("### Gesamtübersicht der Woche")
    
    html_table = "<table style='width:100%; border-collapse: collapse; font-family: sans-serif;'>"
    html_table += "<tr style='background-color: #f4f4f4;'><th style='border: 1px solid #ddd; padding: 12px; text-align: left;'>Projekt / Baustelle</th>"
    for t in WOCHENTAGE_DATEN:
        html_table += f"<th style='border: 1px solid #ddd; padding: 12px; text-align: left; width: 18%;'>{t['anzeige']}</th>"
    html_table += "</tr>"
    
    for prj in data["projekte"]:
        html_table += f"<tr><td style='border: 1px solid #ddd; padding: 12px; font-weight: bold; background-color: #fafafa;'>{prj}</td>"
        for t in WOCHENTAGE_DATEN:
            tag = t["name"]
            arbeit = data["einsatz"].get(prj, {}).get(tag, {}).get("arbeit", "—")
            mitarbeiter = ", ".join(data["einsatz"].get(prj, {}).get(tag, {}).get("mitarbeiter", []))
            if not mitarbeiter:
                mitarbeiter = "<i>Keine Mitarbeiter</i>"
                
            html_table += f"<td style='border: 1px solid #ddd; padding: 12px; vertical-align: top;'>"
            html_table += f"<div style='font-size: 0.9em; color: #555; margin-bottom: 5px;'>🛠️ {arbeit}</div>"
            html_table += f"<div style='font-size: 0.95em; font-weight: 500;'>👥 {mitarbeiter}</div>"
            html_table += "</td>"
        html_table += "</tr>"
        
    html_table += "<tr style='background-color: #fff0f0;'><td style='border: 1px solid #ddd; padding: 12px; font-weight: bold; color: #c0392b;'>🛑 ABWESEND</td>"
    for t in WOCHENTAGE_DATEN:
        tag = t["name"]
        abw_liste = ", ".join(data["abwesend"].get(tag, []))
        if not abw_liste:
            abw_liste = "<i>Niemand abwesend</i>"
        html_table += f"<td style='border: 1px solid #ddd; padding: 12px; vertical-align: top; color: #c0392b;'>{abw_liste}</td>"
    html_table += "</tr>"
    html_table += "</table>"
    
    st.markdown(html_table, unsafe_allow_html=True)

# --- 8. MODUS B: BEARBEITUNGS-MODUS ---
else:
    st.markdown("### Planungsdaten eintragen")
    st.info("Hinweis: Änderungen werden live im Hintergrund vorbereitet. Klicke unten auf 'Speichern', um sie dauerhaft zu sichern.")

    konflikte = []
    for t in WOCHENTAGE_DATEN:
        tag = t["name"]
        for abw_mitarbeiter in data["abwesend"].get(tag, []):
            if abw_mitarbeiter in belegte_mitarbeiter[tag]:
                projekte_liste = ", ".join(belegte_mitarbeiter[tag][abw_mitarbeiter])
                konflikte.append(f"⚠️ **{abw_mitarbeiter}** ist am **{t['anzeige']}** als **abwesend** eingetragen, aber auf folgender Baustelle eingeteilt: {projekte_liste}")
    
    if konflikte:
        for k in konflikte:
            st.error(k)

    for prj in data["projekte"]:
        with st.expander(f"🏗️ {prj}", expanded=True):
            cols = st.columns(5)
            for i, t in enumerate(WOCHENTAGE_DATEN):
                tag = t["name"]
                with cols[i]:
                    st.markdown(f"**{t['anzeige']}**")
                    
                    def_arb = data["einsatz"].get(prj, {}).get(tag, {}).get("arbeit", "")
                    def_mit = data["einsatz"].get(prj, {}).get(tag, {}).get("mitarbeiter", [])
                    
                    arb_input = st.text_input("Arbeiten:", value=def_arb, key=f"arb_{prj}_{tag}_{kw_auswahl}")
                    mit_input = st.multiselect("Mitarbeiter:", MITARBEITER_POOL, default=def_mit, key=f"mit_{prj}_{tag}_{kw_auswahl}")
                    
                    if prj not in data["einsatz"]:
                        data["einsatz"][prj] = {}
                    if tag not in data["einsatz"][prj]:
                        data["einsatz"][prj][tag] = {}
                    data["einsatz"][prj][tag]["arbeit"] = arb_input
                    data["einsatz"][prj][tag]["mitarbeiter"] = mit_input

    st.markdown("---")
    st.markdown("### 🛑 Abwesende Mitarbeiter eintragen")
    cols_abw = st.columns(5)
    for i, t in enumerate(WOCHENTAGE_DATEN):
        tag = t["name"]
        with cols_abw[i]:
            def_abw = data["abwesend"].get(tag, [])
            abw_input = st.multiselect(f"Abwesend am {t['anzeige']}:", MITARBEITER_POOL, default=def_abw, key=f"abw_{tag}_{kw_auswahl}")
            data["abwesend"][tag] = abw_input

    st.markdown("###")
    if st.button("💾 Alle Änderungen für diese Woche speichern", type="primary"):
        save_data(kw_auswahl, data)
        st.success(f"Die Planung für die {kw_auswahl} wurde erfolgreich gespeichert!")
        st.rerun()