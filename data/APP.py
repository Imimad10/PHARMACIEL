import streamlit as st

st.set_page_config(page_title="Pharmaciel", layout="wide", page_icon="💊")

# --- CENTRALISATION AUTHENTIFICATION ---
if "user_authenticated" not in st.session_state:
    st.session_state.user_authenticated = None

if st.session_state.user_authenticated is None:
    st.title("🔐 Connexion Pharmaciel")
    u = st.text_input("Utilisateur")
    p = st.text_input("Mot de passe", type="a")
    if st.button("Se connecter"):
        # Ajoutez ici votre logique de vérification globale
        if u and p: 
            st.session_state.user_authenticated = u
            st.rerun()
    st.stop()

# --- DASHBOARD PRINCIPAL ---
st.title("💊 Bienvenue sur Pharmaciel")
st.write(f"Bonjour **{st.session_state.user_authenticated}**, que souhaitez-vous gérer aujourd'hui ?")

col1, col2, col3 = st.columns(3)
# app_pharm.py

# Remplacez les appels actuels par ceux-ci (assurez-vous de la casse exacte)
st.page_link("pages/1_expedition.py", label="Accéder à la Logistique", icon="🚛")
st.page_link("pages/2_inventaire.py", label="Accéder à l'Inventaire", icon="📦")
st.page_link("pages/3_suivi.py", label="Accéder au Suivi", icon="📊")
if st.sidebar.button("Déconnexion"):
    st.session_state.user_authenticated = None
    st.rerun()
