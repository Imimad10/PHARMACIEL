import streamlit as st
import pandas as pd
from datetime import datetime
import os
import plotly.express as px
from fpdf import FPDF
from utils import log_action

# --- CONFIGURATION ---
# st.set_page_config(page_title="Darpharm Solution - Suivi Frigo", layout="wide")
DATA_FILE = "suivi_data.csv"

if "current_user" not in st.session_state or st.session_state.current_user is None:
    st.warning("Veuillez vous connecter depuis la page principale.")
    st.stop()


# --- FONCTIONS ---
def clean_frigo_data(df):
    if 'Température' in df.columns:
        df.loc[(df['Température'] >= 2.0) & (df['Température'] <= 8.0), 'Statut'] = 'OK'
        df.loc[(df['Température'] < 2.0) | (df['Température'] > 8.0), 'Statut'] = 'ALERTE'
    if 'Type' in df.columns:
        df['Type'] = df['Type'].replace('Relevé Standard', 'Plage idéale :+2°C+8°C')
    return df

def generer_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "DARPHARM SOLUTION - RAPPORT MENSUEL", 0, 1, 'C')
    pdf.ln(10)
    pdf.set_font("Arial", size=9)
    for _, row in df.iterrows():
        texte = f"{row['Date']} {row['Heure']} | {row['Type']} | T°: {row['Température']}°C | Agent: {row['Agent']}"
        pdf.cell(0, 7, texte, 0, 1)
    # Conversion en bytes corrigée ici
    return pdf.output(dest='S').encode('latin-1', 'replace')

def save_data(data):
    df_to_save = pd.DataFrame([data])
    # Création du header uniquement si le fichier n'existe pas
    file_exists = os.path.isfile(DATA_FILE)
    df_to_save.to_csv(DATA_FILE, mode='a', header=not file_exists, index=False)
    
    # Historisation et Alerte
    log_action(data['Agent'], f"Saisie température: {data['Température']}°C ({data['Statut']})", "Suivi Frigo")
    if data['Statut'] == "ALERTE":
        st.error(f"⚠️ ALERTE : La température ({data['Température']}°C) est en dehors de la plage idéale (+2°C à +8°C) !")
    else:
        st.success("✅ Donnée enregistrée !")

# --- INTERFACE ---
st.title(f"🌡️ Darpharm Solution - {st.session_state.current_user['username']}")

tab_names = ["📝 Saisie terrain", "📊 Tableau de bord"]
is_admin = st.session_state.current_user.get('role') == 'Admin'
if is_admin:
    tab_names.append("⚙️ Administration")

tabs = st.tabs(tab_names)
tab_saisie = tabs[0]
tab_data = tabs[1]

with tab_saisie:
    st.subheader("Nouvelle saisie")
    if st.button("🚀 Saisie Rapide (OK - Plage idéale :+2°C+8°C)", use_container_width=True):
        save_data({
            "Date": datetime.now().strftime("%d/%m/%Y"), "Heure": datetime.now().strftime("%H:%M"),
            "Température": 4.0, "Agent": st.session_state.current_user['username'],
            "Statut": "OK", "Commentaire": "Rapide", "Type": "Plage idéale :+2°C+8°C"
        })
        st.rerun()

    with st.form("form_saisie", clear_on_submit=True):
        t = st.number_input("Température (°C)", min_value=-20.0, max_value=30.0, value=4.0, step=0.1)
        type_releve = st.selectbox("Motif", ["Plage idéale :+2°C+8°C", "Remplissage / Arrivage", "Nettoyage", "Autre"])
        comm = st.text_input("Commentaire")
        if st.form_submit_button("Enregistrer", use_container_width=True):
            save_data({
                "Date": datetime.now().strftime("%d/%m/%Y"), "Heure": datetime.now().strftime("%H:%M"),
                "Température": t, "Agent": st.session_state.current_user['username'],
                "Statut": "OK" if 2.0 <= t <= 8.0 else "ALERTE", "Commentaire": comm, "Type": type_releve
            })
            st.rerun()

with tab_data:
    if os.path.isfile(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        df = clean_frigo_data(df)
        
        # Création d'une colonne Timestamp pour le graphe
        df['Timestamp'] = pd.to_datetime(df['Date'] + ' ' + df['Heure'], format="%d/%m/%Y %H:%M", errors='coerce')
        
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

if is_admin:
    tab_admin = tabs[2]
    with tab_admin:
        st.subheader("🛠️ Édition manuelle des relevés")
        if os.path.isfile(DATA_FILE):
            df_admin = pd.read_csv(DATA_FILE)
            df_admin = clean_frigo_data(df_admin)
            edited_df = st.data_editor(df_admin, use_container_width=True, num_rows="dynamic")
            if st.button("💾 Sauvegarder les modifications"):
                edited_df.to_csv(DATA_FILE, index=False)
                st.success("Modifications enregistrées !")
                st.rerun()
        else:
            st.info("Aucun historique à éditer.")
            
        st.divider()
        st.subheader("📥 Importer un historique Excel")
        st.write("Format attendu : **Date, Heure, Température, Agent, Statut, Commentaire, Type**")
        f_up = st.file_uploader("Fichier Excel (.xlsx)", type=["xlsx"])
        if f_up:
            try:
                df_up = pd.read_excel(f_up)
                st.write("Aperçu de l'import :")
                st.dataframe(df_up.head())
                if st.button("Fusionner avec l'historique existant"):
                    if os.path.isfile(DATA_FILE):
                        df_current = pd.read_csv(DATA_FILE)
                        df_final = pd.concat([df_current, df_up], ignore_index=True)
                    else:
                        df_final = df_up
                    df_final = clean_frigo_data(df_final)
                    df_final.to_csv(DATA_FILE, index=False)
                    st.success("Données importées avec succès !")
                    st.rerun()
            except Exception as e:
                st.error(f"Erreur de lecture du fichier : {e}")
