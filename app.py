import streamlit as st
import pandas as pd
import json
import os
from utils_ia import is_ia_enabled
from streamlit_cookies_controller import CookieController
from utils_themes import apply_user_theme, load_themes_db, get_active_themes

# --- 1. CONFIGURATION & THÈME ---
st.set_page_config(page_title="Darpharm Solution - Portail", layout="wide", page_icon="💊")

if "theme" not in st.session_state:
    st.session_state.theme = "Clair"

# --- 1.1 INJECTION PWA & CONNECTIVITÉ ---
st.markdown(
    """
    <link rel="manifest" href="/manifest.json">
    <script>
        if ('serviceWorker' in navigator) {
            window.addEventListener('load', function() {
                navigator.serviceWorker.register('/service-worker.js').then(function(registration) {
                    console.log('ServiceWorker registration successful with scope: ', registration.scope);
                }, function(err) {
                    console.log('ServiceWorker registration failed: ', err);
                });
            });
        }
    </script>
    """,
    unsafe_allow_html=True
)

# Petit indicateur de connexion (JS simple)
st.markdown(
    """
    <script>
        const updateOnlineStatus = () => {
            const status = navigator.onLine ? 'online' : 'offline';
            document.body.setAttribute('data-connection', status);
            // On pourrait envoyer l'info à Streamlit via un query param ou autre si besoin
        };
        window.addEventListener('online', updateOnlineStatus);
        window.addEventListener('offline', updateOnlineStatus);
        updateOnlineStatus();
    </script>
    <style>
        body[data-connection='offline']::after {
            content: "⚠️ MODE HORS-LIGNE ACTIVÉ";
            position: fixed;
            top: 0;
            width: 100%;
            background: #ef4444;
            color: white;
            text-align: center;
            font-weight: bold;
            z-index: 9999;
            padding: 5px;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# Définition des styles selon le thème
extra_css = ""
if st.session_state.theme == "Sombre":
    bg_style = "linear-gradient(135deg, #0e1117 0%, #161b22 100%)"
    text_color = "#e0e6ed"
    card_bg = "rgba(255, 255, 255, 0.05)"
    sidebar_bg = "#0e1117"
elif st.session_state.theme == "Chic Animé":
    bg_style = "linear-gradient(-45deg, #1a1a2e, #16213e, #0f3460, #e94560)"
    text_color = "#ffffff"
    card_bg = "rgba(255, 255, 255, 0.1)"
    sidebar_bg = "rgba(26, 26, 46, 0.85)"
    extra_css = """
        /* ANIMATIONS ET DESIGN 3D CHIC */
        @keyframes gradientShift {
            0% { background-position: 0% 50%; }
            50% { background-position: 100% 50%; }
            100% { background-position: 0% 50%; }
        }
        @keyframes float3D {
            0% { transform: translateY(0px) rotateX(0deg); }
            50% { transform: translateY(-8px) rotateX(4deg); box-shadow: 0 15px 35px rgba(0,0,0,0.4); }
            100% { transform: translateY(0px) rotateX(0deg); }
        }
        @keyframes slideUpFade {
            from { opacity: 0; transform: translateY(40px); }
            to { opacity: 1; transform: translateY(0); }
        }
        @keyframes pulseGlow {
            0% { box-shadow: 0 0 10px rgba(233, 69, 96, 0.4); }
            50% { box-shadow: 0 0 25px rgba(233, 69, 96, 0.8); }
            100% { box-shadow: 0 0 10px rgba(233, 69, 96, 0.4); }
        }

        .stApp {
            background-size: 300% 300% !important;
            animation: gradientShift 15s ease infinite !important;
        }

        /* CHARGEMENT PREMIUM CUSTOM */
        #darpharm-loader {
            position: fixed;
            top: 0; left: 0;
            width: 100vw; height: 100vh;
            background: #f0f2f5;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            z-index: 99999;
            transition: opacity 0.5s ease-out;
        }
        .loader-logo {
            font-size: 80px;
            animation: pulse-logo 2s infinite ease-in-out;
            display: block;
        }
        .loader-bar {
            width: 200px;
            height: 4px;
            background: #e2e8f0;
            border-radius: 10px;
            margin-top: 20px;
            overflow: hidden;
            position: relative;
        }
        .loader-progress {
            width: 0%;
            height: 100%;
            background: #1877f2;
            animation: load-progress 2.5s forwards cubic-bezier(0, 0.43, 1, 0.21);
        }
        @keyframes pulse-logo {
            0%, 100% { transform: scale(1); opacity: 0.8; }
            50% { transform: scale(1.1); opacity: 1; }
        }
        @keyframes load-progress {
            0% { width: 0%; }
            50% { width: 70%; }
            100% { width: 100%; }
        }

        .block-container > div {
            animation: slideUpFade 0.7s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
        }

        [data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(15px);
            -webkit-backdrop-filter: blur(15px);
            border-radius: 20px;
            padding: 20px;
            border: 1px solid rgba(255, 255, 255, 0.15);
            box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.3);
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
            animation: float3D 6s ease-in-out infinite;
        }
        [data-testid="stMetric"]:hover {
            transform: translateY(-15px) scale(1.05) perspective(800px) rotateX(10deg) rotateY(-5deg) !important;
            background: rgba(255, 255, 255, 0.1);
            box-shadow: -10px 20px 40px rgba(0,0,0,0.5);
            border-color: #e94560;
        }

        [data-testid="stSidebar"] {
            background: rgba(26, 26, 46, 0.6) !important;
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border-right: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: 5px 0 25px rgba(0,0,0,0.3);
        }

        .stButton button {
            border-radius: 25px !important;
            background: linear-gradient(135deg, #e94560 0%, #0f3460 100%) !important;
            color: white !important;
            border: none !important;
            box-shadow: 0 5px 15px rgba(233, 69, 96, 0.4), inset 0 -2px 5px rgba(0,0,0,0.2) !important;
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
            text-transform: uppercase;
            font-weight: 700 !important;
            letter-spacing: 1px;
        }
        .stButton button:hover {
            transform: translateY(-5px) scale(1.05) !important;
            box-shadow: 0 10px 25px rgba(233, 69, 96, 0.8), inset 0 -2px 5px rgba(0,0,0,0.2) !important;
            animation: pulseGlow 2s infinite;
        }
        .stButton button:active {
            transform: translateY(2px) scale(0.98) !important;
        }

        .stTextInput input, .stSelectbox select, .stNumberInput input {
            border-radius: 15px !important;
            background: rgba(255, 255, 255, 0.05) !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            color: white !important;
            transition: all 0.4s cubic-bezier(0.68, -0.55, 0.265, 1.55) !important;
            box-shadow: inset 0 2px 5px rgba(0,0,0,0.2);
        }
        .stTextInput input:focus, .stSelectbox select:focus, .stNumberInput input:focus {
            transform: scale(1.02) !important;
            background: rgba(255, 255, 255, 0.1) !important;
            box-shadow: 0 0 20px rgba(233, 69, 96, 0.5), inset 0 2px 5px rgba(0,0,0,0.1) !important;
            border-color: #e94560 !important;
        }

        [data-testid="stDataFrame"] {
            border-radius: 15px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            border: 1px solid rgba(255,255,255,0.1);
        }

        [data-testid="stExpander"] {
            background: rgba(255,255,255,0.03) !important;
            border-radius: 15px !important;
            border: 1px solid rgba(255,255,255,0.1) !important;
            transition: all 0.3s ease !important;
        }
        [data-testid="stExpander"]:hover {
            background: rgba(255,255,255,0.08) !important;
            transform: translateX(8px);
            border-color: rgba(233, 69, 96, 0.6) !important;
            box-shadow: -5px 5px 15px rgba(0,0,0,0.3);
        }
        
        [data-testid="stMetricValue"] {
            text-shadow: 2px 4px 6px rgba(0,0,0,0.4) !important;
            background: -webkit-linear-gradient(45deg, #fff, #e94560);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        /* 3D Icons in sidebar */
        [data-testid="stSidebarNav"] span {
            transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            display: inline-block;
        }
        [data-testid="stSidebarNav"] a:hover span {
            transform: scale(1.4) rotate(-15deg) translateY(-2px);
            filter: drop-shadow(2px 4px 4px rgba(0,0,0,0.5));
        }

        /* En-tête avec glow */
        h1, h2, h3 {
            text-shadow: 0 0 10px rgba(255,255,255,0.2);
        }
    """
elif st.session_state.theme == "USMH":
    bg_img = "file:///C:/Users/DELL/.gemini/antigravity/brain/a5bb6f39-0376-4a2f-9b98-f3ca3de34130/usmh_emblem_1778620364354.png"
    bg_style = f"url({bg_img})"
    text_color = "#ffffff"
    card_bg = "rgba(0, 0, 0, 0.6)"
    sidebar_bg = "rgba(20, 20, 0, 0.95)"
    extra_css = """
        @keyframes yellowGlow { 0% { box-shadow: 0 0 5px #FFD700; } 50% { box-shadow: 0 0 25px #FFD700; } 100% { box-shadow: 0 0 5px #FFD700; } }
        .stApp { background-image: """ + bg_style + """; background-size: cover; background-position: center; background-attachment: fixed; animation: gradientShift 20s infinite alternate; }
        .stApp::before { content: "EL HARRACH - SEMSSEM"; position: fixed; top: 15px; left: 50%; transform: translateX(-50%); font-size: 2rem; font-weight: 900; color: #FFD700; text-shadow: 0 0 20px black, 0 0 10px #FFD700; z-index: 1000; letter-spacing: 5px; pointer-events: none; }
        [data-testid="stMetric"] { background: rgba(0,0,0,0.8) !important; border: 2px solid #FFD700 !important; animation: float3D 5s infinite ease-in-out, yellowGlow 3s infinite; }
        .stButton button { background: linear-gradient(135deg, #FFD700, #000) !important; color: white !important; border: 1px solid #FFD700 !important; transform: skewX(-10deg); }
        .stButton button:hover { transform: skewX(0deg) scale(1.1) !important; box-shadow: 0 0 30px #FFD700 !important; }
    """
elif st.session_state.theme == "CRB":
    bg_img = "file:///C:/Users/DELL/.gemini/antigravity/brain/a5bb6f39-0376-4a2f-9b98-f3ca3de34130/crb_emblem_1778620468103.png"
    bg_style = f"url({bg_img})"
    text_color = "#ffffff"
    card_bg = "rgba(139, 0, 0, 0.4)"
    sidebar_bg = "rgba(255, 255, 255, 0.1)"
    extra_css = """
        @keyframes crbPulse { 0% { transform: scale(1); } 50% { transform: scale(1.02); } 100% { transform: scale(1); } }
        .stApp { background-image: """ + bg_style + """; background-size: cover; background-position: center; background-attachment: fixed; }
        .stApp::before { content: "BELOUIZDAD - LES ROIS"; position: fixed; top: 15px; left: 50%; transform: translateX(-50%); font-size: 2rem; font-weight: 900; color: #ff0000; text-shadow: 0 0 20px white; z-index: 1000; pointer-events: none; }
        [data-testid="stMetric"] { background: rgba(255,255,255,0.1) !important; backdrop-filter: blur(15px); border-radius: 50% 20px 50% 20px !important; border: 1px solid white !important; animation: float3D 6s infinite; }
        .stButton button { background: #ff0000 !important; color: white !important; border-radius: 0px !important; border: 2px solid white !important; transition: 0.5s; }
        .stButton button:hover { background: white !important; color: #ff0000 !important; box-shadow: 0 0 40px red !important; }
    """
elif st.session_state.theme == "USMA":
    bg_img = "file:///C:/Users/DELL/.gemini/antigravity/brain/a5bb6f39-0376-4a2f-9b98-f3ca3de34130/usma_emblem_1778620686784.png"
    bg_style = f"url({bg_img})"
    text_color = "#ffffff"
    card_bg = "rgba(0, 0, 0, 0.8)"
    sidebar_bg = "#000000"
    extra_css = """
        @keyframes usmaFlash { 0%, 100% { opacity: 0.8; } 50% { opacity: 1; filter: brightness(1.5); } }
        .stApp { background-image: """ + bg_style + """; background-size: cover; background-position: center; background-attachment: fixed; }
        .stApp::after { content: ""; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: radial-gradient(circle, transparent 40%, black 100%); pointer-events: none; }
        .stApp::before { content: "SOUSTARA - L'UNION"; position: fixed; top: 15px; left: 50%; transform: translateX(-50%); font-size: 2.2rem; font-weight: 900; color: #ff0000; text-shadow: 3px 3px 0px black; z-index: 1000; animation: usmaFlash 2s infinite; pointer-events: none; }
        [data-testid="stMetric"] { background: rgba(20,20,20,0.9) !important; border-bottom: 4px solid #ff0000 !important; transform: perspective(800px) rotateX(10deg); }
        .stButton button { background: #ff0000 !important; color: black !important; font-weight: bold !important; clip-path: polygon(10% 0, 100% 0, 90% 100%, 0 100%); }
    """
elif st.session_state.theme == "MCA":
    bg_img = "file:///C:/Users/DELL/.gemini/antigravity/brain/a5bb6f39-0376-4a2f-9b98-f3ca3de34130/mca_emblem_1778620924852.png"
    bg_style = f"url({bg_img})"
    text_color = "#ffffff"
    card_bg = "rgba(0, 50, 0, 0.7)"
    sidebar_bg = "rgba(0, 80, 0, 0.9)"
    extra_css = """
        @keyframes mcaSpin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
        .stApp { background-image: """ + bg_style + """; background-size: cover; background-position: center; background-attachment: fixed; }
        .stApp::before { content: "MCA - LE DOYEN"; position: fixed; top: 15px; left: 50%; transform: translateX(-50%); font-size: 2.2rem; font-weight: 900; color: #00ff00; text-shadow: 2px 2px 0px #ff0000; z-index: 1000; pointer-events: none; }
        [data-testid="stMetric"] { background: linear-gradient(135deg, rgba(0,100,0,0.8), rgba(255,0,0,0.2)) !important; border-radius: 50px !important; border: 2px solid #00ff00 !important; }
        .stButton button { background: linear-gradient(90deg, #008000, #ff0000, #008000) !important; background-size: 200% !important; animation: gradientShift 5s linear infinite !important; border-radius: 30px !important; }
    """
else:
    bg_style = "linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)"
    text_color = "#1a1c21"
    card_bg = "rgba(0, 0, 0, 0.02)"
    sidebar_bg = "#f0f2f5"

# --- APPLICATION DU THÈME ---
from utils_themes import get_user_theme, load_themes_db, apply_theme_css

_tdb = load_themes_db()
applied_theme = False

# 1. Priorité au thème choisi manuellement dans le sidebar
if st.session_state.get('theme') and st.session_state.theme != "Clair":
    # Si c'est un thème spécial (Club ou Chic), on injecte son CSS spécifique
    if extra_css:
        st.markdown(f"<style>{extra_css}</style>", unsafe_allow_html=True)
        applied_theme = True
    
    # Si le thème existe aussi dans la DB des thèmes pro, on l'applique
    theme_obj = next((t for t in _tdb["themes"] if t["name"] == st.session_state.theme), None)
    if theme_obj:
        apply_theme_css(theme_obj)
        applied_theme = True

# 2. Si non choisi manuellement, priorité au thème assigné à l'utilisateur
if not applied_theme and st.session_state.get('current_user'):
    u_theme = get_user_theme(st.session_state.current_user.get('username',''), _tdb)
    if u_theme:
        apply_theme_css(u_theme)
        applied_theme = True

# 3. Fallback sur le thème DarPharm Fluffy (Défaut) si rien d'autre n'est appliqué
if not applied_theme:
    fluffy = next((t for t in _tdb["themes"] if t["id"] == "theme_darpharm_fluffy"), None)
    if fluffy:
        apply_theme_css(fluffy)
        
    # Style Responsive et Bouton Déconnexion
    st.markdown("""
    <style>
        /* Modern Sidebar Navigation Styles - BALANCED COMPACT */
        [data-testid="stSidebarNav"] {
            padding-top: 0px !important;
        }
        [data-testid="stSidebarNav"] ul {
            padding-top: 0px !important;
        }
        [data-testid="stSidebarNav"] li {
            padding: 0px 8px !important;
            margin: 2px 0px !important; /* Espace entre les modules */
            height: 38px !important;
        }
        [data-testid="stSidebarNav"] a {
            padding: 0px 12px !important;
            margin: 0px !important;
            height: 34px !important;
            line-height: 34px !important;
            border-radius: 8px !important;
            display: flex !important;
            align-items: center !important;
            background-color: transparent !important;
            transition: all 0.2s ease !important;
        }
        [data-testid="stSidebarNav"] a[aria-current="page"] {
            background-color: rgba(91, 108, 249, 0.12) !important;
            border-left: 4px solid #5b6cf9 !important;
        }
        [data-testid="stSidebarNav"] span {
            font-size: 0.88rem !important;
            font-weight: 600 !important;
            line-height: 1.2 !important;
            color: #4b5563 !important;
        }
        [data-testid="stSidebarNav"] a[aria-current="page"] span {
            color: #5b6cf9 !important;
        }
        
        /* Sidebar Group Headers - BALANCED COMPACT */
        [data-testid="stSidebarNavSeparator"] {
            margin-top: 35px !important; /* Encore plus d'espace avant le groupe suivant */
            margin-bottom: 5px !important;
            border-bottom: 1px solid rgba(0,0,0,0.06) !important;
        }
        [data-testid="stSidebarNav"] div[data-testid="stSidebarNavSeparator"] + div {
            margin-top: 15px !important;
            margin-bottom: 8px !important;
            padding-left: 10px !important;
            font-weight: 800 !important;
            text-transform: uppercase !important;
            font-size: 0.68rem !important;
            letter-spacing: 0.8px !important;
            color: #5b6cf9 !important;
            opacity: 0.9;
            display: block !important;
            clear: both !important;
        }

        div[data-testid="stBaseButton-btn_logout"] button {
            background-color: #fee2e2 !important;
            color: #dc2626 !important;
            border: 1px solid #fecaca !important;
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) !important;
            border-radius: 12px !important;
        }
        div[data-testid="stBaseButton-btn_logout"] button:hover {
            background-color: #ef4444 !important;
            color: #ffffff !important;
            border-color: #ef4444 !important;
            transform: translateY(-2px);
        }

        @media (max-width: 768px) {
            .main .block-container {
                padding: 1rem 0.75rem 5rem 0.75rem !important;
                max-width: 100% !important;
            }
            .stButton button {
                width: 100% !important;
                min-height: 52px !important;
                font-size: 16px !important;
                margin-bottom: 8px !important;
                border-radius: 12px !important;
            }
        }
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
USER_COLUMNS = ["username", "password", "role", "pages", "nom", "prenom", "zone", "depot", "metier", "sous_metier", "tel"]
df_users = load_gs_data(DB_USERS_WORKSHEET, DB_USERS_FALLBACK, USER_COLUMNS)

# ═══════════════════════════════════════════════════════
# CHARTE OFFICIELLE DES RÔLES DARPHARM — GOLDEN BACKUP
# Point de restauration automatique des accès utilisateurs
# ═══════════════════════════════════════════════════════
import json

GOLDEN_BACKUP_PATH = "data/golden_roles_backup.json"

# Définition des pages par métier (synchronisée avec golden_roles_backup.json)
PAGES_BY_METIER = {
    "Admin": str(['Dashboard', 'Profil', 'Admin Centrale', 'Logistique', 'Inventaire', 'Inventaire Détail', 'Inventaire Triple', 'Suivi', 'Recouvrement', 'Pointage', 'Pointage Expéditeur', 'Pointage Marchandise', 'Péremptions', 'Scanneur QR', 'Scan Mobile', 'Litiges Fournisseurs', 'Analyse Rotation', 'RH', 'RH Planning', 'Clients', 'Liste des Lots', 'Catalogue Produits', 'Page de Garde', 'Assistant IA', 'Transferts', 'Coordination', 'Qualité IA', 'Mon Coin', 'Briefing IA', 'Maintenance', 'Académie', 'Prévisions', 'Mode Meeting', 'Répartition Zones', 'Analyse Réclamations', 'Performance Ventes', 'Cortex IA', 'Automatisation']),
    "Agent de Stock": str(['Profil', 'Dashboard', 'Inventaire', 'Inventaire Détail', 'Inventaire Triple', 'Péremptions', 'Liste des Lots', 'Catalogue Produits', 'Répartition Zones', 'Scanneur QR', 'Scan Mobile', 'Transferts']),
    "Chef Livreurs & Parc": str(['Profil', 'Dashboard', 'Logistique', 'Pointage Expéditeur', 'Recouvrement', 'Maintenance', 'Clients', 'Suivi', 'Analyse Rotation', 'Transferts', 'Page de Garde']),
    "Superviseur": str(['Profil', 'Dashboard', 'Analyse Rotation', 'Analyse Réclamations', 'Performance Ventes', 'Prévisions', 'Logistique', 'Inventaire', 'RH', 'Briefing IA', 'Mode Meeting']),
    "Préparateur": str(['Profil', 'Pointage Marchandise', 'Inventaire Détail', 'Scanneur QR', 'Scan Mobile', 'Transferts']),
}

# --- SURCHARGE DYNAMIQUE DES PERMISSIONS ---
DB_ROLES_WORKSHEET = "Roles_Config"
DB_ROLES_FALLBACK = "data/db_roles.csv"
COLS_ROLES = ["role_name", "permissions", "icon", "description"]

try:
    df_roles_dyn = load_gs_data(DB_ROLES_WORKSHEET, DB_ROLES_FALLBACK, COLS_ROLES)
    if not df_roles_dyn.empty:
        for _, row in df_roles_dyn.iterrows():
            r_name = str(row.get('role_name', ''))
            r_perms = str(row.get('permissions', '[]'))
            # L'Admin garde tous les droits fixes pour la sécurité, les autres métiers sont mis à jour dynamiquement
            if r_name and r_name != "Admin":
                PAGES_BY_METIER[r_name] = r_perms
except Exception as e:
    pass # Si erreur, on garde les valeurs par défaut de la Charte


# ─────────────────────────────────────────────────────────────────
# CHARTE OFFICIELLE — Source de vérité absolue pour tous les accès
#   Stock (rez-de-chaussée / rayon) : Ayoub, Islem, Seif
#   Préparation (dépôt principal / 1er étage) : Idris, Aymen, Kheiro,
#                                                Rabeh, Yacine, Aek,
#                                                Aymenk, Mustapha
# ─────────────────────────────────────────────────────────────────
GOLDEN_USERS = [
    # username        password           role      metier                   depot
    ('admin_imad',   'admin_imad_pwd',  'Admin',  'Admin',                 'Administration'),
    ('Ayoub',        'ayoub2026',       'Saisie', 'Agent de Stock',        'Stock'),
    ('Islem',        'islem2026',       'Saisie', 'Agent de Stock',        'Stock'),
    ('Seif',         'seif2026',        'Saisie', 'Agent de Stock',        'Stock'),
    ('Karim',        'karim2026',       'Saisie', 'Chef Livreurs & Parc',  'Expédition'),
    ('Rami',         'rami2026',        'Saisie', 'Superviseur',           'Administration'),
    ('Idris',        'idris2026',       'Saisie', 'Préparateur',           'Préparation'),
    ('Aymen',        'aymen2026',       'Saisie', 'Préparateur',           'Préparation'),
    ('Kheiro',       'kheiro2026',      'Saisie', 'Préparateur',           'Préparation'),
    ('Rabeh',        'rabeh2026',       'Saisie', 'Préparateur',           'Préparation'),
    ('Yacine',       'yacine2026',      'Saisie', 'Préparateur',           'Préparation'),
    ('Aek',          'aek2026',         'Saisie', 'Préparateur',           'Préparation'),
    ('Aymenk',       'aymenk2026',      'Saisie', 'Préparateur',           'Préparation'),
    ('Mustapha',     'mustapha2026',    'Saisie', 'Préparateur',           'Préparation'),
]

def apply_golden_pages(metier, role):
    if role == 'Admin':
        return PAGES_BY_METIER['Admin']
    return PAGES_BY_METIER.get(metier, PAGES_BY_METIER['Préparateur'])

if "setup_done" not in st.session_state:
    changes_made = False

    # --- NETTOYAGE DES DOUBLONS ---
    if not df_users.empty:
        initial_len = len(df_users)
        df_users['uname_lower'] = df_users['username'].astype(str).str.lower().str.strip()
        df_users = df_users.drop_duplicates(subset=['uname_lower'], keep='last').drop(columns=['uname_lower'])
        if len(df_users) < initial_len:
            changes_made = True

    for (uname, pwd, urole, umetier, udepot) in GOLDEN_USERS:
        correct_pages = apply_golden_pages(umetier, urole)

        # Vérification d'existence insensible à la casse
        user_exists = not df_users.empty and uname.lower() in df_users['username'].astype(str).str.lower().str.strip().values
        
        if not user_exists:
            # Utilisateur absent → création complète
            new_row = {
                'username': uname, 'password': pwd, 'role': urole,
                'metier': umetier, 'depot': udepot, 'zone': 'Aucune',
                'nom': uname, 'prenom': '', 'pages': correct_pages
            }
            df_users = pd.concat([df_users, pd.DataFrame([new_row])], ignore_index=True)
            changes_made = True
        else:
            # Utilisateur existant → force-correction du métier et du dépôt
            mask = df_users['username'].astype(str).str.lower().str.strip() == uname.lower()
            current_metier = str(df_users.loc[mask, 'metier'].values[0]) if 'metier' in df_users.columns else ''
            current_pages  = str(df_users.loc[mask, 'pages'].values[0])  if 'pages'  in df_users.columns else ''

            # On corrige si le métier a changé ou si les pages ne correspondent plus à la règle dynamique actuelle
            if current_metier != umetier or current_pages != correct_pages or not current_pages or current_pages in ['nan', '[]', '']:
                df_users.loc[mask, 'metier'] = umetier
                df_users.loc[mask, 'depot']  = udepot
                df_users.loc[mask, 'pages']  = correct_pages
                df_users.loc[mask, 'role']   = urole
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
    # Appliquer le thème personnalisé de l'utilisateur (depuis la base de thèmes)
    apply_user_theme(st.session_state.current_user.get('username', ''))

# --- 4. ÉCRAN DE CONNEXION ---
if st.session_state.current_user is None:
    # Variables dynamiques pour le login selon le thème
    if st.session_state.theme == "Chic Animé":
        login_bg = "transparent"
        logo_color = "#e94560"
        slogan_color = "#ffffff"
        card_bg_color = "rgba(255, 255, 255, 0.1)"
        card_shadow = "0 15px 35px rgba(0, 0, 0, 0.3)"
        card_backdrop = "backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);"
        input_bg = "rgba(255, 255, 255, 0.05)"
        input_border = "rgba(255,255,255,0.2)"
        input_text = "white"
        btn_bg = "linear-gradient(135deg, #e94560 0%, #0f3460 100%)"
        btn_hover = "linear-gradient(135deg, #ff5c77 0%, #1a4b85 100%)"
    else:
        login_bg = "#f0f2f5"
        logo_color = "#1877f2"
        slogan_color = "#4b4f56"
        card_bg_color = "white"
        card_shadow = "0 2px 4px rgba(0, 0, 0, .1), 0 8px 16px rgba(0, 0, 0, .1)"
        card_backdrop = ""
        input_bg = "white"
        input_border = "#dddfe2"
        input_text = "#1c1e21"
        btn_bg = "#1877f2"
        btn_hover = "#166fe5"

    # Affichage du loader (CSS pur - sans dépendance externe)
    st.markdown("""
        <div id="darpharm-loader">
            <div class="loader-logo">💊</div>
            <div style="font-weight: 800; font-size: 1.4rem; color: #1877f2; margin: 10px 0; letter-spacing: -0.5px;">DarPharm Solutions</div>
            <div class="loader-bar"><div class="loader-progress"></div></div>
            <script>
                setTimeout(() => {
                    const loader = document.getElementById('darpharm-loader');
                    if (loader) loader.style.opacity = '0';
                    setTimeout(() => { if (loader) loader.style.display = 'none'; }, 500);
                }, 2000);
            </script>
        </div>
    """, unsafe_allow_html=True)

    # Injection CSS spécifique pour l'écran de connexion Facebook-style
    st.markdown(f"""
        <style>
            /* Cacher d'éventuels éléments indésirables */
            [data-testid="stSidebar"], [data-testid="stSidebarNav"] {{display: none;}}
            section[data-testid="stSidebar"] {{width: 0px;}}
            [data-testid="stHeader"] {{display: none;}}
            
            .stApp {{
                background-color: {login_bg} !important;
            }}
            
            .main .block-container {{
                max-width: 1000px;
                padding-top: 100px;
                margin: auto;
            }}
            
            /* Styles du contenu gauche */
            .fb-left-container {{
                padding-top: 40px;
                animation: slideUpFade 0.8s ease-out forwards;
            }}
            .fb-logo-text {{
                color: {logo_color};
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                font-size: 55px;
                font-weight: bold;
                letter-spacing: -1.5px;
                margin-bottom: 0px;
                line-height: 1;
                text-shadow: 2px 4px 10px rgba(0,0,0,0.2);
            }}
            .fb-slogan {{
                font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                font-size: 24px;
                line-height: 28px;
                font-weight: normal;
                color: {slogan_color} !important;
                margin-top: 15px;
                max-width: 500px;
            }}
            
            /* Styles de la carte de connexion (Ciblage direct de la colonne) */
            [data-testid="column"]:nth-of-type(2) > div {{
                background: {card_bg_color} !important;
                {card_backdrop}
                padding: 40px 30px !important;
                border-radius: 20px !important;
                box-shadow: {card_shadow} !important;
                border: 1px solid rgba(255,255,255,0.1) !important;
                animation: float3D 6s infinite ease-in-out;
            }}
            
            /* Supprimer les marges par défaut entre les widgets dans la carte */
            [data-testid="column"]:nth-of-type(2) [data-testid="stVerticalBlock"] > div {{
                padding-bottom: 0px !important;
                margin-bottom: -5px !important;
            }}
            
            /* Style des inputs Streamlit */
            .stTextInput input {{
                height: 52px !important;
                font-size: 17px !important;
                padding: 14px 16px !important;
                border: 1px solid {input_border} !important;
                border-radius: 12px !important;
                color: {input_text} !important;
                background: {input_bg} !important;
                margin-bottom: 10px !important;
                transition: all 0.3s ease;
            }}
            .stTextInput input:focus {{
                border-color: {logo_color} !important;
                box-shadow: 0 0 15px rgba(233, 69, 96, 0.4) !important;
                transform: scale(1.02);
            }}
            
            /* Visibilité des placeholders */
            ::placeholder {{
                color: #8d949e !important;
                opacity: 1 !important;
            }}
            
            /* Style du bouton de connexion */
            .stButton button {{
                background: {btn_bg} !important;
                color: white !important;
                font-size: 20px !important;
                font-weight: bold !important;
                height: 52px !important;
                border-radius: 12px !important;
                border: none !important;
                width: 100% !important;
                margin-top: 10px !important;
                transition: all 0.3s ease !important;
                box-shadow: 0 5px 15px rgba(0,0,0,0.2) !important;
            }}
            .stButton button:hover {{
                background: {btn_hover} !important;
                transform: translateY(-3px) scale(1.02) !important;
                box-shadow: 0 8px 25px rgba(0,0,0,0.3) !important;
            }}

            /* Supprimer l'espace vide des markdowns dans la carte */
            .stMarkdown:empty {{
                display: none !important;
            }}
            div.element-container:has(div.stMarkdown:empty) {{
                display: none !important;
            }}
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
        # Thème selector très compact
        themes_login = ["Clair", "Sombre", "Chic Animé", "Executive White", "Glass Pro", "Midnight Gold", "Nordic Clean", "USMH", "CRB", "USMA", "MCA"]
        idx_theme = themes_login.index(st.session_state.theme) if st.session_state.theme in themes_login else 0
        choix_theme = st.selectbox("Thème", themes_login, index=idx_theme, key="login_theme_selector", label_visibility="collapsed")
        if choix_theme != st.session_state.theme:
            st.session_state.theme = choix_theme
            st.rerun()

        u = st.text_input("Username", placeholder="Nom d'utilisateur", label_visibility="collapsed", key="login_u")
        p = st.text_input("Password", type="password", placeholder="Mot de passe", label_visibility="collapsed", key="login_p")
        
        rester_connecte = st.checkbox("Rester connecté", value=True)
        
        if st.button("Se connecter", type="primary", use_container_width=True):
            res = df_users[(df_users['username'] == u) & (df_users['password'] == p)]
            if not res.empty:
                user_data = res.iloc[0].to_dict()
                st.session_state.current_user = user_data
                if rester_connecte:
                    st.session_state.remember_me = True
                    try:
                        controller.set("user_token", str(user_data['username']), max_age=86400 * 30) 
                    except Exception as e:
                        st.warning(f"Note : Connexion auto non enregistrée ({e})")
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
    for extra_page in ["Cortex IA", "Automatisation", "Liste des Lots", "Répartition Zones", "Analyse Réclamations", "Performance Ventes", "Pointage Expéditeur", "Inventaire Triple", "Pointage Marchandise", "Assistant IA", "Transferts", "Coordination", "Qualité IA", "Mon Coin", "Briefing IA", "Maintenance", "Académie", "Prévisions", "Mode Meeting", "Page de Garde"]:
        if extra_page not in user_pages:
            user_pages.append(extra_page)

# Profil toujours accessible à tous les utilisateurs
if "Profil" not in user_pages:
    user_pages.append("Profil")

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
    "RH Planning": st.Page("modules/22_rh_permanence.py", title="RH & Planning (Permanence)", icon="📅"),
    "Clients": st.Page("modules/12_gestion_clients.py", title="Gestion Clients (CRM)", icon="🤝"),
    "Liste des Lots": st.Page("modules/14_liste_des_lots.py", title="Liste des Lots", icon="📑"),
    "Catalogue Produits": st.Page("modules/17_catalogue_produits.py", title="Catalogue Produits", icon="📚"),
    "Pointage Marchandise": st.Page("modules/18_reception.py", title="Pointage Marchandise", icon="📦"),
    "Page de Garde": st.Page("modules/18_page_garde.py", title="Page de Garde (Factures)", icon="📄"),
    "Assistant IA": st.Page("modules/19_chat_pharmaciel.py", title="Assistant IA (Chat)", icon="🤖"),
    "Transferts": st.Page("modules/20_transferts.py", title="Transferts (Zéro Papier)", icon="🔄"),
    "Coordination": st.Page("modules/21_coordination_equipe.py", title="Coordination Équipe", icon="🤝"),
    "Qualité IA": st.Page("modules/22_controle_qualite_ia.py", title="Contrôle Qualité IA", icon="🛡️"),
    "Mon Coin": st.Page("modules/23_mon_coin_admin.py", title="Mon Coin (Secret)", icon="🤫"),
    "Briefing IA": st.Page("modules/24_briefing_ia.py", title="Briefing Matinal", icon="📢"),
    "Maintenance": st.Page("modules/25_maintenance_flotte.py", title="Maintenance & Flotte", icon="🚛"),
    "Académie": st.Page("modules/26_academie.py", title="Académie DarPharm", icon="🎓"),
    "Prévisions": st.Page("modules/27_prevision_charge.py", title="Prévision de Charge", icon="📈"),
    "Mode Meeting": st.Page("modules/28_presentation_ia.py", title="Mode Meeting (DataShow)", icon="📽️"),
    "Répartition Zones": st.Page("modules/30_repartition_zones.py", title="Répartition Zones", icon="🧩"),
    "Analyse Réclamations": st.Page("modules/31_analyse_reclamations.py", title="Analyse Réclamations", icon="🎯"),
    "Performance Ventes": st.Page("modules/32_analyse_ventes.py", title="Performance Ventes", icon="💰"),
    "Cortex IA": st.Page("modules/33_cortex_ia.py", title="Cortex Stratégique IA", icon="🧠"),
    "Profil": st.Page("modules/17_profil.py", title="Mon Profil", icon="👤")
}

if is_ia_enabled():
    ALL_PAGES["Automatisation"] = st.Page("modules/9_automatisation.py", title="Automatisation & IA", icon="🤖")

# --- REGROUPEMENT ROBUSTE DES MODULES ---
pages_to_show = {}
assigned_keys = []

# Définition des groupes et de leurs membres (clés de ALL_PAGES)
CATEGORIES = {
    "👤 MON PROFIL": ["Profil", "Mon Coin"],
    "📊 SUPERVISION": ["Dashboard", "Analyse Rotation", "Prévisions", "Mode Meeting", "Analyse Réclamations", "Performance Ventes", "Suivi", "Dashboard Premium"],
    "📦 GESTION DES STOCKS": ["Inventaire", "Inventaire Détail", "Inventaire Triple", "Péremptions", "Liste des Lots", "Catalogue Produits", "Répartition Zones"],
    "📝 POINTAGES & FLUX": ["Pointage", "Pointage Expéditeur", "Pointage Marchandise", "Page de Garde", "Recouvrement", "Logistique", "Scanneur QR", "Scan Mobile", "Transferts", "Clients"],
    "🤖 DARPHARM IA": ["Cortex IA", "Assistant IA", "Qualité IA", "Briefing IA", "Automatisation", "Coordination", "Académie"],
    "🏥 ADMINISTRATION": ["Admin Centrale", "RH", "RH Planning", "Maintenance"]
}

# 1. On remplit les groupes définis
for cat_name, members in CATEGORIES.items():
    cat_list = []
    for m in members:
        if m in user_pages and m in ALL_PAGES:
            cat_list.append(ALL_PAGES[m])
            assigned_keys.append(m)
    if cat_list:
        pages_to_show[cat_name] = cat_list

# 2. Sécurité : On ajoute TOUT ce qui reste dans "AUTRES" pour ne rien perdre
autres_list = []
for p_key in user_pages:
    if p_key in ALL_PAGES and p_key not in assigned_keys:
        autres_list.append(ALL_PAGES[p_key])

if autres_list:
    pages_to_show["🧩 AUTRES MODULES"] = autres_list

# 3. Ajout spécial Admin Centrale si non déjà fait
if is_admin and "🏛️ ADMINISTRATION" not in pages_to_show:
    pages_to_show["🏛️ ADMINISTRATION"] = [
        st.Page("modules/0_admin_centrale.py", title="Admin Centrale (Data)", icon="🏛️"),
        st.Page("modules/5_admin.py", title="Gestion des Accès", icon="⚙️")
    ]
elif is_admin:
    # On s'assure que les pages d'admin pur sont présentes
    admin_pages = [
        st.Page("modules/0_admin_centrale.py", title="Admin Centrale (Data)", icon="🏛️"),
        st.Page("modules/5_admin.py", title="Gestion des Accès", icon="⚙️")
    ]
    for ap in admin_pages:
        if ap not in pages_to_show["🏛️ ADMINISTRATION"]:
            pages_to_show["🏛️ ADMINISTRATION"].insert(0, ap)

if not pages_to_show:
    st.warning("Vous n'avez accès à aucun module. Contactez l'administrateur.")
    if st.button("Déconnexion"):
        st.session_state.current_user = None
        st.rerun()
    st.stop()

# --- 6. NAVIGATION ET SIDEBAR (ACCORDÉON) ---
from utils_notifications import show_notification_center
from utils_search import show_search_bar

if "active_group" not in st.session_state:
    st.session_state.active_group = "📊 SUPERVISION"

# Initialiser la navigation (Masquer le menu par défaut)
pg = st.navigation(pages_to_show, position="hidden")

# Injection CSS pour la lisibilité
st.markdown("""
    <style>
        [data-testid="stSidebar"] .stButton > button {
            font-size: 1.1rem !important;
            font-weight: 700 !important;
            border-radius: 10px !important;
            height: 50px !important;
            margin-bottom: 10px !important;
            display: flex !important;
            flex-direction: row !important;
            align-items: center !important;
            justify-content: flex-start !important;
            padding-left: 20px !important;
            white-space: nowrap !important;
            overflow: hidden !important;
            text-overflow: ellipsis !important;
        }
        .sidebar-header {
            font-size: 1.2rem !important;
            font-weight: 800 !important;
            color: var(--sidebar-header-color, #1a1f3c) !important;
            margin-top: 30px !important;
            margin-bottom: 15px !important;
            padding-left: 5px !important;
        }
        .user-box {
            background: var(--bg-card, #ffffff);
            padding: 15px;
            border-radius: 15px;
            box-shadow: var(--shadow-neu, 0 4px 12px rgba(0,0,0,0.05));
            border: 1px solid rgba(0,0,0,0.05);
            margin-bottom: 20px;
        }
        /* Amélioration lisibilité liens de pages */
        [data-testid="stSidebar"] a {
            font-size: 1rem !important;
            font-weight: 600 !important;
            color: var(--sidebar-text-color, #4a5568) !important;
            padding: 10px 15px !important;
            border-radius: 8px !important;
            margin: 4px 0 !important;
            display: flex !important;
            flex-direction: row !important;
            align-items: center !important;
            white-space: nowrap !important;
            text-decoration: none !important;
        }
        [data-testid="stSidebar"] a:hover {
            background: rgba(0,0,0,0.03) !important;
        }
        /* Fix for vertical text in sidebar icons/labels */
        [data-testid="stSidebar"] span {
            white-space: nowrap !important;
        }
    </style>
""", unsafe_allow_html=True)

with st.sidebar:
    # 1. ACCORDÉON DE NAVIGATION (EN PREMIER)
    st.markdown('<p class="sidebar-header">🗺️ MODULES</p>', unsafe_allow_html=True)
    for group_name, pages in pages_to_show.items():
        is_active = st.session_state.active_group == group_name
        
        if st.button(group_name, key=f"grp_{group_name}", use_container_width=True, 
                     type="primary" if is_active else "secondary"):
            st.session_state.active_group = group_name
            
        if is_active:
            st.markdown('<div style="padding-left: 15px; border-left: 3px solid #5b6cf9; margin-top: 5px; margin-bottom: 15px;">', unsafe_allow_html=True)
            for p in pages:
                st.page_link(p, label=p.title, icon=p.icon)
            st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    # 2. NOTIFICATIONS & RECHERCHE
    show_notification_center()
    show_search_bar()
    
    st.markdown("<div style='margin: 30px 0;'></div>", unsafe_allow_html=True)

    # 3. INFOS UTILISATEUR & THÈME (EN BAS)
    with st.expander("👤 MON COMPTE", expanded=False):
        st.markdown(f"""
            <div class="user-box">
                <p style="margin: 0; font-size: 0.9rem; color: #6b7299;">Connecté en tant que :</p>
                <p style="margin: 0; font-size: 1.1rem; font-weight: 800; color: #1a1f3c;">{user['username']}</p>
                <p style="margin: 0; font-size: 0.85rem; color: #5b6cf9; font-weight: 600;">Rôle : {user.get('role', 'Saisie')}</p>
            </div>
        """, unsafe_allow_html=True)
        
        themes_disponibles = ["Clair", "Sombre", "Chic Animé", "Executive White", "Glass Pro", "Midnight Gold", "Nordic Clean", "USMH", "CRB", "USMA", "MCA"]
        current_index = themes_disponibles.index(st.session_state.theme) if st.session_state.theme in themes_disponibles else 0
        new_theme = st.selectbox("🎨 Thème visuel", themes_disponibles, index=current_index, key="sidebar_theme_selector")
        if new_theme != st.session_state.theme:
            st.session_state.theme = new_theme
            st.rerun()

        if st.button("🚪 Déconnexion", use_container_width=True, key="btn_logout"):
            st.session_state.current_user = None
            try:
                if controller.get("user_token"):
                    controller.remove("user_token")
            except Exception: pass
            st.rerun()

    st.divider()

    # 4. LOGO (TOUT EN BAS)
    if os.path.exists("logo.png"):
        st.image("logo.png", use_container_width=True)
    else:
        st.markdown('<h2 style="text-align:center; color:#5b6cf9;">DarPharm</h2>', unsafe_allow_html=True)

# Exécuter la page
pg.run()
