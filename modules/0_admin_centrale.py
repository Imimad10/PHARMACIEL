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
            mapping.update({c: "ddp" for c in cols if c.lower() in ["ddp", "peremption", "péremption", "exp", "date"]})
            mapping.update({c: "ppa" for c in cols if c.lower() in ["ppa", "prix public", "prix"]})
            mapping.update({c: "shp" for c in cols if c.lower() in ["shp", "tarif"]})
        
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
                db_path, db_cols, key = "data_inventaire_detail/master_detail.csv", ["depot", "zone", "produit", "lot", "qte_logi", "colissage", "ddp", "ppa", "shp"], "lot"
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
                
                if target == "Master_Inventaire_Zone":
                    # Remplacement COMPLET pour l'inventaire
                    df_merged = df_up[cols_to_keep]
                    if 'inv_work_df' in st.session_state:
                        del st.session_state.inv_work_df
                else:
                    # Fusion / Ajout pour les autres bases
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
    
    c1, c2, c3 = st.columns(3)
    if c1.button("💾 Sauvegarder", key="btn_save_clients", use_container_width=True):
        save_gs_data(edited_clients, "Base_Clients", DATA_CLIENTS)
        st.success("Base Clients mise à jour !")

    if c2.button("📥 Importer depuis Secteurs", key="btn_import_secteurs", use_container_width=True):
        df_sec = load_gs_data("Secteurs", DATA_SECTEURS, COLS_SECTEURS)
        rows = []
        for _, row in df_sec.iterrows():
            rows.append({
                "Nom Client": str(row.get("Client", "")),
                "Région":     str(row.get("Ville", "")),
                "Téléphone":  str(row.get("Tel", "")),
                "Secteur":    str(row.get("Secteur", ""))
            })
        df_new_clients = pd.DataFrame(rows, columns=COLS_CLIENTS)
        df_old_clients = load_gs_data("Base_Clients", DATA_CLIENTS, COLS_CLIENTS)
        df_merged = pd.concat([df_old_clients, df_new_clients], ignore_index=True).drop_duplicates(subset=["Nom Client"])
        save_gs_data(df_merged, "Base_Clients", DATA_CLIENTS)
        st.success(f"✅ Clients importés depuis Secteurs Logistique !")
        st.cache_data.clear()
        st.rerun()

    if c3.button("🔄 Transmettre vers Secteurs", key="btn_sync_secteurs", use_container_width=True, type="primary"):
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
    
    # --- AJOUT ---
    with st.expander("➕ Ajouter un nouveau Livreur"):
        with st.form("form_add_livreur", clear_on_submit=True):
            c_a1, c_a2, c_a3, c_a4 = st.columns(4)
            n_nom = c_a1.text_input("Nom*")
            n_pre = c_a2.text_input("Prénom")
            n_tel = c_a3.text_input("Téléphone")
            n_sec = c_a4.text_input("Secteur")
            
            if st.form_submit_button("Ajouter", type="primary"):
                if n_nom:
                    new_liv = pd.DataFrame([{"Nom": n_nom.upper(), "Prénom": n_pre.capitalize(), "Téléphone": n_tel, "Secteur": n_sec.upper()}])
                    df_liv = pd.concat([df_liv, new_liv], ignore_index=True)
                    save_gs_data(df_liv, "Livreurs", DATA_LIVREURS)
                    st.success("Livreur ajouté avec succès !")
                    st.rerun()
                else:
                    st.error("Le Nom est obligatoire.")

    st.divider()

    # --- ÉTAT DE SESSION POUR L'ÉDITION ---
    if 'edit_liv_idx' not in st.session_state: st.session_state.edit_liv_idx = None
    if 'del_liv_idx' not in st.session_state: st.session_state.del_liv_idx = None

    if not df_liv.empty:
        # En-têtes
        h1, h2, h3, h4, h5 = st.columns([2, 2, 2, 2, 2])
        h1.markdown("**Nom**")
        h2.markdown("**Prénom**")
        h3.markdown("**Téléphone**")
        h4.markdown("**Secteur**")
        h5.markdown("**Actions**")
        st.write("---")

        for idx, row in df_liv.iterrows():
            with st.container():
                # MODE ÉDITION
                if st.session_state.edit_liv_idx == idx:
                    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 2])
                    e_nom = c1.text_input("Nom", value=str(row.get('Nom', '')), key=f"en_{idx}", label_visibility="collapsed")
                    e_pre = c2.text_input("Prénom", value=str(row.get('Prénom', '')), key=f"ep_{idx}", label_visibility="collapsed")
                    e_tel = c3.text_input("Téléphone", value=str(row.get('Téléphone', '')), key=f"et_{idx}", label_visibility="collapsed")
                    e_sec = c4.text_input("Secteur", value=str(row.get('Secteur', '')), key=f"es_{idx}", label_visibility="collapsed")
                    
                    ca, cb = c5.columns(2)
                    if ca.button("💾", key=f"save_{idx}", help="Enregistrer"):
                        df_liv.at[idx, 'Nom'] = e_nom.upper()
                        df_liv.at[idx, 'Prénom'] = e_pre.capitalize()
                        df_liv.at[idx, 'Téléphone'] = e_tel
                        df_liv.at[idx, 'Secteur'] = e_sec.upper()
                        save_gs_data(df_liv, "Livreurs", DATA_LIVREURS)
                        st.session_state.edit_liv_idx = None
                        st.rerun()
                    if cb.button("❌", key=f"canc_ed_{idx}", help="Annuler"):
                        st.session_state.edit_liv_idx = None
                        st.rerun()

                # MODE SUPPRESSION
                elif st.session_state.del_liv_idx == idx:
                    st.warning(f"⚠️ Voulez-vous vraiment supprimer **{row.get('Nom', '')}** ?")
                    c1, c2 = st.columns(2)
                    if c1.button("✅ Confirmer la suppression", key=f"conf_del_{idx}", type="primary"):
                        df_liv = df_liv.drop(idx)
                        save_gs_data(df_liv, "Livreurs", DATA_LIVREURS)
                        st.session_state.del_liv_idx = None
                        st.success("Supprimé !")
                        st.rerun()
                    if c2.button("🚫 Annuler", key=f"canc_del_{idx}"):
                        st.session_state.del_liv_idx = None
                        st.rerun()

                # MODE NORMAL (AFFICHAGE)
                else:
                    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 2])
                    c1.write(str(row.get('Nom', '')))
                    c2.write(str(row.get('Prénom', '')))
                    c3.write(str(row.get('Téléphone', '')))
                    c4.write(str(row.get('Secteur', '')))
                    
                    ca, cb = c5.columns(2)
                    if ca.button("✏️", key=f"ed_{idx}", help="Modifier cette ligne"):
                        st.session_state.edit_liv_idx = idx
                        st.session_state.del_liv_idx = None
                        st.rerun()
                    if cb.button("🗑️", key=f"del_{idx}", help="Supprimer cette ligne"):
                        st.session_state.del_liv_idx = idx
                        st.session_state.edit_liv_idx = None
                        st.rerun()
                st.write("---")
    else:
        st.info("Aucun livreur enregistré pour le moment.")

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
