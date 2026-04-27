import streamlit as st
import pandas as pd
import os
from datetime import datetime
from fpdf import FPDF

# --- CONFIGURATION ---
DATA_RECOUV = "data_recouvrement.csv"
COLS = ["Client", "Mode Paiement", "Région", "Reste à payer", "Livreur", "Date", "Statut"]

# --- FONCTION GÉNÉRATION PDF ---
def generate_pdf(df, livreur_name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, f"FEUILLE DE ROUTE : {livreur_name}", ln=True, align='C')
    pdf.set_font("Arial", "", 12)
    pdf.cell(190, 10, f"Date: {datetime.now().strftime('%d/%m/%Y')}", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(60, 10, "Client", 1, 0, 'C', True)
    pdf.cell(35, 10, "Region", 1, 0, 'C', True)
    pdf.cell(35, 10, "Montant", 1, 0, 'C', True)
    pdf.cell(25, 10, "Mode", 1, 0, 'C', True)
    pdf.cell(35, 10, "Reglement", 1, 1, 'C', True)
    
    pdf.set_font("Arial", "", 9)
    for _, row in df.iterrows():
        client = str(row['Client']).encode('latin-1', 'replace').decode('latin-1')
        region = str(row['Région']).encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(60, 10, client[:30], 1)
        pdf.cell(35, 10, region, 1)
        pdf.cell(35, 10, f"{row['Reste à payer']:,.2f} DA", 1, 0, 'R')
        pdf.cell(25, 10, str(row['Mode Paiement']), 1, 0, 'C')
        pdf.cell(35, 10, "", 1, 1)
    
    return bytes(pdf.output(dest='S'))

# --- LOGIQUE DE GESTION DES DONNÉES ---
def load_csv(path):
    if os.path.exists(path):
        try:
            df = pd.read_csv(path, sep=',', encoding='utf-8-sig')
            if "Reste à payer" in df.columns:
                df["Reste à payer"] = pd.to_numeric(
                    df["Reste à payer"].astype(str).str.replace(',', '.').str.replace(r'\s+', '', regex=True), 
                    errors='coerce'
                ).fillna(0.0)
            return df.reindex(columns=COLS)
        except: return pd.DataFrame(columns=COLS)
    return pd.DataFrame(columns=COLS)

def save_csv(df, path):
    # Suppression des doublons avant sauvegarde
    df_clean = df.drop_duplicates(subset=["Client", "Région", "Reste à payer"], keep='first')
    df_clean.to_csv(path, index=False, sep=',', encoding='utf-8-sig')
    return df_clean

def get_livreur(region_val):
    reg = str(region_val).strip().upper() if pd.notna(region_val) else ""
    mapping = {"ALGER 1": "FETHI", "ALGER 2": "FARES", "ALGER EST": "MAIDI", "TIPAZA": "HAROUN", "BLIDA": "HAROUN"}
    hamid_list = ["MEDEA", "CHLEF", "DJELFA", "AIN-DEFLA", "RELIZANE", "LAGHOUAT", "ORAN"]
    if reg in mapping: return mapping[reg]
    if any(h in reg for h in hamid_list): return "HAMID"
    return "NON ASSIGNÉ"

# --- INTERFACE ---
st.set_page_config(page_title="Pharmaciel - Recouvrement", layout="wide")
st.title("💰 Système de Recouvrement Pharmaciel")

tabs = st.tabs(["🆕 Créer / Importer", "📄 Feuilles de Route", "📊 Suivi Global", "⚙️ Administration"])

# --- ONGLET 1 : IMPORT & SAISIE ---
with tabs[0]:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Saisie Manuelle")
        with st.form("form_manuel", clear_on_submit=True):
            nom = st.text_input("Nom du Client")
            reg_in = st.text_input("Région")
            mont = st.number_input("Montant", min_value=0.0)
            mode = st.selectbox("Mode", ["CASH", "CHÈQUE", "VERSEMENT"])
            if st.form_submit_button("Enregistrer"):
                db = load_csv(DATA_RECOUV)
                new_line = pd.DataFrame([{
                    "Client": nom.upper(), "Mode Paiement": mode, "Région": reg_in.upper(),
                    "Reste à payer": mont, "Livreur": get_livreur(reg_in),
                    "Date": str(datetime.now().date()), "Statut": "En attente"
                }])
                save_csv(pd.concat([db, new_line], ignore_index=True), DATA_RECOUV)
                st.success("Client ajouté (doublons filtrés) !")
                st.rerun()

    with col2:
        st.subheader("Import Excel")
        file = st.file_uploader("Déposer rec.xlsx", type=["xlsx"])
        if file:
            df_excel = pd.read_excel(file)
            if st.button("🚀 Valider l'importation"):
                df_excel["Livreur"] = df_excel["Région"].apply(get_livreur)
                df_excel["Date"], df_excel["Statut"] = str(datetime.now().date()), "En attente"
                db_old = load_csv(DATA_RECOUV)
                save_csv(pd.concat([db_old, df_excel[COLS]], ignore_index=True), DATA_RECOUV)
                st.success("Importation réussie et doublons supprimés !")
                st.rerun()

# --- ONGLET 2 : FEUILLES DE ROUTE ---
with tabs[1]:
    df_main = load_csv(DATA_RECOUV)
    if not df_main.empty:
        liste_livreurs = sorted(df_main["Livreur"].unique())
        selection = st.selectbox("Livreur", liste_livreurs)
        mask = df_main["Livreur"] == selection
        df_filtre = df_main[mask].copy()

        col_pdf, col_clean = st.columns([1, 1])
        with col_pdf:
            st.download_button("📥 Télécharger PDF", generate_pdf(df_filtre, selection), f"Route_{selection}.pdf", "application/pdf")
        
        with col_clean:
            if st.button("🧹 Nettoyer les doublons ici"):
                df_main = save_csv(df_main, DATA_RECOUV)
                st.success("Base de données nettoyée !")
                st.rerun()

        edited = st.data_editor(df_filtre, use_container_width=True, hide_index=True)
        if st.button("💾 Sauvegarder"):
            save_csv(pd.concat([df_main[~mask], edited], ignore_index=True), DATA_RECOUV)
            st.rerun()
    else:
        st.info("Aucune donnée.")

# --- ONGLET 3 & 4 ---
with tabs[2]:
    df_suivi = load_csv(DATA_RECOUV)
    if not df_suivi.empty:
        st.metric("Total", f"{df_suivi['Reste à payer'].sum():,.2f} DA")
        st.dataframe(df_suivi, use_container_width=True)

with tabs[3]:
    if st.button("🗑️ Tout effacer"):
        if os.path.exists(DATA_RECOUV): os.remove(DATA_RECOUV)
        st.rerun()
