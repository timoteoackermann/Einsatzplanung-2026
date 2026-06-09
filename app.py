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
        leftMargin=20, 
        topMargin=20, 
        bottomMargin=20
    )
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'TitleStyle', parent=styles['Heading1'], fontSize=18, leading=22, textColor=colors.HexColor("#1f2937"), spaceAfter=15
    )
    company_style = ParagraphStyle(
        'CompanyHeader', fontName='Helvetica-Bold', fontSize=18, leading=22, textColor=colors.HexColor("#1f2937"), alignment=2
    )
    cell_header_style = ParagraphStyle(
        'CellHeaderStyle', parent=styles['Normal'], fontSize=9, leading=11, fontName='Helvetica-Bold', textColor=colors.HexColor("#1f2937"), alignment=1
    )
    cell_bold_style = ParagraphStyle(
        'CellBoldStyle', parent=styles['Normal'], fontSize=9, leading=11, fontName='Helvetica-Bold', textColor=colors.HexColor("#1f2937")
    )
    cell_text_style = ParagraphStyle(
        'CellTextStyle', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.HexColor("#374151")
    )
    cell_abw_style = ParagraphStyle(
        'CellAbwStyle', parent=styles['Normal'], fontSize=8, leading=10, textColor=colors.HexColor("#b91c1c")
    )

    title_p = Paragraph(f"Einsatzplanung — {kw_text} 2026", title_style)
    
    logo_img = None
    if os.path.exists("logo.png"):
        try:
            logo_img = Image("logo.png", width=24, height=24)
        except:
            logo_img = None

    if logo_img:
        header_right_table = Table([[Paragraph("Ackermann Bau", company_style), logo_img]], colWidths=[140, 30])
        header_right_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
            ('LEFTPADDING', (0,0), (-1,-1), 0),
            ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ]))
        header_content = header_right_table
    else:
        header_content = Paragraph("Ackermann Bau", company_style)

    header_table = Table([[title_p, header_content]], colWidths=[550, 252])
    header_table.setStyle(TableStyle([('VALIGN', (0,0), (-1,-1), 'MIDDLE'), ('BOTTOMPADDING', (0,0), (-1,-1), 0)]))
    story.append(header_table)
    story.append(Spacer(1, 10))
    
    table_data = []
    header_row_1 = [Paragraph("<b>Projekt / Baustelle</b>", cell_header_style)]
    for t in wochentage_daten:
        header_row_1.extend([Paragraph(f"<b>{t['anzeige']}</b>", cell_header_style), ""])
    table_data.append(header_row_1)
    
    header_row_2 = [""]
    for _ in wochentage_daten:
        header_row_2.extend([Paragraph("<b>Arbeiten</b>", cell_header_style), Paragraph("<b>Mitarbeiter</b>", cell_header_style)])
    table_data.append(header_row_2)
    
    for prj in data["projekte"]:
        row = [Paragraph(prj, cell_bold_style)]
        for t in wochentage_daten:
            tag = t["name"]
            arbeit = data["einsatz"].get(prj, {}).get(tag, {}).get("arbeit", "-")
            if not arbeit.strip():
                arbeit = "-"
            mitarbeiter_list = data["einsatz"].get(prj, {}).get(tag, {}).get("mitarbeiter", [])
            mitarbeiter = ", ".join(mitarbeiter_list) if mitarbeiter_list else "-"
            
            row.append(Paragraph(arbeit.replace("\n", "<br/>"), cell_text_style))
            row.append(Paragraph(mitarbeiter, cell_text_style))
        table_data.append(row)
        
    abw_row = [Paragraph("<b>ABWESEND</b>", ParagraphStyle('AbwTitle', parent=cell_bold_style, textColor=colors.HexColor("#b91c1c")))]
    for t in wochentage_daten:
        tag = t["name"]
        abw_liste = ", ".join(data["abwesend"].get(tag, []))
        if not abw_liste:
            abw_liste = "Niemand"
        abw_row.extend([Paragraph(abw_liste, cell_abw_style), ""])
    table_data.append(abw_row)
    
    col_widths = [112] + [69] * 10
    t_style = [
        ('BACKGROUND', (0,0), (-1,1), colors.HexColor("#f3f4f6")),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 4),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e5e7eb")),
        ('BACKGROUND', (0,2), (0,-2), colors.HexColor("#f9fafb")),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor("#fef2f2")),
        ('SPAN', (0,0), (0,1)),
    ]
    
    for idx in range(1, 11, 2):
        t_style.append(('SPAN', (idx, 0), (idx+1, 0)))
    abw_row_idx = len(table_data) - 1
    for idx in range(1, 11, 2):
        t_style.append(('SPAN', (idx, abw_row_idx), (idx+1, abw_row_idx)))
        
    t = Table(table_data, colWidths=col_widths, repeatRows=2)
    t.setStyle(TableStyle(t_style))
    story.append(t)
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# --- 4. SEITENLEISTE (MONATSKALENDER & STRUKTUR) ---
st.sidebar.header("🗓️ Kalenderauswahl")

monat_index = MONATE_NAMEN.index(st.session_state.selected_month)
gewaehlter_monat = st.sidebar.selectbox("Monat wechseln:", MONATE_NAMEN, index=monat_index)

if gewaehlter_monat != st.session_state.selected_month:
    st.session_state.selected_month = gewaehlter_monat
    st.session_state.kw_auswahl = wochen_pro_monat[gewaehlter_monat][0]["kw_text"]
    st.rerun()

wochen_optionen = wochen_pro_monat[st.session_state.selected_month]
wochen_labels = [w["anzeige"] for w in wochen_optionen]
wochen_keys = [w["kw_text"] for w in wochen_optionen]

try:
    radio_index = wochen_keys.index(st.session_state.kw_auswahl)
except ValueError:
    radio_index = 0
    st.session_state.kw_auswahl = wochen_keys[0]

gewaehlte_woche_anzeige = st.sidebar.radio("Woche auswählen:", options=wochen_labels, index=radio_index)

kw_auswahl = wochen_keys[wochen_labels.index(gewaehlte_woche_anzeige)]
if kw_auswahl != st.session_state.kw_auswahl:
    st.session_state.kw_auswahl = kw_auswahl
    st.rerun()

if 'current_kw' not in st.session_state or st.session_state.current_kw != kw_auswahl:
    st.session_state.current_kw = kw_auswahl
    st.session_state.data = load_data(kw_auswahl)

data = st.session_state.data
WOCHENTAGE_DATEN = get_wochentage_mit_datum(kw_auswahl)

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
    col_nav_prev, col_nav_next = st.columns(2)
    with col_nav_prev:
        if st.button("⬅️ Vorige Woche", use_container_width=True, key="btn_nav_prev"):
            kw_num = int(st.session_state.kw_auswahl.replace("KW", "").strip())
            neu_kw = kw_num - 1 if kw_num > 1 else 53
            st.session_state.kw_auswahl = f"KW {neu_kw}"
            st.session_state.selected_month = kw_zu_monat_mapping[f"KW {neu_kw}"]
            st.rerun()
            
    with col_nav_next:
        if st.button("Nächste Woche ➡️", use_container_width=True, key="btn_nav_next"):
            kw_num = int(st.session_state.kw_auswahl.replace("KW", "").strip())
            neu_kw = kw_num + 1 if kw_num < 53 else 1
            st.session_state.kw_auswahl = f"KW {neu_kw}"
            st.session_state.selected_month = kw_zu_monat_mapping[f"KW {neu_kw}"]
            st.rerun()
            
    st.markdown("### Gesamtübersicht der Woche")
    
    try:
        pdf_data = create_pdf(data, WOCHENTAGE_DATEN, kw_auswahl)
        st.download_button(
            label="📥 Diese Woche als PDF exportieren",
            data=pdf_data,
            file_name=f"Einsatzplanung_{kw_auswahl.replace(' ', '_')}_2026.pdf",
            mime="application/pdf",
            key="pdf_download_btn",
            use_container_width=True
        )
    except Exception as e:
        st.error(f"Fehler bei der PDF-Vorbereitung: {e}")
        
    st.markdown(" ")

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
            
            html_table += f"<td style='border: 1px solid #ddd; padding: 12px; vertical-align: top;'>
            html_table += f"<div style='font-size: 0.9em; color: #555; margin-bottom: 5px;'>🛠️ {arbeit}</div>"
            if mitarbeiter:  # Zeigt Mitarbeiter und Symbol NUR an, wenn Daten vorhanden sind
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

    # --- BRANDNEUE FILTERFUNKTION: PROJEKT-HISTORIE ---
    st.markdown("---")
    st.markdown("### 🔍 Projekt-Historie (Gesamtzeitraum)")
    
    # Alle vorhandenen JSON-Planungsdateien scannen, um lückenlos alle jemals erfassten Projekte zu finden
    all_stored_projects = set()
    json_files = glob.glob("planung_kw_*.json")
    for f in json_files:
        try:
            with open(f, "r", encoding="utf-8") as file:
                p_data = json.load(file)
                if "projekte" in p_data:
                    all_stored_projects.update(p_data["projekte"])
                if "einsatz" in p_data:
                    all_stored_projects.update(p_data["einsatz"].keys())
        except:
            pass
    sorted_global_projects = sorted(list(all_stored_projects))
    
    if sorted_global_projects:
        selected_global_project = st.selectbox(
            "Wähle ein Projekt aus, um dessen gesamte Historie anzuzeigen:", 
            sorted_global_projects, 
            key="global_project_history_filter"
        )
        
        project_history = []
        for f in json_files:
            base = os.path.basename(f)
            kw_part = base.replace("planung_kw_", "").replace(".json", "")
            try:
                kw_num = int(kw_part)
            except ValueError:
                continue
                
            try:
                with open(f, "r", encoding="utf-8") as file:
                    p_data = json.load(file)
                    if "einsatz" in p_data and selected_global_project in p_data["einsatz"]:
                        prj_data = p_data["einsatz"][selected_global_project]
                        for tag_name, details in prj_data.items():
                            arbeit = details.get("arbeit", "").strip()
                            mitarbeiter_list = details.get("mitarbeiter", [])
                            
                            if arbeit or mitarbeiter_list:
                                try:
                                    tag_idx = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag"].index(tag_name) + 1
                                    tag_datum = datetime.date.fromisocalendar(2026, kw_num, tag_idx)
                                    datum_str = tag_datum.strftime('%d.%m.%Y')
                                except:
                                    datum_str = "Datum unleserlich"
                                    tag_datum = datetime.date(2026, 1, 1)
                                
                                project_history.append({
                                    "datum_sort": tag_datum,
                                    "kw": kw_num,
                                    "anzeige_tag": f"{tag_name}, {datum_str} (KW {kw_num})",
                                    "arbeit": arbeit if arbeit else "—",
                                    "mitarbeiter": ", ".join(mitarbeiter_list) if mitarbeiter_list else "—"
                                })
            except:
                pass
        
        # Chronologisch nach echtem Datum sortieren (älteste Einträge oben, neueste unten)
        project_history.sort(key=lambda x: x["datum_sort"])
        
        if project_history:
            hist_table = "<table style='width:100%; border-collapse: collapse; font-family: sans-serif; margin-top: 10px;'>"
            hist_table += "<tr style='background-color: #f4f4f4;'><th style='border: 1px solid #ddd; padding: 10px; text-align: left; width: 25%;'>Datum / Kalenderwoche</th><th style='border: 1px solid #ddd; padding: 10px; text-align: left; width: 45%;'>Durchgeführte Arbeiten</th><th style='border: 1px solid #ddd; padding: 10px; text-align: left; width: 30%;'>Eingeteilte Mitarbeiter</th></tr>"
            for item in project_history:
                hist_table += f"<tr><td style='border: 1px solid #ddd; padding: 10px; font-weight: bold;'>{item['anzeige_tag']}</td><td style='border: 1px solid #ddd; padding: 10px;'>{item['arbeit']}</td><td style='border: 1px solid #ddd; padding: 10px;'>{item['mitarbeiter']}</td></tr>"
            hist_table += "</table>"
            st.markdown(hist_table, unsafe_allow_html=True)
        else:
            st.info("Zu diesem Projekt wurden in den Datensätzen bisher keine konkreten Arbeiten oder Mitarbeiter dokumentiert.")
    else:
        st.info("Es wurden noch keine gespeicherten Projektdaten auf dem Server gefunden.")

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
                    
                    safe_def_mit = [m for m in def_mit if m in MITARBEITER_POOL]
                    
                    arb_input = st.text_input("Arbeiten:", value=def_arb, key=f"arb_{prj}_{tag}_{kw_auswahl}")
                    mit_input = st.multiselect("Mitarbeiter:", MITARBEITER_POOL, default=safe_def_mit, key=f"mit_{prj}_{tag}_{kw_auswahl}")
                    
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
            safe_def_abw = [m for m in def_abw if m in MITARBEITER_POOL]
            
            abw_input = st.multiselect(f"Abwesend am {t['anzeige']}:", MITARBEITER_POOL, default=safe_def_abw, key=f"abw_{tag}_{kw_auswahl}")
            data["abwesend"][tag] = abw_input

    st.markdown("###")
    if st.button("💾 Alle Änderungen für diese Woche speichern", type="primary"):
        save_data(kw_auswahl, data)
        st.success(f"Die Planung für die {kw_auswahl} wurde erfolgreich gespeichert!")
        st.rerun()