import streamlit as st
import pandas as pd
import json
import os
from tinydb import TinyDB, Query
from utils_ia import is_ia_enabled
from streamlit_cookies_controller import CookieController

# --- 1. CONFIGURATION & THÈME ---
st.set_page_config(page_title="Darpharm Solution - Portail", layout="wide", page_icon="💊")

if "theme" not in st.session_state:
    st.session_state.theme = "Clair"

# Définition des styles selon le thème
if st.session_state.theme == "Sombre":
    bg_style = "linear-gradient(135deg, #0e1117 0%, #161b22 100%)"
    text_color = "#e0e6ed"
    card_bg = "rgba(255, 255, 255, 0.05)"
    sidebar_bg = "#0e1117"
else:
    bg_style = "linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)"
    text_color = "#1a1c21"
    card_bg = "rgba(0, 0, 0, 0.02)"
    sidebar_bg = "#f0f2f5"

# Injection CSS
st.markdown(f"""
    <style>
        .stApp {{
            background: {bg_style};
        }}
        [data-testid="stSidebar"] {{
            background-color: {sidebar_bg} !important;
        }}
        [data-testid="stHeader"] {{
            background: rgba(0,0,0,0);
        }}
        
        /* Optimisations mobiles globales */
        @media (max-width: 768px) {{
            .stButton button {{
                width: 100% !important;
                height: 50px !important;
                margin-bottom: 10px;
            }}
            [data-testid="stMetricValue"] {{
                font-size: 1.8rem !important;
            }}
        }}

        /* Fix visibility for metrics and text */
        [data-testid="stMetricLabel"] {{
            color: {text_color} !important;
            opacity: 0.9;
            font-weight: 600 !important;
        }}
        [data-testid="stMetricValue"] {{
            color: {text_color} !important;
            font-weight: 800 !important;
        }}
        h1, h2, h3, h4, h5, h6, p, span {{
            color: {text_color};
        }}

        /* BOUTON ACTUALISER (Bleu clair -> Gris) */
        div[data-testid="stBaseButton-btn_refresh"] button {{
            background-color: #e0f2fe !important;
            color: #0369a1 !important;
            border: 1px solid #bae6fd !important;
            transition: all 0.3s ease !important;
        }}
        div[data-testid="stBaseButton-btn_refresh"] button:hover {{
            background-color: #f3f4f6 !important;
            color: #374151 !important;
            border-color: #d1d5db !important;
            transform: scale(1.02);
        }}

        /* BOUTON MOBILE (Clair -> Foncé) */
        div[data-testid="stBaseButton-btn_mobile"] button {{
            background-color: #f9fafb !important;
            color: #374151 !important;
            border: 1px solid #e5e7eb !important;
            transition: all 0.3s ease !important;
        }}
        div[data-testid="stBaseButton-btn_mobile"] button:hover {{
            background-color: #1f2937 !important;
            color: #ffffff !important;
            transform: translateY(-2px);
        }}

        /* BOUTON DÉCONNEXION (Rouge -> Bye Bye) */
        div[data-testid="stBaseButton-btn_logout"] button {{
            background-color: #fee2e2 !important;
            color: #dc2626 !important;
            border: 1px solid #fecaca !important;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
        }}
        div[data-testid="stBaseButton-btn_logout"] button:hover {{
            background-color: #ef4444 !important;
            color: #ffffff !important;
            border-color: #ef4444 !important;
        }}
        div[data-testid="stBaseButton-btn_logout"] button:hover div::after {{
            content: " 👋";
        }}
    </style>
""", unsafe_allow_html=True)

# --- 2. INITIALISATION DE LA BASE UTILISATEURS ---
os.makedirs("data", exist_ok=True)
db_users = TinyDB('data/db_users.json')
User = Query()

# Toujours s'assurer que l'admin principal existe
if not db_users.search(User.username == 'admin_imad'):
    db_users.insert({
        'username': 'admin_imad',
        'password': 'admin_imad_pwd',
        'role': 'Admin',
        'pages': ['Admin Centrale', 'Dashboard', 'Logistique', 'Inventaire', 'Inventaire Détail', 'Inventaire Triple', 'Suivi', 'Recouvrement', 'Pointage', 'Pointage Expéditeur', 'Péremptions', 'Scanneur QR', 'Automatisation', 'Litiges Fournisseurs', 'Analyse Rotation', 'Scan Mobile', 'RH']
    })

# Liste des utilisateurs essentiels à maintenir
essentials = [
    {'username': 'Ayoub', 'password': 'ayoub2026', 'role': 'Saisie', 'pages': ['Logistique', 'Suivi', 'Inventaire Détail']},
    {'username': 'Islem', 'password': 'islem2026', 'role': 'Saisie', 'pages': ['Logistique', 'Suivi', 'Inventaire Détail']},
    {'username': 'Seif', 'password': 'seif2026', 'role': 'Saisie', 'pages': ['Inventaire', 'Inventaire Détail']}
]

for ess in essentials:
    if not db_users.search(User.username == ess['username']):
        db_users.insert(ess)

# --- 3. GESTION DE SESSION ET COOKIES ---
if "current_user" not in st.session_state:
    st.session_state.current_user = None

# Initialiser le contrôleur de cookies
controller = CookieController()

# On tente de récupérer le token depuis les cookies de façon transparente
token_user = controller.get("user_token")

# --- Auto-Login via Cookie ---
if st.session_state.current_user is None and token_user:
    U = Query()
    res = db_users.search(U.username == token_user)
    if res:
        st.session_state.current_user = res[0]
        st.session_state.remember_me = True # On maintient l'état

# Rafraîchir les données de l'utilisateur depuis la DB à chaque chargement pour éviter les désync
if st.session_state.current_user:
    U = Query()
    updated_user = db_users.get(U.username == st.session_state.current_user['username'])
    if updated_user:
        st.session_state.current_user = updated_user

# --- 4. ÉCRAN DE CONNEXION ---
if st.session_state.current_user is None:
    # Injection CSS spécifique pour l'écran de connexion Facebook-style
    st.markdown("""
        <style>
            /* Cacher la barre latérale et le header */
            [data-testid="stSidebar"], [data-testid="stSidebarNav"] {display: none;}
            section[data-testid="stSidebar"] {width: 0px;}
            [data-testid="stHeader"] {display: none;}
            
            .stApp {
                background-color: #f0f2f5 !important;
            }
            
            .main .block-container {
                max-width: 1000px;
                padding-top: 100px;
                margin: auto;
            }
            
            /* Styles du contenu gauche */
            .fb-left-container {
                padding-top: 40px;
            }
            .fb-logo-text {
                color: #1877f2;
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                font-size: 55px;
                font-weight: bold;
                letter-spacing: -1.5px;
                margin-bottom: 0px;
                line-height: 1;
            }
            .fb-slogan {
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                font-size: 24px;
                line-height: 28px;
                font-weight: normal;
                color: #4b4f56 !important;
                margin-top: 15px;
                max-width: 500px;
            }
            
            /* Styles de la carte de connexion */
            .login-card {
                background-color: white;
                padding: 20px 20px 25px 20px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0, 0, 0, .1), 0 8px 16px rgba(0, 0, 0, .1);
            }
            
            /* Style des inputs Streamlit */
            .stTextInput input {
                height: 52px !important;
                font-size: 17px !important;
                padding: 14px 16px !important;
                border: 1px solid #dddfe2 !important;
                border-radius: 6px !important;
                color: #1c1e21 !important;
                background-color: white !important;
                margin-bottom: 10px !important;
            }
            .stTextInput input:focus {
                border-color: #1877f2 !important;
                box-shadow: 0 0 0 2px #e7f3ff !important;
            }
            
            /* Visibilité des placeholders */
            ::placeholder {
                color: #8d949e !important;
                opacity: 1 !important;
            }
            
            /* Style du bouton de connexion (Submit Button) */
            div[data-testid="stFormSubmitButton"] button {
                background-color: #1877f2 !important;
                color: white !important;
                font-size: 20px !important;
                font-weight: bold !important;
                height: 48px !important;
                border-radius: 6px !important;
                border: none !important;
                width: 100% !important;
                margin-top: 5px !important;
                transition: background-color 0.2s;
            }
            div[data-testid="stFormSubmitButton"] button:hover {
                background-color: #166fe5 !important;
                color: white !important;
            }

            [data-testid="stForm"] {
                border: none !important;
                padding: 0 !important;
            }

            /* Cacher d'éventuels éléments indésirables */
            [data-testid="stForm"] hr, [data-testid="stForm"] .forgot-link {
                display: none !important;
            }
        </style>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1.3, 1], gap="large")

    with col1:
        st.markdown('<div class="fb-left-container">', unsafe_allow_html=True)
        if os.path.exists("logo.png"):
            st.image("logo.png", width=220)
        st.markdown('<h1 class="fb-logo-text">DarPharm®Solutions</h1>', unsafe_allow_html=True)
        st.markdown('<p class="fb-slogan">DarPharm®Solutions vous aide à gérer vos stocks, vos expéditions et votre logistique en toute simplicité.</p>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        with st.form("login_form"):
            u = st.text_input("Username", placeholder="Nom d'utilisateur", label_visibility="collapsed")
            p = st.text_input("Password", type="password", placeholder="Mot de passe", label_visibility="collapsed")
            rester_connecte = st.checkbox("Rester connecté")
            submit = st.form_submit_button("Se connecter")
            
            if submit:
                User = Query()
                result = db_users.search((User.username == u) & (User.password == p))
                if result:
                    st.session_state.current_user = result[0]
                    if rester_connecte:
                        st.session_state.remember_me = True
                        controller.set("user_token", result[0]['username'], max_age=86400 * 30) # Valide 30 jours
                    else:
                        st.session_state.remember_me = False
                        controller.remove("user_token")
                    st.rerun()
                else:
                    st.error("Identifiants incorrects.")
        st.markdown('</div>', unsafe_allow_html=True)

    st.stop()

# --- 5. DÉFINITION DES PAGES DISPONIBLES ---
user = st.session_state.current_user
user_pages = user.get('pages', [])
is_admin = user.get('role') == 'Admin'

if is_admin:
    if "Automatisation" not in user_pages:
        user_pages.append("Automatisation")
    if "Liste des Lots" not in user_pages:
        user_pages.append("Liste des Lots")
    if "Pointage Expéditeur" not in user_pages:
        user_pages.append("Pointage Expéditeur")
    if "Inventaire Triple" not in user_pages:
        user_pages.append("Inventaire Triple")

# Dictionnaire de toutes les pages possibles (Key: Nom, Value: Path)
ALL_PAGES = {
    "Dashboard": st.Page("pages/0_tableau_de_bord.py", title="Tableau de Bord", icon="📊"),
    "Logistique": st.Page("pages/1_expedition.py", title="Logistique", icon="🚛"),
    "Inventaire": st.Page("pages/2_inventaire.py", title="Inventaire", icon="📦"),
    "Inventaire Détail": st.Page("pages/8_inventaire_detail.py", title="Inventaire Détail", icon="🔍"),
    "Inventaire Triple": st.Page("pages/16_inventaire_triple.py", title="Inventaire Triple", icon="📋"),
    "Suivi": st.Page("pages/3_suivi.py", title="Suivi Frigo", icon="❄️"),
    "Recouvrement": st.Page("pages/4_recouvrement.py", title="Recouvrement", icon="💰"),
    "Pointage": st.Page("pages/5_pointage.py", title="Pointage Factures", icon="📝"),
    "Pointage Expéditeur": st.Page("pages/15_pointage_expediteur.py", title="Pointage Expéditeur", icon="📦"),
    "Péremptions": st.Page("pages/6_peremptions.py", title="Gestion des Péremptions", icon="⏳"),
    "Scanneur QR": st.Page("pages/7_scanneur_qr.py", title="Scanneur QR", icon="📸"),
    "Litiges Fournisseurs": st.Page("pages/10_reclamations_fournisseurs.py", title="Litiges Fournisseurs", icon="🏢"),
    "Analyse Rotation": st.Page("pages/11_analyse_rotation.py", title="Analyse Rotation", icon="📈"),
    "Scan Mobile": st.Page("pages/12_mobile_scan.py", title="Scan Mobile", icon="📱"),
    "RH": st.Page("pages/13_rh.py", title="RH & Performance", icon="👥"),
    "Liste des Lots": st.Page("pages/14_liste_des_lots.py", title="Liste des Lots", icon="📑")
}

if is_ia_enabled():
    ALL_PAGES["Automatisation"] = st.Page("pages/9_automatisation.py", title="Automatisation & IA", icon="🤖")

# Filtrer selon les privilèges
pages_to_show = {}
nav_list = []

# On s'assure que Dashboard est en premier si l'utilisateur y a accès
ordered_user_pages = user_pages.copy()
if "Dashboard" in ordered_user_pages:
    ordered_user_pages.remove("Dashboard")
    ordered_user_pages.insert(0, "Dashboard")

for p_name in ordered_user_pages:
    if p_name in ALL_PAGES:
        nav_list.append(ALL_PAGES[p_name])

if nav_list:
    pages_to_show["Mes Modules"] = nav_list

if is_admin:
    # Page cachée ou dédiée à l'administration
    pages_to_show["Administration Centrale"] = [
        st.Page("pages/0_admin_centrale.py", title="Admin Centrale (Data)", icon="🏛️"),
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
    
    st.divider()
    # Sélecteur de thème
    new_theme = st.selectbox("🎨 Thème d'affichage", ["Clair", "Sombre"], 
                              index=0 if st.session_state.theme == "Clair" else 1)
    if new_theme != st.session_state.theme:
        st.session_state.theme = new_theme
        st.rerun()
    st.divider()

    if st.button("📱 Mode Mobile", use_container_width=True, key="btn_mobile"):
        st.switch_page("pages/12_mobile_scan.py")
        
    if st.button("🚪 Déconnexion", use_container_width=True, key="btn_logout"):
        st.session_state.current_user = None
        controller.remove("user_token")
        st.rerun()

pg.run()
