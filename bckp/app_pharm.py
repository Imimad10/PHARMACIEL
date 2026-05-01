import streamlit as st
from streamlit import Page

# Configuration de la page
st.set_page_config(page_title="Pharmaciel", layout="wide", page_icon="💊")

# --- CENTRALISATION AUTHENTIFICATION ---
if "user_authenticated" not in st.session_state:
    st.session_state.user_authenticated = None

if st.session_state.user_authenticated is None:
    st.title("🔐 Connexion Pharmaciel")
    u = st.text_input("Utilisateur")
    p = st.text_input("Mot de passe", type="password")
    
    if st.button("Se connecter"):
        # Logique de connexion simplifiée
        if u and p: 
            st.session_state.user_authenticated = u
            st.rerun()
    st.stop()

# --- DASHBOARD PRINCIPAL ---
st.title("💊 Bienvenue sur Pharmaciel")
st.write(f"Bonjour **{st.session_state.user_authenticated}**, que souhaitez-vous gérer aujourd'hui ?")

# 1. Définition des pages (C'est cette étape qui corrige le KeyError)
page_expedition = Page("pages/1_expedition.py", title="Accéder à la Logistique", icon="🚛")
page_inventaire = Page("pages/2_inventaire.py", title="Accéder à l'Inventaire", icon="📦")
page_suivi = Page("pages/3_suivi.py", title="Accéder au Suivi", icon="📊")

# 2. Affichage des liens via les objets Page
col1, col2, col3 = st.columns(3)

with col1:
    st.page_link(page_expedition)
with col2:
    st.page_link(page_inventaire)
with col3:
    st.page_link(page_suivi)

# Bouton de déconnexion dans la barre latérale
if st.sidebar.button("Déconnexion"):
    st.session_state.user_authenticated = None
    st.rerun()
