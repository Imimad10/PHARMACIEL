import streamlit as st
import pandas as pd
import os
from datetime import datetime
from fpdf import FPDF

# --- CONFIGURATION DES FICHIERS ---
DATA_RECOUV = "data_recouvrement.csv"
DATA_LIVREURS = "livreurs.csv"
DATA_REGIONS = "regions.csv"
DATA_CLIENTS = "clients.csv"

COL_RESTE = "Reste à payer"
COL_MODE = "Mode Paiement"

MODES_AVEC_ICONS = {
    "CASH": "💵 CASH",
    "CHEQUE": "🏦 CHEQUE",
    "VERSEMENT": "📝 VERSEMENT"
}

# --- CHARGEMENT DES DONNÉES ---
def load_csv(file_path, default_cols):
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path)
            # Correction spécifique pour le fichier recouvrement
            if file_path == DATA_RECOUV and COL_RESTE in df.columns:
                df[COL_RESTE] = pd.to_numeric(df[COL_RESTE].astype(str).str.replace(',', '.').str.replace(' ', ''), errors='coerce').fillna(0.0)
            return df
        except:
            return pd.DataFrame(columns=default_cols)
    return pd.DataFrame(columns=default_cols)

def save_csv(df, file_path):
    df.to_csv(file_path, index=False)

# --- LOGIQUE D'ASSIGNATION ---
def auto_assign(client_name, region_name):
    """Logique d'assignation basée sur les tables de l'administration"""
    df_c = load_csv(DATA_CLIENTS, ["Client", "Région"])
    df_r = load_csv(DATA_REGIONS, ["Région", "Livreur"])
    
    final_region = region_name
    # 1. Vérifier si le client a une région prédéfinie
    if client_name in df_c["Client"].values:
        final_region = df_c[df_c["Client"] == client_name]["Région"].values[0]
    
    # 2. Trouver le livreur associé à la région
    if final_region in df_r["Région"].values:
        return df_r[df_r["Région"] == final_region]["Livreur"].values[0], final_region
    
    return "NON ASSIGNÉ", final_region

# --- GÉNÉRATION PDF ---
def generate_pdf(df, livreur_name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "PHARMACIEL - FEUILLE DE ROUTE", ln=True, align='C')
    pdf.set_font("Arial", '', 12)
    pdf.cell(190, 10, f"Livreur : {livreur_name} | Date : {datetime.now().strftime('%d/%m/%Y')}", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(200, 220, 255)
    for h, w in [("CLIENT", 65), ("MONTANT (DA)", 40), ("MODE", 45), ("NOTE", 40)]:
        pdf.cell(w, 10, h, 1, 0, 'C', True)
    pdf.ln()
    pdf.set_font("Arial", '', 10)
    for _, row in df.iterrows():
        pdf.cell(65, 10, str(row['Client'])[:25], 1)
        # Fix pour l'affichage PDF du montant
        mt = float(row[COL_RESTE]) if not pd.isna(row[COL_RESTE]) else 0.0
        pdf.cell(40, 10, f"{mt:.2f} DA", 1)
        pdf.cell(45, 10, str(row[COL_MODE]), 1)
        pdf.cell(40, 10, "", 1)
        pdf.ln()
    return pdf.output(dest='S')

# --- INTERFACE ---
st.set_page_config(page_title="Pharmaciel - Recouvrement", layout="wide")
st.title("💰 Système de Recouvrement Pharmaciel")

tab1, tab2, tab3, tab4 = st.tabs(["🆕 Créer / Importer", "📄 Feuilles de Route", "📊 Suivi Global", "⚙️ Administration"])

# --- TAB 1 : CRÉATION / IMPORT ---
with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Saisie Manuelle")
        with st.form("form_manuel", clear_on_submit=True):
            cli = st.text_input("Nom du Client")
            reg_input = st.text_input("Région (optionnel)")
            mt = st.number_input("Montant à recouvrer", min_value=0.0)
            mod = st.selectbox("Mode de paiement", list(MODES_AVEC_ICONS.values()))
            if st.form_submit_button("Enregistrer"):
                liv, reg_final = auto_assign(cli, reg_input)
                df_rec = load_csv(DATA_RECOUV, ["Date", "Livreur", "Client", COL_RESTE, COL_MODE, "Statut", "Région"])
                new = {"Date": str(datetime.now().date()), "Livreur": liv, "Client": cli, "Région": reg_final, COL_RESTE: mt, COL_MODE: mod, "Statut": "En attente"}
                save_csv(pd.concat([df_rec, pd.DataFrame([new])], ignore_index=True), DATA_RECOUV)
                st.success(f"Ajouté ! Assigné à {liv}")

    with c2:
        st.subheader("Import Excel")
        file = st.file_uploader("Déposer le fichier Excel", type=["xlsx"])
        if file:
            df_i = pd.read_excel(file)
            st.write("Aperçu de l'import :")
            st.dataframe(df_i.head(5), use_container_width=True)
            
            if st.button("🚀 Valider l'importation"):
                # Application de la logique d'assignation sur chaque ligne
                assignations = df_i.apply(lambda x: auto_assign(x['Client'], x.get('Région', '')), axis=1)
                df_i['Livreur'] = [a[0] for a in assignations]
                df_i['Région'] = [a[1] for a in assignations]
                df_i['Date'] = str(datetime.now().date())
                df_i['Statut'] = "En attente"
                df_i[COL_RESTE] = pd.to_numeric(df_i[COL_RESTE], errors='coerce').fillna(0.0)
                
                df_total = load_csv(DATA_RECOUV, [])
                save_csv(pd.concat([df_total, df_i], ignore_index=True, sort=False), DATA_RECOUV)
                st.success("Importation terminée avec assignations automatiques.")
                st.rerun()

# --- TAB 2 : FEUILLES DE ROUTE ---
with tab2:
    df_f = load_csv(DATA_RECOUV, [])
    df_f = df_f[df_f[COL_RESTE] > 0] if not df_f.empty else df_f
    
    if not df_f.empty:
        liv_list = sorted(df_f["Livreur"].unique())
        sel_liv = st.selectbox("Choisir un Livreur", liv_list)
        sub = df_f[df_f["Livreur"] == sel_liv].copy()
        
        col_btn1, col_btn2 = st.columns([1, 4])
        with col_btn1:
            st.download_button("📄 PDF Feuille de Route", data=bytes(generate_pdf(sub, sel_liv)), file_name=f"{sel_liv}.pdf")
            
        edited = st.data_editor(
            sub, 
            use_container_width=True, 
            hide_index=True,
            num_rows="dynamic",
            column_config={
                COL_MODE: st.column_config.SelectboxColumn("Mode", options=list(MODES_AVEC_ICONS.values())),
                COL_RESTE: st.column_config.NumberColumn("Montant", format="%.2f DA")
            }
        )
        
        if st.button("💾 Sauvegarder les modifications"):
            df_full = load_csv(DATA_RECOUV, [])
            # Suppression des anciennes données du livreur et remplacement par les éditées
            df_full = df_full[~((df_full["Livreur"] == sel_liv) & (df_full[COL_RESTE] > 0))]
            save_csv(pd.concat([df_full, edited], ignore_index=True), DATA_RECOUV)
            st.success("Fichier mis à jour.")
            st.rerun()

# --- TAB 3 : SUIVI GLOBAL ---
with tab3:
    df_s = load_csv(DATA_RECOUV, [])
    if not df_s.empty:
        # Conversion forcée pour le calcul de la métrique
        total_du = pd.to_numeric(df_s[COL_RESTE], errors='coerce').sum()
        st.metric("Total à recouvrer", f"{total_du:,.2f} DA")
        st.bar_chart(df_s.groupby("Livreur")[COL_RESTE].sum())

# --- TAB 4 : ADMINISTRATION (GESTION DES RÉFÉRENCES) ---
with tab4:
    st.header("⚙️ Gestion des Référentiels")
    st.info("Configurez ici les liens entre Livreur ↔ Région ↔ Client pour l'automatisation.")
    
    col_adm1, col_adm2 = st.columns(2)
    
    with col_adm1:
        st.subheader("1. Livreur par Région")
        df_reg = load_csv(DATA_REGIONS, ["Région", "Livreur"])
        edit_reg = st.data_editor(df_reg, num_rows="dynamic", use_container_width=True, key="ed_reg")
        if st.button("Sauvegarder Régions"):
            save_csv(edit_reg, DATA_REGIONS)
            st.success("Régions mises à jour.")

    with col_adm2:
        st.subheader("2. Clients par Région")
        df_cli_ref = load_csv(DATA_CLIENTS, ["Client", "Région"])
        edit_cli_ref = st.data_editor(df_cli_ref, num_rows="dynamic", use_container_width=True, key="ed_cli")
        if st.button("Sauvegarder Clients"):
            save_csv(edit_cli_ref, DATA_CLIENTS)
            st.success("Clients mis à jour.")
            
    st.write("---")
    st.subheader("3. Liste des Livreurs actifs")
    df_liv_list = load_csv(DATA_LIVREURS, ["Nom"])
    edit_liv = st.data_editor(df_liv_list, num_rows="dynamic", use_container_width=True, key="ed_liv")
    if st.button("Sauvegarder Livreurs"):
        save_csv(edit_liv, DATA_LIVREURS)
