import streamlit as st
import pandas as pd
import json
import os
from tinydb import TinyDB, Query
from utils_ia import is_ia_enabled

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Darpharm Solution - Portail", layout="wide", page_icon="💊")

# --- 2. BASE DE DONNÉES UTILISATEURS ---
os.makedirs("data", exist_ok=True)
db_users = TinyDB('data/db_users.json')
if len(db_users) == 0:
    # Création de l'administrateur par défaut
    db_users.insert({
        'username': 'admin_imad',
        'password': 'admin_imad_pwd',
        'role': 'Admin',
        'pages': ['Logistique', 'Inventaire', 'Suivi', 'Recouvrement', 'Pointage', 'Péremptions', 'Dashboard']
    })
    # Quelques utilisateurs de test basés sur le code existant
    db_users.insert({'username': 'Ayoub', 'password': 'ayoub2026', 'role': 'Saisie', 'pages': ['Logistique', 'Suivi']})
    db_users.insert({'username': 'Islem', 'password': 'islem2026', 'role': 'Saisie', 'pages': ['Logistique', 'Suivi']})
    db_users.insert({'username': 'Seif', 'password': 'seif2026', 'role': 'Saisie', 'pages': ['Inventaire']})

# --- 3. GESTION DE SESSION ET "RESTER CONNECTÉ" ---
SESSION_FILE = 'data/session.json'

def save_session(username):
    if not os.path.exists('data'): os.makedirs('data')
    with open(SESSION_FILE, 'w') as f:
        json.dump({'username': username}, f)

def clear_session():
    if os.path.exists(SESSION_FILE):
        try: os.remove(SESSION_FILE)
        except: pass

def get_session():
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, 'r') as f:
                return json.load(f).get('username')
        except:
            return None
    return None

if "current_user" not in st.session_state:
    st.session_state.current_user = None
    saved_user = get_session()
    if saved_user:
        User = Query()
        result = db_users.search(User.username == saved_user)
        if result:
            st.session_state.current_user = result[0]

# --- 4. ÉCRAN DE CONNEXION ---
if st.session_state.current_user is None:
    st.markdown("""
        <style>
            [data-testid="stSidebar"], [data-testid="stSidebarNav"] {display: none;}
            section[data-testid="stSidebar"] {width: 0px;}
        </style>
    """, unsafe_allow_html=True)
    if os.path.exists("logo.png"):
        st.image("logo.png", width=200)
    st.title("🔐 Portail Darpharm Solution")
    st.write("Veuillez vous connecter pour accéder à vos modules.")
    
    with st.form("login_form"):
        u = st.text_input("Nom d'utilisateur")
        p = st.text_input("Mot de passe", type="password")
        remember = st.checkbox("Rester connecté")
        submit = st.form_submit_button("Se connecter", use_container_width=True)
        
        if submit:
            User = Query()
            result = db_users.search((User.username == u) & (User.password == p))
            if result:
                st.session_state.current_user = result[0]
                if remember:
                    save_session(u)
                st.rerun()
            else:
                st.error("Identifiants incorrects.")
    st.stop()

# --- 5. DÉFINITION DES PAGES DISPONIBLES ---
user = st.session_state.current_user
user_pages = user.get('pages', [])
is_admin = user.get('role') == 'Admin'

if is_admin and "Automatisation" not in user_pages:
    user_pages.append("Automatisation")

# Dictionnaire de toutes les pages possibles (Key: Nom, Value: Path)
ALL_PAGES = {
    "Logistique": st.Page("pages/1_expedition.py", title="Logistique", icon="🚛"),
    "Inventaire": st.Page("pages/2_inventaire.py", title="Inventaire", icon="📦"),
    "Inventaire Détail": st.Page("pages/8_inventaire_detail.py", title="Inventaire Détail", icon="🔍"),
    "Suivi": st.Page("pages/3_suivi.py", title="Suivi Frigo", icon="📊"),
    "Recouvrement": st.Page("pages/4_recouvrement.py", title="Recouvrement", icon="💰"),
    "Pointage": st.Page("pages/5_pointage.py", title="Pointage Factures", icon="📝"),
    "Péremptions": st.Page("pages/6_peremptions.py", title="Gestion des Péremptions", icon="⏳"),
    "Dashboard": st.Page("pages/7_dashboard.py", title="Tableau de Bord", icon="📊")
}

if is_ia_enabled():
    ALL_PAGES["Automatisation"] = st.Page("pages/9_automatisation.py", title="Automatisation & IA", icon="🤖")

# Filtrer selon les privilèges
pages_to_show = {}
nav_list = []

for p_name in user_pages:
    if p_name in ALL_PAGES:
        nav_list.append(ALL_PAGES[p_name])

if nav_list:
    pages_to_show["Mes Modules"] = nav_list

if is_admin:
    # Page cachée ou dédiée à l'administration
    pages_to_show["Administration Centrale"] = [
        st.Page("pages/5_admin.py", title="Gestion des Accès", icon="⚙️")
    ]

if not pages_to_show:
    st.warning("Vous n'avez accès à aucun module. Contactez l'administrateur.")
    if st.button("Déconnexion"):
        st.session_state.current_user = None
        st.rerun()
    st.stop()

# --- 6. NAVIGATION ET SIDEBAR ---
pg = st.navigation(pages_to_show)

with st.sidebar:
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    else:
        st.title("💊 Darpharm Solution")
    st.write(f"Connecté: **{user['username']}** ({user.get('role', 'Saisie')})")
    if st.button("🚪 Déconnexion", use_container_width=True):
        clear_session()
        st.session_state.current_user = None
        st.rerun()

pg.run()
