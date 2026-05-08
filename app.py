import streamlit as st
import pandas as pd
import json
import os
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

        /* BOUTON ACTUALISER */
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

        /* BOUTON MOBILE */
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

        /* BOUTON DÉCONNEXION */
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

        /* ==========================================
           MOBILE-FIRST RESPONSIVE DESIGN
           ========================================== */

        /* Tablettes (768px et moins) */
        @media (max-width: 768px) {{

            /* Padding réduit pour maximiser l'espace */
            .main .block-container {{
                padding: 1rem 0.75rem 5rem 0.75rem !important;
                max-width: 100% !important;
            }}

            /* Boutons pleine largeur et plus grands (touch-friendly) */
            .stButton button {{
                width: 100% !important;
                min-height: 52px !important;
                font-size: 16px !important;
                margin-bottom: 8px !important;
                border-radius: 12px !important;
                touch-action: manipulation;
            }}

            /* Métriques plus lisibles */
            [data-testid="stMetricValue"] {{
                font-size: 2rem !important;
            }}
            [data-testid="stMetricLabel"] {{
                font-size: 0.85rem !important;
            }}

            /* Colonnes empilées sur mobile */
            [data-testid="column"] {{
                width: 100% !important;
                flex: none !important;
            }}

            /* Tableaux scrollables horizontalement */
            [data-testid="stDataFrame"], .stDataFrame {{
                overflow-x: auto !important;
                -webkit-overflow-scrolling: touch;
            }}

            /* Inputs plus grands pour les doigts */
            .stTextInput input,
            .stSelectbox select,
            .stNumberInput input {{
                min-height: 48px !important;
                font-size: 16px !important; /* Évite le zoom auto sur iOS */
                border-radius: 10px !important;
            }}

            /* Titre de la page */
            h1 {{
                font-size: 1.5rem !important;
                margin-bottom: 0.5rem !important;
            }}
            h2 {{
                font-size: 1.25rem !important;
            }}
            h3 {{
                font-size: 1.1rem !important;
            }}

            /* Sidebar se comporte comme un panneau glissant */
            [data-testid="stSidebar"] {{
                width: 85vw !important;
                max-width: 320px !important;
            }}

            /* Header plus compact */
            [data-testid="stHeader"] {{
                height: 3rem !important;
            }}

            /* Expanders plus faciles à tapper */
            [data-testid="stExpander"] summary {{
                min-height: 48px !important;
                font-size: 15px !important;
                align-items: center !important;
            }}

            /* Tabs touch-friendly */
            [data-testid="stTabs"] [role="tab"] {{
                min-height: 44px !important;
                font-size: 14px !important;
                padding: 0 12px !important;
            }}

            /* Upload zone simplifiée */
            [data-testid="stFileUploader"] {{
                border-radius: 12px !important;
                padding: 1rem !important;
            }}

            /* Checkbox et radio plus grands */
            [data-testid="stCheckbox"] label,
            [data-testid="stRadio"] label {{
                min-height: 44px !important;
                font-size: 16px !important;
                display: flex !important;
                align-items: center !important;
            }}

            /* Form submit pleine largeur */
            div[data-testid="stFormSubmitButton"] button {{
                width: 100% !important;
                min-height: 52px !important;
                font-size: 18px !important;
                border-radius: 12px !important;
            }}

            /* Sliders plus larges */
            [data-testid="stSlider"] {{
                padding: 1rem 0 !important;
            }}

            /* Ajouter de l'espace en bas pour la zone safe area (iOS) */
            .main {{
                padding-bottom: env(safe-area-inset-bottom, 20px) !important;
            }}
        }}

        /* Très petits écrans (moins de 400px) */
        @media (max-width: 400px) {{
            .main .block-container {{
                padding: 0.75rem 0.5rem 5rem 0.5rem !important;
            }}
            [data-testid="stMetricValue"] {{
                font-size: 1.6rem !important;
            }}
            h1 {{ font-size: 1.3rem !important; }}
        }}

        /* Empêcher le zoom iOS sur double-tap */
        * {{
            touch-action: manipulation;
        }}

        /* Scrollbar invisible sur mobile mais fonctionnelle */
        @media (max-width: 768px) {{
            ::-webkit-scrollbar {{
                width: 0px;
                background: transparent;
            }}
        }}

    </style>
""", unsafe_allow_html=True)

# Meta tags PWA pour l'installation sur l'écran d'accueil
st.markdown("""
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <meta name="mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="default">
    <meta name="apple-mobile-web-app-title" content="DarPharm">
    <meta name="theme-color" content="#1877f2">
""", unsafe_allow_html=True)

# --- 2. CONFIGURATION BASE DE DONNÉES ---
from utils_gsheets import load_gs_data, save_gs_data, DB_USERS_WORKSHEET, DB_USERS_FALLBACK

# Chargement initial des utilisateurs
df_users = load_gs_data(DB_USERS_WORKSHEET, DB_USERS_FALLBACK, ["username", "password", "role", "pages", "nom", "prenom", "zone"])

# Toujours s'assurer que l'admin principal existe
if 'admin_imad' not in df_users['username'].values:
    admin_data = {
        'username': 'admin_imad',
        'password': 'admin_imad_pwd',
        'role': 'Admin',
        'nom': 'Administrateur',
        'prenom': 'Imad',
        'pages': ['Profil', 'Admin Centrale', 'Dashboard', 'Logistique', 'Inventaire', 'Inventaire Détail', 'Inventaire Triple', 'Suivi', 'Recouvrement', 'Pointage', 'Pointage Expéditeur', 'Péremptions', 'Scanneur QR', 'Automatisation', 'Litiges Fournisseurs', 'Analyse Rotation', 'Scan Mobile', 'RH'],
        'zone': 'Aucune'
    }
    df_users = pd.concat([df_users, pd.DataFrame([admin_data])], ignore_index=True)
    save_gs_data(df_users, DB_USERS_WORKSHEET, DB_USERS_FALLBACK)

# Liste des utilisateurs essentiels à maintenir
essentials = [
    {'username': 'Ayoub', 'password': 'ayoub2026', 'role': 'Saisie', 'pages': ['Logistique', 'Suivi', 'Inventaire Détail']},
    {'username': 'Islem', 'password': 'islem2026', 'role': 'Saisie', 'pages': ['Logistique', 'Suivi', 'Inventaire Détail']},
    {'username': 'Seif', 'password': 'seif2026', 'role': 'Saisie', 'pages': ['Inventaire', 'Inventaire Détail']}
]

# Synchronisation des essentiels
changes_made = False
for ess in essentials:
    if df_users.empty or ess['username'] not in df_users['username'].values:
        df_users = pd.concat([df_users, pd.DataFrame([ess])], ignore_index=True)
        changes_made = True

if changes_made:
    save_gs_data(df_users, DB_USERS_WORKSHEET, DB_USERS_FALLBACK)

# --- 3. GESTION DE SESSION ET COOKIES ---
if "current_user" not in st.session_state:
    st.session_state.current_user = None

# Initialiser le contrôleur de cookies
controller = CookieController(key="main_cookie_controller")

# On tente de récupérer le token depuis les cookies de façon transparente
try:
    token_user = controller.get("user_token")
except Exception:
    token_user = None

# --- Auto-Login via Cookie ---
# Si on a un cookie mais pas encore de session, on tente la reconnexion automatique
if st.session_state.current_user is None and token_user:
    res = df_users[df_users['username'] == token_user]
    if not res.empty:
        st.session_state.current_user = res.iloc[0].to_dict()
        st.session_state.remember_me = True
        st.rerun() # On force un rafraîchissement pour charger les modules

# Rafraîchir les données de l'utilisateur depuis la DB à chaque chargement pour éviter les désync
if st.session_state.current_user:
    res = df_users[df_users['username'] == st.session_state.current_user['username']]
    if not res.empty:
        st.session_state.current_user = res.iloc[0].to_dict()

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
            rester_connecte = st.checkbox("Rester connecté", value=True)
            submit = st.form_submit_button("Se connecter")
            
            if submit:
                res = df_users[(df_users['username'] == u) & (df_users['password'] == p)]
                if not res.empty:
                    user_data = res.iloc[0].to_dict()
                    st.session_state.current_user = user_data
                    if rester_connecte:
                        st.session_state.remember_me = True
                        controller.set("user_token", user_data['username'], max_age=86400 * 30) # Valide 30 jours
                    else:
                        st.session_state.remember_me = False
                        try:
                            if controller.get("user_token"):
                                controller.remove("user_token")
                        except Exception:
                            pass
                    st.rerun()
                else:
                    st.error("Identifiants incorrects.")
        st.markdown('</div>', unsafe_allow_html=True)

    st.stop()

# --- 5. DÉFINITION DES PAGES DISPONIBLES ---
user = st.session_state.current_user
user_pages = user.get('pages', [])

# Conversion sécurisée si pages est stocké sous forme de chaîne (GSheets)
if isinstance(user_pages, str):
    import ast
    try:
        # Tente de parser "['p1', 'p2']"
        user_pages = ast.literal_eval(user_pages)
    except:
        # Fallback : split par virgule si format simple "p1, p2"
        user_pages = [p.strip() for p in user_pages.replace('[','').replace(']','').replace("'","").split(',') if p.strip()]

if not isinstance(user_pages, list):
    user_pages = []

is_admin = user.get('role') == 'Admin'

if is_admin:
    for extra_page in ["Automatisation", "Liste des Lots", "Pointage Expéditeur", "Inventaire Triple"]:
        if extra_page not in user_pages:
            user_pages.append(extra_page)

# Dictionnaire de toutes les pages possibles (Key: Nom, Value: Path)
ALL_PAGES = {
    "Dashboard": st.Page("modules/0_tableau_de_bord.py", title="Tableau de Bord", icon="📊"),
    "Logistique": st.Page("modules/1_expedition.py", title="Logistique", icon="🚛"),
    "Inventaire": st.Page("modules/2_inventaire.py", title="Inventaire", icon="📦"),
    "Inventaire Détail": st.Page("modules/8_inventaire_detail.py", title="Inventaire Détail", icon="🔍"),
    "Inventaire Triple": st.Page("modules/16_inventaire_triple.py", title="Inventaire Triple", icon="📋"),
    "Suivi": st.Page("modules/3_suivi.py", title="Suivi Frigo", icon="❄️"),
    "Recouvrement": st.Page("modules/4_recouvrement.py", title="Recouvrement", icon="💰"),
    "Pointage": st.Page("modules/5_pointage.py", title="Pointage Factures", icon="📝"),
    "Pointage Expéditeur": st.Page("modules/15_pointage_expediteur.py", title="Pointage Expéditeur", icon="📦"),
    "Péremptions": st.Page("modules/6_peremptions.py", title="Gestion des Péremptions", icon="⏳"),
    "Scanneur QR": st.Page("modules/7_scanneur_qr.py", title="Scanneur QR", icon="📸"),
    "Litiges Fournisseurs": st.Page("modules/10_reclamations_fournisseurs.py", title="Litiges Fournisseurs", icon="🏢"),
    "Analyse Rotation": st.Page("modules/11_analyse_rotation.py", title="Analyse Rotation", icon="📈"),
    "Scan Mobile": st.Page("modules/12_mobile_scan.py", title="Scan Mobile", icon="📱"),
    "RH": st.Page("modules/13_rh.py", title="RH & Performance", icon="👥"),
    "Liste des Lots": st.Page("modules/14_liste_des_lots.py", title="Liste des Lots", icon="📑"),
    "Profil": st.Page("modules/17_profil.py", title="Mon Profil", icon="👤")
}

if is_ia_enabled():
    ALL_PAGES["Automatisation"] = st.Page("modules/9_automatisation.py", title="Automatisation & IA", icon="🤖")

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
        st.Page("modules/0_admin_centrale.py", title="Admin Centrale (Data)", icon="🏛️"),
        st.Page("modules/5_admin.py", title="Gestion des Accès", icon="⚙️")
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


    st.divider()
    if st.button("📱 Mode Mobile", use_container_width=True, key="btn_mobile"):
        st.switch_page("modules/12_mobile_scan.py")
        
    if st.button("🚪 Déconnexion", use_container_width=True, key="btn_logout"):
        st.session_state.current_user = None
        try:
            if controller.get("user_token"):
                controller.remove("user_token")
        except Exception:
            pass
        st.rerun()

pg.run()
