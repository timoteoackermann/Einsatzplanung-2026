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
        except Exception:
            pass
            
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
            except Exception:
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
    except Exception:
        return ""

# --- POP-UP DIALOG ---
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
            except Exception:
                col_text.write("• Fehlerhaftes Datum")
                
            if col_del.button("🗑️", key=f"del_range_{ma_name}_{idx}"):
                stammdaten["abwesenheiten"].remove(abw)
                save_stammdaten(stammdaten)
                st.rerun()

# --- 2. MONATSKALENDER ---
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

# --- 3. WOCHENDATEN ---
def get_filename(kw):
    return f"planung_{kw.lower().replace(' ', '_')}.json"

def load_data(kw):
    filename = get_filename(kw)
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
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
    except Exception:
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
        except Exception:
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