import streamlit as st
import pandas as pd
from tinydb import TinyDB, Query
import os

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Pharmaciel - Portail", layout="wide", page_icon="💊")

# --- 2. BASE DE DONNÉES UTILISATEURS ---
os.makedirs("data", exist_ok=True)
db_users = TinyDB('data/db_users.json')
if len(db_users) == 0:
    # Création de l'administrateur par défaut
    db_users.insert({
        'username': 'admin_imad',
        'password': 'admin_imad_pwd',
        'role': 'Admin',
        'pages': ['Logistique', 'Inventaire', 'Suivi', 'Recouvrement', 'Pointage', 'Péremptions']
    })
    # Quelques utilisateurs de test basés sur le code existant
    db_users.insert({'username': 'Ayoub', 'password': 'ayoub2026', 'role': 'Saisie', 'pages': ['Logistique', 'Suivi']})
    db_users.insert({'username': 'Islem', 'password': 'islem2026', 'role': 'Saisie', 'pages': ['Logistique', 'Suivi']})
    db_users.insert({'username': 'Seif', 'password': 'seif2026', 'role': 'Saisie', 'pages': ['Inventaire']})

# --- 3. GESTION DE SESSION ---
if "current_user" not in st.session_state:
    st.session_state.current_user = None

# --- 4. ÉCRAN DE CONNEXION ---
if st.session_state.current_user is None:
    st.title("🔐 Portail Pharmaciel")
    st.write("Veuillez vous connecter pour accéder à vos modules.")
    
    with st.form("login_form"):
        u = st.text_input("Nom d'utilisateur")
        p = st.text_input("Mot de passe", type="password")
        submit = st.form_submit_button("Se connecter")
        
        if submit:
            User = Query()
            result = db_users.search((User.username == u) & (User.password == p))
            if result:
                st.session_state.current_user = result[0]
                st.rerun()
            else:
                st.error("Identifiants incorrects.")
    st.stop()

# --- 5. DÉFINITION DES PAGES DISPONIBLES ---
user = st.session_state.current_user
user_pages = user.get('pages', [])
is_admin = user.get('role') == 'Admin'

# Dictionnaire de toutes les pages possibles (Key: Nom, Value: Path)
ALL_PAGES = {
    "Logistique": st.Page("pages/1_expedition.py", title="Logistique", icon="🚛"),
    "Inventaire": st.Page("pages/2_inventaire.py", title="Inventaire", icon="📦"),
    "Suivi": st.Page("pages/3_suivi.py", title="Suivi Frigo", icon="📊"),
    "Recouvrement": st.Page("pages/4_recouvrement.py", title="Recouvrement", icon="💰"),
    "Pointage": st.Page("pages/5_pointage.py", title="Pointage Factures", icon="📝"),
    "Péremptions": st.Page("pages/6_peremptions.py", title="Gestion des Péremptions", icon="⏳")
}

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
    pages_to_show["Administration Centrale"] = [st.Page("pages/5_admin.py", title="Gestion des Accès", icon="⚙️")]

if not pages_to_show:
    st.warning("Vous n'avez accès à aucun module. Contactez l'administrateur.")
    if st.button("Déconnexion"):
        st.session_state.current_user = None
        st.rerun()
    st.stop()

# --- 6. NAVIGATION ET SIDEBAR ---
pg = st.navigation(pages_to_show)

with st.sidebar:
    st.title("💊 Pharmaciel")
    st.write(f"Connecté: **{user['username']}** ({user.get('role', 'Saisie')})")
    if st.button("🚪 Déconnexion", use_container_width=True):
        st.session_state.current_user = None
        st.rerun()

pg.run()
