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
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&family=Outfit:wght@300;500;700&display=swap');

        :root {{
            --primary: #1877f2;
            --secondary: #00d2ff;
            --accent: #ff007a;
            --glass-bg: rgba(255, 255, 255, 0.7);
            --glass-border: rgba(255, 255, 255, 0.2);
            --shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
        }}

        .stApp {{
            background: {bg_style};
            font-family: 'Inter', sans-serif;
        }}

        /* Entrance Animations */
        @keyframes fadeInUp {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        @keyframes slideInRight {{
            from {{ opacity: 0; transform: translateX(50px); }}
            to {{ opacity: 1; transform: translateX(0); }}
        }}

        @keyframes pulseGlow {{
            0% {{ box-shadow: 0 0 5px rgba(24, 119, 242, 0.2); }}
            50% {{ box-shadow: 0 0 20px rgba(24, 119, 242, 0.6); }}
            100% {{ box-shadow: 0 0 5px rgba(24, 119, 242, 0.2); }}
        }}

        .main .block-container {{
            animation: fadeInUp 0.8s cubic-bezier(0.2, 0.8, 0.2, 1);
        }}

        /* 3D and Interactive Elements */
        .stButton button {{
            border-radius: 12px !important;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
            border: 1px solid var(--glass-border) !important;
            box-shadow: 0 4px 15px rgba(0,0,0,0.05) !important;
        }}

        .stButton button:hover {{
            transform: translateY(-5px) scale(1.02) perspective(1000px) rotateX(5deg) !important;
            box-shadow: 0 12px 25px rgba(24, 119, 242, 0.25) !important;
            background: var(--primary) !important;
            color: white !important;
        }}

        /* Premium Titles */
        h1 {{
            font-family: 'Outfit', sans-serif !important;
            font-weight: 800 !important;
            background: linear-gradient(90deg, #1877f2, #00d2ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            letter-spacing: -1.5px;
        }}

        /* Metric Cards (Glassmorphism) */
        [data-testid="stMetric"] {{
            background: {card_bg};
            padding: 20px !important;
            border-radius: 20px !important;
            border: 1px solid var(--glass-border) !important;
            backdrop-filter: blur(10px);
            transition: all 0.3s ease;
        }}
        [data-testid="stMetric"]:hover {{
            transform: translateY(-5px);
            box-shadow: var(--shadow);
        }}

        /* ==========================================
           RESPONSIVE & MOBILE OPTIMIZATIONS
           ========================================== */
        @media (max-width: 768px) {{
            .main .block-container {{
                padding: 1rem 0.75rem 5rem 0.75rem !important;
            }}
            .stButton button {{
                width: 100% !important;
                min-height: 52px !important;
                font-size: 16px !important;
                border-radius: 12px !important;
            }}
            [data-testid="stMetricValue"] {{ font-size: 1.8rem !important; }}
            [data-testid="column"] {{ width: 100% !important; flex: none !important; }}
            
            /* Sidebar Panel */
            [data-testid="stSidebar"] {{
                width: 85vw !important;
                max-width: 320px !important;
            }}
        }}

        /* Scrollbar styling */
        ::-webkit-scrollbar {{ width: 6px; height: 6px; }}
        ::-webkit-scrollbar-thumb {{ background: rgba(24, 119, 242, 0.3); border-radius: 10px; }}

        /* Prevent auto-zoom on iOS */
        * {{ touch-action: manipulation; }}

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
USER_COLUMNS = ["username", "password", "role", "pages", "nom", "prenom", "zone", "depot"]
df_users = load_gs_data(DB_USERS_WORKSHEET, DB_USERS_FALLBACK, USER_COLUMNS)

# Synchronisation des essentiels (Uniquement une fois par session pour la rapidité)
if "setup_done" not in st.session_state:
    changes_made = False
    
    # Toujours s'assurer que l'admin principal existe
    if 'admin_imad' not in df_users['username'].values:
        admin_data = {
            'username': 'admin_imad',
            'password': 'admin_imad_pwd',
            'role': 'Admin',
            'nom': 'Administrateur',
            'prenom': 'Imad',
            'pages': str(['Profil', 'Admin Centrale', 'Dashboard', 'Logistique', 'Inventaire', 'Inventaire Détail', 'Inventaire Triple', 'Suivi', 'Recouvrement', 'Pointage', 'Pointage Expéditeur', 'Péremptions', 'Scanneur QR', 'Automatisation', 'Litiges Fournisseurs', 'Analyse Rotation', 'Scan Mobile', 'RH']),
            'zone': 'Aucune',
            'depot': 'Administration'
        }
        df_users = pd.concat([df_users, pd.DataFrame([admin_data])], ignore_index=True)
        changes_made = True

    # Liste des utilisateurs essentiels à maintenir
    essentials = [
        {'username': 'Ayoub', 'password': 'ayoub2026', 'role': 'Saisie', 'pages': str(['Logistique', 'Suivi', 'Inventaire Détail']), 'depot': 'Expédition'},
        {'username': 'Islem', 'password': 'islem2026', 'role': 'Saisie', 'pages': str(['Logistique', 'Suivi', 'Inventaire Détail']), 'depot': 'Expédition'},
        {'username': 'Seif', 'password': 'seif2026', 'role': 'Saisie', 'pages': str(['Inventaire', 'Inventaire Détail']), 'depot': 'Préparation'}
    ]

    for ess in essentials:
        if df_users.empty or ess['username'] not in df_users['username'].values:
            df_users = pd.concat([df_users, pd.DataFrame([ess])], ignore_index=True)
            changes_made = True

    if changes_made:
        save_gs_data(df_users, DB_USERS_WORKSHEET, DB_USERS_FALLBACK)
    
    st.session_state.setup_done = True

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
    "Catalogue Produits": st.Page("modules/17_catalogue_produits.py", title="Catalogue Produits", icon="📚"),
    "Profil": st.Page("modules/17_profil.py", title="Mon Profil", icon="👤")
}

if is_ia_enabled():
    ALL_PAGES["Automatisation"] = st.Page("modules/9_automatisation.py", title="Automatisation & IA", icon="🤖")

# Filtrer selon les privilèges
pages_to_show = {}
nav_list = []

# On s'assure que Dashboard est en premier et Profil est présent
ordered_user_pages = user_pages.copy()
if "Profil" not in ordered_user_pages:
    ordered_user_pages.insert(0, "Profil")
    
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
    # Sélecteur de Mode de Stockage
    if "storage_mode" not in st.session_state:
        st.session_state.storage_mode = "Cloud"
    
    st.session_state.storage_mode = st.radio(
        "📂 Mode de Stockage", 
        ["Cloud", "Local"], 
        index=0 if st.session_state.storage_mode == "Cloud" else 1,
        help="Cloud: Synchronisation directe. Local: Travail sur PC avec synchro manuelle."
    )
    
    if st.session_state.storage_mode == "Local":
        st.warning("⚡ Mode Local : N'oubliez pas d'exporter vos données vers le Cloud.")
    
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
