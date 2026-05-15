import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from utils_gsheets import load_gs_data, save_gs_data, DB_USERS_WORKSHEET, DB_USERS_FALLBACK

LOGS_WORKSHEET = "Logs"
LOGS_FALLBACK  = "data/db_logs.csv"
RH_WORKSHEET   = "DB_RH_Gestion"
RH_FALLBACK    = "data/db_rh.csv"
TASKS_WORKSHEET = "DB_Tasks_Team"
TASKS_FALLBACK  = "data/db_tasks.csv"
COLS_TASKS      = ["id", "creation_date", "task", "assigned_to", "priority", "status"]

SOUS_METIERS = ["Préparateur", "Contrôleur", "Étalagiste", "Ramasseur", "Magasinier", "Agent Polyvalent"]

if 'current_user' not in st.session_state or not st.session_state.current_user:
    st.warning("Veuillez vous connecter.")
    st.stop()

user     = st.session_state.current_user
username = user['username']
role     = user.get('role', 'Saisie')
is_admin = role == 'Admin'

# ── CSS ─────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
* { font-family: 'Outfit', sans-serif; }

.profile-hero {
    background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
    border-radius: 24px; padding: 40px; color: white;
    display: flex; align-items: center; gap: 30px;
    margin-bottom: 30px;
    box-shadow: 0 20px 40px rgba(0,0,0,0.15);
}
.avatar-circle {
    width: 110px; height: 110px; border-radius: 50%;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    display: flex; align-items: center; justify-content: center;
    font-size: 3rem; flex-shrink: 0;
    box-shadow: 0 0 0 4px rgba(255,255,255,0.15);
}
.hero-name   { font-size: 2rem; font-weight: 800; margin: 0; }
.hero-meta   { font-size: 0.95rem; opacity: 0.7; margin: 4px 0 0; }
.hero-badge  { display: inline-block; background: rgba(255,255,255,0.15);
               padding: 4px 14px; border-radius: 20px; font-size: 0.8rem;
               font-weight: 600; margin-top: 10px; }

.stat-card {
    background: white; border-radius: 16px; padding: 22px;
    border: 1px solid #f1f5f9; text-align: center;
    box-shadow: 0 4px 12px rgba(0,0,0,0.04);
    transition: all .3s ease;
}
.stat-card:hover { transform: translateY(-4px); box-shadow: 0 12px 24px rgba(0,0,0,0.08); }
.stat-num   { font-size: 2.2rem; font-weight: 800; color: #6366f1; }
.stat-label { font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; }

.agenda-card {
    background: white; border-radius: 14px; padding: 16px;
    border-left: 5px solid #10b981; margin-bottom: 10px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
.trophy-item {
    background: white; border-radius: 14px; padding: 18px;
    text-align: center; border: 2px solid #e2e8f0;
    transition: all .3s ease;
}
.trophy-item.earned { border-color: #6366f1; background: #faf5ff; }
.trophy-item.locked { opacity: .5; filter: grayscale(1); }

.edit-section {
    background: #f8fafc; border-radius: 20px; padding: 28px;
    border: 1px solid #e2e8f0; margin-top: 20px;
}
</style>
""", unsafe_allow_html=True)

# ── Chargement des données ───────────────────────────────────────────────────
df_users = load_gs_data(DB_USERS_WORKSHEET, DB_USERS_FALLBACK)
df_logs  = load_gs_data(LOGS_WORKSHEET, LOGS_FALLBACK, ["timestamp","user","module","action"])
df_rh    = load_gs_data(RH_WORKSHEET,   RH_FALLBACK,   ["ID","Date_Debut","Date_Fin","Agent","Type","Statut","Commentaire"])
df_tasks = load_gs_data(TASKS_WORKSHEET, TASKS_FALLBACK, COLS_TASKS)

u_row = df_users[df_users['username'] == username]
nom_complet = ""
if not u_row.empty:
    nom  = str(u_row.iloc[0].get('nom',  '') or '')
    pren = str(u_row.iloc[0].get('prenom','') or '')
    nom_complet = f"{pren} {nom}".strip() or username
    metier      = str(u_row.iloc[0].get('metier',   '') or '')
    sous_metier = str(u_row.iloc[0].get('sous_metier','') or '')
    depot       = str(u_row.iloc[0].get('depot',    '') or '')
else:
    metier = sous_metier = depot = ''

# Statistiques
u_logs = df_logs[df_logs['user'] == username] if not df_logs.empty else pd.DataFrame()
total_actions = len(u_logs)
best_mod = u_logs['module'].value_counts().idxmax() if not u_logs.empty else "—"

# ── HERO HEADER ─────────────────────────────────────────────────────────────
metier_icon = {"Agent de Stock":"📦","Préparateur":"⚙️","Chef Livreurs & Parc":"🚚",
               "Superviseur":"🔭","Admin":"👑"}.get(metier, "👤")

st.markdown(f"""
<div class="profile-hero">
    <div class="avatar-circle">{metier_icon}</div>
    <div>
        <p class="hero-name">{nom_complet}</p>
        <p class="hero-meta">@{username} · {depot}</p>
        <span class="hero-badge">🏷️ {metier}{' — ' + sous_metier if sous_metier else ''}</span>
        <span class="hero-badge" style="margin-left:8px;">🕐 {datetime.now().strftime('%H:%M')}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── KPIs ────────────────────────────────────────────────────────────────────
TROPHY_DEFS = [
    ("Maître Stock",    "📦", (u_logs['module'].value_counts().get("Inventaire Détail",0)+u_logs['module'].value_counts().get("Inventaire",0)) >= 50 if not u_logs.empty else False, "50+ actions stock"),
    ("Logisticien",     "🚚", u_logs['module'].value_counts().get("Logistique",0) >= 30 if not u_logs.empty else False,  "30+ expéditions"),
    ("As Recouvrement", "💰", u_logs['module'].value_counts().get("Recouvrement",0) >= 20 if not u_logs.empty else False,"20+ factures"),
    ("Scanneur",        "📱", (u_logs['module'].value_counts().get("Scanneur QR",0)+u_logs['module'].value_counts().get("Scan Mobile",0)) >= 15 if not u_logs.empty else False, "15+ scans"),
    ("Vétéran",         "🎖️", total_actions >= 200, "200+ actions"),
    ("Pionnier",        "🚀", total_actions >= 1,   "1ère action"),
]
earned = sum(1 for _,_,ok,_ in TROPHY_DEFS if ok)

c1,c2,c3 = st.columns(3)
c1.markdown(f'<div class="stat-card"><div class="stat-num">{total_actions}</div><div class="stat-label">Actions Totales</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="stat-card"><div class="stat-num" style="font-size:1.3rem;">{best_mod}</div><div class="stat-label">Module Favori</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="stat-card"><div class="stat-num">{earned}/{len(TROPHY_DEFS)}</div><div class="stat-label">Trophées</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── TABS ─────────────────────────────────────────────────────────────────────
tab_taches, tab_agenda, tab_edit, tab_trophees, tab_activite, tab_compte = st.tabs(
    ["✅ Mes Tâches", "📅 Mon Agenda", "✏️ Mon Profil", "🏅 Trophées", "📈 Activité", "⚙️ Compte"])

# ── TAB : TÂCHES & MISSIONS ──────────────────────────────────────────────────
with tab_taches:
    st.write("#### 🎯 Mes Missions du Jour")
    if not df_tasks.empty:
        my_tasks = df_tasks[df_tasks['assigned_to'] == username]
        if my_tasks.empty:
            st.info("Aucune tâche ne vous est assignée pour le moment. Bon travail ! 🎉")
        else:
            for _, row in my_tasks.iterrows():
                # Définition des couleurs selon la priorité et le statut
                priority_colors = {"Urgent": "#ef4444", "Normale": "#f59e0b", "Basse": "#3b82f6"}
                status_colors = {"À faire": "#f1f5f9", "En cours": "#fef3c7", "Terminé": "#dcfce3"}
                p_col = priority_colors.get(str(row.get('priority')), "#94a3b8")
                s_col = status_colors.get(str(row.get('status')), "#ffffff")
                
                # Checkbox pour marquer comme fait (visuel uniquement, le vrai changement se fait par l'Admin ou via le Dashboard)
                is_done = row.get('status') == "Terminé"
                icon_done = "✅" if is_done else "⏳"
                
                st.markdown(f"""
                <div style="background:{s_col}; border-left: 5px solid {p_col}; padding: 15px; border-radius: 10px; margin-bottom: 12px; box-shadow: 0 2px 4px rgba(0,0,0,0.05);">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                        <span style="font-weight: 700; font-size: 1.05rem; color: #1e293b;">{row.get('task', 'Tâche')}</span>
                        <span style="font-size: 0.8rem; background: {p_col}22; color: {p_col}; padding: 2px 8px; border-radius: 10px; font-weight: 600;">Priorité {row.get('priority', 'Normale')}</span>
                    </div>
                    <div style="font-size: 0.85rem; color: #64748b;">
                        {icon_done} Statut : <b>{row.get('status', 'À faire')}</b>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            st.caption("ℹ️ Vos tâches sont gérées par le Superviseur ou l'Administrateur via le module de Coordination.")
    else:
        st.info("Aucune tâche ne vous est assignée pour le moment.")

# ── TAB : AGENDA RH ──────────────────────────────────────────────────────────
with tab_agenda:
    st.write("#### 📅 Mes Événements RH")
    if not df_rh.empty:
        u_plan = df_rh[df_rh['Agent'] == username].sort_values("Date_Debut", ascending=False)
        if u_plan.empty:
            st.info("Aucun événement planifié pour vous pour le moment.")
        else:
            for _, row in u_plan.head(6).iterrows():
                color = "#10b981" if row['Statut'] == "Validé" else "#f59e0b"
                icon  = "🕒" if "Permanence" in str(row['Type']) else "🏥"
                st.markdown(f"""
                <div class="agenda-card" style="border-left-color:{color};">
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <b>{icon} {row['Type']}</b>
                        <span style="background:{color}22;color:{color};padding:2px 10px;border-radius:12px;font-size:.75rem;font-weight:700;">{row['Statut']}</span>
                    </div>
                    <div style="color:#64748b;font-size:.9rem;margin-top:5px;">📅 {row['Date_Debut']} → {row['Date_Fin']}</div>
                    <div style="color:#94a3b8;font-size:.8rem;font-style:italic;">{row.get('Commentaire','') or 'Aucune note'}</div>
                </div>""", unsafe_allow_html=True)
    else:
        st.info("Module RH en cours de configuration.")

# ── TAB : ÉDITION PROFIL ─────────────────────────────────────────────────────
with tab_edit:
    st.write("#### ✏️ Modifier mes Informations")
    st.info("Vous pouvez mettre à jour votre nom, prénom et votre spécialité.")

    with st.form("form_edit_profil"):
        col1, col2 = st.columns(2)
        new_nom  = col1.text_input("Nom de famille",  value=nom  if not u_row.empty else "")
        new_pren = col2.text_input("Prénom",          value=pren if not u_row.empty else "")

        # Sous-métier : champ libre dans la Charte officielle
        sm_idx = SOUS_METIERS.index(sous_metier) if sous_metier in SOUS_METIERS else 0
        new_sm = st.selectbox("Ma spécialité au sein de mon équipe",
                              SOUS_METIERS, index=sm_idx,
                              help="Votre rôle précis dans votre dépôt")

        new_tel = st.text_input("Téléphone (optionnel)",
                                value=str(u_row.iloc[0].get('tel','') or '') if not u_row.empty else "")

        if st.form_submit_button("💾 Sauvegarder mes modifications", type="primary", use_container_width=True):
            if not u_row.empty:
                mask = df_users['username'] == username
                # S'assurer que les colonnes existent en type object (string)
                for col in ['nom', 'prenom', 'sous_metier', 'tel']:
                    if col not in df_users.columns:
                        df_users[col] = ''
                    df_users[col] = df_users[col].astype(object)
                df_users.loc[mask, 'nom']         = new_nom
                df_users.loc[mask, 'prenom']       = new_pren
                df_users.loc[mask, 'sous_metier']  = new_sm
                df_users.loc[mask, 'tel']          = new_tel
                save_gs_data(df_users, DB_USERS_WORKSHEET, DB_USERS_FALLBACK)
                # Mise à jour session
                st.session_state.current_user['nom']        = new_nom
                st.session_state.current_user['prenom']     = new_pren
                st.session_state.current_user['sous_metier']= new_sm
                st.success("✅ Profil mis à jour avec succès !")
                st.rerun()
            else:
                st.error("Utilisateur introuvable.")

# ── TAB : TROPHÉES ───────────────────────────────────────────────────────────
with tab_trophees:
    st.write("#### 🏅 Galerie des Trophées")
    cols = st.columns(3)
    for i,(name,emoji,ok,desc) in enumerate(TROPHY_DEFS):
        cls  = "earned" if ok else "locked"
        icon = emoji if ok else "🔒"
        cols[i%3].markdown(f"""
        <div class="trophy-item {cls}">
            <div style="font-size:2.5rem;margin-bottom:8px;">{icon}</div>
            <div style="font-weight:800;font-size:.9rem;">{name}</div>
            <div style="font-size:.75rem;color:#94a3b8;">{desc}</div>
        </div>""", unsafe_allow_html=True)

# ── TAB : ACTIVITÉ ───────────────────────────────────────────────────────────
with tab_activite:
    st.write("#### 📈 Mon Activité Récente")
    if not u_logs.empty:
        u_logs2 = u_logs.copy()
        u_logs2['date'] = pd.to_datetime(u_logs2['timestamp'], errors='coerce').dt.date
        daily = u_logs2.groupby('date').size().reset_index(name='Actions')
        fig = px.area(daily, x='date', y='Actions', template="plotly_white",
                      color_discrete_sequence=['#6366f1'])
        fig.update_layout(height=250, margin=dict(l=0,r=0,t=10,b=0), showlegend=False,
                          paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        st.write("**20 dernières actions :**")
        recent = u_logs.tail(20)[['timestamp','module','action']].iloc[::-1]
        st.dataframe(recent, use_container_width=True, hide_index=True)
    else:
        st.info("Aucune activité enregistrée.")

# ── TAB : COMPTE ─────────────────────────────────────────────────────────────
with tab_compte:
    st.write("#### ⚙️ Paramètres de Sécurité")

    with st.form("form_pwd"):
        new_p = st.text_input("Nouveau mot de passe", type="password")
        conf_p= st.text_input("Confirmer le mot de passe", type="password")
        if st.form_submit_button("🔒 Changer le mot de passe"):
            if new_p and new_p == conf_p:
                if len(new_p) < 6:
                    st.error("Mot de passe trop court (min. 6 caractères).")
                else:
                    mask = df_users['username'] == username
                    df_users.loc[mask, 'password'] = new_p
                    save_gs_data(df_users, DB_USERS_WORKSHEET, DB_USERS_FALLBACK)
                    st.success("✅ Mot de passe mis à jour !")
            else:
                st.error("Les mots de passe ne correspondent pas.")

    st.divider()
    if st.button("🚪 Se Déconnecter", type="primary", use_container_width=True):
        st.session_state.current_user = None
        st.rerun()

st.markdown('<div style="text-align:center;color:#cbd5e1;font-size:.75rem;margin-top:40px;">DarPharm Pro · Espace Personnel Sécurisé</div>', unsafe_allow_html=True)
