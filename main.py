import streamlit as st
from streamlit import Page

# 1. CONFIGURATION (Impérativement la première ligne du script)
st.set_page_config(page_title="Darpharm Solution", layout="wide", page_icon="💊")

# 2. INITIALISATION DE L'AUTHENTIFICATION
if "user_authenticated" not in st.session_state:
    st.session_state.user_authenticated = None

# --- ÉCRAN DE CONNEXION ---
if st.session_state.user_authenticated is None:
    st.markdown("""
        <style>
            [data-testid="stSidebar"], [data-testid="stSidebarNav"] {display: none;}
            section[data-testid="stSidebar"] {width: 0px;}
            [data-testid="stHeader"] {display: none;}
            .stApp { background-color: #f0f2f5 !important; }
            .main .block-container { max-width: 1000px; padding-top: 100px; margin: auto; }
            .fb-logo-text { color: #1877f2; font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 55px; font-weight: bold; letter-spacing: -1.5px; margin-bottom: 0px; }
            .fb-slogan { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-size: 24px; color: #1c1e21; margin-top: 15px; }
            .login-card { background-color: white; padding: 20px 20px 25px 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0, 0, 0, .1), 0 8px 16px rgba(0, 0, 0, .1); }
            .stTextInput input { height: 52px !important; border: 1px solid #dddfe2 !important; border-radius: 6px !important; margin-bottom: 10px !important; }
            ::placeholder { color: #8d949e !important; opacity: 1 !important; }
            div[data-testid="stFormSubmitButton"] button { background-color: #1877f2 !important; color: white !important; font-size: 20px !important; font-weight: bold !important; height: 48px !important; border-radius: 6px !important; width: 100% !important; border: none !important; }
            [data-testid="stForm"] { border: none !important; padding: 0 !important; }
        </style>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1.3, 1], gap="large")
    with col1:
        st.markdown('<h1 class="fb-logo-text">DarPharm®Solutions</h1>', unsafe_allow_html=True)
        st.markdown('<p class="fb-slogan">Gérez votre logistique et vos stocks en toute simplicité.</p>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        with st.form("login_form_main"):
            u = st.text_input("Username", placeholder="Utilisateur", label_visibility="collapsed")
            p = st.text_input("Password", type="password", placeholder="Mot de passe", label_visibility="collapsed")
            if st.form_submit_button("Se connecter"):
                if u and p:
                    st.session_state.user_authenticated = u
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
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
