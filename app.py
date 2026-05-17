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

# --- 2. CONFIGURATION BASE DE DONNÉES (Établissement-Aware) ---
from utils_gsheets import load_gs_data, save_gs_data, DB_USERS_WORKSHEET, DB_USERS_FALLBACK, USER_COLUMNS
from config_etablissements import ETABLISSEMENTS, MULTI_ETABLISSEMENT_USERNAMES

# Init établissement depuis session
if "etablissement" not in st.session_state:
    st.session_state.etablissement = None

_etab_id = st.session_state.etablissement or "darpharm"
_etab_cfg = ETABLISSEMENTS[_etab_id]
_users_ws  = _etab_cfg["users_worksheet"]
_users_fb  = _etab_cfg["users_fallback"] or "data/db_users_empty.csv"

df_users = load_gs_data(_users_ws, _users_fb, USER_COLUMNS)

# ═══════════════════════════════════════════════════════
# CHARTE OFFICIELLE DES RÔLES DARPHARM — GOLDEN BACKUP
# Point de restauration automatique des accès utilisateurs
# ═══════════════════════════════════════════════════════
import json

GOLDEN_BACKUP_PATH = "data/golden_roles_backup.json"

# Définition des pages par métier (synchronisée avec golden_roles_backup.json)
PAGES_BY_METIER = {
    "Admin": str(['Dashboard', 'Profil', 'Admin Centrale', 'Logistique', 'Inventaire', 'Inventaire Détail', 'Inventaire Triple', 'Suivi', 'Recouvrement', 'Pointage', 'Pointage Expéditeur', 'Pointage Marchandise', 'Réception Fournisseurs', 'Péremptions', 'Scanneur QR', 'Scan Mobile', 'Litiges Fournisseurs', 'Analyse Rotation', 'RH', 'RH Planning', 'Clients', 'Liste des Lots', 'Catalogue Produits', 'Page de Garde', 'Assistant IA', 'Transferts', 'Coordination', 'Qualité IA', 'Mon Coin', 'Briefing IA', 'Maintenance', 'Académie', 'Prévisions', 'Mode Meeting', 'Répartition Zones', 'Analyse Réclamations', 'Performance Ventes', 'Cortex IA', 'Automatisation']),
    "Agent de Stock": str(['Profil', 'Dashboard', 'Inventaire', 'Inventaire Détail', 'Inventaire Triple', 'Péremptions', 'Liste des Lots', 'Catalogue Produits', 'Répartition Zones', 'Scanneur QR', 'Scan Mobile', 'Transferts']),
    "Chef Livreurs & Parc": str(['Profil', 'Dashboard', 'Logistique', 'Pointage Expéditeur', 'Recouvrement', 'Maintenance', 'Clients', 'Suivi', 'Analyse Rotation', 'Transferts', 'Page de Garde']),
    "Superviseur": str(['Profil', 'Dashboard', 'Analyse Rotation', 'Analyse Réclamations', 'Performance Ventes', 'Prévisions', 'Logistique', 'Inventaire', 'RH', 'Briefing IA', 'Mode Meeting']),
    "Préparateur": str(['Profil', 'Pointage Marchandise', 'Réception Fournisseurs', 'Inventaire Détail', 'Scanneur QR', 'Scan Mobile', 'Transferts']),
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

# ═══════════════════════════════════════════════════════════════════
# CHARTE PHARMACIEL (Filiale) — Golden Backup
# ═══════════════════════════════════════════════════════════════════
PAGES_BY_METIER_PHARMACIEL = {
    "Admin": str(['Dashboard', 'Profil', 'Admin Centrale', 'Logistique', 'Inventaire', 'Inventaire Détail', 'Inventaire Triple', 'Suivi', 'Recouvrement', 'Pointage', 'Pointage Expéditeur', 'Pointage Marchandise', 'Réception Fournisseurs', 'Péremptions', 'Scanneur QR', 'Scan Mobile', 'Litiges Fournisseurs', 'Analyse Rotation', 'RH', 'RH Planning', 'Liste des Lots', 'Catalogue Produits', 'Page de Garde', 'Assistant IA', 'Transferts', 'Coordination', 'Qualité IA', 'Mon Coin', 'Briefing IA', 'Académie', 'Prévisions', 'Répartition Zones', 'Analyse Réclamations', 'Performance Ventes', 'Cortex IA', 'Automatisation']),
    "Gestionnaire de Stock": str(['Profil', 'Dashboard', 'Inventaire', 'Inventaire Détail', 'Inventaire Triple', 'Péremptions', 'Liste des Lots', 'Catalogue Produits', 'Répartition Zones', 'Scanneur QR', 'Scan Mobile', 'Transferts', 'Réception Fournisseurs', 'Coordination', 'Analyse Rotation']),
    "Préparateur": str(['Profil', 'Pointage Marchandise', 'Réception Fournisseurs', 'Inventaire Détail', 'Scanneur QR', 'Scan Mobile', 'Transferts', 'Coordination']),
}

GOLDEN_USERS_PHARMACIEL = [
    ('Imad',     'admin_imad_pwd',  'Admin',  'Admin',                  'Administration'),
    ('Ayoub',    'ayoub2026',       'Saisie', 'Gestionnaire de Stock',  'Stock'),
    ('Islem',    'islem2026',       'Saisie', 'Gestionnaire de Stock',  'Stock'),
    ('Seif',     'seif2026',        'Saisie', 'Gestionnaire de Stock',  'Stock'),
    ('Karime',   'karime2026',      'Saisie', 'Préparateur',            'Préparation'),
    ('Malek',    'malek2026',       'Saisie', 'Préparateur',            'Préparation'),
]

def apply_golden_pages(metier, role, etab="darpharm"):
    pages_dict = PAGES_BY_METIER_PHARMACIEL if etab == "pharmaciel" else PAGES_BY_METIER
    fallback = list(pages_dict.values())[-1]
    if role == 'Admin':
        return pages_dict.get('Admin', fallback)
    return pages_dict.get(metier, fallback)

_setup_key = _etab_cfg["setup_key"]

if _setup_key not in st.session_state:
    _active_etab = st.session_state.etablissement or "darpharm"
    _golden = GOLDEN_USERS_PHARMACIEL if _active_etab == "pharmaciel" else GOLDEN_USERS
    changes_made = False

    # --- NETTOYAGE DES DOUBLONS ---
    if not df_users.empty:
        initial_len = len(df_users)
        df_users['uname_lower'] = df_users['username'].astype(str).str.lower().str.strip()
        df_users = df_users.drop_duplicates(subset=['uname_lower'], keep='last').drop(columns=['uname_lower'])
        if len(df_users) < initial_len:
            changes_made = True

    # --- PURGE DES UTILISATEURS NON-AUTORISÉS (Pour Pharmaciel) ---
    if _active_etab == "pharmaciel" and not df_users.empty:
        allowed_unames = [u[0].lower() for u in _golden] + [un.lower() for un in MULTI_ETABLISSEMENT_USERNAMES]
        mask_to_keep = df_users['username'].astype(str).str.lower().str.strip().isin(allowed_unames)
        if not mask_to_keep.all():
            df_users = df_users[mask_to_keep].reset_index(drop=True)
            changes_made = True

    for (uname, pwd, urole, umetier, udepot) in _golden:
        correct_pages = apply_golden_pages(umetier, urole, _active_etab)
        user_exists = not df_users.empty and uname.lower() in df_users['username'].astype(str).str.lower().str.strip().values

        if not user_exists:
            new_row = {
                'username': uname, 'password': pwd, 'role': urole,
                'metier': umetier, 'depot': udepot, 'zone': 'Aucune',
                'nom': uname, 'prenom': '', 'pages': correct_pages
            }
            df_users = pd.concat([df_users, pd.DataFrame([new_row])], ignore_index=True)
            changes_made = True
        else:
            mask = df_users['username'].astype(str).str.lower().str.strip() == uname.lower()
            current_metier = str(df_users.loc[mask, 'metier'].values[0]) if 'metier' in df_users.columns else ''
            current_pages  = str(df_users.loc[mask, 'pages'].values[0])  if 'pages'  in df_users.columns else ''
            if current_metier != umetier or current_pages != correct_pages or not current_pages or current_pages in ['nan', '[]', '']:
                for col in ['metier', 'depot', 'pages', 'role']:
                    if col not in df_users.columns:
                        df_users[col] = ''
                    df_users[col] = df_users[col].astype(object)
                df_users.loc[mask, 'metier'] = umetier
                df_users.loc[mask, 'depot']  = udepot
                df_users.loc[mask, 'pages']  = correct_pages
                df_users.loc[mask, 'role']   = urole
                changes_made = True

    if changes_made:
        save_gs_data(df_users, _users_ws, _users_fb)

    st.session_state[_setup_key] = True

# --- 3. GESTION DE SESSION ET COOKIES ---
if "current_user" not in st.session_state:
    st.session_state.current_user = None

# Initialiser le contrôleur de cookies
controller = CookieController(key="main_cookie_controller")

# Récupérer tokens depuis cookies
try:
    token_user = controller.get("user_token")
except Exception:
    token_user = None
try:
    token_etab = controller.get("etab_token")
except Exception:
    token_etab = None

# Restaurer l'établissement depuis le cookie (si pas déjà en session)
if st.session_state.etablissement is None and token_etab in ETABLISSEMENTS:
    st.session_state.etablissement = token_etab
    st.rerun()

# --- Auto-Login via Cookie ---
if st.session_state.current_user is None and token_user and st.session_state.etablissement:
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

    # ── Si aucun établissement choisi → Afficher le sélecteur ─────────────────
    if st.session_state.etablissement is None:
        st.markdown("""
        <style>
            [data-testid="stSidebar"], [data-testid="stSidebarNav"] {display: none;}
            section[data-testid="stSidebar"] {width: 0px;}
            [data-testid="stHeader"] {display: none;}
            .stApp { background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%) !important; }
            .main .block-container { max-width: 900px; padding-top: 80px; margin: auto; }
            @keyframes cardFloat { 0%,100%{transform:translateY(0px)} 50%{transform:translateY(-8px)} }
            @keyframes fadeInUp { from{opacity:0;transform:translateY(30px)} to{opacity:1;transform:translateY(0)} }
        </style>
        """, unsafe_allow_html=True)

        st.markdown("""
        <div style="text-align:center; animation: fadeInUp 0.8s ease forwards; margin-bottom: 40px;">
            <div style="font-size:3rem; margin-bottom:8px;">⚕️</div>
            <h1 style="color:white; font-size:2.2rem; font-weight:800; margin:0; letter-spacing:-1px;">
                Groupe Pharmaceutique
            </h1>
            <p style="color:rgba(255,255,255,0.5); font-size:1rem; margin-top:6px;">
                Choisissez votre établissement pour continuer
            </p>
        </div>
        """, unsafe_allow_html=True)

        col_dp, col_ph = st.columns(2, gap="large")

        with col_dp:
            st.markdown("""
            <div style="background:linear-gradient(135deg,#1877f2,#0f3460);border-radius:20px;padding:40px 30px;
                        text-align:center;cursor:pointer;animation:cardFloat 4s ease-in-out infinite;
                        box-shadow:0 20px 60px rgba(24,119,242,0.4);border:1px solid rgba(255,255,255,0.15);">
                <div style="font-size:4rem;margin-bottom:12px;">🏭</div>
                <h2 style="color:white;margin:0;font-size:1.6rem;font-weight:800;">DarPharm</h2>
                <p style="color:rgba(255,255,255,0.7);margin:8px 0 0;font-size:0.9rem;">
                    Grossiste & Distribution Pharmaceutique
                </p>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            if st.button("🏭  Accéder à DarPharm", key="btn_select_darpharm",
                         use_container_width=True, type="primary"):
                st.session_state.etablissement = "darpharm"
                st.cache_data.clear()
                try:
                    controller.set("etab_token", "darpharm", max_age=86400 * 30)
                except Exception:
                    pass
                st.rerun()

        with col_ph:
            st.markdown("""
            <div style="background:linear-gradient(135deg,#6B46C1,#2D6A4F);border-radius:20px;padding:40px 30px;
                        text-align:center;cursor:pointer;animation:cardFloat 4s ease-in-out infinite 0.5s;
                        box-shadow:0 20px 60px rgba(107,70,193,0.4);border:1px solid rgba(255,255,255,0.15);">
                <div style="font-size:4rem;margin-bottom:12px;">🏪</div>
                <h2 style="color:white;margin:0;font-size:1.6rem;font-weight:800;">Pharmaciel</h2>
                <p style="color:rgba(255,255,255,0.7);margin:8px 0 0;font-size:0.9rem;">
                    Filiale — Distribution & Répartition
                </p>
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
            if st.button("🏪  Accéder à Pharmaciel", key="btn_select_pharmaciel",
                         use_container_width=True):
                st.session_state.etablissement = "pharmaciel"
                st.cache_data.clear()
                try:
                    controller.set("etab_token", "pharmaciel", max_age=86400 * 30)
                except Exception:
                    pass
                st.rerun()

        st.stop()

    # ── Établissement choisi → Afficher la page de login ──────────────────────
    _active_etab_login = st.session_state.etablissement
    _etab_info = ETABLISSEMENTS[_active_etab_login]
    _etab_color = _etab_info["color_primary"]
    _etab_nom   = _etab_info["nom_complet"]
    _etab_icon  = _etab_info["icon"]

    # ── Variables de branding par établissement ────────────────────────────────
    _c1 = _etab_info["color_primary"]
    _c2 = _etab_info["color_secondary"]
    _grad = _etab_info["color_gradient"]

    # ── CSS Premium ────────────────────────────────────────────────────────────
    st.markdown(f"""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800;900&display=swap');

        [data-testid="stSidebar"], [data-testid="stSidebarNav"] {{display:none!important;}}
        section[data-testid="stSidebar"] {{width:0!important;}}
        [data-testid="stHeader"] {{display:none!important;}}
        [data-testid="stStatusWidget"] {{display:none!important;}}
        /* Masquer les warnings pendant le login */
        [data-testid="stAlertContainer"] {{display:none!important;}}
        .stAlert {{display:none!important;}}

        * {{ font-family: 'Inter', sans-serif !important; }}

        .stApp {{
            background: linear-gradient(135deg, #0a0a1a 0%, #0d1b2a 40%, #0a0a1a 100%) !important;
            min-height: 100vh;
        }}

        .main .block-container {{
            padding: 0 !important;
            max-width: 100% !important;
        }}

        /* ── Colonne gauche (branding) ── */
        [data-testid="column"]:nth-of-type(1) > div:first-child {{
            background: {_grad} !important;
            min-height: 100vh;
            padding: 60px 50px !important;
            position: relative;
            overflow: hidden;
        }}

        /* ── Colonne droite (formulaire) ── */
        [data-testid="column"]:nth-of-type(2) > div:first-child {{
            background: transparent !important;
            min-height: 100vh;
            padding: 60px 50px !important;
            display: flex;
            align-items: center;
        }}

        /* ── Inputs ── */
        .stTextInput > div {{
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
        }}
        .stTextInput > div > div {{
            background: rgba(255,255,255,0.07) !important;
            border: 1.5px solid rgba(255,255,255,0.15) !important;
            border-radius: 14px !important;
            transition: all 0.3s ease !important;
            backdrop-filter: blur(10px);
            height: 54px !important;
            padding-right: 10px !important;
        }}
        .stTextInput > div > div:focus-within {{
            border-color: {_c1} !important;
            background: rgba(255,255,255,0.1) !important;
            box-shadow: 0 0 0 3px {_c1}33 !important;
        }}
        .stTextInput > div > div > input {{
            color: white !important;
            font-size: 15px !important;
            background: transparent !important;
            border: none !important;
            box-shadow: none !important;
            padding: 0 18px !important;
            height: 100% !important;
        }}
        .stTextInput > div > div > input::placeholder {{
            color: rgba(255,255,255,0.4) !important;
        }}
        
        /* Autofill fixes */
        .stTextInput input:-webkit-autofill,
        .stTextInput input:-webkit-autofill:hover, 
        .stTextInput input:-webkit-autofill:focus, 
        .stTextInput input:-webkit-autofill:active {{
            -webkit-box-shadow: 0 0 0 30px #0a0a1a inset !important;
            -webkit-text-fill-color: white !important;
            transition: background-color 5000s ease-in-out 0s;
        }}

        /* Eye icon */
        .stTextInput > div > div > button {{
            color: rgba(255,255,255,0.5) !important;
            background: transparent !important;
            border: none !important;
        }}

        /* ── Bouton principal ── */
        .stButton > button[kind="primary"] {{
            background: {_grad} !important;
            border: none !important;
            border-radius: 14px !important;
            color: white !important;
            font-size: 16px !important;
            font-weight: 700 !important;
            height: 54px !important;
            width: 100% !important;
            letter-spacing: 0.5px;
            box-shadow: 0 8px 30px {_c1}55 !important;
            transition: all 0.3s cubic-bezier(0.175,0.885,0.32,1.275) !important;
        }}
        .stButton > button[kind="primary"]:hover {{
            transform: translateY(-3px) !important;
            box-shadow: 0 14px 40px {_c1}77 !important;
        }}

        /* ── Bouton secondaire (Changer) ── */
        .stButton > button[kind="secondary"] {{
            background: rgba(255,255,255,0.08) !important;
            border: 1px solid rgba(255,255,255,0.2) !important;
            border-radius: 30px !important;
            color: rgba(255,255,255,0.8) !important;
            font-size: 13px !important;
            font-weight: 600 !important;
            height: 38px !important;
            padding: 0 18px !important;
            transition: all 0.2s ease !important;
        }}
        .stButton > button[kind="secondary"]:hover {{
            background: rgba(255,255,255,0.15) !important;
            border-color: rgba(255,255,255,0.4) !important;
            color: white !important;
        }}

        /* ── Checkbox ── */
        [data-testid="stCheckbox"] label span {{
            color: rgba(255,255,255,0.6) !important;
            font-size: 14px !important;
        }}

        /* ── Selectbox (thème) ── */
        [data-testid="stSelectbox"] > div > div {{
            background: rgba(255,255,255,0.07) !important;
            border: 1px solid rgba(255,255,255,0.15) !important;
            border-radius: 10px !important;
            color: rgba(255,255,255,0.7) !important;
        }}

        @keyframes fadeLeft {{
            from {{ opacity:0; transform:translateX(-30px); }}
            to {{ opacity:1; transform:translateX(0); }}
        }}
        @keyframes fadeRight {{
            from {{ opacity:0; transform:translateX(30px); }}
            to {{ opacity:1; transform:translateX(0); }}
        }}
        @keyframes pulse-ring {{
            0% {{ transform:scale(0.95); box-shadow:0 0 0 0 {_c1}88; }}
            70% {{ transform:scale(1); box-shadow:0 0 0 15px transparent; }}
            100% {{ transform:scale(0.95); box-shadow:0 0 0 0 transparent; }}
        }}
    </style>
    """, unsafe_allow_html=True)

    # ── Layout principal ───────────────────────────────────────────────────────
    col1, col2 = st.columns([1, 1], gap="small")

    # ── Colonne gauche : Branding ──────────────────────────────────────────────
    with col1:
        st.markdown(f"""
<div style="animation:fadeLeft 0.8s ease forwards; height:100%; display:flex; flex-direction:column; justify-content:center; min-height:85vh;">

<!-- Badge établissement -->
<div style="display:inline-flex; align-items:center; gap:8px; background:rgba(255,255,255,0.15); backdrop-filter:blur(10px); border:1px solid rgba(255,255,255,0.25); border-radius:30px; padding:8px 18px; width:fit-content; margin-bottom:40px;">
<span style="font-size:1.1rem;">{_etab_icon}</span>
<span style="color:white; font-size:0.85rem; font-weight:600; letter-spacing:0.5px;">{_etab_info['nom'].upper()}</span>
</div>

<!-- Titre principal -->
<h1 style="color:white; font-size:3.2rem; font-weight:900; line-height:1.1; margin:0 0 16px; letter-spacing:-2px;">{_etab_nom}</h1>

<!-- Sous-titre -->
<p style="color:rgba(255,255,255,0.7); font-size:1.1rem; margin:0 0 50px; line-height:1.6; font-weight:400; max-width:340px;">{_etab_info['subtitle']}</p>

<!-- Séparateur décoratif -->
<div style="width:60px; height:4px; background:rgba(255,255,255,0.5); border-radius:4px; margin-bottom:40px;"></div>

<!-- Features -->
<div style="display:flex; flex-direction:column; gap:16px;">
<div style="display:flex; align-items:center; gap:12px;">
<div style="width:36px; height:36px; background:rgba(255,255,255,0.15); border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:1rem;">📦</div>
<span style="color:rgba(255,255,255,0.8); font-size:0.9rem;">Gestion stocks & inventaires</span>
</div>
<div style="display:flex; align-items:center; gap:12px;">
<div style="width:36px; height:36px; background:rgba(255,255,255,0.15); border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:1rem;">🚛</div>
<span style="color:rgba(255,255,255,0.8); font-size:0.9rem;">Logistique & expéditions</span>
</div>
<div style="display:flex; align-items:center; gap:12px;">
<div style="width:36px; height:36px; background:rgba(255,255,255,0.15); border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:1rem;">🤖</div>
<span style="color:rgba(255,255,255,0.8); font-size:0.9rem;">Assistant IA intégré</span>
</div>
</div>
</div>
""", unsafe_allow_html=True)

    # ── Colonne droite : Formulaire ────────────────────────────────────────────
    with col2:
        st.markdown(f"""
<div style="animation:fadeRight 0.8s ease forwards;">
<div style="background:rgba(255,255,255,0.05); backdrop-filter:blur(20px); -webkit-backdrop-filter:blur(20px); border:1px solid rgba(255,255,255,0.12); border-radius:24px; padding:48px 44px; box-shadow:0 30px 80px rgba(0,0,0,0.5);">
<p style="color:rgba(255,255,255,0.45); font-size:0.8rem; font-weight:600; letter-spacing:2px; text-transform:uppercase; margin:0 0 8px;">
CONNEXION
</p>
<h2 style="color:white; font-size:1.8rem; font-weight:800; margin:0 0 32px; letter-spacing:-0.5px;">
Bienvenue 👋
</h2>
""", unsafe_allow_html=True)

        # Thème selector compact
        themes_login = ["Clair", "Sombre", "Chic Animé", "Executive White", "Glass Pro",
                        "Midnight Gold", "Nordic Clean", "USMH", "CRB", "USMA", "MCA"]
        idx_theme = themes_login.index(st.session_state.theme) if st.session_state.theme in themes_login else 0
        choix_theme = st.selectbox("🎨 Thème", themes_login, index=idx_theme,
                                   key="login_theme_selector", label_visibility="collapsed")
        if choix_theme != st.session_state.theme:
            st.session_state.theme = choix_theme
            st.rerun()

        u = st.text_input("u", placeholder="👤  Nom d'utilisateur",
                          label_visibility="collapsed", key="login_u")
        p = st.text_input("p", type="password", placeholder="🔒  Mot de passe",
                          label_visibility="collapsed", key="login_p")

        c1b, c2b = st.columns([1, 1])
        with c1b:
            rester_connecte = st.checkbox("Rester connecté", value=True)
        with c2b:
            st.markdown("")

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        if st.button(f"Se connecter  {_etab_icon}", type="primary", use_container_width=True):
            res = df_users[(df_users['username'] == u) & (df_users['password'] == p)]
            if not res.empty:
                user_data = res.iloc[0].to_dict()
                st.session_state.current_user = user_data
                st.session_state.etablissement = _active_etab_login
                if rester_connecte:
                    st.session_state.remember_me = True
                    try:
                        controller.set("user_token", str(user_data['username']), max_age=86400 * 30)
                        controller.set("etab_token", _active_etab_login, max_age=86400 * 30)
                    except Exception as e:
                        pass
                else:
                    st.session_state.remember_me = False
                    try:
                        controller.remove("user_token")
                        controller.remove("etab_token")
                    except Exception:
                        pass
                st.rerun()
            else:
                st.markdown(f"""
                <div style="background:rgba(239,68,68,0.15); border:1px solid rgba(239,68,68,0.4);
                             border-radius:12px; padding:14px 18px; margin-top:12px;
                             color:#fca5a5; font-size:0.9rem; font-weight:500;">
                    ❌ Identifiants incorrects — vérifiez vos informations
                </div>
                """, unsafe_allow_html=True)

        st.markdown("""
            <div style="text-align:center; margin-top:24px;">
                <div style="width:100%; height:1px; background:rgba(255,255,255,0.08);
                             margin-bottom:20px;"></div>
            </div>
        """, unsafe_allow_html=True)

        if st.button("⬅️  Changer d'établissement", key="btn_change_etab",
                     use_container_width=True):
            st.session_state.etablissement = None
            st.session_state.current_user = None
            st.cache_data.clear()
            try:
                controller.remove("etab_token")
                controller.remove("user_token")
            except Exception:
                pass
            st.rerun()

        st.markdown("</div></div>", unsafe_allow_html=True)

    st.stop()



# --- 5. DÉFINITION DES PAGES DISPONIBLES ---
user = st.session_state.current_user
umetier = user.get('metier', '')
urole = user.get('role', '')
_etab_actif = st.session_state.get('etablissement', 'darpharm')
_pages_ref = PAGES_BY_METIER_PHARMACIEL if _etab_actif == 'pharmaciel' else PAGES_BY_METIER

# Force la lecture en temps réel de la Charte Dynamique
if urole == 'Admin':
    user_pages = _pages_ref.get('Admin', '[]')
else:
    user_pages = _pages_ref.get(umetier, user.get('pages', '[]'))

# Conversion sécurisée si pages est stocké sous forme de chaîne
if isinstance(user_pages, str):
    import ast
    try:
        user_pages = ast.literal_eval(user_pages)
    except:
        user_pages = [p.strip() for p in user_pages.replace('[','').replace(']','').replace("'","").split(',') if p.strip()]

if not isinstance(user_pages, list):
    user_pages = []

is_admin = user.get('role') == 'Admin'

if is_admin:
    for extra_page in ["Cortex IA", "Automatisation", "Liste des Lots", "Répartition Zones", "Analyse Réclamations", "Performance Ventes", "Pointage Expéditeur", "Inventaire Triple", "Pointage Marchandise", "Réception Fournisseurs", "Litiges Fournisseurs", "Assistant IA", "Base IA", "Transferts", "Coordination", "Qualité IA", "Mon Coin", "Briefing IA", "Maintenance", "Académie", "Prévisions", "Mode Meeting", "Page de Garde"]:
        if extra_page not in user_pages:
            user_pages.append(extra_page)

# Profil toujours accessible à tous les utilisateurs
if "Profil" not in user_pages:
    user_pages.append("Profil")

# Dictionnaire de toutes les pages possibles (Key: Nom, Value: Path)
ALL_PAGES = {
    "Master Global": st.Page("modules/0_master_control.py", title="Master Global Control", icon="🌐"),
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
    "Pointage Marchandise": st.Page("modules/18_reception.py", title="Pointage Marchandise", icon="🔍"),
    "Réception Fournisseurs": st.Page("modules/34_arrivage_reception.py", title="Réception Fournisseurs", icon="🚚"),
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
    "Base IA": st.Page("modules/35_base_ia.py", title="Base d'Apprentissage IA", icon="🤖"),
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
    "📊 SUPERVISION": ["Master Global", "Dashboard", "Analyse Rotation", "Prévisions", "Mode Meeting", "Analyse Réclamations", "Performance Ventes", "Suivi", "Dashboard Premium"],
    "📦 GESTION DES STOCKS": ["Inventaire", "Inventaire Détail", "Inventaire Triple", "Péremptions", "Liste des Lots", "Catalogue Produits", "Répartition Zones"],
    "🏭 FOURNISSEURS": ["Réception Fournisseurs", "Pointage Marchandise", "Litiges Fournisseurs"],
    "📝 POINTAGES & FLUX": ["Pointage", "Pointage Expéditeur", "Page de Garde", "Recouvrement", "Logistique", "Scanneur QR", "Scan Mobile", "Transferts", "Clients"],
    "🤖 DARPHARM IA": ["Cortex IA", "Assistant IA", "Base IA", "Qualité IA", "Briefing IA", "Automatisation", "Coordination", "Académie"],
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
    # 0. CALENDRIER GLOBAL
    from datetime import datetime
    today = datetime.now()
    day_name = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"][today.weekday()]
    st.markdown(f"<div style='margin-bottom:10px; font-weight:700; font-size:1.1rem;'>📅 Aujourd'hui : {day_name}</div>", unsafe_allow_html=True)
    if today.weekday() == 4: # Vendredi
        st.error("🔴 Aujourd'hui est un Vendredi (Weekend)")
    elif today.weekday() == 5: # Samedi
        st.warning("🟡 Aujourd'hui : Samedi (Permanence 9h - 15h)")
    else:
        pass # Pas de message vert pour garder la sidebar clean en semaine
        
    # 1. ACCORDÉON DE NAVIGATION
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
        _etab_badge_color = ETABLISSEMENTS.get(_etab_actif, {}).get("color_primary", "#1877f2")
        _etab_badge_nom   = ETABLISSEMENTS.get(_etab_actif, {}).get("nom", "DarPharm")
        _etab_badge_icon  = ETABLISSEMENTS.get(_etab_actif, {}).get("icon", "🏭")
        st.markdown(f"""
            <div class="user-box">
                <p style="margin:0 0 4px; font-size:0.75rem; font-weight:700; color:white;
                           background:{_etab_badge_color}; padding:3px 10px; border-radius:20px;
                           display:inline-block;">{_etab_badge_icon} {_etab_badge_nom}</p>
                <p style="margin: 4px 0 0; font-size: 0.9rem; color: #6b7299;">Connecté en tant que :</p>
                <p style="margin: 0; font-size: 1.1rem; font-weight: 800; color: #1a1f3c;">{user['username']}</p>
                <p style="margin: 0; font-size: 0.85rem; color: #5b6cf9; font-weight: 600;">Rôle : {user.get('role', 'Saisie')}</p>
            </div>
        """, unsafe_allow_html=True)

        
        themes_disponibles = ["Clair", "Sombre", "Chic Animé", "Executive White", "Glass Pro", "Midnight Gold", "Nordic Clean", "Pharmaciel Luxe", "USMH", "CRB", "USMA", "MCA"]
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

# --- WIDGET DE TRADUCTION GOOGLE (ARABE / FRANCAIS) ---
import streamlit.components.v1 as components
components.html("""
<script>
const doc = window.parent.document;
if (!doc.getElementById('google_translate_script')) {
    const script1 = doc.createElement('script');
    script1.type = 'text/javascript';
    script1.innerHTML = `
        function googleTranslateElementInit() {
          new window.google.translate.TranslateElement({
              pageLanguage: 'fr', 
              includedLanguages: 'ar,fr,en', 
              layout: window.google.translate.TranslateElement.InlineLayout.SIMPLE, 
              autoDisplay: false
          }, 'google_translate_element');
        }
    `;
    doc.head.appendChild(script1);
    
    const script2 = doc.createElement('script');
    script2.id = 'google_translate_script';
    script2.type = 'text/javascript';
    script2.src = '//translate.google.com/translate_a/element.js?cb=googleTranslateElementInit';
    doc.head.appendChild(script2);
    
    const floatingDiv = doc.createElement('div');
    floatingDiv.id = 'google_translate_element';
    floatingDiv.style.position = 'fixed';
    floatingDiv.style.bottom = '20px';
    floatingDiv.style.right = '20px';
    floatingDiv.style.zIndex = '999999';
    floatingDiv.style.background = 'white';
    floatingDiv.style.padding = '5px 10px';
    floatingDiv.style.borderRadius = '8px';
    floatingDiv.style.boxShadow = '0 4px 15px rgba(0,0,0,0.1)';
    floatingDiv.style.fontFamily = 'sans-serif';
    doc.body.appendChild(floatingDiv);
}
</script>
""", height=0, width=0)

# Exécuter la page
pg.run()
