import streamlit as st
from streamlit import Page

# 1. CONFIGURATION (Doit être la TOUTE première ligne)
st.set_page_config(page_title="Pharmaciel Pro", layout="wide", page_icon="💊")

# 2. INITIALISATION DE L'AUTHENTIFICATION
if "user_authenticated" not in st.session_state:
    st.session_state.user_authenticated = None

# --- ÉCRAN DE CONNEXION ---
if st.session_state.user_authenticated is None:
    st.title("🔐 Connexion Pharmaciel")
    col_auth, _ = st.columns([1, 2])
    with col_auth:
        u = st.text_input("Utilisateur")
        p = st.text_input("Mot de passe", type="password")
        if st.button("Se connecter", use_container_width=True):
            if u and p:
                st.session_state.user_authenticated = u
                st.rerun()
    st.stop()

# --- NAVIGATION ---
try:
    p1 = Page("pages/1_expedition.py", title="Logistique", icon="🚛")
    p2 = Page("pages/2_inventaire.py", title="Inventaire", icon="📦")
    p3 = Page("pages/3_suivi.py", title="Analyses", icon="📊")

    pg = st.navigation({"Menu Principal": [p1, p2, p3]})
    
    st.sidebar.title("💊 Pharmaciel")
    st.sidebar.write(f"Connecté : **{st.session_state.user_authenticated}**")
    
    if st.sidebar.button("Déconnexion"):
        st.session_state.user_authenticated = None
        st.rerun()

    pg.run()
except Exception as e:
    st.error(f"Erreur : {e}")
