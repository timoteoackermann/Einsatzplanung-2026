import streamlit as st
import os
import json
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# 1. Seiteneinstellungen für Streamlit
st.set_page_config(page_title="Einsatzplanung Ackermann Bau", page_icon="🏗️", layout="wide")

# 2. Passwort-Schutz ("Bauleitung2026")
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    
    if not st.session_state.authenticated:
        st.title("🏗️ Ackermann Bau — Login")
        password = st.text_input("Bitte Passwort eingeben:", type="password")
        if st.button("Einloggen"):
            if password == "Bauleitung2026":
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Falsches Passwort!")
        return False
    return True

# Wenn Passwort korrekt, App ausführen
if check_password():
    # Session State für Kalenderwoche und Jahr initialisieren
    if "kw" not in st.session_state:
        st.session_state.kw = 24
    if "jahr" not in st.session_state:
        st.session_state.jahr = 2026

    # Datei zur lokalen Speicherung der Daten
    DATA_FILE = "einsatzplanung_data.json"

    def load_data():
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_data(data):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    all_data = load_data()
    kw_str = str(st.session_state.kw)

    # Tage definieren
    days_list = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag"]
    
    # Struktur anlegen, falls für die KW noch nichts existiert
    if kw_str not in all_data:
        all_data[kw_str] = {day: {"arbeiten": "", "mitarbeiter": ""} for day in days_list}

    # Haupt-Überschrift (Sauberes Format: KW XX 2026 ohne Klammern)
    st.title(f"🏗️ Einsatzplanung — KW {st.session_state.kw} {st.session_state.jahr}")

    # Ansichtsmodus-Auswahl
    st.write("Ansicht wählen:")
    mode = st.radio(
        "Ansicht",
        options=["👀 Kompakte Wochenübersicht", "📝 Planungs-Modus (Bearbeiten)"],
        label_visibility="collapsed"
    )

    # Wochen-Navigation
    col_nav_prev, col_nav_space, col_nav_next = st.columns([1, 4, 1])
    with col_nav_prev:
        if st.button("⬅️ Vorige Woche"):
            if st.session_state.kw > 1:
                st.session_state.kw -= 1
                st.rerun()
    with col_nav_next:
        if st.button("Nächste Woche ➡️"):
            if st.session_state.kw < 52:
                st.session_state.kw += 1
                st.rerun()

    st.markdown("---")

    # --- MODUS 1: PLANUNGS-MODUS (BEARBEITEN) ---
    if mode == "📝 Planungs-Modus (Bearbeiten)":
        st.subheader(f"Bearbeitungs-Modus für die KW {st.session_state.kw}")
        
        for day in days_list:
            st.markdown(f"#### 📅 {day}")
            col1, col2 = st.columns(2)
            with col1:
                all_data[kw_str][day]["arbeiten"] = st.text_area(
                    f"Arbeiten am {day}",
                    value=all_data[kw_str][day]["arbeiten"],
                    key=f"arb_{day}",
                    height=120
                )
            with col2:
                all_data[kw_str][day]["mitarbeiter"] = st.text_area(
                    f"Mitarbeiter am {day}",
                    value=all_data[kw_str][day]["mitarbeiter"],
                    key=f"mit_{day}",
                    height=120
                )
            st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("💾 Gesamten Wochenplan speichern", type="primary"):
            save_data(all_data)
            st.success("Planung erfolgreich gespeichert!")
            st.rerun()

    # --- MODUS 2: KOMPAKTE WOCHENÜBERSICHT ---
    else:
        st.subheader("Gesamttübersicht der Woche")
        
        for day in days_list:
            arb_text = all_data[kw_str][day]["arbeiten"]
            mit_text = all_data[kw_str][day]["mitarbeiter"]
            
            if arb_text or mit_text:
                st.markdown(f"### 📅 {day}")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**Arbeiten:**")
                    st.info(arb_text if arb_text else "Keine Arbeiten eingetragen")
                with col2:
                    st.markdown("**Mitarbeiter:**")
                    st.success(mit_text if mit_text else "Keine Mitarbeiter zugewiesen")
                st.markdown("<br>", unsafe_allow_html=True)

        # --- PDF EXPORT SEKTION ---
        st.markdown("---")
        
        def generate_pdf(kw, jahr, data):
            pdf_filename = f"Einsatzplanung_KW_{kw}_{jahr}.pdf"
            
            # PDF im Querformat (landscape) aufbauen
            doc = SimpleDocTemplate(
                pdf_filename,
                pagesize=landscape(A4),
                rightMargin=30,
                leftMargin=30,
                topMargin=30,
                bottomMargin=30
            )
            
            styles = getSampleStyleSheet()
            
            # Eigene Stile für das Japandi-Design (Minimalistisch, edles Dunkelblau/Anthrazit)
            title_style = ParagraphStyle(
                'PDFTitle',
                parent=styles['Heading1'],
                fontName='Helvetica-Bold',
                fontSize=22,
                textColor=colors.HexColor('#1A2530'),
                spaceAfter=5
            )
            
            company_style = ParagraphStyle(
                'CompanyHeader',
                fontName='Helvetica-Bold',
                fontSize=18,
                textColor=colors.HexColor('#1A2530'),
                alignment=2  # Rechtsbündig
            )
            
            day_header_style = ParagraphStyle(
                'DayHeader',
                fontName='Helvetica-Bold',
                fontSize=12,
                textColor=colors.white
            )
            
            sub_header_style = ParagraphStyle(
                'SubHeader',
                fontName='Helvetica-Bold',
                fontSize=10,
                textColor=colors.HexColor('#2C3E50')
            )
            
            cell_style = ParagraphStyle(
                'CellText',
                fontName='Helvetica',
                fontSize=10,
                textColor=colors.HexColor('#333333'),
                leading=14
            )
            
            story = []
            
            # --- HEADER-ZEILE (Titel links, Firma & transparentes Logo rechts) ---
            title_paragraph = Paragraph(f"Einsatzplanung — KW {kw} {jahr}", title_style)
            
            logo_img = None
            if os.path.exists("logo.png"):
                try:
                    logo_img = Image("logo.png", width=35, height=35)
                except:
                    pass
            
            if logo_img:
                # Tabelle rechts: Text "Ackermann Bau" direkt neben dem Logo platziert
                header_right_content = Table(
                    [[Paragraph("Ackermann Bau", company_style), logo_img]],
                    colWidths=[150, 45]
                )
                header_right_content.setStyle(TableStyle([
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('ALIGN', (0,0), (-1,-1), 'RIGHT'),
                    ('LEFTPADDING', (0,0), (-1,-1), 0),
                    ('RIGHTPADDING', (0,0), (-1,-1), 0),
                ]))
            else:
                header_right_content = Paragraph("Ackermann Bau", company_style)
            
            # Große Header-Tabelle über die gesamte Breite
            header_table = Table([[title_paragraph, header_right_content]], colWidths=[520, 220])
            header_table.setStyle(TableStyle([
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ]))
            story.append(header_table)
            story.append(Spacer(1, 15))
            
            # --- WOCHENPLAN-TABELLEN (Nebeneinander-Spalten) ---
            for day in ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag"]:
                arb_content = data[day]["arbeiten"].strip().replace("\n", "<br/>")
                mit_content = data[day]["mitarbeiter"].strip().replace("\n", "<br/>")
                
                # Nur Tage mit Inhalt anzeigen
                if arb_content or mit_content:
                    # Farbiger Balken für den Wochentag
                    day_title_table = Table([[Paragraph(day, day_header_style)]], colWidths=[740])
                    day_title_table.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#2C3E50')),
                        ('TOPPADDING', (0,0), (-1,-1), 6),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                        ('LEFTPADDING', (0,0), (-1,-1), 8),
                    ]))
                    
                    # 2 getrennte Spalten nebeneinander ("Arbeiten" & "Mitarbeiter")
                    p_head_arb = Paragraph("Arbeiten", sub_header_style)
                    p_head_mit = Paragraph("Mitarbeiter", sub_header_style)
                    p_text_arb = Paragraph(arb_content if arb_content else "-", cell_style)
                    p_text_mit = Paragraph(mit_content if mit_content else "-", cell_style)
                    
                    day_content_table = Table(
                        [
                            [p_head_arb, p_head_mit],
                            [p_text_arb, p_text_mit]
                        ],
                        colWidths=[370, 370]
                    )
                    day_content_table.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (1,0), colors.HexColor('#ECF0F1')), # Helle Titelzeile
                        ('TOPPADDING', (0,0), (-1,-1), 6),
                        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                        ('LEFTPADDING', (0,0), (-1,-1), 8),
                        ('RIGHTPADDING', (0,0), (-1,-1), 8),
                        ('VALIGN', (0,0), (-1,-1), 'TOP'),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#BDC3C7')), # Dezent graue Rahmenlinien
                    ]))
                    
                    # KeepTogether verhindert unschöne Seitenumbrüche mitten im Tag
                    story.append(KeepTogether([day_title_table, day_content_table]))
                    story.append(Spacer(1, 12))
            
            doc.build(story)
            return pdf_filename

        # Download-Button anzeigen
        if st.button("📥 Diese Woche als PDF exportieren"):
            current_week_data = all_data[kw_str]
            pdf_file = generate_pdf(st.session_state.kw, st.session_state.jahr, current_week_data)
            
            if os.path.exists(pdf_file):
                with open(pdf_file, "rb") as f:
                    st.download_button(
                        label="📄 PDF-Datei herunterladen",
                        data=f,
                        file_name=pdf_file,
                        mime="application/pdf"
                    )
            else:
                st.error("Fehler bei der PDF-Erstellung.")