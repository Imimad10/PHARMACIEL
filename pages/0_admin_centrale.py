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
        st.write("Aperçu des données détectées :")
        st.dataframe(df_up.head(5), use_container_width=True)
        
        # Détection automatique
        cols = df_up.columns.tolist()
        
        target = None
        if any(c in cols for c in ["Raison sociale", "Nom Client", "Nom"]):
            if "Secteur" in cols and "Ville" in cols:
                target = "Secteurs"
                mapping = {"Client": "Client", "Ville": "Ville", "Secteur": "Secteur", "Tel": "Tel", "tel": "Tel"}
            elif "Nom" in cols and "Prénom" in cols:
                target = "Livreurs"
                mapping = {"Nom": "Nom", "Prénom": "Prénom", "Secteur": "Secteur"}
            else:
                target = "Base_Clients"
                mapping = {"Raison sociale": "Nom Client", "Nom Client": "Nom Client", "Région": "Région", "Téléphone": "Téléphone"}
        
        if target:
            st.success(f"🎯 Type détecté : **{target}**")
            if st.button(f"📥 Fusionner avec la base {target}", type="primary", use_container_width=True):
                # Mapping et nettoyage
                df_up = df_up.rename(columns=mapping)
                
                # Chargement de la base actuelle
                if target == "Base_Clients":
                    db_path, db_cols = DATA_CLIENTS, COLS_CLIENTS
                    key = "Nom Client"
                elif target == "Livreurs":
                    db_path, db_cols = DATA_LIVREURS, COLS_LIVREURS
                    key = "Nom"
                else:
                    db_path, db_cols = DATA_SECTEURS, COLS_SECTEURS
                    key = "Client"
                
                df_old = load_gs_data(target, db_path, db_cols)
                cols_to_keep = [c for c in db_cols if c in df_up.columns]
                df_new = pd.concat([df_old, df_up[cols_to_keep]], ignore_index=True).drop_duplicates(subset=[key])
                
                save_gs_data(df_new, target, db_path)
                st.success(f"✅ Migration réussie vers {target} ({len(df_up)} lignes traitées).")
                log_action(st.session_state.current_user['username'], f"Importation Master Data : {target}", "Admin Centrale")
                st.rerun()
        else:
            st.warning("Impossible de détecter automatiquement le type de données. Assurez-vous que les colonnes sont correctement nommées.")

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
