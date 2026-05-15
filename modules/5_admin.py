import streamlit as st
import pandas as pd
import ast, re
from utils_gsheets import load_gs_data, save_gs_data, DB_USERS_WORKSHEET, DB_USERS_FALLBACK

DB_ROLES_WORKSHEET = "Roles_Config"
DB_ROLES_FALLBACK  = "data/db_roles.csv"
COLS_ROLES         = ["role_name","permissions","icon","description"]
DB_SETTINGS_WORKSHEET = "Settings"
DB_SETTINGS_FALLBACK  = "data/db_settings.csv"
COLS_SETTINGS         = ["name","value"]

GOLDEN_METIERS = {
    "Admin":                {'icon':'👑','color':'#7c3aed','bg':'#f5f3ff'},
    "Agent de Stock":       {'icon':'📦','color':'#2563eb','bg':'#eff6ff'},
    "Chef Livreurs & Parc": {'icon':'🚚','color':'#059669','bg':'#ecfdf5'},
    "Superviseur":          {'icon':'🔭','color':'#d97706','bg':'#fffbeb'},
    "Préparateur":          {'icon':'⚙️','color':'#64748b','bg':'#f8fafc'},
}
PAGES_BY_METIER = {
    "Admin": str(['Dashboard','Profil','Admin Centrale','Gestion des Accès','Logistique','Inventaire','Inventaire Détail','Inventaire Triple','Suivi','Recouvrement','Pointage','Pointage Expéditeur','Pointage Marchandise','Péremptions','Scanneur QR','Scan Mobile','Litiges Fournisseurs','Analyse Rotation','RH','RH Planning','Clients','Liste des Lots','Catalogue Produits','Page de Garde','Assistant IA','Transferts','Coordination','Qualité IA','Mon Coin','Briefing IA','Maintenance','Académie','Prévisions','Mode Meeting','Répartition Zones','Analyse Réclamations','Performance Ventes','Cortex IA','Automatisation']),
    "Agent de Stock":       str(['Profil','Dashboard','Inventaire','Inventaire Détail','Inventaire Triple','Péremptions','Liste des Lots','Catalogue Produits','Répartition Zones','Scanneur QR','Scan Mobile','Transferts']),
    "Chef Livreurs & Parc": str(['Profil','Dashboard','Logistique','Pointage Expéditeur','Recouvrement','Maintenance','Clients','Coordination','Suivi','Analyse Rotation','Transferts','Page de Garde']),
    "Superviseur":          str(['Profil','Dashboard','Analyse Rotation','Analyse Réclamations','Performance Ventes','Prévisions','Logistique','Inventaire','RH','Coordination','Briefing IA','Mode Meeting']),
    "Préparateur":          str(['Profil','Pointage Marchandise','Inventaire Détail','Scanneur QR','Scan Mobile','Transferts']),
}
GOLDEN_USERS = [
    ('admin_imad','admin_imad_pwd','Admin','Admin','Administration'),
    ('Ayoub','ayoub2026','Saisie','Agent de Stock','Stock'),
    ('Islem','islem2026','Saisie','Agent de Stock','Stock'),
    ('Seif','seif2026','Saisie','Agent de Stock','Stock'),
    ('Karim','karim2026','Saisie','Chef Livreurs & Parc','Expédition'),
    ('Rami','rami2026','Saisie','Superviseur','Administration'),
    ('Idris','idris2026','Saisie','Préparateur','Préparation'),
    ('Aymen','aymen2026','Saisie','Préparateur','Préparation'),
    ('Kheiro','kheiro2026','Saisie','Préparateur','Préparation'),
    ('Rabeh','rabeh2026','Saisie','Préparateur','Préparation'),
    ('Yacine','yacine2026','Saisie','Préparateur','Préparation'),
    ('Aek','aek2026','Saisie','Préparateur','Préparation'),
    ('Aymenk','aymenk2026','Saisie','Préparateur','Préparation'),
    ('Mustapha','mustapha2026','Saisie','Préparateur','Préparation'),
]

def parse_list(p):
    if isinstance(p, list): return p
    if not isinstance(p, str) or not p.strip(): return []
    try: return ast.literal_eval(p)
    except: return [x.strip() for x in p.replace('[','').replace(']','').replace("'",'').split(',') if x.strip()]

def safe_set(df, mask, col, value):
    """Set a string value safely, ensuring the column exists as object dtype."""
    if col not in df.columns:
        df[col] = ''
    df[col] = df[col].astype(object)
    df.loc[mask, col] = value
    return df

def get_available_modules():
    mods = ["Admin Centrale"]
    try:
        with open("app.py","r",encoding="utf-8") as f:
            content = f.read()
            match = re.search(r'ALL_PAGES\s*=\s*\{(.*?)\}', content, re.DOTALL)
            if match:
                for k in re.findall(r'"([^"]+)"\s*:\s*st\.Page', match.group(1)):
                    if k not in mods: mods.append(k)
    except: pass
    return mods

# ── Sécurité ─────────────────────────────────────────────────────────────────
user     = st.session_state.get('current_user')
if not user or user.get('role') not in ['Admin','Superviseur']:
    st.error("⛔ Accès réservé à l'Administration."); st.stop()
is_admin = user.get('role') == 'Admin'

# ── CSS Elite Minimal ────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
* { font-family:'Outfit',sans-serif; }

.admin-hero {
    background: linear-gradient(135deg,#1e293b 0%,#0f172a 100%);
    border-radius:20px; padding:30px 35px; color:white; margin-bottom:28px;
    display:flex; align-items:center; justify-content:space-between;
}
.admin-hero h1 { font-size:1.8rem; font-weight:800; margin:0; }
.admin-hero p  { opacity:.65; margin:4px 0 0; font-size:.95rem; }

.kpi-mini {
    background:white; border-radius:14px; padding:20px;
    border:1px solid #f1f5f9; text-align:center;
    box-shadow:0 2px 8px rgba(0,0,0,0.04);
    transition:all .25s ease;
}
.kpi-mini:hover { transform:translateY(-3px); box-shadow:0 8px 20px rgba(0,0,0,0.08); }
.kpi-mini .num  { font-size:2rem; font-weight:800; color:#1e293b; }
.kpi-mini .lbl  { font-size:.72rem; color:#94a3b8; text-transform:uppercase; letter-spacing:1px; }

.user-row {
    display:grid; grid-template-columns:1.5fr 1.5fr 1fr 1fr 1fr;
    padding:12px 16px; border-radius:10px; border:1px solid #f1f5f9;
    margin-bottom:6px; background:white; align-items:center;
    transition:all .2s ease;
}
.user-row:hover { border-color:#6366f1; box-shadow:0 4px 12px rgba(99,102,241,.08); }
.metier-pill {
    display:inline-flex; align-items:center; gap:5px;
    padding:3px 10px; border-radius:20px; font-size:.78rem; font-weight:700;
}

.restore-banner {
    background: linear-gradient(135deg,#4f46e5,#7c3aed);
    border-radius:14px; padding:16px 20px; color:white; margin-bottom:20px;
    display:flex; align-items:center; justify-content:space-between;
}

.section-title {
    font-size:1rem; font-weight:700; color:#1e293b;
    margin:0 0 14px; padding-bottom:8px; border-bottom:2px solid #f1f5f9;
}
</style>
""", unsafe_allow_html=True)

# ── HERO ─────────────────────────────────────────────────────────────────────
df_users = load_gs_data(DB_USERS_WORKSHEET, DB_USERS_FALLBACK)
df_roles = load_gs_data(DB_ROLES_WORKSHEET, DB_ROLES_FALLBACK, COLS_ROLES)
if 'permissions' in df_roles.columns:
    df_roles['permissions'] = df_roles['permissions'].apply(parse_list)

nb_metiers = len(df_roles) if not df_roles.empty else len(GOLDEN_METIERS)

st.markdown(f"""
<div class="admin-hero">
    <div>
        <h1>🛡️ Gouvernance DarPharm</h1>
        <p>Administration · Gestion des accès & des métiers</p>
    </div>
    <div style="text-align:right;opacity:.7;font-size:.85rem;">
        Connecté : <b>{user['username']}</b><br>
        {__import__('datetime').datetime.now().strftime('%d/%m/%Y — %H:%M')}
    </div>
</div>
""", unsafe_allow_html=True)

# KPIs
k1,k2,k3,k4 = st.columns(4)
k1.markdown(f'<div class="kpi-mini"><div class="num">{len(df_users)}</div><div class="lbl">Collaborateurs</div></div>', unsafe_allow_html=True)
k2.markdown(f'<div class="kpi-mini"><div class="num">{nb_metiers}</div><div class="lbl">Métiers</div></div>', unsafe_allow_html=True)
k3.markdown(f'<div class="kpi-mini"><div class="num">{len(df_users[df_users["role"]=="Admin"]) if "role" in df_users.columns else 1}</div><div class="lbl">Admins</div></div>', unsafe_allow_html=True)
k4.markdown(f'<div class="kpi-mini"><div class="num" style="color:#10b981;">OK</div><div class="lbl">Sécurité</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── TABS ─────────────────────────────────────────────────────────────────────
tabs = st.tabs(["👥 Équipe & Accès","🏗️ Métiers","⚙️ Système & IA"])

# ═══════════════════════════════════════════════════════════════════
# TAB 1 : ÉQUIPE & ACCÈS
# ═══════════════════════════════════════════════════════════════════
with tabs[0]:

    # ── Bannière Restauration ──────────────────────────────────────
    col_b1, col_b2 = st.columns([4,1])
    col_b1.markdown("**🔐 Point de Sauvegarde Officiel** — Restaurez la Charte des Rôles DarPharm en un clic si les accès sont corrompus.")
    if col_b2.button("🛡️ Restaurer la Charte", type="primary", use_container_width=True):
        restored = 0
        for (uname,_,urole,umetier,udepot) in GOLDEN_USERS:
            mask = df_users['username'] == uname
            if mask.any():
                df_users = safe_set(df_users, mask, 'metier', umetier)
                df_users = safe_set(df_users, mask, 'depot',  udepot)
                df_users = safe_set(df_users, mask, 'pages',  PAGES_BY_METIER.get(umetier, PAGES_BY_METIER['Préparateur']))
                df_users = safe_set(df_users, mask, 'role',   urole)
                restored += 1
        save_gs_data(df_users, DB_USERS_WORKSHEET, DB_USERS_FALLBACK)
        st.success(f"✅ Charte restaurée pour {restored} utilisateurs.")
        st.rerun()

    st.markdown("---")

    # ── Tableau des Utilisateurs + Identifiants ────────────────────
    col_table, col_quick = st.columns([3,2])

    with col_table:
        st.markdown('<div class="section-title">📋 Liste des Collaborateurs</div>', unsafe_allow_html=True)

        # Toggle mot de passe
        show_pwd = st.toggle("👁️ Afficher les mots de passe", value=False, key="toggle_pwd")

        if not df_users.empty:
            for _, row in df_users.iterrows():
                uname    = row.get('username','')
                umetier  = str(row.get('metier','') or row.get('depot',''))
                urole    = str(row.get('role',''))
                udepot   = str(row.get('depot',''))
                upwd     = str(row.get('password','')) if show_pwd else '••••••••'
                info     = GOLDEN_METIERS.get(umetier, {'icon':'👤','color':'#64748b','bg':'#f8fafc'})

                st.markdown(f"""
                <div class="user-row">
                    <div><b>{uname}</b></div>
                    <div><span class="metier-pill" style="background:{info['bg']};color:{info['color']};">{info['icon']} {umetier}</span></div>
                    <div style="color:#94a3b8;font-size:.82rem;">{udepot}</div>
                    <div style="color:#94a3b8;font-size:.82rem;font-family:monospace;">{upwd}</div>
                    <div style="color:#94a3b8;font-size:.75rem;">{urole}</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.info("Aucun utilisateur chargé.")

    with col_quick:
        st.markdown('<div class="section-title">⚡ Affectation Rapide</div>', unsafe_allow_html=True)

        u_list = df_users['username'].tolist() if not df_users.empty else []
        u_target = st.selectbox("Collaborateur", u_list, key="u_assign")
        m_target = st.selectbox("Nouveau Métier", list(GOLDEN_METIERS.keys()), key="m_assign")

        if m_target in GOLDEN_METIERS:
            info = GOLDEN_METIERS[m_target]
            st.markdown(f"<span style='color:{info['color']};font-weight:600;'>{info['icon']} Métier sélectionné</span>", unsafe_allow_html=True)

        if st.button("✅ Appliquer", type="primary", use_container_width=True):
            mask = df_users['username'] == u_target
            df_users = safe_set(df_users, mask, 'metier', m_target)
            df_users = safe_set(df_users, mask, 'pages',  PAGES_BY_METIER.get(m_target, PAGES_BY_METIER['Préparateur']))
            df_users = safe_set(df_users, mask, 'role',   'Admin' if m_target == 'Admin' else 'Saisie')
            save_gs_data(df_users, DB_USERS_WORKSHEET, DB_USERS_FALLBACK)
            st.success(f"✅ {u_target} → {GOLDEN_METIERS[m_target]['icon']} {m_target}")
            st.rerun()

        st.markdown("---")
        st.markdown('<div class="section-title">➕ Nouvel Utilisateur</div>', unsafe_allow_html=True)
        with st.form("form_add_user"):
            nu = st.text_input("Nom d'utilisateur")
            np_ = st.text_input("Mot de passe", type="password")
            nm = st.selectbox("Métier", list(GOLDEN_METIERS.keys()), key="nm_new")
            if st.form_submit_button("Créer le compte", use_container_width=True):
                if nu and np_:
                    if not df_users.empty and nu in df_users['username'].values:
                        st.error("Utilisateur déjà existant.")
                    else:
                        new_row = {'username':nu,'password':np_,'role':'Saisie' if nm!='Admin' else 'Admin',
                                   'metier':nm,'depot':GOLDEN_METIERS[nm]['icon'],
                                   'pages':PAGES_BY_METIER.get(nm,PAGES_BY_METIER['Préparateur']),
                                   'nom':nu,'prenom':'','zone':'Aucune'}
                        df_users = pd.concat([df_users, pd.DataFrame([new_row])], ignore_index=True)
                        save_gs_data(df_users, DB_USERS_WORKSHEET, DB_USERS_FALLBACK)
                        st.success(f"✅ Compte {nu} créé !")
                        st.rerun()
                else:
                    st.error("Remplissez tous les champs.")

# ═══════════════════════════════════════════════════════════════════
# TAB 2 : MÉTIERS
# ═══════════════════════════════════════════════════════════════════
with tabs[1]:
    st.markdown('<div class="section-title">🏗️ Carte des Métiers DarPharm</div>', unsafe_allow_html=True)

    # Aperçu visuel des métiers
    m_cols = st.columns(len(GOLDEN_METIERS))
    for i,(nom_m,info) in enumerate(GOLDEN_METIERS.items()):
        nb = len(df_users[df_users.get('metier','_') == nom_m]) if 'metier' in df_users.columns else 0
        m_cols[i].markdown(f"""
        <div class="kpi-mini" style="border-top:4px solid {info['color']};">
            <div style="font-size:2rem;">{info['icon']}</div>
            <div style="font-weight:700;font-size:.9rem;color:#1e293b;">{nom_m}</div>
            <div class="num" style="font-size:1.6rem;color:{info['color']};">{nb}</div>
            <div class="lbl">membres</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # Édition avancée des permissions
    if is_admin:
        df_roles_edit = load_gs_data(DB_ROLES_WORKSHEET, DB_ROLES_FALLBACK, COLS_ROLES)
        if not df_roles_edit.empty:
            # --- SYNCHRONISATION FORCÉE AVEC GOLDEN METIERS ---
            # Supprimer les anciens noms de métiers obsolètes (ex: "stock")
            df_roles_edit = df_roles_edit[df_roles_edit['role_name'].isin(GOLDEN_METIERS.keys())].copy()
            
            # Ajouter les métiers manquants de la Charte
            for m in GOLDEN_METIERS.keys():
                if m not in df_roles_edit['role_name'].values:
                    perms = PAGES_BY_METIER.get(m, "[]")
                    new_r = pd.DataFrame([{'role_name': m, 'permissions': perms, 'icon': GOLDEN_METIERS[m]['icon'], 'description': ''}])
                    df_roles_edit = pd.concat([df_roles_edit, new_r], ignore_index=True)
                    
            df_roles_edit['permissions'] = df_roles_edit['permissions'].apply(parse_list)
            
            role_to_edit = st.selectbox("Configurer le métier :", list(GOLDEN_METIERS.keys()))
            if role_to_edit:
                r_idx = df_roles_edit[df_roles_edit['role_name'] == role_to_edit].index[0]
                r_cur = df_roles_edit.loc[r_idx]
                with st.form("form_edit_metier"):
                    c1,c2 = st.columns([1,3])
                    new_icon = c1.text_input("Icône", value=r_cur['icon'])
                    new_desc = c2.text_input("Description", value=r_cur['description'])
                    st.write("**Permissions :**")
                    all_mods = get_available_modules()
                    cols3 = st.columns(3)
                    updated = []
                    for j,m in enumerate(all_mods):
                        with cols3[j%3]:
                            if st.checkbox(m, value=(m in r_cur['permissions'] or 'ALL' in r_cur['permissions']), key=f"p_{role_to_edit}_{m}"):
                                updated.append(m)
                    if st.form_submit_button("💾 Sauvegarder", type="primary", use_container_width=True):
                        df_roles_edit.at[r_idx,'permissions'] = updated
                        df_roles_edit.at[r_idx,'icon'] = new_icon
                        df_roles_edit.at[r_idx,'description'] = new_desc
                        save_gs_data(df_roles_edit, DB_ROLES_WORKSHEET, DB_ROLES_FALLBACK)
                        
                        # UPDATE ALL USERS WITH THIS ROLE
                        if not df_users.empty and 'metier' in df_users.columns:
                            mask = df_users['metier'] == role_to_edit
                            if mask.any():
                                df_users.loc[mask, 'pages'] = str(updated)
                                save_gs_data(df_users, DB_USERS_WORKSHEET, DB_USERS_FALLBACK)
                                
                        st.success("✅ Métier mis à jour et accès synchronisés pour les agents !")
                        st.rerun()
    else:
        st.info("La configuration avancée est réservée aux administrateurs.")

# ═══════════════════════════════════════════════════════════════════
# TAB 3 : SYSTÈME & IA
# ═══════════════════════════════════════════════════════════════════
with tabs[2]:
    col_ia, col_maint = st.columns(2)

    with col_ia:
        st.markdown('<div class="section-title">🤖 Configuration IA</div>', unsafe_allow_html=True)
        df_settings = load_gs_data(DB_SETTINGS_WORKSHEET, DB_SETTINGS_FALLBACK, COLS_SETTINGS)

        def get_s(n, d=""): 
            if df_settings.empty: return d
            r = df_settings[df_settings['name'] == n]
            return str(r['value'].values[0]) if not r.empty else d

        with st.form("form_ia"):
            ia_on   = st.toggle("🟢 IA Activée Globalement", value=get_s('ia_global_enabled','True')=='True')
            provider= st.selectbox("Moteur IA",["OpenRouter","Gemini (Google)","Claude"])
            key_or  = st.text_input("Clé API OpenRouter", value=get_s('openrouter_api_key'), type="password")
            key_gm  = st.text_input("Clé API Gemini",     value=get_s('gemini_api_key'),     type="password")
            if st.form_submit_button("Sauvegarder", type="primary", use_container_width=True):
                new_s = pd.DataFrame([
                    {'name':'ia_global_enabled','value':str(ia_on)},
                    {'name':'active_provider',  'value':provider},
                    {'name':'openrouter_api_key','value':key_or},
                    {'name':'gemini_api_key',    'value':key_gm},
                ])
                save_gs_data(new_s, DB_SETTINGS_WORKSHEET, DB_SETTINGS_FALLBACK)
                st.success("✅ Configuration IA sauvegardée !")

    with col_maint:
        st.markdown('<div class="section-title">💾 Maintenance & Backup</div>', unsafe_allow_html=True)
        st.info("Utilisez ces outils pour maintenir l'intégrité des données.")

        if st.button("📦 Exporter les Utilisateurs (CSV)", use_container_width=True):
            csv = df_users.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Télécharger", csv, "darpharm_users_backup.csv", "text/csv", use_container_width=True)

        st.markdown("---")

        st.markdown("**🔄 Restauration d'Urgence**")
        if st.button("🛡️ Restaurer Charte Officielle", type="primary", use_container_width=True, key="sys_restore"):
            restored = 0
            for (uname,_,urole,umetier,udepot) in GOLDEN_USERS:
                mask = df_users['username'] == uname
                if mask.any():
                    df_users = safe_set(df_users, mask, 'metier', umetier)
                    df_users = safe_set(df_users, mask, 'depot',  udepot)
                    df_users = safe_set(df_users, mask, 'pages',  PAGES_BY_METIER.get(umetier, PAGES_BY_METIER['Préparateur']))
                    df_users = safe_set(df_users, mask, 'role',   urole)
                    restored += 1
            save_gs_data(df_users, DB_USERS_WORKSHEET, DB_USERS_FALLBACK)
            st.success(f"✅ {restored} comptes restaurés depuis la Charte Officielle.")
            st.rerun()

        if is_admin:
            st.markdown("---")
            st.markdown("**⚠️ Zone Sensible**")
            del_target = st.selectbox("Supprimer un compte :", 
                [u for u in df_users['username'].tolist() if u != 'admin_imad'] if not df_users.empty else [], 
                key="del_user")
            if st.button("🗑️ Supprimer ce compte", key="btn_del"):
                df_users = df_users[df_users['username'] != del_target]
                save_gs_data(df_users, DB_USERS_WORKSHEET, DB_USERS_FALLBACK)
                st.warning(f"Compte {del_target} supprimé.")
                st.rerun()
