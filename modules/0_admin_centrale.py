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
tabs = st.tabs(["📤 Importateur Universel", "👥 Base Clients", "🚚 Livreurs", "🗺️ Secteurs Logistique", "📦 Archivage Cloud"])

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
        
        elif "username" in cols_lower:
            target = "Utilisateurs"
            mapping = {c: "username" for c in cols if c.lower() == "username"}
            mapping.update({c: "password" for c in cols if c.lower() in ["password", "mot de passe", "pwd"]})
            mapping.update({c: "nom" for c in cols if c.lower() == "nom"})
            mapping.update({c: "prenom" for c in cols if c.lower() in ["prenom", "prénom"]})
            mapping.update({c: "role" for c in cols if c.lower() in ["role", "rôle"]})
            mapping.update({c: "zone" for c in cols if c.lower() == "zone"})
            mapping.update({c: "pages" for c in cols if c.lower() == "pages"})
        
        elif any(x in cols_lower for x in ["dépôt", "depot", "quantité dépôt", "quantité depot", "qte.globale"]):
            target = "Master_Inventaire_Zone"
            mapping = {c: "depot" for c in cols if c.lower() in ["dépôt", "depot"]}
            mapping.update({c: "produit" for c in cols if c.lower() in ["produit", "article", "désignation", "designation"]})
            mapping.update({c: "lot" for c in cols if c.lower() in ["n°lot", "lot", "batch", "nlot"]})
            mapping.update({c: "qte_logi" for c in cols if c.lower() in ["quantité dépôt", "quantité depot", "qte.globale", "quantité", "qte"]})
            mapping.update({c: "colissage" for c in cols if c.lower() in ["colis", "u/colis", "colissage", "nbr colis"]})
            mapping.update({c: "zone" for c in cols if c.lower() in ["zone produit", "zone", "emplacement"]})
        
        st.write("**Aperçu des données :**")
        st.dataframe(df_up.head(5), use_container_width=True)
        
        if target:
            st.success(f"🎯 Type détecté : **{target}**")
            
            # Définition des paramètres de destination
            if target == "Base_Clients":
                db_path, db_cols, key = DATA_CLIENTS, COLS_CLIENTS, "Nom Client"
            elif target == "Livreurs":
                db_path, db_cols, key = DATA_LIVREURS, COLS_LIVREURS, "Nom"
            elif target == "Utilisateurs":
                from utils_gsheets import DB_USERS_WORKSHEET, DB_USERS_FALLBACK
                db_path, db_cols, key = DB_USERS_FALLBACK, ["username", "password", "role", "pages", "nom", "prenom", "zone"], "username"
            elif target == "Master_Inventaire_Zone":
                db_path, db_cols, key = "data_inventaire_detail/master_detail.csv", ["depot", "zone", "produit", "lot", "qte_logi", "colissage"], "lot"
            else:
                db_path, db_cols, key = DATA_SECTEURS, COLS_SECTEURS, "Client"

            if st.button(f"📥 Fusionner avec la base {target}", type="primary", use_container_width=True):
                # On renomme intelligemment pour éviter les colonnes en double
                new_cols = []
                mapped_targets = set()
                for c in df_up.columns:
                    target_name = mapping.get(c, c)
                    if target_name in db_cols and target_name not in mapped_targets:
                        new_cols.append(target_name)
                        mapped_targets.add(target_name)
                    else:
                        new_cols.append(f"old_{c}")
                
                df_up.columns = new_cols
                
                if target == "Base_Clients":
                    # Région = Secteur si Secteur vide
                    if "Région" in df_up.columns and ("Secteur" not in df_up.columns or df_up["Secteur"].isnull().all()):
                        df_up["Secteur"] = df_up["Région"]
                
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
    
    c1, c2 = st.columns(2)
    if c1.button("💾 Sauvegarder Clients", key="btn_save_clients", use_container_width=True):
        save_gs_data(edited_clients, "Base_Clients", DATA_CLIENTS)
        st.success("Base Clients mise à jour !")

    if c2.button("🔄 Transmettre vers Secteurs Logistique", key="btn_sync_secteurs", use_container_width=True, type="primary"):
        df_src = edited_clients.copy()
        # Construction propre du DataFrame Secteurs depuis zéro
        rows = []
        for _, row in df_src.iterrows():
            rows.append({
                "Client": str(row.get("Nom Client", "")),
                "Ville":  str(row.get("Région", "")),   # Ville = Région
                "Tel":    str(row.get("Téléphone", "")),
                "Secteur": str(row.get("Région", ""))   # Secteur = Région
            })
        df_new_sec = pd.DataFrame(rows, columns=COLS_SECTEURS)
        df_old_sec = load_gs_data("Secteurs", DATA_SECTEURS, COLS_SECTEURS)
        df_merged = pd.concat([df_old_sec, df_new_sec], ignore_index=True).drop_duplicates(subset=["Client"])
        save_gs_data(df_merged, "Secteurs", DATA_SECTEURS)
        st.success(f"✅ {len(df_new_sec)} clients transmis vers Secteurs Logistique !")
        st.cache_data.clear()

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

# ONGLET 4 : ARCHIVAGE CLOUD
with tabs[4]:
    st.subheader("📦 Archivage & Nettoyage Cloud")
    st.write("Cet outil permet de déplacer les données anciennes vers un **nouveau fichier Google Sheets** séparé pour garder la base principale légère et rapide.")
    
    col_arch1, col_arch2 = st.columns(2)
    module_to_archive = col_arch1.selectbox("Sélectionner le module à archiver", ["Logs", "Recouvrement", "Pointages", "Saisie_Inventaire"])
    
    # Paramètres par défaut selon module
    fallback_map = {
        "Logs": "data/db_logs.csv",
        "Recouvrement": "data_recouvrement.csv",
        "Pointages": "data/db_pointages.csv",
        "Saisie_Inventaire": "data_inventaire/saisie.csv"
    }
    
    archive_name = col_arch2.text_input("Nom du nouveau fichier archive", value=f"Archive_{module_to_archive}_{datetime.now().strftime('%m_%Y')}")
    
    if st.button("🚀 Créer l'archive et Vider la base actuelle", type="primary", use_container_width=True):
        from utils_gsheets import create_archive_spreadsheet
        
        # 1. Charger les données actuelles
        df_to_archive = load_gs_data(module_to_archive, fallback_map[module_to_archive], [])
        
        if not df_to_archive.empty:
            # 2. Créer le nouveau fichier
            archive_url = create_archive_spreadsheet(archive_name, df_to_archive)
            
            if archive_url:
                st.success(f"✅ Nouveau fichier Sheets créé avec succès !")
                st.markdown(f"🔗 [Cliquez ici pour ouvrir l'archive : {archive_name}]({archive_url})")
                
                # 3. Vider la base actuelle (On garde les colonnes)
                empty_df = pd.DataFrame(columns=df_to_archive.columns)
                save_gs_data(empty_df, module_to_archive, fallback_map[module_to_archive])
                
                st.warning("⚠️ La base actuelle a été vidée pour optimiser les performances.")
                log_action(st.session_state.current_user['username'], f"Archivage Cloud : {module_to_archive} -> {archive_name}", "Admin Centrale")
                st.cache_data.clear()
        else:
            st.warning("La base sélectionnée est déjà vide.")
