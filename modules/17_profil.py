import streamlit as st
import pandas as pd
from datetime import datetime
from utils_gsheets import load_gs_data, save_gs_data, DB_USERS_WORKSHEET, DB_USERS_FALLBACK

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

st.title("👤 Mon Profil")

if 'current_user' not in st.session_state or not st.session_state.current_user:
    st.warning("Veuillez vous connecter pour accéder à votre profil.")
    st.stop()

user = st.session_state.current_user
username = user['username']

# --- SECTION 1 : INFORMATIONS PERSONNELLES ---
st.header("📋 Informations Personnelles")
col1, col2 = st.columns(2)

with col1:
    st.markdown(f"**Nom d'utilisateur :** `{username}`")
    st.markdown(f"**Rôle :** {user.get('role', 'Saisie')}")
    st.markdown(f"**Zone d'inventaire :** {user.get('zone', 'Aucune')}")

with col2:
    st.markdown(f"**Nom :** {user.get('nom', 'Non renseigné')}")
    st.markdown(f"**Prénom :** {user.get('prenom', 'Non renseigné')}")

st.divider()

# --- SECTION 2 : EXPLOITS & PERFORMANCE ---
st.header("🏆 Mes Exploits & Trophées")

def get_trophies(username):
    df_logs = load_gs_data(LOGS_WORKSHEET, LOGS_FALLBACK, ["timestamp", "user", "module", "action"])
    if df_logs.empty:
        return []
    
    u_logs = df_logs[df_logs['user'] == username]
    counts = u_logs['module'].value_counts()
    total = len(u_logs)
    
    trophies = []
    
    # Définition des trophées (Nom, Emoji, Condition, Description)
    trophy_defs = [
        ("Maître de l'Inventaire", "📦", counts.get("Inventaire Détail", 0) + counts.get("Inventaire", 0) >= 50, "50+ actions d'inventaire"),
        ("Champion Logistique", "🚚", counts.get("Logistique", 0) >= 30, "30+ expéditions gérées"),
        ("As du Recouvrement", "💰", counts.get("Recouvrement", 0) >= 20, "20+ pointages de factures"),
        ("Gardien du Froid", "❄️", counts.get("Suivi Frigo", 0) >= 10, "10+ relevés de température"),
        ("Scanneur Fou", "📱", counts.get("Scanneur QR", 0) + counts.get("Scan Mobile", 0) >= 15, "15+ scans effectués"),
        ("Vétéran Darpharm", "🎖️", total >= 200, "Plus de 200 actions au total"),
        ("Pionnier", "🚀", total >= 1, "Première action réalisée")
    ]
    
    return trophy_defs, total

trophy_list, total_act = get_trophies(username)

# Affichage des métriques de base
c1, c2 = st.columns(2)
c1.metric("Total Actions", total_act)
if total_act > 0:
    # On recalcule best_mod ici
    df_logs = load_gs_data(LOGS_WORKSHEET, LOGS_FALLBACK, ["timestamp", "user", "module", "action"])
    best_mod = df_logs[df_logs['user'] == username]['module'].value_counts().idxmax()
    c2.metric("Module de Prédilection", best_mod)

st.write("---")
st.subheader("🏅 Galerie des Trophées")

# Affichage en grille
cols_t = st.columns(4)
for i, (name, emoji, earned, desc) in enumerate(trophy_list):
    with cols_t[i % 4]:
        if earned:
            st.markdown(f"""
                <div style="text-align: center; padding: 15px; border-radius: 10px; background-color: #d4edda; border: 2px solid #28a745; margin-bottom: 10px;">
                    <div style="font-size: 2.5rem;">{emoji}</div>
                    <div style="font-weight: bold; color: #155724; font-size: 0.9rem;">{name}</div>
                    <div style="font-size: 0.7rem; color: #155724;">{desc}</div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div style="text-align: center; padding: 15px; border-radius: 10px; background-color: #f8f9fa; border: 2px dotted #ced4da; opacity: 0.5; margin-bottom: 10px;">
                    <div style="font-size: 2.5rem; filter: grayscale(100%);">🔒</div>
                    <div style="font-weight: bold; color: #6c757d; font-size: 0.9rem;">{name}</div>
                    <div style="font-size: 0.7rem; color: #6c757d;">{desc}</div>
                </div>
            """, unsafe_allow_html=True)

st.divider()

# --- SECTION 2.5 : MISSIONS & RÉCOMPENSES ---
st.header("🌟 Mes Missions & Primes")
TASKS_WORKSHEET = "DB_Tasks_Team"
TASKS_FALLBACK = "data/db_tasks.csv"
COLS_TASKS = ["id", "creation_date", "task", "assigned_to", "priority", "status"]

df_tasks = load_gs_data(TASKS_WORKSHEET, TASKS_FALLBACK, COLS_TASKS)
if not df_tasks.empty:
    user_tasks = df_tasks[(df_tasks['assigned_to'] == username) & (df_tasks['status'] == "Terminé")]
    num_completed = len(user_tasks)
    prime_est = num_completed * 100 # 100 DA par mission
    
    col_p1, col_p2, col_p3 = st.columns(3)
    col_p1.metric("Missions Accomplies", num_completed, help="Nombre de tâches marquées comme terminées ce mois-ci.")
    col_p2.metric("Prime Estimée", f"{prime_est} DA", delta=f"{num_completed*10} pts", help="Basé sur 100 DA par mission.")
    
    if num_completed > 0:
        st.success(f"Bravo {username} ! Vous êtes dans le top performance ce mois-ci. 🚀")
        with st.expander("📝 Détail de mes missions terminées"):
            st.table(user_tasks[['creation_date', 'task', 'priority']])
    else:
        st.info("Aucune mission terminée pour le moment. Acceptez une tâche dans le module 'Coordination Équipe' pour commencer à cumuler des primes !")
else:
    st.info("Le système de missions est en attente de données.")

st.divider()
st.header("🔐 Sécurité")
with st.form("change_pwd_profile"):
    st.write("Changer mon mot de passe")
    new_p = st.text_input("Nouveau mot de passe", type="password")
    confirm_p = st.text_input("Confirmer le mot de passe", type="password")
    
    if st.form_submit_button("Mettre à jour mon mot de passe"):
        if new_p and new_p == confirm_p:
            df_all = load_gs_data(DB_USERS_WORKSHEET, DB_USERS_FALLBACK, ["username", "password", "role", "pages", "nom", "prenom", "zone"])
            mask = df_all['username'] == username
            if mask.any():
                df_all.loc[mask, 'password'] = new_p
                save_gs_data(df_all, DB_USERS_WORKSHEET, DB_USERS_FALLBACK)
                st.success("✅ Mot de passe mis à jour avec succès !")
                st.session_state.current_user['password'] = new_p
            else:
                st.error("Erreur technique : Profil introuvable.")
        else:
            st.error("Les mots de passe ne correspondent pas ou sont vides.")

st.divider()
if st.button("🚪 Déconnexion", type="primary", use_container_width=True):
    st.session_state.current_user = None
    st.rerun()
