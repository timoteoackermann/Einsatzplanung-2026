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
                typ_anzeige = abw.get("typ", "Ganztägig").split(" (")[0]
                col_text.write(f"• **{start_formatted}** bis **{end_formatted}** — *{typ_anzeige}*")
            except:
                col_text.write("• Fehlerhaftes Datum")
                
            if col_del.button("🗑️", key=f"del_range_{ma_name}_{idx}"):
                stammdaten["abwesenheiten"].remove(abw)
                save_stammdaten(stammdaten)
                st.rerun()

# --- 2. GENERIERUNG DES MONATSKALENDERS ---
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

# --- 3. WOCHENDATEN-VERWALTUNG ---
def get_filename(kw):
    return f"planung_{kw.lower().replace(' ', '_')}.json"

def load_data(kw):
    filename = get_filename(kw)
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    else:
        return {
            "projekte": ["2026-01 - Baustelle Hauptstraße", "2026-02 - Projekt Nordstadt"],
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
                "date": tag_datum,
                "anzeige": f"{name} ({tag_datum.strftime('%d.%m.')})"
            })
        return tage_liste
    except:
        return [{"name": n, "date": None, "anzeige": n} for n in ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag"]]

# --- PDF GENERIERUNG ---
def create_pdf(data, wochentage_daten, kw_text, kw_datum_str):
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
        'TitleStyle', parent=styles['Heading1'], fontSize=16, leading=20, textColor=colors.HexColor("#1f2937")
    )
    company_style = ParagraphStyle(
        'CompanyHeader', fontName='Helvetica-Bold', fontSize=16, leading=20, textColor=colors.HexColor("#1f2937"), alignment=2
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

    title_p = Paragraph(f"Einsatzplanung — {kw_text} ({kw_datum_str})", title_style)
    
    logo_img = None
    if os.path.exists("logo.png"):
        try:
            logo_img = Image("logo.png", width=60, height=30)
        except:
            logo_img = None

    if logo_img:
        header_table = Table(
            [[logo_img, title_p, Paragraph("Ackermann Bau", company_style)]],
            colWidths=[80, 522, 200]
        )
    else:
        header_table = Table(
            [[title_p, Paragraph("Ackermann Bau", company_style)]],
            colWidths=[602, 200]
        )

    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10)
    ]))
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
            implicit_einsatz = data["einsatz"].get(prj, {}).get(tag, {})
            if isinstance(implicit_einsatz, dict):
                arbeit = implicit_einsatz.get("arbeit", "-")
                mitarbeiter_list = implicit_einsatz.get("mitarbeiter", [])
            else:
                arbeit = "-"
                mitarbeiter_list = []
                
            if not arbeit or not arbeit.strip():
                arbeit = "-"
            mitarbeiter = ", ".join(mitarbeiter_list) if mitarbeiter_list else "-"
            
            row.append(Paragraph(arbeit.replace("\n", "<br/>"), cell_text_style))
            row.append(Paragraph(mitarbeiter, cell_text_style))
        table_data.append(row)
        
    abw_row = [Paragraph("<b>ABWESEND</b>", ParagraphStyle('AbwTitle', parent=cell_bold_style, textColor=colors.HexColor("#b91c1c")))]
    for t in wochentage_daten:
        tag = t["name"]
        eff_abw = get_effective_absences(tag, t.get("date"), data)
        abw_liste = ", ".join(eff_abw)
        if not abw_liste:
            abw_liste = "Niemand"
        abw_row.extend([Paragraph(abw_liste, cell_abw_style), ""])
    table_data.append(abw_row)
    
    col_widths = [112] + [69] * 10
    t_style = [
        ('BACKGROUND', (0,0), (-1,1), colors.HexColor("#f3f4f6")),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('TOPPADDING', (0,0), (-1,-1), 5),
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

# --- 4. SEITENLEISTE NAVI & STAMMDATEN ---
kw_auswahl = st.session_state.kw_auswahl
if 'current_kw' not in st.session_state or st.session_state.current_kw != kw_auswahl:
    st.session_state.current_kw = kw_auswahl
    st.session_state.data = load_data(kw_auswahl)

data = st.session_state.data
WOCHENTAGE_DATEN = get_wochentage_mit_datum(kw_auswahl)
kw_datum_str = get_kw_date_range_str(WOCHENTAGE_DATEN)

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

st.sidebar.markdown("---")

with st.sidebar.expander("👥 Mitarbeiter-Pool verwalten"):
    st.write("Aktuelles Team:")
    for ma in MITARBEITER_POOL:
        col_ma_name, col_ma_abw, col_ma_del = st.columns([3, 1, 1])
        col_ma_name.write(f"• {ma}")
        if col_ma_abw.button("📅", key=f"btn_dialog_trigger_{ma}"):
            manage_absences_dialog(ma)
        if col_ma_del.button("🗑️", key=f"del_ma_{ma}"):
            stammdaten["mitarbeiter"].remove(ma)
            if "abwesenheiten" in stammdaten:
                stammdaten["abwesenheiten"] = [a for a in stammdaten["abwesenheiten"] if a["mitarbeiter"] != ma]
            save_stammdaten(stammdaten)
            st.rerun()
    neuer_ma = st.text_input("Neuer Mitarbeiter Name:", key="add_ma_input")
    if st.button("➕ Mitarbeiter hinzufügen"):
        if neuer_ma and neuer_ma not in stammdaten["mitarbeiter"]:
            stammdaten["mitarbeiter"].append(neuer_ma)
            save_stammdaten(stammdaten)
            st.rerun()

with st.sidebar.expander("🏗️ Globaler Projekt-Pool (Stammdaten)"):
    st.write("Alle hinterlegten Projekte:")
    for p in stammdaten.get("projekte", []):
        col_p_info, col_p_del = st.columns([4, 1])
        col_p_info.write(f"**{p['nummer']}** - {p['name']}")
        if col_p_del.button("🗑️", key=f"del_global_p_{p['nummer']}"):
            stammdaten["projekte"].remove(p)
            save_stammdaten(stammdaten)
            st.rerun()
    st.markdown("**Neues Projekt anlegen:**")
    neue_p_nr = st.text_input("Projektnummer (z.B. 2026-05):", key="add_p_num_input")
    neuer_p_name = st.text_input("Projektname:", key="add_p_name_input")
    if st.button("➕ Projekt in Stammdaten sichern"):
        if neue_p_nr and neue_p_name:
            if not any(p['nummer'] == neue_p_nr for p in stammdaten["projekte"]):
                stammdaten["projekte"].append({"nummer": neue_p_nr, "name": neuer_p_name})
                save_stammdaten(stammdaten)
                st.success("Projekt dauerhaft gespeichert!")
                st.rerun()
            else:
                st.error("Diese Projektnummer existiert bereits!")

st.sidebar.markdown("---")

with st.sidebar.expander("📅 Baustellen dieser Woche verwalten"):
    st.write("In dieser KW aktive Projekte:")
    for prj in list(data["projekte"]):
        col_prj_name, col_prj_del = st.columns([4, 1])
        col_prj_name.write(f"• {prj}")
        if col_prj_del.button("🗑️", key=f"del_prj_{prj}"):
            data["projekte"].remove(prj)
            if prj in data["einsatz"]:
                del data["einsatz"][prj]
            save_data(kw_auswahl, data)
            st.rerun()
    st.markdown("**Projekt aus Stammdaten hinzufügen:**")
    global_p_options = [f"{p['nummer']} - {p['name']}" for p in stammdaten.get("projekte", [])]
    available_p_options = [opt for opt in global_p_options if opt not in data["projekte"]]
    selected_p_to_add = st.selectbox("Suchen (Nummer/Name):", options=["-- Projekt auswählen --"] + available_p_options, key="search_select_project_to_kw")
    if st.button("➕ Zu dieser Woche hinzufügen"):
        if selected_p_to_add != "-- Projekt auswählen --":
            data["projekte"].append(selected_p_to_add)
            save_data(kw_auswahl, data)
            st.rerun()

if st.sidebar.button("🚪 Logout"):
    st.session_state.authenticated = False
    st.rerun()

# --- 5. HAUPTBEREICH & MODUS-AUSWAHL ---
col_title_logo, col_title_text = st.columns([1, 10])
with col_title_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=110)
with col_title_text:
    st.title(f"Einsatzplanung — {kw_auswahl} ({kw_datum_str})")

modus = st.radio("Ansicht wählen:", ["👀 Kompakte Wochenübersicht", "✍️ Planungs-Modus (Bearbeiten)"], horizontal=True)

belegte_mitarbeiter = {t["name"]: {} for t in WOCHENTAGE_DATEN}
for prj in data["projekte"]:
    for t in WOCHENTAGE_DATEN:
        tag = t["name"]
        implicit_einsatz = data["einsatz"].get(prj, {}).get(tag, {})
        if isinstance(implicit_einsatz, dict):
            eingeteilt = implicit_einsatz.get("mitarbeiter", [])
        else:
            eingeteilt = []
        for mitarbeiter in eingeteilt:
            if mitarbeiter not in belegte_mitarbeiter[tag]:
                belegte_mitarbeiter[tag][mitarbeiter] = []
            belegte_mitarbeiter[tag][mitarbeiter].append(prj)

# --- 6. MODUS A: KOMPAKTE WOCHENÜBERSICHT ---
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
        pdf_data = create_pdf(data, WOCHENTAGE_DATEN, kw_auswahl, kw_datum_str)
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
        
    html_table = "<table style='width:100%; border-collapse: collapse; font-family: sans-serif; font-size: 11px;'>"
    html_table += "<tr style='background-color: #f4f4f4;'><th style='border: 1px solid #ddd; padding: 5px 6px; text-align: left; font-size: 13px;'>Projekt / Baustelle</th>"
    for t in WOCHENTAGE_DATEN:
        html_table += f"<th style='border: 1px solid #ddd; padding: 5px 6px; text-align: left; width: 18%; font-size: 13px;'>{t['anzeige']}</th>"
    html_table += "</tr>"
    
    for prj in data["projekte"]:
        html_table += f"<tr><td style='border: 1px solid #ddd; padding: 5px 6px; font-weight: bold; background-color: #fafafa; font-size: 13px;'>{prj}</td>"
        for t in WOCHENTAGE_DATEN:
            tag = t["name"]
            implicit_einsatz = data["einsatz"].get(prj, {}).get(tag, {})
            if isinstance(implicit_einsatz, dict):
                arbeit = implicit_einsatz.get("arbeit", "—")
                mitarbeiter_list = implicit_einsatz.get("mitarbeiter", [])
            else:
                arbeit = "—"
                mitarbeiter_list = []
            if not arbeit or not arbeit.strip():
                arbeit = "—"
            mitarbeiter = ", ".join(mitarbeiter_list)
            
            html_table += f"<td style='border: 1px solid #ddd; padding: 5px 6px; vertical-align: top;'>"
            html_table += f"<div style='font-size: 11px; color: #444; margin-bottom: 3px;'>🛠️ {arbeit}</div>"
            if mitarbeiter:
                html_table += f"<div style='font-size: 11px; font-weight: 600; color: #111;'>👥 {mitarbeiter}</div>"
            html_table += "</td>"
        html_table += "</tr>"
        
    html_table += "<tr style='background-color: #fff0f0;'><td style='border: 1px solid #ddd; padding: 5px 6px; font-weight: bold; color: #c0392b; font-size: 13px;'>🛑 ABWESEND</td>"
    for t in WOCHENTAGE_DATEN:
        tag = t["name"]
        eff_abw = get_effective_absences(tag, t.get("date"), data)
        abw_liste = ", ".join(eff_abw)
        if not abw_liste:
            abw_liste = "<i>Niemand abwesend</i>"
        html_table += f"<td style='border: 1px solid #ddd; padding: 5px 6px; vertical-align: top; color: #c0392b; font-size: 11px;'>{abw_liste}</td>"
    html_table += "</tr>"
    html_table += "</table>"
    st.markdown(html_table, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🔍 Projekt-Historie (Gesamtzeitraum)")
    
    all_stored_projects = set()
    json_files = glob.glob("planung_*.json")
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
        selected_global_project = st.selectbox("Wähle ein Projekt aus, um dessen gesamte Historie anzuzeigen:", sorted_global_projects, key="global_project_history_filter")
        project_history = []
        for f in json_files:
            base = os.path.basename(f)
            kw_part = base.replace("planung_", "").replace(".json", "").replace("kw_", "").strip()
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
                            if isinstance(details, dict):
                                arbeit = details.get("arbeit", "").strip()
                                mitarbeiter_list = details.get("mitarbeiter", [])
                            else:
                                arbeit = ""
                                mitarbeiter_list = []
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
        project_history.sort(key=lambda x: x["datum_sort"])
        if project_history:
            hist_table = "<table style='width:100%; border-collapse: collapse; font-family: sans-serif; font-size: 11px; margin-top: 10px;'>"
            hist_table += "<tr style='background-color: #f4f4f4;'><th style='border: 1px solid #ddd; padding: 5px 6px; text-align: left; width: 25%; font-size: 13px;'>Datum / Kalenderwoche</th><th style='border: 1px solid #ddd; padding: 5px 6px; text-align: left; width: 45%; font-size: 13px;'>Durchgeführte Arbeiten</th><th style='border: 1px solid #ddd; padding: 5px 6px; text-align: left; width: 30%; font-size: 13px;'>Eingeteilte Mitarbeiter</th></tr>"
            for item in project_history:
                hist_table += f"<tr><td style='border: 1px solid #ddd; padding: 5px 6px; font-weight: bold; font-size: 13px;'>{item['anzeige_tag']}</td><td style='border: 1px solid #ddd; padding: 5px 6px;'>{item['arbeit']}</td><td style='border: 1px solid #ddd; padding: 5px 6px;'>{item['mitarbeiter']}</td></tr>"
            hist_table += "</table>"
            st.markdown(hist_table, unsafe_allow_html=True)
        else:
            st.info("Zu diesem Projekt wurden noch keine Arbeiten dokumentiert.")
    else:
        st.info("Keine Projektdaten auf dem Server gefunden.")

# --- 7. MODUS B: BEARBEITUNGS-MODUS ---
else:
    st.markdown("### Planungsdaten eintragen")
    st.markdown("#### 🔍 Schnellauswahl: Projekt zur aktuellen Woche hinzufügen")
    global_p_options = [f"{p['nummer']} - {p['name']}" for p in stammdaten.get("projekte", [])]
    available_p_options = [opt for opt in global_p_options if opt not in data["projekte"]]
    
    col_search_field, col_search_btn = st.columns([3, 1])
    with col_search_field:
        selected_p_main = st.selectbox("Projekt nach Nummer oder Name durchsuchen:", options=["-- Hier tippen zum Suchen --"] + available_p_options, key="main_search_select_project")
    with col_search_btn:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        if st.button("➕ Hinzufügen", key="btn_main_add_project", use_container_width=True):
            if selected_p_main != "-- Hier tippen zum Suchen --":
                data["projekte"].append(selected_p_main)
                save_data(kw_auswahl, data)
                st.rerun()

    st.markdown("---")

    konflikte_ganztag = []
    konflikte_halbtag = []
    
    for t in WOCHENTAGE_DATEN:
        tag = t["name"]
        tag_absences = {}
        for ma in data["abwesend"].get(tag, []):
            if ma in MITARBEITER_POOL:
                tag_absences[ma] = "Ganztägig"
        if t.get("date"):
            for entry in stammdaten.get("abwesenheiten", []):
                try:
                    if datetime.date.fromisoformat(entry["start"]) <= t["date"] <= datetime.date.fromisoformat(entry["ende"]):
                        ma = entry["mitarbeiter"]
                        if ma in MITARBEITER_POOL:
                            typ_raw = entry.get("typ", "Ganztägig")
                            if "Vormittags" in typ_raw:
                                tag_absences[ma] = "Vormittags"
                            elif "Nachmittags" in typ_raw:
                                tag_absences[ma] = "Nachmittags"
                            else:
                                tag_absences[ma] = "Ganztägig"
                except:
                    pass
                    
        for abw_mitarbeiter, typ in tag_absences.items():
            if abw_mitarbeiter in belegte_mitarbeiter[tag]:
                projekte_liste = ", ".join(belegte_mitarbeiter[tag][abw_mitarbeiter])
                if typ == "Ganztägig":
                    konflikte_ganztag.append(f"🛑 **{abw_mitarbeiter}** ist am **{t['anzeige']}** **ganztägig abwesend**, aber eingeteilt auf: {projekte_liste}")
                else:
                    konflikte_halbtag.append(f"⚠️ **{abw_mitarbeiter}** ist am **{t['anzeige']}** nur **{typ} abwesend** (Einteilung für andere Tageshälfte möglich!) auf: {projekte_liste}")
                    
    if konflikte_ganztag:
        for k in konflikte_ganztag:
            st.error(k)
    if konflikte_halbtag:
        for k in konflikte_halbtag:
            st.warning(k)

    for p_idx, prj in enumerate(data["projekte"]):
        with st.expander(f"🏗️ {prj}", expanded=True):
            cols = st.columns(5)
            for i, t in enumerate(WOCHENTAGE_DATEN):
                tag = t["name"]
                with cols[i]:
                    st.markdown(f"**{t['anzeige']}**")
                    implicit_einsatz = data["einsatz"].get(prj, {}).get(tag, {})
                    if isinstance(implicit_einsatz, dict):
                        def_arb = implicit_einsatz.get("arbeit", "")
                        def_mit = implicit_einsatz.get("mitarbeiter", [])
                    else:
                        def_arb = ""
                        def_mit = []
                    
                    safe_def_mit = [m for m in def_mit if m in MITARBEITER_POOL]
                    
                    arb_input = st.text_input("Arbeiten:", value=def_arb, key=f"arb_{prj}_{tag}_{kw_auswahl}_{p_idx}")
                    mit_input = st.multiselect("Mitarbeiter:", options=MITARBEITER_POOL, default=safe_def_mit, key=f"mit_{prj}_{tag}_{kw_auswahl}_{p_idx}")
                    
                    if prj not in data["einsatz"]:
                        data["einsatz"][prj] = {}
                    if tag not in data["einsatz"][prj]:
                        data["einsatz"][prj][tag] = {}
                    data["einsatz"][prj][tag]["arbeit"] = arb_input
                    data["einsatz"][prj][tag]["mitarbeiter"] = mit_input

    st.markdown("---")
    st.markdown("### 🛑 Abwesende Mitarbeiter verwalten")
    
    cols_abw = st.columns(5)
    for i, t in enumerate(WOCHENTAGE_DATEN):
        tag = t["name"]
        with cols_abw[i]:
            global_details = []
            if t.get("date"):
                for entry in stammdaten.get("abwesenheiten", []):
                    try:
                        if datetime.date.fromisoformat(entry["start"]) <= t["date"] <= datetime.date.fromisoformat(entry["ende"]):
                            typ_clean = entry.get("typ", "Ganztägig").split(" (")[0]
                            global_details.append(f"• {entry['mitarbeiter']} ({typ_clean})")
                    except:
                        pass
            if global_details:
                st.markdown("**Aus Stammdaten:**")
                for det in global_details:
                    st.markdown(f"<span style='color:#b91c1c; font-size:12px;'>{det}</span>", unsafe_allow_html=True)
            
            def_abw = list(data["abwesend"].get(tag, []))
            safe_def_abw = [m for m in def_abw if m in MITARBEITER_POOL]
            abw_input = st.multiselect(f"Zusätzlich abwesend am {tag}:", options=MITARBEITER_POOL, default=safe_def_abw, key=f"abw_{tag}_{kw_auswahl}")
            data["abwesend"][tag] = abw_input

    st.markdown("###")
    if st.button("💾 Alle Änderungen für diese Woche speichern", type="primary"):
        save_data(kw_auswahl, data)
        st.success(f"Die Planung für die {kw_auswahl} wurde erfolgreich gespeichert!")
        st.rerun()