import streamlit as st
import pandas as pd
from tinydb import TinyDB, Query
import os
import shutil
from utils import log_action

# Sécurité
user = st.session_state.get('current_user')
if not user or user.get('role') not in ['Admin', 'Superviseur']:
    st.error("Accès refusé.")
    st.stop()

is_admin = user.get('role') == 'Admin'

st.title("👥 Gestion d'Équipe & Zones")
st.write("Gérez les utilisateurs et leurs zones d'affectation pour l'inventaire détail.")

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

if is_admin:
    tab_list = ["➕ Ajouter", "✏️ Modifier", "🗑️ Supprimer", "📝 Traçabilité (Logs)", "💾 Sauvegarde", "🤖 Configuration IA"]
else:
    tab_list = ["📍 Affectation des Zones"]

tabs = st.tabs(tab_list)

# Mapping des index selon le rôle
if is_admin:
    tab_add, tab_edit, tab_del, tab_logs, tab_backup, tab_ia = tabs
else:
    tab_edit = tabs[0]
    # On désactive les autres onglets pour le superviseur
    tab_add = tab_del = tab_logs = tab_backup = tab_ia = None

MODULES_DISPO = ["Dashboard", "Logistique", "Inventaire", "Inventaire Détail", "Suivi", "Recouvrement", "Pointage", "Péremptions", "Scanneur QR", "Automatisation", "Litiges Fournisseurs", "Analyse Rotation", "Scan Mobile"]

if tab_add:
    with tab_add:
        st.subheader("Créer un nouvel utilisateur")
        with st.form("form_add_user"):
            u_name = st.text_input("Nom d'utilisateur")
            u_pwd = st.text_input("Mot de passe")
            u_role = st.selectbox("Rôle", ["Saisie", "Superviseur", "Admin"])
            
            # Suggestion automatique de pages selon le rôle
            default_p = []
            if u_role == "Superviseur":
                default_p = ["Dashboard", "Logistique", "Inventaire Détail", "Scanneur QR", "Suivi"]
            elif u_role == "Saisie":
                default_p = ["Logistique", "Inventaire", "Inventaire Détail"]
                
            u_pages = st.multiselect("Accès aux modules", MODULES_DISPO, default=default_p)
            u_zone = st.selectbox("Zone Attribuée (Inventaire Détail)", ["Aucune", "A", "B", "C", "D", "Frigo"])
            
            if st.form_submit_button("Créer l'utilisateur"):
                User = Query()
                if db_users.search(User.username == u_name):
                    st.error("Ce nom d'utilisateur existe déjà !")
                elif u_name and u_pwd:
                    db_users.insert({
                        'username': u_name,
                        'password': u_pwd,
                        'role': u_role,
                        'pages': u_pages,
                        'zone': u_zone
                    })
                    st.success(f"Utilisateur {u_name} créé !")
                    log_action(st.session_state.current_user['username'], f"Création de l'utilisateur {u_name}", "Administration")
                    st.rerun()
                else:
                    st.error("Nom d'utilisateur et mot de passe requis.")

if tab_edit:
    with tab_edit:
        st.subheader("Modifier les accès ou le mot de passe" if is_admin else "Affecter une zone de préparation")
        
        # Sélection de l'utilisateur à modifier
        edit_target = st.selectbox("Sélectionner l'utilisateur", [u['username'] for u in users])
        
        if edit_target:
            target_data = next((u for u in users if u['username'] == edit_target), None)
            
            with st.form("form_edit_user"):
                st.write(f"Modifications pour : **{edit_target}**")
                
                if is_admin:
                    new_pwd = st.text_input("Nouveau mot de passe", value=target_data.get('password', ''))
                    role_list = ["Saisie", "Superviseur", "Admin"]
                    current_role = target_data.get('role', 'Saisie')
                    new_role = st.selectbox("Nouveau rôle", role_list, index=role_list.index(current_role) if current_role in role_list else 0)
                    current_pages = [p for p in target_data.get('pages', []) if p in MODULES_DISPO]
                    new_pages = st.multiselect("Accès aux modules", MODULES_DISPO, default=current_pages)
                else:
                    # Superviseur : lecture seule sur les infos sensibles
                    st.info(f"Rôle actuel : {target_data.get('role')}")
                    new_pwd = target_data.get('password')
                    new_role = target_data.get('role')
                    new_pages = target_data.get('pages')

                zones_list = ["Aucune", "A", "B", "C", "D", "Frigo"]
                current_zone = target_data.get('zone', 'Aucune')
                new_zone = st.selectbox("Nouvelle zone d'inventaire", zones_list, index=zones_list.index(current_zone) if current_zone in zones_list else 0)
                
                if st.form_submit_button("Valider l'affectation" if not is_admin else "Mettre à jour"):
                    User = Query()
                    db_users.update({
                        'password': new_pwd,
                        'role': new_role,
                        'pages': new_pages,
                        'zone': new_zone
                    }, User.username == edit_target)
                    st.success("Mise à jour réussie !")
                    st.rerun()



if tab_del:
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

if tab_logs:
    with tab_logs:
        st.subheader("📝 Historique des actions (Logs)")
        if os.path.exists('data/db_logs.json'):
            db_logs = TinyDB('data/db_logs.json')
            logs = db_logs.all()
            if logs:
                df_logs = pd.DataFrame(logs)
                st.dataframe(df_logs.sort_values(by='timestamp', ascending=False), use_container_width=True)
            else:
                st.info("Aucun log disponible.")
            if st.button("🗑️ Nettoyer tout l'historique"):
                db_logs.truncate()
                st.success("Historique vidé !")
                st.rerun()

if tab_backup:
    with tab_backup:
        st.subheader("💾 Sauvegarde complète du système")
        if st.button("📦 Générer le fichier de sauvegarde (ZIP)", use_container_width=True):
            try:
                backup_dir = "backup_temp"
                os.makedirs(backup_dir, exist_ok=True)
                targets = ["data", "data_expedition", "data_inventaire", "suivi_data.csv", "base_clients.csv", "data_recouvrement.csv", "db_pharmaciel.json"]
                for target in targets:
                    if os.path.exists(target):
                        if os.path.isdir(target): shutil.copytree(target, os.path.join(backup_dir, target), dirs_exist_ok=True)
                        else: shutil.copy2(target, backup_dir)
                zip_filename = "Darpharm_Backup"
                shutil.make_archive(zip_filename, 'zip', backup_dir)
                shutil.rmtree(backup_dir)
                with open(f"{zip_filename}.zip", "rb") as f:
                    st.download_button("📥 Télécharger ZIP", f, file_name=f"{zip_filename}.zip", mime="application/zip", use_container_width=True)
                log_action(user['username'], "Génération Sauvegarde ZIP", "Admin")
            except Exception as e: st.error(f"Erreur : {e}")

if tab_ia:
    with tab_ia:
        if is_admin:
            st.subheader("🤖 Configuration de l'Intelligence Artificielle")
            db_settings = TinyDB('data/db_settings.json')
            Setting = Query()
            def get_setting(name, default=""):
                res = db_settings.search(Setting.name == name)
                return res[0]['value'] if res else default
                
            with st.form("form_ia_config_admin"):
                ia_en = st.checkbox("🚀 Activer l'IA globalement", value=get_setting('ia_global_enabled', 'True') == 'True')
                providers = ["Gemini (Google)", "Claude (Anthropic)", "ChatGPT (OpenAI)", "Grok (xAI)"]
                active_p = st.selectbox("Moteur par défaut", providers, index=providers.index(get_setting('active_ai_provider', 'Gemini (Google)')))
                
                st.write("---")
                new_gemini = st.text_input("Clé API Gemini (Google)", value=get_setting('gemini_api_key'), type="password")
                new_claude = st.text_input("Clé API Claude (Anthropic)", value=get_setting('anthropic_api_key'), type="password")
                new_openai = st.text_input("Clé API ChatGPT (OpenAI)", value=get_setting('openai_api_key'), type="password")
                
                if st.form_submit_button("💾 Sauvegarder la configuration IA", use_container_width=True):
                    def save_set(name, val):
                        if db_settings.search(Setting.name == name): db_settings.update({'value': val}, Setting.name == name)
                        else: db_settings.insert({'name': name, 'value': val})
                    save_set('gemini_api_key', new_gemini)
                    save_set('anthropic_api_key', new_claude)
                    save_set('openai_api_key', new_openai)
                    save_set('active_ai_provider', active_p)
                    save_set('ia_global_enabled', str(ia_en))
                    st.success("✅ Configuration IA mise à jour avec succès !")
                    st.rerun()
        else:
            st.warning("⚠️ Accès restreint. Seuls les administrateurs peuvent configurer l'IA.")
