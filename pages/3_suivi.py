import streamlit as st
import pandas as pd
from datetime import datetime
import os
import plotly.express as px
from fpdf import FPDF
from utils import log_action
from streamlit_gsheets import GSheetsConnection
from utils_ia import ask_ai, is_ia_enabled

# --- CONFIGURATION ---
DATA_FILE = "suivi_data.csv"
CHAMBRES = ["Chambre Froide 1", "Chambre Froide 2"]

# Initialisation du fuseau horaire dans le session_state
if "tz_offset" not in st.session_state:
    st.session_state.tz_offset = 1 # Défaut GMT+1

if "current_user" not in st.session_state or st.session_state.current_user is None:
    st.warning("Veuillez vous connecter depuis la page principale.")
    st.stop()

# --- FONCTIONS TEMPORELLES ---
from datetime import timedelta
def get_now():
    return datetime.utcnow() + timedelta(hours=st.session_state.tz_offset)

# --- FONCTIONS ---
def clean_frigo_data(df):
    if 'Température' in df.columns:
        df['Température'] = pd.to_numeric(df['Température'], errors='coerce')
        df.loc[(df['Température'] >= 2.0) & (df['Température'] <= 8.0), 'Statut'] = 'OK'
        df.loc[(df['Température'] < 2.0) | (df['Température'] > 8.0), 'Statut'] = 'ALERTE'
    if 'Type' in df.columns:
        df['Type'] = df['Type'].replace('Relevé Standard', 'Plage idéale :+2°C+8°C')
    if 'Chambre' not in df.columns:
        df['Chambre'] = CHAMBRES[0]
    return df

def generer_pdf(df, chambre_name):
    pdf = FPDF()
    pdf.add_page()
    if os.path.exists("logo.png"):
        try: pdf.image("logo.png", x=10, y=8, w=30)
        except: pass
    pdf.set_font("Arial", 'B', 15)
    pdf.cell(0, 10, "DARPHARM SOLUTION", 0, 1, 'C')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, f"RAPPORT DE SUIVI : {chambre_name.upper()}", 0, 1, 'C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 6, "(Plage cible : +2 C a +8 C)", 0, 1, 'C')
    pdf.set_font("Arial", 'I', 9)
    pdf.cell(0, 6, f"Extrait le : {get_now().strftime('%d/%m/%Y a %H:%M')}", 0, 1, 'C')
    pdf.ln(8)
    
    nb_releves = len(df)
    moyenne = df['Température'].mean() if nb_releves > 0 else 0
    alertes = len(df[df['Statut'] == 'ALERTE'])
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 6, "Resume des releves :", 0, 1)
    pdf.set_font("Arial", '', 9)
    pdf.cell(0, 5, f"- Total des releves : {nb_releves}", 0, 1)
    pdf.cell(0, 5, f"- Temperature moyenne : {moyenne:.1f} C", 0, 1)
    pdf.cell(0, 5, f"- Nombre d'alertes : {alertes}", 0, 1)
    pdf.ln(6)
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font("Arial", 'B', 8)
    w = [25, 15, 20, 20, 60, 50]
    cols = ["Date", "Heure", "Temp (C)", "Statut", "Motif", "Agent"]
    for i, head in enumerate(cols): pdf.cell(w[i], 7, head, border=1, fill=True, align='C')
    pdf.ln()
    pdf.set_font("Arial", '', 8)
    for _, row in df.iterrows():
        if str(row['Statut']) == "ALERTE": pdf.set_text_color(200, 0, 0)
        else: pdf.set_text_color(0, 100, 0)
        pdf.cell(w[0], 6, str(row['Date']), border=1, align='C')
        pdf.cell(w[1], 6, str(row['Heure']), border=1, align='C')
        pdf.cell(w[2], 6, f"{row['Température']} C", border=1, align='C')
        pdf.cell(w[3], 6, str(row['Statut']), border=1, align='C')
        pdf.set_text_color(0, 0, 0)
        pdf.cell(w[4], 6, str(row['Type'])[:35], border=1)
        pdf.cell(w[5], 6, str(row['Agent'])[:25], border=1, ln=1)
    return pdf.output(dest='S').encode('latin-1', 'replace')

def get_data():
    df = pd.DataFrame()
    conn_status = "red"
    error_msg = None
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="Suivi_Frigo", ttl=0).dropna(how="all")
        conn_status = "green"
    except Exception as e:
        error_msg = str(e)
        conn_status = "orange"
        if os.path.isfile(DATA_FILE):
            df = pd.read_csv(DATA_FILE)
    if not df.empty:
        df = clean_frigo_data(df)
    return df, conn_status, error_msg

def save_data(data):
    df_new = pd.DataFrame([data])
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        try:
            existing = conn.read(worksheet="Suivi_Frigo", ttl=0).dropna(how="all")
            updated = pd.concat([existing, df_new], ignore_index=True)
        except: updated = df_new
        conn.update(worksheet="Suivi_Frigo", data=updated)
    except: pass
    file_exists = os.path.isfile(DATA_FILE)
    df_new.to_csv(DATA_FILE, mode='a', header=not file_exists, index=False)
    log_action(data['Agent'], f"T° {data['Chambre']}: {data['Température']}°C", "Suivi Frigo")
    if data['Statut'] == "ALERTE":
        st.error(f"🚨 ALERTE {data['Chambre']} : {data['Température']}°C !")
    else:
        st.success(f"✅ Enregistré pour {data['Chambre']}")

# --- UI INTERFACE ---
st.title(f"🌡️ Suivi Températures - {st.session_state.current_user['username']}")

# Indicateur de Connexion
df_all, conn_status, error_msg = get_data()
if conn_status == "green": st.sidebar.success("📡 Connecté (GSheets Online)")
elif conn_status == "orange": st.sidebar.warning("💾 Mode Local (GSheets Offline)")
else: st.sidebar.error("❌ Erreur Connexion")

tabs = st.tabs(["📝 Saisie CF1", "📝 Saisie CF2", "📊 Dashboard CF1", "📊 Dashboard CF2", "📋 Fiche Manuelle", "⚙️ Admin"])

# --- SAISIE ---
def render_saisie(chambre_name):
    st.subheader(f"Saisie : {chambre_name}")
    now = get_now()
    if st.button(f"🚀 Rapide (OK 4°C) - {chambre_name}", use_container_width=True):
        save_data({
            "Date": now.strftime("%d/%m/%Y"), "Heure": now.strftime("%H:%M"),
            "Température": 4.0, "Agent": st.session_state.current_user['username'],
            "Statut": "OK", "Commentaire": "Rapide", "Type": "Plage idéale :+2°C+8°C",
            "Chambre": chambre_name
        })
        st.rerun()

    with st.form(f"form_{chambre_name.replace(' ','_')}", clear_on_submit=True):
        t = st.number_input("Température (°C)", min_value=-20.0, max_value=30.0, value=4.0, step=0.1)
        motif = st.selectbox("Motif", ["Plage idéale :+2°C+8°C", "Arrivage", "Nettoyage", "Alerte technique"])
        comm = st.text_input("Commentaire")
        if st.form_submit_button("Enregistrer", use_container_width=True):
            save_data({
                "Date": now.strftime("%d/%m/%Y"), "Heure": now.strftime("%H:%M"),
                "Température": t, "Agent": st.session_state.current_user['username'],
                "Statut": "OK" if 2.0 <= t <= 8.0 else "ALERTE", "Commentaire": comm, "Type": motif,
                "Chambre": chambre_name
            })
            st.rerun()

with tabs[0]: render_saisie(CHAMBRES[0])
with tabs[1]: render_saisie(CHAMBRES[1])

# --- DASHBOARD ---
def render_dashboard(chambre_name, df_all):
    df = df_all[df_all['Chambre'] == chambre_name].copy()
    if not df.empty:
        df['Timestamp'] = pd.to_datetime(df['Date'] + ' ' + df['Heure'], format="%d/%m/%Y %H:%M", errors='coerce')
        last_entry = df.iloc[-1]
        if last_entry['Statut'] == "ALERTE":
            st.error(f"🚨 ATTENTION : La dernière température de la {chambre_name} ({last_entry['Température']}°C) est HORS PLAGE !")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Dernier Relevé", f"{last_entry['Température']} °C")
        c2.metric("Moyenne", f"{df['Température'].mean():.1f} °C")
        conformite = (len(df[df['Statut'] == 'OK']) / len(df)) * 100 if len(df) > 0 else 0
        c3.metric("Conformité", f"{conformite:.1f} %")
        c4.metric("Alertes", len(df[df['Statut'] == 'ALERTE']))
        st.plotly_chart(px.line(df.tail(50), x="Timestamp", y="Température", markers=True, title=f"Historique {chambre_name}"), use_container_width=True)
        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            pdf = generer_pdf(df, chambre_name)
            st.download_button(f"📥 Rapport PDF {chambre_name}", data=pdf, file_name=f"Rapport_{chambre_name}.pdf", use_container_width=True)
        with col_exp2:
            if is_ia_enabled():
                if st.button(f"🤖 IA Analyse : {chambre_name}", use_container_width=True):
                    last_30 = df.tail(30)['Température'].tolist()
                    st.info(ask_ai(f"Analyse ces relevés pour {chambre_name} : {last_30}"))
        st.dataframe(df.sort_index(ascending=False), use_container_width=True)
    else:
        st.info(f"Aucune donnée pour {chambre_name}")

with tabs[2]: render_dashboard(CHAMBRES[0], df_all)
with tabs[3]: render_dashboard(CHAMBRES[1], df_all)

# --- ONGLET 4 : FICHE MANUELLE ---
with tabs[4]:
    st.subheader("📋 Génération de Fiche de Relevés Manuels")
    st.write("Générez un tableau vierge à imprimer pour vos relevés au stylo.")
    col_f1, col_f2 = st.columns(2)
    mois_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    mois_sel = col_f1.selectbox("Mois", range(1, 13), format_func=lambda x: mois_noms[x-1], index=get_now().month - 1)
    annee_sel = col_f2.number_input("Année", value=get_now().year, step=1)
    room_fiche = st.selectbox("Chambre Froide concernée", CHAMBRES)
    if st.button("📄 Générer la fiche PDF", use_container_width=True):
        import calendar
        num_days = calendar.monthrange(annee_sel, mois_sel)[1]
        jours_valides = [datetime(annee_sel, mois_sel, d) for d in range(1, num_days + 1)]
        jours_valides = [d.strftime("%d/%m/%Y") for d in jours_valides if d.weekday() not in [4, 5]]
        pdf_f = FPDF()
        pdf_f.add_page()
        pdf_f.set_font("Arial", 'B', 14)
        pdf_f.cell(0, 10, f"FICHE DE SUIVI DES TEMPERATURES ET HUMIDITE", 0, 1, 'C')
        pdf_f.set_font("Arial", 'B', 11)
        pdf_f.cell(0, 8, f"{room_fiche.upper()} - {mois_noms[mois_sel-1]} {annee_sel}", 0, 1, 'C')
        pdf_f.ln(5)
        pdf_f.set_font("Arial", 'B', 9)
        pdf_f.set_fill_color(240, 240, 240)
        h_cell = 8
        w_cols = [35, 25, 30, 30, 70]
        headers = ["Date", "Heure", "Temp (C)", "Humidite (%)", "Remarques"]
        for i, h in enumerate(headers): pdf_f.cell(w_cols[i], h_cell, h, border=1, fill=True, align='C')
        pdf_f.ln()
        pdf_f.set_font("Arial", '', 9)
        for d_str in jours_valides:
            pdf_f.cell(w_cols[0], h_cell, d_str, border=1, align='C')
            pdf_f.cell(w_cols[1], h_cell, "", border=1)
            pdf_f.cell(w_cols[2], h_cell, "", border=1)
            pdf_f.cell(w_cols[3], h_cell, "", border=1)
            pdf_f.cell(w_cols[4], h_cell, "", border=1, ln=1)
        st.download_button("📥 Télécharger la fiche PDF", data=pdf_f.output(dest='S').encode('latin-1'), file_name=f"Fiche_{mois_noms[mois_sel-1]}.pdf", type="primary")

# --- ADMIN ---
with tabs[5]:
    if st.session_state.current_user.get('role') == 'Admin':
        st.subheader("⚙️ Paramètres Système")
        st.session_state.tz_offset = st.number_input("Fuseau Horaire (GMT Offset)", value=st.session_state.tz_offset, step=1)
        st.caption(f"Heure actuelle : {get_now().strftime('%H:%M:%S')}")
        st.divider()
        st.subheader("🛠️ Gestion Administrative")
        df_edit = st.data_editor(df_all, use_container_width=True, num_rows="dynamic")
        if st.button("💾 Sauvegarder"):
            try:
                if conn_status == "green":
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    conn.update(worksheet="Suivi_Frigo", data=df_edit)
                df_edit.to_csv(DATA_FILE, index=False)
                st.success("Base de données mise à jour !")
                st.rerun()
            except Exception as e: st.error(f"Erreur: {e}")
        if st.button("🚀 Migrer vers GSheets"):
            try:
                df_l = pd.read_csv(DATA_FILE)
                conn = st.connection("gsheets", type=GSheetsConnection)
                conn.update(worksheet="Suivi_Frigo", data=df_l)
                st.success("Migration réussie !")
            except Exception as e: st.error(f"Erreur: {e}")
    else:
        st.warning("Accès restreint.")
