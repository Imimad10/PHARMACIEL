import streamlit as st
import pandas as pd
import os
from datetime import datetime
from fpdf import FPDF

# --- CONFIGURATION ET CHEMINS ---
DATA_RECOUV = "data_recouvrement.csv"
DATA_CLIENTS = "base_clients.csv"
COLS_RECOUV = ["Client", "Mode Paiement", "Région", "Reste à payer", "Livreur", "Date", "Statut"]
COLS_CLIENTS = ["Nom Client", "Région", "Téléphone", "Secteur"]

# --- FONCTIONS DE GESTION DES DONNÉES ---
def load_data(path, columns):
    if os.path.exists(path):
        try:
            df = pd.read_csv(path, sep=',', encoding='utf-8-sig')
            # Nettoyage des montants pour éviter les erreurs de calcul
            if "Reste à payer" in df.columns:
                df["Reste à payer"] = pd.to_numeric(
                    df["Reste à payer"].astype(str).str.replace(',', '.').str.replace(r'\s+', '', regex=True), 
                    errors='coerce'
                ).fillna(0.0)
            return df.reindex(columns=columns)
        except:
            return pd.DataFrame(columns=columns)
    return pd.DataFrame(columns=columns)

def save_data(df, path):
    # Suppression des lignes vides avant sauvegarde
    df = df.dropna(how='all')
    df.to_csv(path, index=False, sep=',', encoding='utf-8-sig')
    return df

def get_livreur(region_val):
    reg = str(region_val).strip().upper() if pd.notna(region_val) else ""
    mapping = {"ALGER 1": "FETHI", "ALGER 2": "FARES", "ALGER EST": "MAIDI", "TIPAZA": "HAROUN", "BLIDA": "HAROUN"}
    hamid_list = ["MEDEA", "CHLEF", "DJELFA", "AIN-DEFLA", "RELIZANE", "LAGHOUAT", "ORAN"]
    if reg in mapping: return mapping[reg]
    if any(h in reg for h in hamid_list): return "HAMID"
    return "NON ASSIGNÉ"

def generate_pdf(df, livreur_name):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(190, 10, f"FEUILLE DE ROUTE : {livreur_name}", ln=True, align='C')
    pdf.set_font("Arial", "", 12)
    pdf.cell(190, 10, f"Date: {datetime.now().strftime('%d/%m/%Y')}", ln=True, align='C')
    pdf.ln(10)
    
    # Entête du tableau PDF
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(60, 10, "Client", 1, 0, 'C', True)
    pdf.cell(35, 10, "Region", 1, 0, 'C', True)
    pdf.cell(35, 10, "Montant", 1, 0, 'C', True)
    pdf.cell(25, 10, "Mode", 1, 0, 'C', True)
    pdf.cell(35, 10, "Pointage", 1, 1, 'C', True) # Colonne vide pour stylo
    
    pdf.set_font("Arial", "", 9)
    for _, row in df.iterrows():
        pdf.cell(60, 10, str(row['Client'])[:30].encode('latin-1', 'replace').decode('latin-1'), 1)
        pdf.cell(35, 10, str(row['Région']), 1)
        pdf.cell(35, 10, f"{row['Reste à payer']:,.2f} DA", 1, 0, 'R')
        pdf.cell(25, 10, str(row['Mode Paiement']), 1, 0, 'C')
        pdf.cell(35, 10, "", 1, 1) 
    return bytes(pdf.output(dest='S'))

# --- INTERFACE UTILISATEUR ---
st.title("💰 Système de Recouvrement")

tabs = st.tabs(["🆕 Créer / Importer", "📄 Feuilles de Route", "📊 Suivi Global", "⚙️ Administration"])

# ONGLET 1 : SAISIE ET IMPORT
with tabs[0]:
    col1, col2 = st.columns([1, 2])
    df_clients = load_data(DATA_CLIENTS, COLS_CLIENTS)
    
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
                new_row = pd.DataFrame([{"Client": nom_sel, "Mode Paiement": mode, "Région": reg_auto, "Reste à payer": montant, "Livreur": get_livreur(reg_auto), "Date": str(datetime.now().date()), "Statut": "En attente"}])
                save_data(pd.concat([db, new_row], ignore_index=True), DATA_RECOUV)
                st.success("Enregistré !")
                st.rerun()

    with col2:
        st.subheader("Import Excel")
        f_rec = st.file_uploader("Déposer rec.xlsx", type=["xlsx"])
        if f_rec:
            df_ex = pd.read_excel(f_rec)
            if st.button("🚀 Valider l'importation"):
                df_ex["Livreur"] = df_ex["Région"].apply(get_livreur)
                df_ex["Date"] = str(datetime.now().date())
                df_ex["Statut"] = "En attente"
                db_old = load_data(DATA_RECOUV, COLS_RECOUV)
                save_data(pd.concat([db_old, df_ex], ignore_index=True), DATA_RECOUV)
                st.success("Import terminé !")
                st.rerun()

# ONGLET 2 : FEUILLES DE ROUTE (AVEC SUPPRESSION DOUBLONS ET RÉINITIALISATION)
with tabs[1]:
    df_main = load_data(DATA_RECOUV, COLS_RECOUV)
    if not df_main.empty:
        livs = sorted([str(l) for l in df_main["Livreur"].unique() if str(l).lower() != 'nan'])
        sel_liv = st.selectbox("Sélectionner Livreur", livs)
        
        # FILTRAGE ET SUPPRESSION AUTOMATIQUE DES DOUBLONS
        mask = df_main["Livreur"] == sel_liv
        df_display = df_main[mask].drop_duplicates(subset=["Client", "Reste à payer"], keep='first').copy()
        
        col_btns = st.columns([1, 1, 2])
        with col_btns[0]:
            st.download_button("📥 Télécharger PDF", generate_pdf(df_display, sel_liv), f"Route_{sel_liv}.pdf")
        
        with col_btns[1]:
            # BOUTON RÉINITIALISER LE TABLEAU
            if st.button("🗑️ Réinitialiser Tableau", help="Vide toutes les données de recouvrement"):
                save_data(pd.DataFrame(columns=COLS_RECOUV), DATA_RECOUV)
                st.warning("Tableau vidé avec succès.")
                st.rerun()

        edited = st.data_editor(df_display, use_container_width=True, hide_index=True)
        
        if st.button("💾 Sauvegarder Statuts"):
            df_final = pd.concat([df_main[~mask], edited], ignore_index=True)
            save_data(df_final, DATA_RECOUV)
            st.success("Données mises à jour !")
            st.rerun()
    else:
        st.info("Aucune donnée disponible.")

# ONGLET 3 : SUIVI GLOBAL
with tabs[2]:
    st.subheader("État Global des Recouvrements")
    df_global = load_data(DATA_RECOUV, COLS_RECOUV)
    if not df_global.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total à recouvrer", f"{df_global['Reste à payer'].sum():,.2f} DA")
        c2.metric("Nombre de Clients", len(df_global["Client"].unique()))
        c3.metric("En attente", len(df_global[df_global["Statut"] == "En attente"]))
        st.dataframe(df_global.sort_values("Date", ascending=False), use_container_width=True, hide_index=True)
    else:
        st.info("Base de données vide.")

# ONGLET 4 : ADMINISTRATION
with tabs[3]:
    st.subheader("Gestion de la Base Clients")
    f_cli = st.file_uploader("Importer base clients (Excel)", type=["xlsx"])
    if f_cli:
        df_cli_ex = pd.read_excel(f_cli)
        if st.button("📥 Fusionner"):
            old_cli = load_data(DATA_CLIENTS, COLS_CLIENTS)
            # Sécurité colonnes
            cols_ok = [c for c in COLS_CLIENTS if c in df_cli_ex.columns]
            updated_cli = pd.concat([old_cli, df_cli_ex[cols_ok]], ignore_index=True).drop_duplicates(subset=["Nom Client"])
            save_data(updated_cli, DATA_CLIENTS)
            st.success("Base clients mise à jour.")
            st.rerun()
    
    base_actuelle = load_data(DATA_CLIENTS, COLS_CLIENTS)
    edited_base = st.data_editor(base_actuelle, use_container_width=True, num_rows="dynamic")
    if st.button("💾 Sauvegarder Base"):
        save_data(edited_base, DATA_CLIENTS)
        st.rerun()
