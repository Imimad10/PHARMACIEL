import streamlit as st
import pandas as pd
import os
from datetime import datetime
from fpdf import FPDF

# --- CONFIGURATION ---
DATA_RECOUV = "data_recouvrement.csv"
DATA_CLIENTS = "base_clients.csv"
COLS_RECOUV = ["Client", "Mode Paiement", "Région", "Reste à payer", "Livreur", "Date", "Statut"]
COLS_CLIENTS = ["Nom Client", "Région", "Téléphone", "Secteur"]

# --- GESTION DES DONNÉES ---
def load_data(path, columns):
    if os.path.exists(path):
        try:
            df = pd.read_csv(path, sep=',', encoding='utf-8-sig')
            if "Reste à payer" in df.columns:
                df["Reste à payer"] = pd.to_numeric(
                    df["Reste à payer"].astype(str).str.replace(',', '.').str.replace(r'\s+', '', regex=True), 
                    errors='coerce'
                ).fillna(0.0)
            
            # Nettoyage forcé pour éviter l'erreur TypeError
            if "Nom Client" in df.columns:
                df = df.dropna(subset=["Nom Client"])
                df["Nom Client"] = df["Nom Client"].astype(str).str.strip()
            return df.reindex(columns=columns)
        except: return pd.DataFrame(columns=columns)
    return pd.DataFrame(columns=columns)

def save_data(df, path, subset_duplicates=None):
    if subset_duplicates:
        existing_sub = [c for c in subset_duplicates if c in df.columns]
        df = df.drop_duplicates(subset=existing_sub, keep='first')
    df.to_csv(path, index=False, sep=',', encoding='utf-8-sig')
    return df

def get_livreur(region_val):
    reg = str(region_val).strip().upper() if pd.notna(region_val) else ""
    mapping = {"ALGER 1": "FETHI", "ALGER 2": "FARES", "ALGER EST": "MAIDI", "TIPAZA": "HAROUN", "BLIDA": "HAROUN"}
    hamid_list = ["MEDEA", "CHLEF", "DJELFA", "AIN-DEFLA", "RELIZANE", "LAGHOUAT", "ORAN"]
    if reg in mapping: return mapping[reg]
    if any(h in reg for h in hamid_list): return "HAMID"
    return "NON ASSIGNÉ"

# --- GÉNÉRATION PDF ---
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
    for txt, w in [("Client", 60), ("Region", 35), ("Montant", 35), ("Mode", 25), ("Reglement", 35)]:
        pdf.cell(w, 10, txt, 1, 0, 'C', True)
    pdf.ln(10)
    
    pdf.set_font("Arial", "", 9)
    for _, row in df.iterrows():
        c = str(row['Client']).encode('latin-1', 'replace').decode('latin-1')
        r = str(row['Région']).encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(60, 10, c[:30], 1)
        pdf.cell(35, 10, r, 1)
        pdf.cell(35, 10, f"{row['Reste à payer']:,.2f} DA", 1, 0, 'R')
        pdf.cell(25, 10, str(row['Mode Paiement']), 1, 0, 'C')
        pdf.cell(35, 10, "", 1, 1) # Case vide pour stylo
    return bytes(pdf.output(dest='S'))

# --- INTERFACE ---
st.set_page_config(page_title="Pharmaciel Pro", layout="wide")
st.title("💰 Système de Recouvrement Pharmaciel")

tabs = st.tabs(["🆕 Créer / Importer", "📄 Feuilles de Route", "📊 Suivi Global", "⚙️ Administration"])

# --- ONGLET 1 : CRÉATION ---
with tabs[0]:
    df_clients = load_data(DATA_CLIENTS, COLS_CLIENTS)
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Saisie Manuelle")
        with st.form("form_rec", clear_on_submit=True):
            if not df_clients.empty:
                noms_valides = sorted([n for n in df_clients["Nom Client"].unique() if str(n).lower() != 'nan'])
                nom_sel = st.selectbox("Client", noms_valides)
                reg_auto = df_clients[df_clients["Nom Client"] == nom_sel]["Région"].values[0]
            else:
                nom_sel = st.text_input("Nom Client")
                reg_auto = st.text_input("Région")

            montant = st.number_input("Montant", min_value=0.0)
            mode = st.selectbox("Mode", ["CASH", "CHÈQUE", "VERSEMENT"])
            if st.form_submit_button("Enregistrer"):
                db = load_data(DATA_RECOUV, COLS_RECOUV)
                new = pd.DataFrame([{"Client": nom_sel, "Mode Paiement": mode, "Région": reg_auto, "Reste à payer": montant, "Livreur": get_livreur(reg_auto), "Date": str(datetime.now().date()), "Statut": "En attente"}])
                save_data(pd.concat([db, new], ignore_index=True), DATA_RECOUV)
                st.success("Enregistré !")
                st.rerun()

    with col2:
        st.subheader("Import Recouvrements")
        f_rec = st.file_uploader("Fichier rec.xlsx", type=["xlsx"])
        if f_rec:
            df_ex = pd.read_excel(f_rec)
            if st.button("🚀 Valider l'import"):
                df_ex["Livreur"] = df_ex["Région"].apply(get_livreur)
                df_ex["Date"], df_ex["Statut"] = str(datetime.now().date()), "En attente"
                db_old = load_data(DATA_RECOUV, COLS_RECOUV)
                save_data(pd.concat([db_old, df_ex], ignore_index=True), DATA_RECOUV)
                st.success("Import terminé !")
                st.rerun()

# --- ONGLET 2 : FEUILLES DE ROUTE ---
with tabs[1]:
    df_main = load_data(DATA_RECOUV, COLS_RECOUV)
    if not df_main.empty:
        livs = sorted([str(l) for l in df_main["Livreur"].unique() if str(l).lower() != 'nan'])
        sel_liv = st.selectbox("Livreur", livs)
        mask = df_main["Livreur"] == sel_liv
        df_edit = df_main[mask].copy()
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            st.download_button("📥 Télécharger PDF", generate_pdf(df_edit, sel_liv), f"Route_{sel_liv}.pdf")
        
        edited = st.data_editor(df_edit, use_container_width=True, hide_index=True)
        if st.button("💾 Sauvegarder Statuts"):
            save_data(pd.concat([df_main[~mask], edited], ignore_index=True), DATA_RECOUV)
            st.rerun()
    else: st.info("Aucune donnée disponible.")

# --- ONGLET 3 : SUIVI GLOBAL ---
with tabs[2]:
    st.subheader("État Global des Recouvrements")
    df_global = load_data(DATA_RECOUV, COLS_RECOUV)
    if not df_global.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total à recouvrer", f"{df_global['Reste à payer'].sum():,.2f} DA")
        c2.metric("Nombre de clients", len(df_global))
        c3.metric("En attente", len(df_global[df_global["Statut"] == "En attente"]))
        
        st.dataframe(df_global.sort_values("Date", ascending=False), use_container_width=True, hide_index=True)
    else: st.info("Le tableau de bord est vide.")

# --- ONGLET 4 : ADMINISTRATION ---
with tabs[3]:
    sub1, sub2 = st.tabs(["👥 Base Clients", "⚙️ Système"])
    with sub1:
        f_cli = st.file_uploader("Fichier clients.xlsx", type=["xlsx"])
        if f_cli:
            df_cli_ex = pd.read_excel(f_cli)
            if st.button("📥 Fusionner"):
                old = load_data(DATA_CLIENTS, COLS_CLIENTS)
                # Sécurité pour KeyError 'Secteur'
                cols_ok = [c for c in COLS_CLIENTS if c in df_cli_ex.columns]
                save_data(pd.concat([old, df_cli_ex[cols_ok]], ignore_index=True), DATA_CLIENTS, ["Nom Client"])
                st.rerun()
        
        base_cli = load_data(DATA_CLIENTS, COLS_CLIENTS)
        edited_c = st.data_editor(base_cli, use_container_width=True, num_rows="dynamic")
        if st.button("💾 Enregistrer modifications client"):
            save_data(edited_c, DATA_CLIENTS, ["Nom Client"])
            st.rerun()

    with sub2:
        if st.button("🗑️ Réinitialiser tout le système"):
            for f in [DATA_RECOUV, DATA_CLIENTS]:
                if os.path.exists(f): os.remove(f)
            st.rerun()
