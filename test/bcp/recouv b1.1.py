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

# Harmonisation des noms de colonnes pour éviter les KeyError
COL_RESTE = "Reste à payer"
COL_MODE = "Mode Paiement"

MODES_AVEC_ICONS = {
    "CASH": "💵 CASH",
    "CHEQUE": "🏦 CHEQUE",
    "VERSEMENT": "📝 VERSEMENT"
}

# --- CHARGEMENT ET SAUVEGARDE ---
def load_csv(file_path, default_cols):
    if os.path.exists(file_path):
        try:
            df = pd.read_csv(file_path)
            # Nettoyage automatique du montant pour éviter le ValueError 'f'
            if file_path == DATA_RECOUV and COL_RESTE in df.columns:
                df[COL_RESTE] = pd.to_numeric(
                    df[COL_RESTE].astype(str).str.replace(',', '.').str.replace(' ', ''), 
                    errors='coerce'
                ).fillna(0.0)
            return df
        except:
            return pd.DataFrame(columns=default_cols)
    return pd.DataFrame(columns=default_cols)

def save_csv(df, file_path):
    df.to_csv(file_path, index=False)

# --- LOGIQUE D'ADMINISTRATION & AUTO-APPRENTISSAGE ---
def auto_assign(client_name, region_name):
    """Trouve le livreur et la région basés sur l'administration existante"""
    df_c = load_csv(DATA_CLIENTS, ["Client", "Région"])
    df_r = load_csv(DATA_REGIONS, ["Région", "Livreur"])
    
    final_region = region_name
    if client_name in df_c["Client"].values:
        final_region = df_c[df_c["Client"] == client_name]["Région"].values[0]
    
    if final_region in df_r["Région"].values:
        return df_r[df_r["Région"] == final_region]["Livreur"].values[0], final_region
    
    return "NON ASSIGNÉ", final_region

def update_admin_referentials(df_imported):
    """Alimente l'onglet Administration automatiquement après un import"""
    # 1. Clients par Région
    if "Client" in df_imported.columns and "Région" in df_imported.columns:
        df_clients = load_csv(DATA_CLIENTS, ["Client", "Région"])
        new_c = df_imported[["Client", "Région"]].drop_duplicates()
        df_clients = pd.concat([df_clients, new_c]).drop_duplicates(subset=["Client"], keep='first')
        save_csv(df_clients, DATA_CLIENTS)

    # 2. Livreurs par Région
    if "Livreur" in df_imported.columns and "Région" in df_imported.columns:
        df_reg = load_csv(DATA_REGIONS, ["Région", "Livreur"])
        new_r = df_imported[["Région", "Livreur"]].drop_duplicates()
        df_reg = pd.concat([df_reg, new_r]).drop_duplicates(subset=["Région"], keep='first')
        save_csv(df_reg, DATA_REGIONS)

    # 3. Liste des Livreurs
    if "Livreur" in df_imported.columns:
        df_liv = load_csv(DATA_LIVREURS, ["Nom"])
        new_l = df_imported[["Livreur"]].rename(columns={"Livreur": "Nom"}).drop_duplicates()
        df_liv = pd.concat([df_liv, new_l]).drop_duplicates(subset=["Nom"], keep='first')
        save_csv(df_liv, DATA_LIVREURS)

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
        mt = float(row[COL_RESTE])
        pdf.cell(40, 10, f"{mt:.2f} DA", 1)
        pdf.cell(45, 10, str(row[COL_MODE]), 1)
        pdf.cell(40, 10, "", 1)
        pdf.ln()
    return pdf.output(dest='S')

# --- INTERFACE STREAMLIT ---
st.set_page_config(page_title="Pharmaciel - Recouvrement", layout="wide")
st.title("💰 Système de Recouvrement Pharmaciel")

tab1, tab2, tab3, tab4 = st.tabs(["🆕 Créer / Importer", "📄 Feuilles de Route", "📊 Suivi Global", "⚙️ Administration"])

# --- TAB 1 : IMPORT & SAISIE ---
with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Saisie Manuelle")
        with st.form("manuel", clear_on_submit=True):
            cli = st.text_input("Client")
            reg_in = st.text_input("Région (si nouvelle)")
            mt = st.number_input("Montant", min_value=0.0)
            mod = st.selectbox("Mode", list(MODES_AVEC_ICONS.values()))
            if st.form_submit_button("Enregistrer"):
                liv, reg_f = auto_assign(cli, reg_in)
                df_r = load_csv(DATA_RECOUV, ["Date", "Livreur", "Client", COL_RESTE, COL_MODE, "Statut", "Région"])
                new = {"Date": str(datetime.now().date()), "Livreur": liv, "Client": cli, "Région": reg_f, COL_RESTE: mt, COL_MODE: mod, "Statut": "En attente"}
                save_csv(pd.concat([df_r, pd.DataFrame([new])], ignore_index=True), DATA_RECOUV)
                st.success(f"Enregistré pour {liv}")

    with c2:
        st.subheader("Import Excel")
        file = st.file_uploader("Fichier .xlsx", type=["xlsx"])
        if file:
            df_i = pd.read_excel(file)
            st.write("Aperçu des données :")
            st.dataframe(df_i.head(5), use_container_width=True)
            
            if st.button("🚀 Valider l'importation"):
                # Nettoyage et assignation
                df_i[COL_RESTE] = pd.to_numeric(df_i[COL_RESTE], errors='coerce').fillna(0.0)
                if 'Livreur' not in df_i.columns:
                    assigns = df_i.apply(lambda x: auto_assign(x['Client'], x.get('Région', '')), axis=1)
                    df_i['Livreur'] = [a[0] for a in assigns]
                    df_i['Région'] = [a[1] for a in assigns]
                
                df_i['Date'] = str(datetime.now().date())
                df_i['Statut'] = "En attente"
                
                # Action : Mise à jour Administration
                update_admin_referentials(df_i)
                
                df_all = load_csv(DATA_RECOUV, [])
                save_csv(pd.concat([df_all, df_i], ignore_index=True, sort=False), DATA_RECOUV)
                st.success("Données importées et Administration actualisée !")
                st.rerun()

# --- TAB 2 : FEUILLES DE ROUTE ---
with tab2:
    df_f = load_csv(DATA_RECOUV, [])
    # Filtre automatique : Montant > 0
    df_f = df_f[df_f[COL_RESTE] > 0] if not df_f.empty else df_f
    
    if not df_f.empty:
        liv_sel = st.selectbox("Livreur", sorted(df_f["Livreur"].unique()))
        sub = df_f[df_f["Livreur"] == liv_sel].copy()
        
        st.download_button("📄 PDF", data=bytes(generate_pdf(sub, liv_sel)), file_name=f"{liv_sel}.pdf")
        
        # Éditeur avec liste déroulante et suppression
        edited = st.data_editor(
            sub, use_container_width=True, hide_index=True, num_rows="dynamic",
            column_config={
                COL_MODE: st.column_config.SelectboxColumn("Mode", options=list(MODES_AVEC_ICONS.values())),
                COL_RESTE: st.column_config.NumberColumn("Montant", format="%.2f DA")
            }
        )
        
        if st.button("💾 Sauvegarder modifications"):
            df_full = load_csv(DATA_RECOUV, [])
            # On remplace uniquement les données modifiées pour ce livreur
            df_full = df_full[~((df_full["Livreur"] == liv_sel) & (df_full[COL_RESTE] > 0))]
            save_csv(pd.concat([df_full, edited], ignore_index=True), DATA_RECOUV)
            st.success("Modifications enregistrées.")
            st.rerun()

# --- TAB 3 : SUIVI ---
with tab3:
    df_s = load_csv(DATA_RECOUV, [])
    if not df_s.empty:
        # Calcul sécurisé pour éviter le ValueError
        valide = pd.to_numeric(df_s[COL_RESTE], errors='coerce').fillna(0)
        st.metric("Total à recouvrer", f"{valide.sum():,.2f} DA")
        st.bar_chart(df_s.groupby("Livreur")[COL_RESTE].sum())

# --- TAB 4 : ADMINISTRATION ---
with tab4:
    st.header("⚙️ Gestion des Référentiels")
    adm_col1, adm_col2 = st.columns(2)
    
    with adm_col1:
        st.subheader("1. Livreur par Région")
        df_r_adm = load_csv(DATA_REGIONS, ["Région", "Livreur"])
        ed_r = st.data_editor(df_r_adm, num_rows="dynamic", use_container_width=True, key="adm_r")
        if st.button("Sauver Régions"): save_csv(ed_r, DATA_REGIONS)

    with adm_col2:
        st.subheader("2. Clients par Région")
        df_c_adm = load_csv(DATA_CLIENTS, ["Client", "Région"])
        ed_c = st.data_editor(df_c_adm, num_rows="dynamic", use_container_width=True, key="adm_c")
        if st.button("Sauver Clients"): save_csv(ed_c, DATA_CLIENTS)
