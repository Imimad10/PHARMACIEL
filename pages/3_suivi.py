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

if "current_user" not in st.session_state or st.session_state.current_user is None:
    st.warning("Veuillez vous connecter depuis la page principale.")
    st.stop()

# --- FONCTIONS ---
def clean_frigo_data(df):
    if 'Température' in df.columns:
        df['Température'] = pd.to_numeric(df['Température'], errors='coerce')
        df.loc[(df['Température'] >= 2.0) & (df['Température'] <= 8.0), 'Statut'] = 'OK'
        df.loc[(df['Température'] < 2.0) | (df['Température'] > 8.0), 'Statut'] = 'ALERTE'
    if 'Type' in df.columns:
        df['Type'] = df['Type'].replace('Relevé Standard', 'Plage idéale :+2°C+8°C')
    if 'Chambre' not in df.columns:
        df['Chambre'] = CHAMBRES[0] # Par défaut CF1 pour l'ancien historique
    return df

def generer_pdf(df, chambre_name):
    pdf = FPDF()
    pdf.add_page()
    
    # 1. Logo
    if os.path.exists("logo.png"):
        try: pdf.image("logo.png", x=10, y=8, w=30)
        except: pass
            
    # 2. En-tête
    pdf.set_font("Arial", 'B', 15)
    pdf.cell(0, 10, "DARPHARM SOLUTION", 0, 1, 'C')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, f"RAPPORT DE SUIVI : {chambre_name.upper()}", 0, 1, 'C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 6, "(Plage cible : +2 C a +8 C)", 0, 1, 'C')
    
    pdf.set_font("Arial", 'I', 9)
    pdf.cell(0, 6, f"Extrait le : {datetime.now().strftime('%d/%m/%Y a %H:%M')}", 0, 1, 'C')
    pdf.ln(8)
    
    # 3. KPIs
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
    
    # 4. Tableau
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font("Arial", 'B', 8)
    w = [25, 15, 20, 20, 60, 50]
    cols = ["Date", "Heure", "Temp (C)", "Statut", "Motif", "Agent"]
    for i, head in enumerate(cols):
        pdf.cell(w[i], 7, head, border=1, fill=True, align='C')
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
    is_gsheets = False
    error_msg = None
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="Suivi_Frigo", ttl=0).dropna(how="all")
        is_gsheets = True
    except Exception as e:
        error_msg = str(e)
        if os.path.isfile(DATA_FILE):
            df = pd.read_csv(DATA_FILE)
    
    if not df.empty:
        df = clean_frigo_data(df)
    return df, is_gsheets, error_msg

def save_data(data):
    df_new = pd.DataFrame([data])
    gsheets_ok = False
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        try:
            existing = conn.read(worksheet="Suivi_Frigo", ttl=0).dropna(how="all")
            updated = pd.concat([existing, df_new], ignore_index=True)
        except: updated = df_new
        conn.update(worksheet="Suivi_Frigo", data=updated)
        gsheets_ok = True
    except: pass

    # Local
    file_exists = os.path.isfile(DATA_FILE)
    df_new.to_csv(DATA_FILE, mode='a', header=not file_exists, index=False)
    
    log_action(data['Agent'], f"T° {data['Chambre']}: {data['Température']}°C", "Suivi Frigo")
    if data['Statut'] == "ALERTE":
        st.error(f"🚨 ALERTE {data['Chambre']} : {data['Température']}°C !")
    else:
        st.success(f"✅ Enregistré pour {data['Chambre']}")

# --- UI INTERFACE ---
st.title(f"🌡️ Suivi Températures - {st.session_state.current_user['username']}")

tabs = st.tabs(["📝 Saisie CF1", "📝 Saisie CF2", "📊 Dashboard CF1", "📊 Dashboard CF2", "⚙️ Admin"])

# --- LOGIQUE SAISIE (REUTILISABLE) ---
def render_saisie(chambre_name):
    st.subheader(f"Saisie : {chambre_name}")
    if st.button(f"🚀 Rapide (OK 4°C) - {chambre_name}", use_container_width=True):
        save_data({
            "Date": datetime.now().strftime("%d/%m/%Y"), "Heure": datetime.now().strftime("%H:%M"),
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
                "Date": datetime.now().strftime("%d/%m/%Y"), "Heure": datetime.now().strftime("%H:%M"),
                "Température": t, "Agent": st.session_state.current_user['username'],
                "Statut": "OK" if 2.0 <= t <= 8.0 else "ALERTE", "Commentaire": comm, "Type": motif,
                "Chambre": chambre_name
            })
            st.rerun()

with tabs[0]: render_saisie(CHAMBRES[0])
with tabs[1]: render_saisie(CHAMBRES[1])

# --- LOGIQUE DASHBOARD ---
def render_dashboard(chambre_name, df_all):
    df = df_all[df_all['Chambre'] == chambre_name].copy()
    if not df.empty:
        df['Timestamp'] = pd.to_datetime(df['Date'] + ' ' + df['Heure'], format="%d/%m/%Y %H:%M", errors='coerce')
        c1, c2, c3 = st.columns(3)
        last_t = df.iloc[-1]['Température']
        c1.metric("Dernier Relevé", f"{last_t} °C")
        c2.metric("Moyenne", f"{df['Température'].mean():.1f} °C")
        c3.metric("Alertes", len(df[df['Statut'] == 'ALERTE']))
        
        st.plotly_chart(px.line(df.tail(50), x="Timestamp", y="Température", markers=True, 
                                title=f"Historique {chambre_name}", color_discrete_sequence=['#00CC96']), use_container_width=True)
        
        # Export
        pdf = generer_pdf(df, chambre_name)
        st.download_button(f"📥 Rapport PDF {chambre_name}", data=pdf, file_name=f"Rapport_{chambre_name.replace(' ','_')}.pdf")
        
        # IA
        if is_ia_enabled():
            with st.expander("🤖 Analyse IA Maintenance"):
                if st.button(f"✨ Analyser la santé : {chambre_name}"):
                    last_30 = df.tail(30)['Température'].tolist()
                    prompt = f"Analyse ces 30 relevés de la chambre froide '{chambre_name}' : {last_30}. Risque de panne ? Tendance ? Conseil court."
                    st.info(ask_ai(prompt))
                    
        st.write("### Historique complet")
        st.dataframe(df.sort_index(ascending=False), use_container_width=True)
    else:
        st.info(f"Aucune donnée pour {chambre_name}")

df_all, is_gs, _ = get_data()
with tabs[2]: render_dashboard(CHAMBRES[0], df_all)
with tabs[3]: render_dashboard(CHAMBRES[1], df_all)

# --- ADMIN ---
with tabs[4]:
    if st.session_state.current_user.get('role') == 'Admin':
        st.subheader("🛠️ Gestion Administrative")
        # Edition directe
        st.write("Modification globale de la base de données :")
        df_edit = st.data_editor(df_all, use_container_width=True, num_rows="dynamic")
        if st.button("💾 Sauvegarder les modifications"):
            try:
                if is_gs:
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    conn.update(worksheet="Suivi_Frigo", data=df_edit)
                df_edit.to_csv(DATA_FILE, index=False)
                st.success("Base de données mise à jour !")
                st.rerun()
            except Exception as e: st.error(f"Erreur: {e}")
            
        st.divider()
        if st.button("🚀 Migrer Local -> Google Sheets"):
            try:
                df_local = pd.read_csv(DATA_FILE)
                conn = st.connection("gsheets", type=GSheetsConnection)
                conn.update(worksheet="Suivi_Frigo", data=df_local)
                st.success("Migration terminée !")
            except Exception as e: st.error(f"Erreur: {e}")
    else:
        st.warning("Accès réservé aux administrateurs.")
