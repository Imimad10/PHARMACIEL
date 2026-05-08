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
st.header("🏆 Mes Exploits")
total_act, best_mod = get_user_exploits(username)

c1, c2 = st.columns(2)
c1.metric("Total Actions", total_act)
c2.metric("Module de Prédilection", best_mod)

if total_act > 100:
    st.success("🌟 Vous êtes un utilisateur expert ! Plus de 100 actions enregistrées.")
elif total_act > 50:
    st.info("📈 Bel effort ! Vous êtes très actif sur la plateforme.")
else:
    st.write("Continuez à utiliser les modules pour débloquer de nouveaux exploits !")

st.divider()

# --- SECTION 3 : SÉCURITÉ ---
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
