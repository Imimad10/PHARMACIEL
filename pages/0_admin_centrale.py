import streamlit as st
import pandas as pd
import os
from datetime import datetime
from utils_gsheets import load_gs_data, save_gs_data, get_gs_client, get_gs_url
from utils import log_action

# --- CONFIGURATION ---
DATA_CLIENTS = "base_clients.csv"
DATA_LIVREURS = "data_expedition/livreurs.csv"
DATA_SECTEURS = "data_expedition/secteurs.csv"

COLS_CLIENTS = ["Nom Client", "Région", "Téléphone", "Secteur"]
COLS_LIVREURS = ["Nom", "Prénom", "Téléphone", "Secteur"]
COLS_SECTEURS = ["Client", "Ville", "Tel", "Secteur"]

# Sécurité
if "current_user" not in st.session_state or st.session_state.current_user is None:
    st.warning("Veuillez vous connecter.")
    st.stop()

if st.session_state.current_user.get('role') not in ['Admin', 'Superviseur']:
    st.error("Accès réservé à l'administration.")
    st.stop()

st.set_page_config(page_title="Administration Centrale", layout="wide")
st.title("🏛️ Administration Centrale (Master Data)")
st.write("Gestion centralisée des clients, livreurs et secteurs pour tous les modules.")

# --- TABS ---
tabs = st.tabs(["📤 Importateur Universel", "👥 Base Clients", "🚚 Livreurs", "🗺️ Secteurs Logistique"])

# ONGLET 0 : IMPORTATEUR UNIVERSEL (DRAG & DROP)
with tabs[0]:
    st.subheader("🚀 Importation Centralisée")
    st.info("Déposez un fichier Excel contenant vos données. Le système détectera automatiquement s'il s'agit de clients, de livreurs ou de secteurs.")
    
    f_up = st.file_uploader("Fichier Master Data (Excel)", type=["xlsx"])
    if f_up:
        df_up = pd.read_excel(f_up)
        
        # Détection automatique du type de données
        cols = [str(c).strip() for c in df_up.columns.tolist()]
        cols_lower = [c.lower() for c in cols]
        
        target = None
        mapping = {}

        if "prenom" in cols_lower or "prénom" in cols_lower:
            target = "Livreurs"
            mapping = {c: "Prénom" for c in cols if c.lower() in ["prenom","prénom"]}
            mapping.update({c: "Nom" for c in cols if c.lower() == "nom"})
            mapping.update({c: "Secteur" for c in cols if c.lower() == "secteur"})
            mapping.update({c: "Téléphone" for c in cols if c.lower() in ["téléphone","telephone","tel"]})
        elif "ville" in cols_lower:
            target = "Secteurs"
            mapping = {c: "Client" for c in cols if c.lower() in ["client","raison sociale","raison sociale","nom client"]}
            mapping.update({c: "Ville" for c in cols if c.lower() == "ville"})
            mapping.update({c: "Secteur" for c in cols if c.lower() == "secteur"})
            mapping.update({c: "Tel" for c in cols if c.lower() in ["tel","téléphone","telephone"]})
        elif any(c.lower() in ["raison sociale","nom client","nom"] for c in cols):
            target = "Base_Clients"
            mapping = {c: "Nom Client" for c in cols if c.lower() in ["raison sociale","nom client","nom"]}
            mapping.update({c: "Région" for c in cols if c.lower() in ["région","region"]})
            mapping.update({c: "Secteur" for c in cols if c.lower() == "secteur"})
            mapping.update({c: "Téléphone" for c in cols if c.lower() in ["téléphone","telephone","tel"]})
        
        st.write("**Aperçu des données :**")
        st.dataframe(df_up.head(5), use_container_width=True)
        
        if target:
            st.success(f"🎯 Type détecté : **{target}**")
            if st.button(f"📥 Fusionner avec la base {target}", type="primary", use_container_width=True):
                df_up = df_up.rename(columns=mapping)
                
                if target == "Base_Clients":
                    db_path, db_cols, key = DATA_CLIENTS, COLS_CLIENTS, "Nom Client"
                    # Région = Secteur si Secteur vide
                    if "Région" in df_up.columns and ("Secteur" not in df_up.columns or df_up["Secteur"].isnull().all()):
                        df_up["Secteur"] = df_up["Région"]
                elif target == "Livreurs":
                    db_path, db_cols, key = DATA_LIVREURS, COLS_LIVREURS, "Nom"
                else:
                    db_path, db_cols, key = DATA_SECTEURS, COLS_SECTEURS, "Client"
                
                df_old = load_gs_data(target, db_path, db_cols)
                cols_to_keep = [c for c in db_cols if c in df_up.columns]
                df_merged = pd.concat([df_old, df_up[cols_to_keep]], ignore_index=True).drop_duplicates(subset=[key])
                
                save_gs_data(df_merged, target, db_path)
                st.success(f"✅ Migration réussie vers **{target}** — {len(df_up)} lignes traitées.")
                log_action(st.session_state.current_user['username'], f"Import Master Data : {target}", "Admin Centrale")
                st.cache_data.clear()
                st.rerun()
        else:
            st.warning("⚠️ Type non reconnu. Vérifiez que vos colonnes sont nommées : 'Raison sociale', 'Prénom', ou 'Ville'.")

# ONGLET 1 : BASE CLIENTS
with tabs[1]:
    st.subheader("👥 Annuaire Général des Clients")
    df_clients = load_gs_data("Base_Clients", DATA_CLIENTS, COLS_CLIENTS)
    edited_clients = st.data_editor(df_clients, use_container_width=True, num_rows="dynamic", key="editor_clients")
    if st.button("💾 Sauvegarder Clients", key="btn_save_clients"):
        save_gs_data(edited_clients, "Base_Clients", DATA_CLIENTS)
        st.success("Base Clients mise à jour !")

# ONGLET 2 : LIVREURS
with tabs[2]:
    st.subheader("🚚 Gestion des Livreurs")
    df_liv = load_gs_data("Livreurs", DATA_LIVREURS, COLS_LIVREURS)
    edited_liv = st.data_editor(df_liv, use_container_width=True, num_rows="dynamic", key="editor_liv")
    if st.button("💾 Sauvegarder Livreurs", key="btn_save_liv"):
        save_gs_data(edited_liv, "Livreurs", DATA_LIVREURS)
        st.success("Liste des Livreurs mise à jour !")

# ONGLET 3 : SECTEURS
with tabs[3]:
    st.subheader("🗺️ Cartographie Secteurs & Clients Logistique")
    df_sec = load_gs_data("Secteurs", DATA_SECTEURS, COLS_SECTEURS)
    edited_sec = st.data_editor(df_sec, use_container_width=True, num_rows="dynamic", key="editor_sec")
    if st.button("💾 Sauvegarder Secteurs", key="btn_save_sec"):
        save_gs_data(edited_sec, "Secteurs", DATA_SECTEURS)
        st.success("Cartographie des Secteurs mise à jour !")
