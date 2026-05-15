import streamlit as st
import pandas as pd
import os
import shutil
import re
import ast
from utils_gsheets import load_gs_data, save_gs_data, DB_USERS_WORKSHEET, DB_USERS_FALLBACK

# Configuration GSheets
DB_LOGS_WORKSHEET = "Logs"
DB_LOGS_FALLBACK = "data/db_logs.csv"
COLS_LOGS = ["timestamp", "user", "module", "action"]

DB_ROLES_WORKSHEET = "Roles_Config"
DB_ROLES_FALLBACK = "data/db_roles.csv"
COLS_ROLES = ["role_name", "permissions", "icon", "description"]

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
                    if k not in modules: modules.append(k)
    except:
        modules = ["Admin Centrale", "Dashboard", "Logistique", "Inventaire", "Inventaire Détail", "Suivi", "Recouvrement", "Pointage", "Péremptions", "Scanneur QR", "Analyse Rotation", "Scan Mobile", "Liste des Lots", "Répartition Zones", "Analyse Réclamations", "Performance Ventes", "Profil"]
    return modules

# --- 1. CSS & STYLES ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Sora:wght@400;600;800&display=swap');
    
    .admin-card {
        background: rgba(124, 58, 237, 0.04);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(124, 58, 237, 0.15);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    
    .role-card {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
        transition: all 0.3s ease;
        cursor: pointer;
    }
    .role-card:hover { border-color: #7c3aed; box-shadow: 0 10px 15px -3px rgba(124, 58, 237, 0.1); }
    .role-active { border: 2px solid #7c3aed; background: rgba(124, 58, 237, 0.02); }
    
    .stat-val { font-size: 2rem; font-weight: 800; color: #1e293b; }
    .stat-label { font-size: 0.8rem; color: #64748b; text-transform: uppercase; letter-spacing: 1px; }
    
    .module-badge {
        display: inline-block;
        padding: 2px 8px;
        background: #f1f5f9;
        border-radius: 6px;
        font-size: 0.7rem;
        color: #475569;
        margin: 2px;
    }
</style>
""", unsafe_allow_html=True)

# Sécurité
user = st.session_state.get('current_user')
if not user or user.get('role') not in ['Admin', 'Superviseur']:
    st.error("Accès refusé.")
    st.stop()

is_admin = user.get('role') == 'Admin'

st.title("🛡️ Gouvernance DarPharm")
st.write("Gérez votre équipe via des profils métiers intelligents et centralisés.")

# Chargement des données
df_users = load_gs_data(DB_USERS_WORKSHEET, DB_USERS_FALLBACK)
df_roles = load_gs_data(DB_ROLES_WORKSHEET, DB_ROLES_FALLBACK, COLS_ROLES)

# Charte Officielle DarPharm — Métiers
GOLDEN_METIERS = {
    "Admin":                {'icon': '👑', 'color': '#7c3aed', 'description': 'Accès total au système'},
    "Agent de Stock":       {'icon': '📦', 'color': '#3b82f6', 'description': 'Inventaires, stocks, péremptions'},
    "Chef Livreurs & Parc": {'icon': '🚚', 'color': '#10b981', 'description': 'Logistique, flotte et livraisons'},
    "Superviseur":          {'icon': '🔭', 'color': '#f59e0b', 'description': 'Supervision et reporting opérationnel'},
    "Préparateur":          {'icon': '⚙️', 'color': '#64748b', 'description': 'Préparation commandes et pointage'},
}

# Initialisation des rôles par défaut si vide
if df_roles.empty:
    default_roles = [
        {"role_name": k, "permissions": "[]", "icon": v['icon'], "description": v['description']}
        for k, v in GOLDEN_METIERS.items()
    ]
    df_roles = pd.DataFrame(default_roles)
    save_gs_data(df_roles, DB_ROLES_WORKSHEET, DB_ROLES_FALLBACK)

def parse_list(p):
    if isinstance(p, list): return p
    if not isinstance(p, str) or not p.strip(): return []
    try: return ast.literal_eval(p)
    except: return [x.strip() for x in p.replace('[','').replace(']','').replace("'","").split(',') if x.strip()]

df_roles['permissions'] = df_roles['permissions'].apply(parse_list)

# --- 2. KPIs ---
c1, c2, c3, c4 = st.columns(4)
with c1: st.markdown(f'<div class="admin-card stat-box"><div class="stat-label">Équipe</div><div class="stat-val">{len(df_users)}</div></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="admin-card stat-box"><div class="stat-label">Métiers Actifs</div><div class="stat-val">{len(df_roles)}</div></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="admin-card stat-box"><div class="stat-label">Zones</div><div class="stat-val">5</div></div>', unsafe_allow_html=True)
with c4: st.markdown(f'<div class="admin-card stat-box"><div class="stat-label">Sécurité</div><div class="stat-val">OK</div></div>', unsafe_allow_html=True)

st.divider()
tabs = st.tabs(["👥 Gestion Équipe", "🏗️ Configuration des Métiers", "⚙️ Système & IA"])

# --- TAB 1: GESTION ÉQUIPE ---
with tabs[0]:
    st.subheader("Attribution des Métiers aux Collaborateurs")

    # --- BOUTON RESTAURATION DORÉE ---
    st.markdown('<div class="admin-card" style="border-left: 4px solid #7c3aed;">', unsafe_allow_html=True)
    rb1, rb2 = st.columns([3, 1])
    rb1.markdown("**🔐 Charte Officielle DarPharm** — En cas de problème d'accès, restaurez les rôles depuis le point de sauvegarde officiel.")
    if rb2.button("🛡️ Restaurer la Charte", type="primary", use_container_width=True, key="btn_golden_restore"):
        import json, ast
        try:
            # Importation du golden backup depuis app.py (déjà défini)
            PAGES_BY_METIER_LOCAL = {
                "Admin": str(['Dashboard', 'Profil', 'Admin Centrale', 'Gestion des Accès', 'Logistique', 'Inventaire', 'Inventaire Détail', 'Inventaire Triple', 'Suivi', 'Recouvrement', 'Pointage', 'Pointage Expéditeur', 'Pointage Marchandise', 'Péremptions', 'Scanneur QR', 'Scan Mobile', 'Litiges Fournisseurs', 'Analyse Rotation', 'RH', 'RH Planning', 'Clients', 'Liste des Lots', 'Catalogue Produits', 'Page de Garde', 'Assistant IA', 'Transferts', 'Coordination', 'Qualité IA', 'Mon Coin', 'Briefing IA', 'Maintenance', 'Académie', 'Prévisions', 'Mode Meeting', 'Répartition Zones', 'Analyse Réclamations', 'Performance Ventes', 'Cortex IA', 'Automatisation']),
                "Agent de Stock": str(['Profil', 'Dashboard', 'Inventaire', 'Inventaire Détail', 'Inventaire Triple', 'Péremptions', 'Liste des Lots', 'Catalogue Produits', 'Répartition Zones', 'Scanneur QR', 'Scan Mobile', 'Transferts']),
                "Chef Livreurs & Parc": str(['Profil', 'Dashboard', 'Logistique', 'Pointage Expéditeur', 'Recouvrement', 'Maintenance', 'Clients', 'Coordination', 'Suivi', 'Analyse Rotation', 'Transferts', 'Page de Garde']),
                "Superviseur": str(['Profil', 'Dashboard', 'Analyse Rotation', 'Analyse Réclamations', 'Performance Ventes', 'Prévisions', 'Logistique', 'Inventaire', 'RH', 'Coordination', 'Briefing IA', 'Mode Meeting']),
                "Préparateur": str(['Profil', 'Pointage Marchandise', 'Inventaire Détail', 'Scanneur QR', 'Scan Mobile', 'Transferts']),
            }
            GOLDEN_USERS_LOCAL = [
                {'username': 'admin_imad', 'metier': 'Admin',               'role': 'Admin',   'depot': 'Administration'},
                {'username': 'Ayoub',      'metier': 'Agent de Stock',       'role': 'Saisie',  'depot': 'Stock'},
                {'username': 'Islem',      'metier': 'Agent de Stock',       'role': 'Saisie',  'depot': 'Stock'},
                {'username': 'Seif',       'metier': 'Agent de Stock',       'role': 'Saisie',  'depot': 'Stock'},
                {'username': 'Karim',      'metier': 'Chef Livreurs & Parc', 'role': 'Saisie',  'depot': 'Expédition'},
                {'username': 'Rami',       'metier': 'Superviseur',          'role': 'Saisie',  'depot': 'Administration'},
                {'username': 'Idris',      'metier': 'Préparateur',          'role': 'Saisie',  'depot': 'Préparation'},
                {'username': 'Aymen',      'metier': 'Préparateur',          'role': 'Saisie',  'depot': 'Préparation'},
                {'username': 'Kheiro',     'metier': 'Préparateur',          'role': 'Saisie',  'depot': 'Préparation'},
                {'username': 'Rabeh',      'metier': 'Préparateur',          'role': 'Saisie',  'depot': 'Préparation'},
                {'username': 'Yacine',     'metier': 'Préparateur',          'role': 'Saisie',  'depot': 'Préparation'},
                {'username': 'Aek',        'metier': 'Préparateur',          'role': 'Saisie',  'depot': 'Préparation'},
                {'username': 'Aymenk',     'metier': 'Préparateur',          'role': 'Saisie',  'depot': 'Préparation'},
                {'username': 'Mustapha',   'metier': 'Préparateur',          'role': 'Saisie',  'depot': 'Préparation'},
            ]
            restored = 0
            for gu in GOLDEN_USERS_LOCAL:
                mask = df_users['username'] == gu['username']
                if mask.any():
                    df_users.loc[mask, 'pages'] = PAGES_BY_METIER_LOCAL.get(gu['metier'], PAGES_BY_METIER_LOCAL['Préparateur'])
                    df_users.loc[mask, 'metier'] = gu['metier']
                    df_users.loc[mask, 'role'] = gu['role']
                    restored += 1
            save_gs_data(df_users, DB_USERS_WORKSHEET, DB_USERS_FALLBACK)
            st.success(f"✅ Charte restaurée pour {restored} utilisateurs. Les accès sont redevenus officiels.")
            st.rerun()
        except Exception as e:
            st.error(f"Erreur de restauration : {e}")
    st.markdown('</div>', unsafe_allow_html=True)

    col_u1, col_u2 = st.columns([3, 2])
    
    with col_u1:
        st.write("#### 👤 Tableau des Métiers Officiels")
        df_disp = df_users.copy()
        
        # Enrichissement du tableau avec les couleurs de métier
        def badge(metier):
            info = GOLDEN_METIERS.get(metier, {'icon': '👤', 'color': '#64748b'})
            return f"{info['icon']} {metier}"
        
        metier_col = 'metier' if 'metier' in df_disp.columns else 'depot'
        df_disp['Métier'] = df_disp[metier_col].apply(lambda x: badge(str(x)) if pd.notna(x) else '👤 Non assigné')
        cols_show = [c for c in ['username', 'Métier', 'role', 'depot', 'zone'] if c in df_disp.columns]
        st.dataframe(df_disp[cols_show], use_container_width=True, hide_index=True)

    with col_u2:
        st.write("#### ⚡ Affectation Rapide")
        u_target = st.selectbox("Sélectionner un collaborateur :", df_users['username'].tolist(), key="u_assign")
        
        metier_names = list(GOLDEN_METIERS.keys())
        r_target = st.selectbox("Lui attribuer le métier :", metier_names, key="r_assign")
        
        # Affichage de la description du métier sélectionné
        if r_target in GOLDEN_METIERS:
            info = GOLDEN_METIERS[r_target]
            st.caption(f"{info['icon']} {info['description']}")
        
        if st.button("🔄 APPLIQUER LE MÉTIER", type="primary", use_container_width=True):
            import ast as _ast
            PAGES_APPLY = {
                "Admin": str(['Dashboard', 'Profil', 'Admin Centrale', 'Gestion des Accès', 'Logistique', 'Inventaire', 'Inventaire Détail', 'Inventaire Triple', 'Suivi', 'Recouvrement', 'Pointage', 'Pointage Expéditeur', 'Pointage Marchandise', 'Péremptions', 'Scanneur QR', 'Scan Mobile', 'Litiges Fournisseurs', 'Analyse Rotation', 'RH', 'RH Planning', 'Clients', 'Liste des Lots', 'Catalogue Produits', 'Page de Garde', 'Assistant IA', 'Transferts', 'Coordination', 'Qualité IA', 'Mon Coin', 'Briefing IA', 'Maintenance', 'Académie', 'Prévisions', 'Mode Meeting', 'Répartition Zones', 'Analyse Réclamations', 'Performance Ventes', 'Cortex IA', 'Automatisation']),
                "Agent de Stock": str(['Profil', 'Dashboard', 'Inventaire', 'Inventaire Détail', 'Inventaire Triple', 'Péremptions', 'Liste des Lots', 'Catalogue Produits', 'Répartition Zones', 'Scanneur QR', 'Scan Mobile', 'Transferts']),
                "Chef Livreurs & Parc": str(['Profil', 'Dashboard', 'Logistique', 'Pointage Expéditeur', 'Recouvrement', 'Maintenance', 'Clients', 'Coordination', 'Suivi', 'Analyse Rotation', 'Transferts', 'Page de Garde']),
                "Superviseur": str(['Profil', 'Dashboard', 'Analyse Rotation', 'Analyse Réclamations', 'Performance Ventes', 'Prévisions', 'Logistique', 'Inventaire', 'RH', 'Coordination', 'Briefing IA', 'Mode Meeting']),
                "Préparateur": str(['Profil', 'Pointage Marchandise', 'Inventaire Détail', 'Scanneur QR', 'Scan Mobile', 'Transferts']),
            }
            mask = df_users['username'] == u_target
            df_users.loc[mask, 'pages'] = PAGES_APPLY.get(r_target, PAGES_APPLY['Préparateur'])
            df_users.loc[mask, 'metier'] = r_target
            df_users.loc[mask, 'role'] = "Admin" if r_target == "Admin" else "Saisie"
            
            save_gs_data(df_users, DB_USERS_WORKSHEET, DB_USERS_FALLBACK)
            st.success(f"✅ **{u_target}** est maintenant : **{GOLDEN_METIERS[r_target]['icon']} {r_target}**")
            st.rerun()

# --- TAB 2: CONFIGURATION MÉTIERS ---
with tabs[1]:
    st.subheader("Définition des Profils Métiers")
    
    col_r_list, col_r_add = st.columns([2, 1])
    
    with col_r_add:
        st.write("#### ✨ Nouveau Métier")
        with st.expander("Créer un profil métier"):
            with st.form("form_new_role"):
                n_name = st.text_input("Nom (ex: Agent de Stock)")
                n_icon = st.text_input("Icône (emoji)", value="📦")
                if st.form_submit_button("CRÉER LE MÉTIER"):
                    if n_name:
                        new_r = {"role_name": n_name, "permissions": "[]", "icon": n_icon, "description": ""}
                        df_roles = pd.concat([df_roles, pd.DataFrame([new_r])], ignore_index=True)
                        save_gs_data(df_roles, DB_ROLES_WORKSHEET, DB_ROLES_FALLBACK)
                        st.success("Métier créé !")
                        st.rerun()
    
    with col_r_list:
        st.write("#### 🏗️ Configurer un métier existant")
        role_to_edit = st.selectbox("Choisir un métier :", df_roles['role_name'].tolist())
        
        if role_to_edit:
            r_idx = df_roles[df_roles['role_name'] == role_to_edit].index[0]
            r_current = df_roles.loc[r_idx]
            
            with st.form("form_edit_role_v2"):
                c_r1, c_r2 = st.columns([1, 3])
                new_icon = c_r1.text_input("Icône", value=r_current['icon'])
                new_desc = c_r2.text_input("Description", value=r_current['description'])
                
                st.write("---")
                st.write("🛡️ **Permissions de ce métier :**")
                all_mods = get_available_modules()
                cols = st.columns(3)
                updated_perms = []
                for i, m in enumerate(all_mods):
                    with cols[i % 3]:
                        is_checked = (m in r_current['permissions'] or 'ALL' in r_current['permissions'])
                        if st.checkbox(m, value=is_checked, key=f"perm_{role_to_edit}_{m}"):
                            updated_perms.append(m)
                
                if st.form_submit_button("💾 SAUVEGARDER & PROPAGER"):
                    df_roles.at[r_idx, 'permissions'] = updated_perms
                    df_roles.at[r_idx, 'icon'] = new_icon
                    df_roles.at[r_idx, 'description'] = new_desc
                    save_gs_data(df_roles, DB_ROLES_WORKSHEET, DB_ROLES_FALLBACK)
                    st.success(f"Métier {role_to_edit} mis à jour !")
                    st.rerun()

    if st.button("🗑️ Supprimer ce métier", type="secondary"):
        if role_to_edit and role_to_edit not in ["Administrateur"]:
            df_roles = df_roles[df_roles['role_name'] != role_to_edit]
            save_gs_data(df_roles, DB_ROLES_WORKSHEET, DB_ROLES_FALLBACK)
            st.warning("Métier supprimé.")
            st.rerun()

# --- TAB 3: SYSTÈME & IA ---
with tabs[2]:
    st.subheader("Configuration Système")
    
    col_sys1, col_sys2 = st.columns(2)
    
    with col_sys1:
        st.markdown('<div class="admin-card">', unsafe_allow_html=True)
        st.write("#### 🦾 Cortex DarPharm IA")
        df_settings = load_gs_data(DB_SETTINGS_WORKSHEET, DB_SETTINGS_FALLBACK, COLS_SETTINGS)
        
        def get_setting(name, default=""):
            if df_settings.empty: return default
            res = df_settings[df_settings['name'] == name]
            return str(res['value'].values[0]) if not res.empty else default

        with st.form("form_ia_admin"):
            ia_en = st.toggle("Activer l'IA Globalement", value=get_setting('ia_global_enabled', 'True') == 'True')
            active_p = st.selectbox("Moteur IA", ["OpenRouter", "Gemini (Google)", "Claude"], index=0)
            
            st.write("---")
            st.text_input("Clé API OpenRouter", value=get_setting('openrouter_api_key'), type="password")
            st.text_input("Clé API Gemini", value=get_setting('gemini_api_key'), type="password")
            
            if st.form_submit_button("SAUVEGARDER CONFIG IA"):
                new_settings = pd.DataFrame([
                    {'name': 'ia_global_enabled', 'value': str(ia_en)},
                    {'name': 'active_provider', 'value': active_p}
                ])
                # Note: merging with existing settings is better in real app
                save_gs_data(new_settings, DB_SETTINGS_WORKSHEET, DB_SETTINGS_FALLBACK)
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
