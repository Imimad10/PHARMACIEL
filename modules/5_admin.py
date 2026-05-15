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

# Initialisation des rôles par défaut si vide
if df_roles.empty:
    default_roles = [
        {"role_name": "Préparateur", "permissions": "['Inventaire', 'Inventaire Détail', 'Inventaire Triple', 'Péremptions', 'Liste des Lots']", "icon": "📦", "description": "Gestion des stocks et inventaires"},
        {"role_name": "Livreur", "permissions": "['Logistique', 'Recouvrement', 'Pointage Expéditeur', 'Scan Mobile']", "icon": "🚚", "description": "Flux de livraison et encaissements"},
        {"role_name": "Administrateur", "permissions": "['ALL']", "icon": "👑", "description": "Accès total au système"}
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
    
    col_u1, col_u2 = st.columns([3, 2])
    
    with col_u1:
        st.write("#### 👤 Liste des accès actuels")
        df_disp = df_users.copy()
        # On essaie de deviner le métier basé sur les permissions ou on affiche juste le rôle technique
        st.dataframe(df_disp[['username', 'role', 'depot', 'zone']], use_container_width=True, hide_index=True)

    with col_u2:
        st.write("#### ⚡ Affectation Rapide")
        u_target = st.selectbox("Sélectionner un collaborateur :", df_users['username'].tolist(), key="u_assign")
        r_target = st.selectbox("Lui attribuer le métier :", df_roles['role_name'].tolist(), key="r_assign")
        
        if st.button("🔄 APPLIQUER LE MÉTIER", type="primary", use_container_width=True):
            role_data = df_roles[df_roles['role_name'] == r_target].iloc[0]
            perms = role_data['permissions']
            if 'ALL' in perms: perms = get_available_modules()
            
            mask = df_users['username'] == u_target
            df_users.loc[mask, 'pages'] = str(perms)
            df_users.loc[mask, 'role'] = "Admin" if r_target == "Administrateur" else "Saisie"
            df_users.loc[mask, 'depot'] = r_target # On détourne depot pour stocker le nom du métier visuel
            
            save_gs_data(df_users, DB_USERS_WORKSHEET, DB_USERS_FALLBACK)
            st.success(f"✅ {u_target} est maintenant : **{r_target}**")
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
    st.markdown('<div class="admin-card">', unsafe_allow_html=True)
    st.write("#### 🦾 Cortex DarPharm IA")
    # ... (Le reste des réglages IA ici) ...
    st.markdown('</div>', unsafe_allow_html=True)
