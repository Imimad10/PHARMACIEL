import streamlit as st
import pandas as pd
import os
import shutil
from utils_gsheets import load_gs_data, save_gs_data, DB_USERS_WORKSHEET, DB_USERS_FALLBACK

# Configuration GSheets pour Admin
DB_LOGS_WORKSHEET = "Logs"
DB_LOGS_FALLBACK = "data/db_logs.csv"
COLS_LOGS = ["timestamp", "user", "module", "action"]

DB_SETTINGS_WORKSHEET = "Settings"
DB_SETTINGS_FALLBACK = "data/db_settings.csv"
COLS_SETTINGS = ["name", "value"]

# Sécurité
user = st.session_state.get('current_user')
if not user or user.get('role') not in ['Admin', 'Superviseur']:
    st.error("Accès refusé.")
    st.stop()

is_admin = user.get('role') == 'Admin'

st.title("👥 Gestion d'Équipe & Zones")
st.write("Gérez les utilisateurs et leurs zones d'affectation pour l'inventaire détail.")

# Chargement des utilisateurs via GSheets
df_users = load_gs_data(DB_USERS_WORKSHEET, DB_USERS_FALLBACK, ["username", "password", "role", "pages", "nom", "prenom", "zone"])

# Conversion sécurisée des pages pour tout le dataframe
def parse_pages(p):
    if isinstance(p, list): return p
    if not isinstance(p, str) or not p.strip(): return []
    import ast
    try: return ast.literal_eval(p)
    except: return [x.strip() for x in p.replace('[','').replace(']','').replace("'","").split(',') if x.strip()]

if not df_users.empty:
    df_users['pages'] = df_users['pages'].apply(parse_pages)

st.subheader("👥 Liste des Utilisateurs")

# Affichage des utilisateurs avec un mot de passe masqué
if not df_users.empty:
    df_display = df_users.copy()
    df_display['password'] = "********"
    # Convertir les listes en strings lisibles pour le st.dataframe
    df_display['pages'] = df_display['pages'].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x))
    # S'assurer que les colonnes existent
    needed = ['username', 'role', 'pages', 'password']
    cols_avail = [c for c in needed if c in df_display.columns]
    st.dataframe(df_display[cols_avail], use_container_width=True)

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

def get_available_modules():
    import re
    modules = ["Admin Centrale"]
    try:
        with open("app.py", "r", encoding="utf-8") as f:
            content = f.read()
            match = re.search(r'ALL_PAGES\s*=\s*\{(.*?)\}', content, re.DOTALL)
            if match:
                dict_content = match.group(1)
                keys = re.findall(r'"([^"]+)"\s*:\s*st\.Page', dict_content)
                for k in keys:
                    if k not in modules:
                        modules.append(k)
            
            if 'ALL_PAGES["Automatisation"]' in content and "Automatisation" not in modules:
                modules.append("Automatisation")
    except:
        modules = ["Admin Centrale", "Dashboard", "Logistique", "Inventaire", "Inventaire Détail", "Suivi", "Recouvrement", "Pointage", "Péremptions", "Scanneur QR", "Automatisation", "Litiges Fournisseurs", "Analyse Rotation", "Scan Mobile", "Liste des Lots", "Pointage Expéditeur", "Inventaire Triple", "Profil", "RH"]
    return modules

MODULES_DISPO = get_available_modules()

if tab_add:
    with tab_add:
        st.subheader("Créer un nouvel utilisateur")
        with st.form("form_add_user"):
            u_name = st.text_input("Nom d'utilisateur")
            u_pwd = st.text_input("Mot de passe")
            u_role = st.selectbox("Rôle", ["Saisie", "Superviseur", "Admin"])
            c1, c2 = st.columns(2)
            u_nom = c1.text_input("Nom de famille")
            u_prenom = c2.text_input("Prénom")
            
            # Suggestion automatique de pages selon le rôle
            default_p = []
            if u_role == "Superviseur":
                default_p = ["Dashboard", "Logistique", "Inventaire Détail", "Scanneur QR", "Suivi"]
            elif u_role == "Saisie":
                default_p = ["Logistique", "Inventaire", "Inventaire Détail"]
                
            u_pages = st.multiselect("Accès aux modules", MODULES_DISPO, default=default_p)
            u_zone = st.selectbox("Zone Attribuée (Inventaire Détail)", ["Aucune", "A", "B", "C", "D", "Frigo"])
            
            if st.form_submit_button("Créer l'utilisateur"):
                if not df_users.empty and u_name in df_users['username'].values:
                    st.error("Ce nom d'utilisateur existe déjà !")
                elif u_name and u_pwd:
                    new_user = {
                        'username': u_name,
                        'password': u_pwd,
                        'role': u_role,
                        'nom': u_nom,
                        'prenom': u_prenom,
                        'pages': str(u_pages),
                        'zone': u_zone
                    }
                    df_users = pd.concat([df_users, pd.DataFrame([new_user])], ignore_index=True)
                    save_gs_data(df_users, DB_USERS_WORKSHEET, DB_USERS_FALLBACK)
                    st.success(f"Utilisateur {u_name} créé !")
                    from utils import log_action
                    log_action(st.session_state.current_user['username'], f"Création de l'utilisateur {u_name}", "Administration")
                    st.rerun()
                else:
                    st.error("Nom d'utilisateur et mot de passe requis.")

if tab_edit:
    with tab_edit:
        st.subheader("Modifier les accès ou le mot de passe" if is_admin else "Affecter une zone de préparation")
        
        # Sélection de l'utilisateur à modifier
        user_list = df_users['username'].tolist() if not df_users.empty else []
        edit_target = st.selectbox("Sélectionner l'utilisateur", user_list)
        
        if edit_target:
            target_data = df_users[df_users['username'] == edit_target].iloc[0]
            
            with st.form("form_edit_user"):
                st.write(f"Modifications pour : **{edit_target}**")
                
                if is_admin:
                    new_pwd = st.text_input("Nouveau mot de passe", value=target_data.get('password', ''))
                    role_list = ["Saisie", "Superviseur", "Admin"]
                    current_role = target_data.get('role', 'Saisie')
                    new_role = st.selectbox("Nouveau rôle", role_list, index=role_list.index(current_role) if current_role in role_list else 0)
                    current_pages = [p for p in target_data.get('pages', []) if p in MODULES_DISPO]
                    new_pages = st.multiselect("Accès aux modules", MODULES_DISPO, default=current_pages)
                    
                    ce1, ce2 = st.columns(2)
                    new_nom = ce1.text_input("Nom de famille", value=target_data.get('nom', ''))
                    new_prenom = ce2.text_input("Prénom", value=target_data.get('prenom', ''))
                else:
                    # Superviseur : lecture seule sur les infos sensibles
                    st.info(f"Rôle actuel : {target_data.get('role')}")
                    new_pwd = target_data.get('password')
                    new_role = target_data.get('role')
                    new_pages = target_data.get('pages')
                    new_nom = target_data.get('nom', '')
                    new_prenom = target_data.get('prenom', '')

                zones_list = ["Aucune", "A", "B", "C", "D", "Frigo"]
                current_zone = target_data.get('zone', 'Aucune')
                new_zone = st.selectbox("Nouvelle zone d'inventaire", zones_list, index=zones_list.index(current_zone) if current_zone in zones_list else 0)
                
                if st.form_submit_button("Valider l'affectation" if not is_admin else "Mettre à jour"):
                    mask = df_users['username'] == edit_target
                    df_users.loc[mask, 'password'] = new_pwd
                    df_users.loc[mask, 'role'] = new_role
                    df_users.loc[mask, 'pages'] = str(new_pages)
                    df_users.loc[mask, 'zone'] = new_zone
                    df_users.loc[mask, 'nom'] = new_nom
                    df_users.loc[mask, 'prenom'] = new_prenom
                    save_gs_data(df_users, DB_USERS_WORKSHEET, DB_USERS_FALLBACK)
                    st.success("Mise à jour réussie sur GSheets !")
                    st.rerun()



if tab_del:
    with tab_del:
        st.subheader("Supprimer définitivement un utilisateur")
        del_options = [u for u in df_users['username'].tolist() if u != st.session_state.current_user['username']] if not df_users.empty else []
        if not del_options:
            st.info("Aucun autre utilisateur à supprimer.")
        else:
            with st.form("form_del_user"):
                u_del = st.selectbox("Sélectionner l'utilisateur à supprimer", del_options)
                st.warning("⚠️ Cette action est irréversible.")
                if st.form_submit_button("Confirmer la suppression"):
                    df_users = df_users[df_users['username'] != u_del]
                    save_gs_data(df_users, DB_USERS_WORKSHEET, DB_USERS_FALLBACK)
                    st.success(f"Utilisateur {u_del} supprimé sur GSheets.")
                    from utils import log_action
                    log_action(st.session_state.current_user['username'], f"Suppression de l'utilisateur {u_del}", "Administration")
                    st.rerun()

if tab_logs:
    with tab_logs:
        st.subheader("📝 Historique des actions (Logs)")
        df_logs = load_gs_data(DB_LOGS_WORKSHEET, DB_LOGS_FALLBACK, COLS_LOGS)
        if not df_logs.empty:
            st.dataframe(df_logs.sort_values(by='timestamp', ascending=False), use_container_width=True)
        else:
            st.info("Aucun log disponible sur GSheets.")
        
        if st.button("🗑️ Nettoyer tout l'historique sur GSheets"):
            save_gs_data(pd.DataFrame(columns=COLS_LOGS), DB_LOGS_WORKSHEET, DB_LOGS_FALLBACK)
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

        st.divider()
        st.subheader("🛡️ Restauration de Sécurité")
        st.info("Si vous perdez vos utilisateurs sur Google Sheets, vous pouvez les restaurer ici à partir de la sauvegarde statique du code.")
        
        if st.button("🔄 Restaurer les Utilisateurs par défaut", type="primary", use_container_width=True):
            from utils_gsheets import restore_users_from_config
            success, msg = restore_users_from_config()
            if success:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

if tab_ia:
    with tab_ia:
        if is_admin:
            st.subheader("🤖 Configuration de l'Intelligence Artificielle")
            df_settings = load_gs_data(DB_SETTINGS_WORKSHEET, DB_SETTINGS_FALLBACK, COLS_SETTINGS)
            
            def get_setting(name, default=""):
                if df_settings.empty: return default
                res = df_settings[df_settings['name'] == name]
                return str(res['value'].values[0]) if not res.empty else default
                
            with st.form("form_ia_config_admin"):
                ia_en = st.checkbox("🚀 Activer l'IA globalement", value=get_setting('ia_global_enabled', 'True') == 'True')
                providers = ["Gemini (Google)", "Claude (Anthropic)", "ChatGPT (OpenAI)", "Grok (xAI)"]
                active_p = st.selectbox("Moteur par défaut", providers, index=providers.index(get_setting('active_ai_provider', 'Gemini (Google)')))
                
                st.write("---")
                new_gemini = st.text_input("Clé API Gemini (Google)", value=get_setting('gemini_api_key'), type="password")
                new_claude = st.text_input("Clé API Claude (Anthropic)", value=get_setting('anthropic_api_key'), type="password")
                new_openai = st.text_input("Clé API ChatGPT (OpenAI)", value=get_setting('openai_api_key'), type="password")
                
                if st.form_submit_button("💾 Sauvegarder la configuration IA", use_container_width=True):
                    def update_setting(name, val):
                        global df_settings
                        if not df_settings.empty and name in df_settings['name'].values:
                            df_settings.loc[df_settings['name'] == name, 'value'] = str(val)
                        else:
                            df_settings = pd.concat([df_settings, pd.DataFrame([{'name': name, 'value': str(val)}])], ignore_index=True)
                    
                    update_setting('gemini_api_key', new_gemini)
                    update_setting('anthropic_api_key', new_claude)
                    update_setting('openai_api_key', new_openai)
                    update_setting('active_ai_provider', active_p)
                    update_setting('ia_global_enabled', ia_en)
                    
                    save_gs_data(df_settings, DB_SETTINGS_WORKSHEET, DB_SETTINGS_FALLBACK)
                    st.success("✅ Configuration IA mise à jour sur GSheets !")
                    st.rerun()
        else:
            st.warning("⚠️ Accès restreint. Seuls les administrateurs peuvent configurer l'IA.")
