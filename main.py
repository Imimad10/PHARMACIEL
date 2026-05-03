import streamlit as st
from streamlit import Page

# 1. CONFIGURATION (Impérativement la première ligne du script)
st.set_page_config(page_title="Darpharm Solution", layout="wide", page_icon="💊")

# 2. INITIALISATION DE L'AUTHENTIFICATION
if "user_authenticated" not in st.session_state:
    st.session_state.user_authenticated = None

# --- ÉCRAN DE CONNEXION ---
if st.session_state.user_authenticated is None:
    st.title("🔐 Connexion Darpharm Solution")
    col_auth, _ = st.columns([1, 2])
    with col_auth:
        u = st.text_input("Utilisateur")
        p = st.text_input("Mot de passe", type="password")
        if st.button("Se connecter", use_container_width=True):
            if u and p:
                st.session_state.user_authenticated = u
                st.rerun()
    st.stop()

# --- NAVIGATION MULTI-PAGES ---
try:
    # Définition des liens vers les fichiers du dossier /pages/
    p1 = Page("pages/1_expedition.py", title="Logistique", icon="🚛")
    p2 = Page("pages/2_inventaire.py", title="Inventaire", icon="📦")
    p3 = Page("pages/3_suivi.py", title="Analyses", icon="📊")
    p4 = Page("pages/4_recouvrement.py", title="Recouvrement", icon="💰")

    # Création du menu de navigation latéral
    pg = st.navigation({
        "Menu Principal": [p1, p2, p3, p4]
    })
    
    # Barre latérale (Sidebar) avec infos utilisateur
    st.sidebar.title("💊 Darpharm Solution")
    st.sidebar.write(f"Connecté : **{st.session_state.user_authenticated}**")
    
    if st.sidebar.button("Déconnexion"):
        st.session_state.user_authenticated = None
        st.rerun()

    # Lancement de la page sélectionnée
    pg.run()

except Exception as e:
    st.error(f"Une erreur est survenue lors du chargement de la navigation : {e}")
