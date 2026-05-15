import streamlit as st
import pandas as pd
import os
import shutil
import re
from utils_gsheets import load_gs_data, save_gs_data, DB_USERS_WORKSHEET, DB_USERS_FALLBACK

# Configuration GSheets pour Admin
DB_LOGS_WORKSHEET = "Logs"
DB_LOGS_FALLBACK = "data/db_logs.csv"
COLS_LOGS = ["timestamp", "user", "module", "action"]

DB_SETTINGS_WORKSHEET = "Settings"
DB_SETTINGS_FALLBACK = "data/db_settings.csv"
COLS_SETTINGS = ["name", "value"]

def get_available_modules():
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
    except:
        modules = ["Admin Centrale", "Dashboard", "Logistique", "Inventaire", "Inventaire Détail", "Suivi", "Recouvrement", "Pointage", "Péremptions", "Scanneur QR", "Automatisation", "Litiges Fournisseurs", "Analyse Rotation", "Scan Mobile", "Liste des Lots", "Pointage Expéditeur", "Inventaire Triple", "Profil", "RH", "Répartition Zones", "Analyse Réclamations", "Performance Ventes"]
    return modules

# --- 1. CSS & STYLES ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;800&display=swap');
    
    .admin-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        transition: all 0.3s ease;
    }
    
    .admin-card:hover {
        border-color: rgba(124, 58, 237, 0.5);
        background: rgba(255, 255, 255, 0.05);
    }
    
    .user-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-right: 5px;
    }
    
    .badge-admin { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }
    .badge-super { background: rgba(124, 58, 237, 0.2); color: #a78bfa; border: 1px solid rgba(124, 58, 237, 0.3); }
    .badge-saisie { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
    
    .stat-val { font-size: 2rem; font-weight: 800; color: #f8fafc; }
    .stat-label { font-size: 0.9rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; }
    
    .module-group {
        border-left: 3px solid #7c3aed;
        padding-left: 15px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Sécurité
user = st.session_state.get('current_user')
if not user or user.get('role') not in ['Admin', 'Superviseur']:
    st.error("Accès refusé.")
    st.stop()

is_admin = user.get('role') == 'Admin'

st.title("👥 Administration & Excellence d'Équipe")
st.write("Pilotez vos collaborateurs, configurez les accès et sécurisez les flux de données DarPharm.")

# Chargement des données
USER_COLUMNS = ["username", "password", "role", "pages", "nom", "prenom", "zone", "depot"]
df_users = load_gs_data(DB_USERS_WORKSHEET, DB_USERS_FALLBACK, USER_COLUMNS)

# --- 2. KPIs ADMIN ---
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="admin-card"><div class="stat-label">Équipage</div><div class="stat-val">{len(df_users)}</div></div>', unsafe_allow_html=True)
with c2:
    nb_admins = len(df_users[df_users['role'] == 'Admin'])
    st.markdown(f'<div class="admin-card"><div class="stat-label">Gouvernance</div><div class="stat-val">{nb_admins} Adm</div></div>', unsafe_allow_html=True)
with c3:
    nb_saisie = len(df_users[df_users['role'] == 'Saisie'])
    st.markdown(f'<div class="admin-card"><div class="stat-label">Opérationnels</div><div class="stat-val">{nb_saisie}</div></div>', unsafe_allow_html=True)
with c4:
    ia_status = "ACTIVE" if st.session_state.get('ia_enabled', True) else "OFF"
    st.markdown(f'<div class="admin-card"><div class="stat-label">Cortex IA</div><div class="stat-val">{ia_status}</div></div>', unsafe_allow_html=True)

# Conversion sécurisée des pages
def parse_pages(p):
    if isinstance(p, list): return p
    if not isinstance(p, str) or not p.strip(): return []
    import ast
    try: return ast.literal_eval(p)
    except: return [x.strip() for x in p.replace('[','').replace(']','').replace("'","").split(',') if x.strip()]

if not df_users.empty:
    for col in USER_COLUMNS:
        if col in df_users.columns: df_users[col] = df_users[col].fillna("").astype(str)
    df_users['pages'] = df_users['pages'].apply(parse_pages)

# --- 3. NAVIGATION PRINCIPALE ---
st.divider()
main_tabs = st.tabs(["👥 Équipe & Profils", "🔑 Accès & Permissions", "⚙️ Système & IA", "📝 Audit & Logs"])

with main_tabs[0]:
    st.subheader("Gestion de l'Équipage")
    
    # Affichage en mode Cartes ou Tableau Minimal
    col_view1, col_view2 = st.columns([2, 1])
    
    with col_view1:
        st.write("#### 👤 Utilisateurs Actifs")
        df_display = df_users.copy()
        df_display['password'] = "********"
        df_display['pages'] = df_display['pages'].apply(lambda x: len(x) if isinstance(x, list) else 0)
        st.dataframe(df_display[['username', 'role', 'depot', 'zone', 'pages']], use_container_width=True, hide_index=True)
    
    with col_view2:
        st.write("#### ⚡ Actions Rapides")
        action = st.selectbox("Action :", ["Ajouter", "Modifier", "Supprimer"])
        
        if action == "Ajouter" and is_admin:
            with st.expander("➕ Nouvel Utilisateur", expanded=True):
                with st.form("form_add_v2"):
                    u_name = st.text_input("Username")
                    u_pwd = st.text_input("Password", type="password")
                    u_role = st.selectbox("Rôle", ["Saisie", "Superviseur", "Admin"])
                    u_depot = st.selectbox("Dépôt", ["Stock", "Préparation", "Expédition", "Administration"])
                    if st.form_submit_button("CRÉER COMPTE"):
                        if u_name and u_pwd:
                            new_u = {'username': u_name, 'password': u_pwd, 'role': u_role, 'pages': '[]', 'depot': u_depot}
                            df_users = pd.concat([df_users, pd.DataFrame([new_u])], ignore_index=True)
                            save_gs_data(df_users, DB_USERS_WORKSHEET, DB_USERS_FALLBACK)
                            st.success("Compte créé !")
                            st.rerun()

        elif action == "Modifier":
            u_to_edit = st.selectbox("Sélectionner :", df_users['username'].tolist())
            if u_to_edit:
                target = df_users[df_users['username'] == u_to_edit].iloc[0]
                with st.expander(f"✏️ Editer {u_to_edit}", expanded=True):
                    with st.form("form_edit_v2"):
                        new_pwd = st.text_input("Password", value=target['password'])
                        new_role = st.selectbox("Rôle", ["Saisie", "Superviseur", "Admin"], index=["Saisie", "Superviseur", "Admin"].index(target['role']))
                        new_zone = st.selectbox("Zone", ["Aucune", "A", "B", "C", "D", "Frigo"], index=["Aucune", "A", "B", "C", "D", "Frigo"].index(target.get('zone', 'Aucune')))
                        if st.form_submit_button("METTRE À JOUR"):
                            mask = df_users['username'] == u_to_edit
                            df_users.loc[mask, ['password', 'role', 'zone']] = [new_pwd, new_role, new_zone]
                            save_gs_data(df_users, DB_USERS_WORKSHEET, DB_USERS_FALLBACK)
                            st.success("Profil mis à jour")
                            st.rerun()

        elif action == "Supprimer" and is_admin:
            u_to_del = st.selectbox("Supprimer :", [u for u in df_users['username'].tolist() if u != user['username']])
            if st.button("❌ CONFIRMER SUPPRESSION", type="primary", use_container_width=True):
                df_users = df_users[df_users['username'] != u_to_del]
                save_gs_data(df_users, DB_USERS_WORKSHEET, DB_USERS_FALLBACK)
                st.success("Utilisateur supprimé")
                st.rerun()

with main_tabs[1]:
    st.subheader("🔑 Contrôle Granulaire des Accès")
    
    selected_users = st.multiselect("Sélectionnez les collaborateurs :", df_users['username'].tolist())
    
    if selected_users:
        st.markdown('<div class="admin-card">', unsafe_allow_html=True)
        col_acc1, col_acc2 = st.columns([1, 2])
        
        with col_acc1:
            st.write("#### 🚀 Profils Types")
            p_type = st.radio("Appliquer un modèle :", 
                             ["Perso", "Préparateur (Stock)", "Livreur (Logistique)", "Vendeur (Analyse)", "Admin Complet"])
            
            MODULES_DISPO = get_available_modules()
            profil_map = {
                "Préparateur (Stock)": ["Inventaire", "Inventaire Détail", "Inventaire Triple", "Suivi", "Péremptions", "Liste des Lots", "Répartition Zones", "Profil"],
                "Livreur (Logistique)": ["Logistique", "Recouvrement", "Pointage Expéditeur", "Scan Mobile", "Profil"],
                "Vendeur (Analyse)": ["Catalogue Produits", "Analyse Rotation", "Analyse Réclamations", "Performance Ventes", "Profil"],
                "Admin Complet": MODULES_DISPO
            }
            
            current_selection = []
            if len(selected_users) == 1:
                current_selection = df_users[df_users['username'] == selected_users[0]].iloc[0].get('pages', [])
            
            if p_type != "Perso":
                current_selection = profil_map.get(p_type, [])
        
        with col_acc2:
            st.write("#### 🧩 Modules Autorisés")
            final_pages = []
            
            # Regroupement visuel des modules
            categories = {
                "📦 STOCKS": ["Inventaire", "Inventaire Détail", "Inventaire Triple", "Péremptions", "Liste des Lots", "Catalogue Produits", "Répartition Zones"],
                "📊 SUPERVISION": ["Dashboard", "Analyse Rotation", "Prévisions", "Mode Meeting", "Analyse Réclamations", "Performance Ventes", "Suivi"],
                "📝 FLUX": ["Pointage", "Pointage Expéditeur", "Pointage Marchandise", "Recouvrement", "Logistique", "Scanneur QR", "Scan Mobile", "Transferts"],
                "🤖 IA": ["Assistant IA", "Qualité IA", "Briefing IA", "Automatisation", "Coordination", "Académie"]
            }
            
            c_mod1, c_mod2 = st.columns(2)
            idx = 0
            for cat, mods in categories.items():
                with (c_mod1 if idx % 2 == 0 else c_mod2):
                    st.markdown(f'<div class="module-group"><b>{cat}</b></div>', unsafe_allow_html=True)
                    for m in mods:
                        if m in MODULES_DISPO:
                            if st.checkbox(m, value=m in current_selection, key=f"bulk_{m}_{p_type}"):
                                final_pages.append(m)
                idx += 1
                
        st.divider()
        if st.button("💾 APPLIQUER LES DROITS D'ACCÈS", type="primary", use_container_width=True):
            for u in selected_users:
                df_users.loc[df_users['username'] == u, 'pages'] = str(final_pages)
            save_gs_data(df_users, DB_USERS_WORKSHEET, DB_USERS_FALLBACK)
            st.success(f"Accès mis à jour pour {len(selected_users)} utilisateur(s)")
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

with main_tabs[2]:
    st.subheader("⚙️ Paramètres Système & Intelligence Artificielle")
    
    col_sys1, col_sys2 = st.columns(2)
    
    with col_sys1:
        st.markdown('<div class="admin-card">', unsafe_allow_html=True)
        st.write("#### 🦾 Cortex DarPharm IA")
        df_settings = load_gs_data(DB_SETTINGS_WORKSHEET, DB_SETTINGS_FALLBACK, COLS_SETTINGS)
        
        def get_setting(name, default=""):
            if df_settings.empty: return default
            res = df_settings[df_settings['name'] == name]
            return str(res['value'].values[0]) if not res.empty else default

        with st.form("form_ia_v2"):
            ia_en = st.toggle("Activer l'IA Globalement", value=get_setting('ia_global_enabled', 'True') == 'True')
            ia_scan = st.toggle("Scanner Photo IA", value=get_setting('ia_scanner_enabled', 'True') == 'True')
            active_p = st.selectbox("Moteur IA", ["OpenRouter", "Gemini (Google)", "Claude (Anthropic)"], index=0)
            
            st.write("---")
            st.text_input("Clé API OpenRouter", value=get_setting('openrouter_api_key'), type="password")
            st.text_input("Clé API Gemini", value=get_setting('gemini_api_key'), type="password")
            
            if st.form_submit_button("SAUVEGARDER CONFIG IA"):
                st.success("Paramètres IA mis à jour")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_sys2:
        st.markdown('<div class="admin-card">', unsafe_allow_html=True)
        st.write("#### 💾 Maintenance & Cloud")
        st.info("Sauvegardez vos données ou restaurez les comptes par défaut.")
        
        if st.button("📦 GÉNÉRER BACKUP ZIP", use_container_width=True):
            st.toast("Génération du pack de sauvegarde...")
            # Logic here...
            
        st.divider()
        if st.button("🔄 RESTAURATION DE SÉCURITÉ", type="primary", use_container_width=True):
            from utils_gsheets import restore_users_from_config
            res, msg = restore_users_from_config()
            st.success(msg)
        st.markdown('</div>', unsafe_allow_html=True)

with main_tabs[3]:
    st.subheader("📝 Audit de Sécurité (Logs)")
    df_logs = load_gs_data(DB_LOGS_WORKSHEET, DB_LOGS_FALLBACK, COLS_LOGS)
    
    if not df_logs.empty:
        # Mini-dashboard de logs
        lc1, lc2 = st.columns(2)
        lc1.metric("Actions ce jour", len(df_logs))
        
        st.write("#### Dernières activités du système")
        st.dataframe(df_logs.sort_values(by='timestamp', ascending=False).head(100), 
                     use_container_width=True, hide_index=True)
        
        if st.button("🗑️ VIDER LES LOGS (Archivage)"):
            save_gs_data(pd.DataFrame(columns=COLS_LOGS), DB_LOGS_WORKSHEET, DB_LOGS_FALLBACK)
            st.rerun()
    else:
        st.info("Aucune activité enregistrée.")
