import streamlit as st
import pandas as pd
import os
import io
from datetime import datetime
from fpdf import FPDF

# --- CONFIGURATION ---
DATA_RECOUV = "data_recouvrement.csv"

def load_recouv():
    if os.path.exists(DATA_RECOUV):
        return pd.read_csv(DATA_RECOUV)
    return pd.DataFrame(columns=["Date", "Livreur", "Client", "Montant_Du", "Mode", "Statut", "Note"])

# --- FONCTION GÉNÉRATION PDF ---
def generate_pdf(df, livreur_name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    
    # Entête
    pdf.cell(190, 10, "DARPHARM SOLUTION - FEUILLE DE ROUTE", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    date_str = datetime.now().strftime("%d/%m/%Y")
    pdf.cell(190, 10, f"Livreur : {livreur_name} | Date d'expédition : {date_str}", ln=True, align='C')
    pdf.ln(10)
    
    # Tableau - Entêtes
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(200, 220, 255)
    pdf.cell(30, 10, "Date", 1, 0, 'C', True)
    pdf.cell(60, 10, "Client", 1, 0, 'C', True)
    pdf.cell(40, 10, "Montant (DA)", 1, 0, 'C', True)
    pdf.cell(60, 10, "Note", 1, 1, 'C', True)
    
    # Tableau - Lignes
    pdf.set_font("Arial", '', 9)
    for _, row in df.iterrows():
        pdf.cell(30, 10, str(row['Date']), 1)
        pdf.cell(60, 10, str(row['Client'])[:25], 1)
        pdf.cell(40, 10, str(row['Montant_Du']), 1)
        pdf.cell(60, 10, str(row['Note'])[:35], 1)
        pdf.ln()
    
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- INTERFACE ---
st.set_page_config(page_title="Darpharm Solution - Recouvrement", layout="wide")
st.title("💰 Suivi du Recouvrement")

tab_creer, tab_suivi = st.tabs(["🆕 Créer une fiche", "📊 État & Téléchargements"])

with tab_creer:
    st.subheader("Préparer la tournée")
    with st.form("ajout_fiche", clear_on_submit=True):
        c1, c2 = st.columns(2)
        d = c1.date_input("Date", datetime.now())
        liv = c1.selectbox("Livreur", ["FARES", "FETHI", "HAROUN", "AMINE", "KARIM", "MAIDI", "SAMIR", "BILEL", "HAMID"])
        cli = c2.text_input("Nom du Client")
        mt = c2.number_input("Montant (DA)", min_value=0.0)
        mode = st.selectbox("Mode prévu", ["VERSEMENT", "CASH", "CHEQUE"])
        note = st.text_input("Note / Instructions")
        
        if st.form_submit_button("Enregistrer"):
            df = load_recouv()
            new_data = pd.DataFrame([{"Date": str(d), "Livreur": liv, "Client": cli, "Montant_Du": mt, "Mode": mode, "Statut": "En attente", "Note": note}])
            pd.concat([df, new_data], ignore_index=True).to_csv(DATA_RECOUV, index=False)
            st.success("Fiche enregistrée !")

with tab_suivi:
    df_res = load_recouv()
    if not df_res.empty:
        # Barre de sélection du livreur
        liste_livreurs = sorted(df_res["Livreur"].unique().tolist())
        sel_livreur = st.selectbox("🎯 Sélectionner le livreur pour l'export :", liste_livreurs)
        
        df_filtered = df_res[df_res["Livreur"] == sel_livreur]
        
        # --- BLOC TÉLÉCHARGEMENT ---
        st.write(f"### 📥 Export pour {sel_livreur}")
        col_pdf, col_xlsx = st.columns(2)
        
        # Option 1 : PDF
        pdf_bytes = generate_pdf(df_filtered, sel_livreur)
        col_pdf.download_button(
            label="📄 Télécharger en PDF (Pour impression)",
            data=pdf_bytes,
            file_name=f"tournee_{sel_livreur}_{datetime.now().strftime('%d_%m')}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        
        # Option 2 : EXCEL
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_filtered.to_excel(writer, index=False, sheet_name='Recouvrement')
        
        col_xlsx.download_button(
            label="Excel Télécharger en EXCEL (Pour modification)",
            data=buffer.getvalue(),
            file_name=f"tournee_{sel_livreur}_{datetime.now().strftime('%d_%m')}.xlsx",
            mime="application/vnd.ms-excel",
            use_container_width=True
        )
        
        st.divider
