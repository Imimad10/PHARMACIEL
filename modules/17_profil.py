import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from utils_gsheets import load_gs_data, save_gs_data, DB_USERS_WORKSHEET, DB_USERS_FALLBACK
import time

# Configuration
LOGS_WORKSHEET = "Logs"
LOGS_FALLBACK = "data/db_logs.csv"

def get_user_exploits(username):
    df_logs = load_gs_data(LOGS_WORKSHEET, LOGS_FALLBACK, ["timestamp", "user", "module", "action"])
    if df_logs.empty:
        return 0, "Aucun"
    
    u_logs = df_logs[df_logs['user'] == username]
    total_actions = len(u_logs)
    if total_actions == 0:
        return 0, "Aucun"
    
    most_active_module = u_logs['module'].value_counts().idxmax()
    return total_actions, most_active_module

def get_trophies(username):
    df_logs = load_gs_data(LOGS_WORKSHEET, LOGS_FALLBACK, ["timestamp", "user", "module", "action"])
    if df_logs.empty:
        return [], 0
    
    u_logs = df_logs[df_logs['user'] == username]
    counts = u_logs['module'].value_counts()
    total = len(u_logs)
    
    trophy_defs = [
        ("Maître Inventaire", "📦", (counts.get("Inventaire Détail", 0) + counts.get("Inventaire", 0)) >= 50, "50+ actions"),
        ("Champion Logistique", "🚚", counts.get("Logistique", 0) >= 30, "30+ expéditions"),
        ("As Recouvrement", "💰", counts.get("Recouvrement", 0) >= 20, "20+ factures"),
        ("Gardien Froid", "❄️", counts.get("Suivi Frigo", 0) >= 10, "10+ relevés"),
        ("Scanneur Fou", "📱", (counts.get("Scanneur QR", 0) + counts.get("Scan Mobile", 0)) >= 15, "15+ scans"),
        ("Vétéran", "🎖️", total >= 200, "200+ actions"),
        ("Pionnier", "🚀", total >= 1, "1ère action")
    ]
    return trophy_defs, total

# --- STYLING ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    .profile-container {
        font-family: 'Outfit', sans-serif;
        color: #1a1c21;
    }
    
    /* Header Animation */
    .profile-header {
        background: linear-gradient(135deg, #1877f2 0%, #00d2ff 100%);
        padding: 40px;
        border-radius: 24px;
        color: white;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 20px 40px rgba(24, 119, 242, 0.2);
        animation: slideDown 0.8s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }
    
    .avatar-glow {
        width: 120px;
        height: 120px;
        background: white;
        border-radius: 50%;
        margin: 0 auto 15px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 60px;
        box-shadow: 0 0 20px rgba(255,255,255,0.5);
        animation: float 3s infinite ease-in-out;
    }
    
    /* KPI Cards */
    .kpi-card {
        background: white;
        padding: 25px;
        border-radius: 20px;
        border: 1px solid #f0f2f5;
        box-shadow: 0 10px 20px rgba(0,0,0,0.03);
        transition: all 0.3s ease;
        text-align: center;
        height: 100%;
    }
    .kpi-card:hover {
        transform: translateY(-8px) scale(1.02);
        box-shadow: 0 15px 30px rgba(0,0,0,0.08);
        border-color: #1877f2;
    }
    
    /* Trophy Grid */
    .trophy-badge {
        padding: 20px 10px;
        border-radius: 20px;
        text-align: center;
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        cursor: pointer;
        position: relative;
        overflow: hidden;
    }
    .trophy-badge.earned {
        background: linear-gradient(145deg, #ffffff, #f0f7ff);
        border: 2px solid #1877f2;
        box-shadow: 0 8px 16px rgba(24, 119, 242, 0.1);
    }
    .trophy-badge.earned:hover {
        transform: rotate(5deg) scale(1.1);
        box-shadow: 0 12px 24px rgba(24, 119, 242, 0.2);
    }
    .trophy-badge.locked {
        background: #f8f9fa;
        border: 2px dashed #e2e8f0;
        opacity: 0.6;
        filter: grayscale(1);
    }
    
    @keyframes slideDown {
        from { transform: translateY(-50px); opacity: 0; }
        to { transform: translateY(0); opacity: 1; }
    }
    @keyframes float {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-10px); }
    }
    
    .status-pill {
        display: inline-block;
        padding: 6px 16px;
        border-radius: 30px;
        font-size: 0.8rem;
        font-weight: 600;
        margin-top: 10px;
        background: rgba(255,255,255,0.2);
        backdrop-filter: blur(5px);
    }
</style>
""", unsafe_allow_html=True)

if 'current_user' not in st.session_state or not st.session_state.current_user:
    st.warning("Veuillez vous connecter pour accéder à votre profil.")
    st.stop()

user = st.session_state.current_user
username = user['username']
role = user.get('role', 'Agent')
nom_complet = f"{user.get('prenom', '')} {user.get('nom', '')}".strip() or username

# --- HEADER ---
st.markdown(f"""
    <div class="profile-header">
        <div class="avatar-glow">👤</div>
        <h1 style="margin: 0; font-size: 2.5rem; font-weight: 800;">{nom_complet}</h1>
        <div style="font-size: 1.1rem; opacity: 0.9;">@{username}</div>
        <div class="status-pill">🌟 {role} | 📍 {user.get('zone', 'Global')}</div>
    </div>
""", unsafe_allow_html=True)

# --- KPI SECTION ---
st.write("### 📊 Ma Performance Live")
total_actions, best_mod = get_user_exploits(username)
trophy_list, _ = get_trophies(username)

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f"""
        <div class="kpi-card">
            <div style="font-size: 3rem; margin-bottom: 10px;">⚡</div>
            <div style="font-size: 2rem; font-weight: 800; color: #1877f2;">{total_actions}</div>
            <div style="color: #64748b; font-weight: 600;">ACTIONS TOTALES</div>
        </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown(f"""
        <div class="kpi-card">
            <div style="font-size: 3rem; margin-bottom: 10px;">🎯</div>
            <div style="font-size: 1.2rem; font-weight: 800; color: #1877f2; text-transform: uppercase;">{best_mod}</div>
            <div style="color: #64748b; font-weight: 600;">DOMAINE D'EXPERTISE</div>
        </div>
    """, unsafe_allow_html=True)

with c3:
    earned_count = sum(1 for t in trophy_list if t[2])
    st.markdown(f"""
        <div class="kpi-card">
            <div style="font-size: 3rem; margin-bottom: 10px;">👑</div>
            <div style="font-size: 2rem; font-weight: 800; color: #1877f2;">{earned_count}/{len(trophy_list)}</div>
            <div style="color: #64748b; font-weight: 600;">TROPHÉES DÉBLOQUÉS</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- TROPHY GALLERY ---
st.write("### 🏅 Galerie des Trophées")
t_cols = st.columns(4)
for i, (name, emoji, earned, desc) in enumerate(trophy_list):
    with t_cols[i % 4]:
        status_class = "earned" if earned else "locked"
        icon = emoji if earned else "🔒"
        st.markdown(f"""
            <div class="trophy-badge {status_class}">
                <div style="font-size: 3rem; margin-bottom: 10px;">{icon}</div>
                <div style="font-weight: 800; font-size: 0.85rem; color: #1e293b;">{name}</div>
                <div style="font-size: 0.7rem; color: #64748b; line-height: 1.2;">{desc}</div>
            </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- AGENDA RH SECTION ---
st.write("### 📅 Mon Agenda DarPharm")
RH_WORKSHEET = "DB_RH_Gestion"
RH_FALLBACK = "data/db_rh.csv"
RH_COLS = ["ID", "Date_Debut", "Date_Fin", "Agent", "Type", "Statut", "Commentaire", "Date_Creation"]

df_rh = load_gs_data(RH_WORKSHEET, RH_FALLBACK, RH_COLS)

if not df_rh.empty:
    u_planning = df_rh[df_rh['Agent'] == username].sort_values("Date_Debut", ascending=False)
    if u_planning.empty:
        st.info("🕒 Aucun événement prévu dans votre agenda pour le moment.")
    else:
        plan_cols = st.columns(2)
        for i, (idx, row) in enumerate(u_planning.head(4).iterrows()):
            with plan_cols[i % 2]:
                status_color = "#10b981" if row['Statut'] == "Validé" else "#f59e0b"
                icon = "🕒" if "Permanence" in row['Type'] else "🏥"
                st.markdown(f"""
                    <div style="background: white; border-radius: 16px; padding: 15px; border-left: 5px solid {status_color}; 
                                box-shadow: 0 4px 12px rgba(0,0,0,0.05); margin-bottom: 10px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-weight: 800; color: #1e293b;">{icon} {row['Type']}</span>
                            <span style="font-size: 0.7rem; background: {status_color}22; color: {status_color}; 
                                         padding: 2px 8px; border-radius: 10px; font-weight: bold;">{row['Statut']}</span>
                        </div>
                        <div style="font-size: 0.9rem; color: #64748b; margin-top: 5px;">
                            📅 Du <b>{row['Date_Debut']}</b> au <b>{row['Date_Fin']}</b>
                        </div>
                        <div style="font-size: 0.8rem; color: #94a3b8; font-style: italic; margin-top: 5px;">
                            {row['Commentaire'] if row['Commentaire'] else 'Aucune observation'}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
else:
    st.info("🕒 Le planning RH est en cours de configuration.")

st.markdown("<br>", unsafe_allow_html=True)

# --- MISSIONS & ACTIVITÉ ---
col_act1, col_act2 = st.columns([1.5, 1])

with col_act1:
    st.write("### 📅 Activité Récente")
    df_logs = load_gs_data(LOGS_WORKSHEET, LOGS_FALLBACK, ["timestamp", "user", "module", "action"])
    if not df_logs.empty:
        u_logs = df_logs[df_logs['user'] == username].tail(50)
        if not u_logs.empty:
            # Chart simple mais joli
            u_logs['date'] = pd.to_datetime(u_logs['timestamp']).dt.date
            daily = u_logs.groupby('date').size().reset_index(name='Actions')
            fig = px.area(daily, x='date', y='Actions', template="plotly_white", 
                         color_discrete_sequence=['#1877f2'])
            fig.update_layout(height=250, margin=dict(l=10, r=10, t=10, b=10), showlegend=False)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("Commencez à utiliser les modules pour voir votre activité ici.")

with col_act2:
    st.write("### 🎁 Bonus & Missions")
    # Simulation de missions
    TASKS_WORKSHEET = "DB_Tasks_Team"
    TASKS_FALLBACK = "data/db_tasks.csv"
    df_tasks = load_gs_data(TASKS_WORKSHEET, TASKS_FALLBACK, ["status", "assigned_to"])
    
    num_done = 0
    if not df_tasks.empty:
        num_done = len(df_tasks[(df_tasks['assigned_to'] == username) & (df_tasks['status'] == "Terminé")])
    
    progress = min(num_done / 10, 1.0) # Objectif 10 missions
    st.markdown(f"""
        <div class="kpi-card" style="text-align: left;">
            <div style="font-weight: bold; margin-bottom: 5px;">Progression Prime Mensuelle</div>
            <div style="height: 12px; background: #e2e8f0; border-radius: 10px; overflow: hidden; margin-bottom: 15px;">
                <div style="width: {progress*100}%; height: 100%; background: linear-gradient(90deg, #1877f2, #00d2ff); transition: width 1s ease-in-out;"></div>
            </div>
            <div style="font-size: 0.9rem; color: #64748b;">
                <b>{num_done} missions</b> accomplies sur 10.<br>
                Prime actuelle : <span style="color: #10b981; font-weight: bold;">{num_done * 100} DA</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    if st.button("🚀 Relever un nouveau défi", use_container_width=True):
        st.toast("Rendez-vous dans 'Coordination Équipe' pour vos missions !")

st.divider()

# --- SETTINGS ---
with st.expander("⚙️ Paramètres du Compte"):
    c_s1, c_s2 = st.columns(2)
    with c_s1:
        st.write("🔒 Sécurité")
        with st.form("pwd_form"):
            new_p = st.text_input("Nouveau mot de passe", type="password")
            confirm_p = st.text_input("Confirmer", type="password")
            if st.form_submit_button("Mettre à jour"):
                if new_p and new_p == confirm_p:
                    df_all = load_gs_data(DB_USERS_WORKSHEET, DB_USERS_FALLBACK, ["username", "password", "role", "pages", "nom", "prenom", "zone"])
                    mask = df_all['username'] == username
                    if mask.any():
                        df_all.loc[mask, 'password'] = new_p
                        save_gs_data(df_all, DB_USERS_WORKSHEET, DB_USERS_FALLBACK)
                        st.success("✅ Mis à jour !")
                    else: st.error("Erreur technique.")
                else: st.error("Incohérence des mots de passe.")
    
    with c_s2:
        st.write("🔧 Session")
        if st.button("🚪 Déconnexion", type="primary", use_container_width=True):
            st.session_state.current_user = None
            st.rerun()

st.markdown('<div style="text-align: center; color: #94a3b8; font-size: 0.8rem; margin-top: 50px;">Pharmaciel Pro v3.0 | Expérience Premium</div>', unsafe_allow_html=True)
