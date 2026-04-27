import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import calendar
import os
import plotly.express as px
from fpdf import FPDF
import time

# --- CONFIGURATION ---
st.set_page_config(page_title="Pharmaciel - Suivi Frigo", layout="wide")
DATA_FILE = "suivi_data.csv"

# --- UTILISATEURS ---
USERS = {
    "Ayoub": "ayoub2026", "Islem": "islem2026", "Seif": "seif2026",
    "Rami (Chef Dépôt)": "rami2026", "Imad (Responsable)": "admin_imad"
}

if "user_authenticated" not in st.session_state:
    st.session_state.user_authenticated = None

# --- AUTHENTIFICATION ---
if st.session_state.user_authenticated is None:
    st.title("🔐 Accès Pharmaciel")
    u = st.selectbox("Utilisateur", list(USERS.keys()))
    p = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        if p == USERS[u]:
            st.session_state.user_authenticated = u
            st.rerun()
        else: st.error("Identifiants incorrects")
    st.stop()

# --- FONCTIONS ---
def generer_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "PHARMACIEL - RAPPORT MENSUEL", 0, 1, 'C')
    pdf.ln(10)
    pdf.set_font("Arial", size=9)
    for _, row in df.iterrows():
        texte = f"{row['Date']} {row['Heure']} | {row['Type']} | T°: {row['Température']}°C | Agent: {row['Agent']}"
        pdf.cell(0, 7, texte, 0, 1)
    # Conversion en bytes corrigée ici
    return bytes(pdf.output(dest='S'))

def save_data(data):
    df_to_save = pd.DataFrame([data])
    # Création du header uniquement si le fichier n'existe pas
    file_exists = os.path.isfile(DATA_FILE)
    df_to_save.to_csv(DATA_FILE, mode='a', header=not file_exists, index=False)
    st.success("✅ Donnée enregistrée !")

# --- INTERFACE ---
st.title(f"🌡️ Pharmaciel - {st.session_state.user_authenticated}")

tab_saisie, tab_data = st.tabs(["📝 Saisie terrain", "📊 Tableau de bord"])

with tab_saisie:
    st.subheader("Nouvelle saisie")
    if st.button("🚀 Saisie Rapide (OK - Standard)", use_container_width=True):
        save_data({
            "Date": datetime.now().strftime("%d/%m/%Y"), "Heure": datetime.now().strftime("%H:%M"),
            "Température": 4.0, "Agent": st.session_state.user_authenticated,
            "Statut": "OK", "Commentaire": "Rapide", "Type": "Relevé Standard"
        })
        time.sleep(0.5); st.rerun()

    with st.form("form_saisie", clear_on_submit=True):
        t = st.number_input("Température (°C)", min_value=-20.0, max_value=30.0, value=4.0, step=0.1)
        type_releve = st.selectbox("Motif", ["Relevé Standard", "Remplissage / Arrivage", "Nettoyage", "Autre"])
        comm = st.text_input("Commentaire")
        if st.form_submit_button("Enregistrer", use_container_width=True):
            save_data({
                "Date": datetime.now().strftime("%d/%m/%Y"), "Heure": datetime.now().strftime("%H:%M"),
                "Température": t, "Agent": st.session_state.user_authenticated,
                "Statut": "OK" if t <= 5.0 else "ALERTE", "Commentaire": comm, "Type": type_releve
            })
            time.sleep(0.5); st.rerun()

with tab_data:
    if os.path.isfile(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        
        # Création d'une colonne Timestamp pour le graphe
        df['Timestamp'] = pd.to_datetime(df['Date'] + ' ' + df['Heure'], dayfirst=True)
        
        # KPIs
        c1, c2, c3 = st.columns(3)
        c1.metric("Dernière T°", f"{df.iloc[-1]['Température']} °C")
        c2.metric("Moyenne", f"{df['Température'].mean():.1f} °C")
        c3.metric("Alertes", len(df[df['Statut'] == 'ALERTE']))
        
        # Graphique chronologique
        st.plotly_chart(px.line(df.tail(50), x="Timestamp", y="Température", markers=True, title="Tendance T°"), use_container_width=True)
        
        # Export PDF
        pdf_data = generer_pdf(df)
        st.download_button("📥 Télécharger Rapport PDF", data=pdf_data, file_name="Rapport_Frigo.pdf", mime="application/pdf")
        
        st.dataframe(df.sort_index(ascending=False), use_container_width=True)
    else:
        st.info("Aucune donnée disponible.")
