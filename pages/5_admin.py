import streamlit as st
import pandas as pd
from tinydb import TinyDB, Query
import os
import shutil
from utils import log_action

# Sécurité
if "current_user" not in st.session_state or st.session_state.current_user is None or st.session_state.current_user.get('role') != 'Admin':
    st.error("Accès refusé.")
    st.stop()

st.title("⚙️ Administration Centrale - Darpharm Solution")
st.write("Gérez les utilisateurs, leurs rôles et leurs accès aux différentes pages de l'application.")

db_users = TinyDB('data/db_users.json')
users = db_users.all()

st.subheader("👥 Liste des Utilisateurs")

# Affichage des utilisateurs avec un mot de passe masqué
df_users = pd.DataFrame(users)
if not df_users.empty:
    df_display = df_users.copy()
    df_display['password'] = "********"
    st.dataframe(df_display[['username', 'role', 'pages', 'password']], use_container_width=True)

st.divider()

tab_add, tab_edit, tab_del, tab_logs, tab_backup, tab_ia = st.tabs([
    "➕ Ajouter", "✏️ Modifier", "🗑️ Supprimer", "📝 Traçabilité (Logs)", "💾 Sauvegarde", "🤖 Configuration IA"
])

MODULES_DISPO = ["Logistique", "Inventaire", "Suivi", "Recouvrement", "Pointage", "Péremptions", "Dashboard"]

with tab_add:
    st.subheader("Créer un nouvel utilisateur")
    with st.form("form_add_user"):
        u_name = st.text_input("Nom d'utilisateur")
        u_pwd = st.text_input("Mot de passe")
        u_role = st.selectbox("Rôle", ["Saisie", "Admin"])
        u_pages = st.multiselect("Accès aux modules", MODULES_DISPO)
        
        if st.form_submit_button("Créer l'utilisateur"):
            User = Query()
            if db_users.search(User.username == u_name):
                st.error("Ce nom d'utilisateur existe déjà !")
            elif u_name and u_pwd:
                db_users.insert({
                    'username': u_name,
                    'password': u_pwd,
                    'role': u_role,
                    'pages': u_pages
                })
                st.success(f"Utilisateur {u_name} créé !")
                log_action(st.session_state.current_user['username'], f"Création de l'utilisateur {u_name}", "Administration")
                st.rerun()
            else:
                st.error("Nom d'utilisateur et mot de passe requis.")

with tab_edit:
    st.subheader("Modifier les accès ou le mot de passe")
    
    # Sélection de l'utilisateur à modifier
    edit_target = st.selectbox("Sélectionner l'utilisateur", [u['username'] for u in users])
    
    if edit_target:
        # Récupération des données actuelles
        target_data = next((u for u in users if u['username'] == edit_target), None)
        
        with st.form("form_edit_user"):
            st.write(f"Modifications pour : **{edit_target}**")
            new_pwd = st.text_input("Nouveau mot de passe", value=target_data.get('password', ''))
            
            role_idx = 0 if target_data.get('role') == 'Saisie' else 1
            new_role = st.selectbox("Nouveau rôle", ["Saisie", "Admin"], index=role_idx)
            
            current_pages = [p for p in target_data.get('pages', []) if p in MODULES_DISPO]
            new_pages = st.multiselect("Accès aux modules", MODULES_DISPO, default=current_pages)
            
            if st.form_submit_button("Mettre à jour"):
                if new_pwd:
                    User = Query()
                    db_users.update({
                        'password': new_pwd,
                        'role': new_role,
                        'pages': new_pages
                    }, User.username == edit_target)
                    
                    # Si l'admin modifie son propre profil, on met à jour la session
                    if edit_target == st.session_state.current_user['username']:
                        st.session_state.current_user['password'] = new_pwd
                        st.session_state.current_user['role'] = new_role
                        st.session_state.current_user['pages'] = new_pages
                    
                    st.success(f"Profil de {edit_target} mis à jour !")
                    log_action(st.session_state.current_user['username'], f"Modification de l'utilisateur {edit_target}", "Administration")
                    st.rerun()
                else:
                    st.error("Le mot de passe ne peut pas être vide.")

with tab_del:
    st.subheader("Supprimer définitivement un utilisateur")
    del_options = [u['username'] for u in users if u['username'] != st.session_state.current_user['username']]
    
    if not del_options:
        st.info("Aucun autre utilisateur à supprimer.")
    else:
        with st.form("form_del_user"):
            u_del = st.selectbox("Sélectionner l'utilisateur à supprimer", del_options)
            st.warning("⚠️ Cette action est irréversible.")
            if st.form_submit_button("Confirmer la suppression"):
                User = Query()
                db_users.remove(User.username == u_del)
                st.success(f"Utilisateur {u_del} supprimé.")
                log_action(st.session_state.current_user['username'], f"Suppression de l'utilisateur {u_del}", "Administration")
                st.rerun()

with tab_logs:
    st.subheader("📝 Historique des actions (Logs)")
    if os.path.exists('data/db_logs.json'):
        db_logs = TinyDB('data/db_logs.json')
        logs = db_logs.all()
        if logs:
            df_logs = pd.DataFrame(logs)
            st.dataframe(df_logs.sort_values(by='timestamp', ascending=False), use_container_width=True)
        else:
            st.info("Aucun log disponible pour le moment.")
    else:
        st.info("La base de logs n'a pas encore été créée.")

with tab_backup:
    st.subheader("💾 Sauvegarde complète du système")
    st.write("Générez une archive contenant toutes les bases de données (Utilisateurs, Logs, Inventaires, Frigo...).")
    
    if st.button("📦 Générer le fichier de sauvegarde (ZIP)", use_container_width=True):
        try:
            # Créer un dossier temporaire pour rassembler les fichiers
            backup_dir = "backup_temp"
            os.makedirs(backup_dir, exist_ok=True)
            
            # Copier les dossiers/fichiers cibles
            targets = ["data", "data_expedition", "data_inventaire", "suivi_data.csv", "base_clients.csv", "data_recouvrement.csv", "db_pharmaciel.json"]
            for target in targets:
                if os.path.exists(target):
                    if os.path.isdir(target):
                        shutil.copytree(target, os.path.join(backup_dir, target), dirs_exist_ok=True)
                    else:
                        shutil.copy2(target, backup_dir)
            
            # Créer l'archive zip
            zip_filename = "Darpharm Solution_Backup"
            shutil.make_archive(zip_filename, 'zip', backup_dir)
            
            # Nettoyer le dossier temporaire
            shutil.rmtree(backup_dir)
            
            # Proposer le téléchargement
            with open(f"{zip_filename}.zip", "rb") as f:
                st.download_button("📥 Télécharger la sauvegarde (.zip)", f, file_name=f"{zip_filename}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.zip", mime="application/zip", type="primary", use_container_width=True)
                
            log_action(st.session_state.current_user['username'], "Génération d'une sauvegarde ZIP", "Administration")
        except Exception as e:
            st.error(f"Erreur lors de la sauvegarde : {e}")

with tab_ia:
    st.subheader("🤖 Configuration de l'Intelligence Artificielle")
    st.write("Configurez ici la clé API Google Gemini pour faire fonctionner le scanner de factures. Plus besoin de modifier les fichiers de secrets complexes !")
    
    db_settings = TinyDB('data/db_settings.json')
    Setting = Query()
    ia_setting = db_settings.search(Setting.name == 'gemini_api_key')
    current_key = ia_setting[0]['value'] if ia_setting else ""
    
    with st.form("form_ia_config"):
        new_key = st.text_input("Clé API Gemini", value=current_key, type="password", help="Obtenez une clé gratuite sur https://aistudio.google.com/app/apikey")
        if st.form_submit_button("Sauvegarder la clé", use_container_width=True):
            if ia_setting:
                db_settings.update({'value': new_key}, Setting.name == 'gemini_api_key')
            else:
                db_settings.insert({'name': 'gemini_api_key', 'value': new_key})
            st.success("✅ Clé API sauvegardée avec succès ! Le scanner de factures est désormais opérationnel.")
            log_action(st.session_state.current_user['username'], "Mise à jour de la clé API IA", "Administration")
            st.rerun()
