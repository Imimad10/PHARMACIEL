"""
utils_themes.py — Gestion centralisée des thèmes PHARMACIEL
Charge, sauvegarde et applique les thèmes à l'application.
"""
import json
import os
import streamlit as st

THEMES_DB_PATH = "data/db_themes.json"

THEMES_DEFAULT = {
    "themes": [
        {
            "id": "theme_dark_pro",
            "name": "Dark Pro",
            "description": "Thème sombre professionnel — parfait pour les longues sessions",
            "preview_color": "#1a1a2e",
            "accent_color": "#4f8ef7",
            "active": True,
            "css_vars": {
                "--bg-main": "#1a1a2e",
                "--bg-sidebar": "#16213e",
                "--bg-card": "#0f3460",
                "--text-primary": "#eaeaea",
                "--text-secondary": "#a0aec0",
                "--accent": "#4f8ef7",
                "--accent-hover": "#3a7bd5"
            }
        },
        {
            "id": "theme_light_clean",
            "name": "Light Clean",
            "description": "Thème clair et épuré — idéal pour les présentations",
            "preview_color": "#ffffff",
            "accent_color": "#2563eb",
            "active": True,
            "css_vars": {
                "--bg-main": "#f8fafc",
                "--bg-sidebar": "#ffffff",
                "--bg-card": "#ffffff",
                "--text-primary": "#1e293b",
                "--text-secondary": "#64748b",
                "--accent": "#2563eb",
                "--accent-hover": "#1d4ed8"
            }
        },
        {
            "id": "theme_pharma_green",
            "name": "Pharma Green",
            "description": "Thème vert pharmaceutique — couleurs du secteur médical",
            "preview_color": "#064e3b",
            "accent_color": "#10b981",
            "active": True,
            "css_vars": {
                "--bg-main": "#064e3b",
                "--bg-sidebar": "#065f46",
                "--bg-card": "#047857",
                "--text-primary": "#ecfdf5",
                "--text-secondary": "#a7f3d0",
                "--accent": "#10b981",
                "--accent-hover": "#059669"
            }
        },
        {
            "id": "theme_violet_premium",
            "name": "Violet Premium",
            "description": "Thème violet luxueux — pour un look haut de gamme",
            "preview_color": "#2d1b69",
            "accent_color": "#8b5cf6",
            "active": False,
            "css_vars": {
                "--bg-main": "#2d1b69",
                "--bg-sidebar": "#3b2380",
                "--bg-card": "#4c2f95",
                "--text-primary": "#f5f3ff",
                "--text-secondary": "#ddd6fe",
                "--accent": "#8b5cf6",
                "--accent-hover": "#7c3aed"
            }
        },
        {
            "id": "theme_darpharm_fluffy",
            "name": "DarPharm Fluffy",
            "description": "Style Neumorphism doux — Ombre 3D et couleurs pastel",
            "preview_color": "#eef0f8",
            "accent_color": "#5b6cf9",
            "active": True,
            "css_vars": {
                "--bg-main": "#eef0f8",
                "--bg-sidebar": "#eef0f8",
                "--bg-card": "#eef0f8",
                "--text-primary": "#1a1f3c",
                "--text-secondary": "#6b7299",
                "--accent": "#5b6cf9",
                "--accent-hover": "#3a47d5",
                "--shadow-neu": "7px 7px 18px #c0c5dc, -7px -7px 18px #ffffff",
                "--shadow-neu-inset": "inset 4px 4px 12px #c0c5dc, inset -4px -4px 12px #ffffff"
            }
        }
    ],
    "user_theme_assignments": {}
}


def load_themes_db() -> dict:
    """Charge la base de données des thèmes et fusionne les nouveaux thèmes par défaut."""
    data = THEMES_DEFAULT.copy()
    if os.path.exists(THEMES_DB_PATH):
        try:
            with open(THEMES_DB_PATH, "r", encoding="utf-8") as f:
                file_data = json.load(f)
                # Fusionner les thèmes du fichier avec ceux par défaut
                existing_ids = [t["id"] for t in data["themes"]]
                for t in file_data.get("themes", []):
                    if t["id"] not in existing_ids:
                        data["themes"].append(t)
                    else:
                        # Mettre à jour les thèmes existants (optionnel, selon besoin)
                        idx = existing_ids.index(t["id"])
                        data["themes"][idx] = t
                
                if "user_theme_assignments" in file_data:
                    data["user_theme_assignments"] = file_data["user_theme_assignments"]
        except Exception:
            pass
    return data


def save_themes_db(data: dict):
    """Sauvegarde la base de données des thèmes."""
    try:
        os.makedirs(os.path.dirname(THEMES_DB_PATH), exist_ok=True)
        with open(THEMES_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Erreur sauvegarde thèmes : {e}")


def get_active_themes(data: dict) -> list:
    """Retourne la liste des thèmes actifs."""
    return [t for t in data.get("themes", []) if t.get("active", False)]


def get_user_theme(username: str, data: dict) -> dict | None:
    """
    Retourne le thème EXPLICITEMENT affecté à un utilisateur.
    Retourne None si aucune affectation individuelle n'existe.
    (Pas de fallback vers un thème par défaut — le thème statique de l'app reste actif.)
    """
    assignments = data.get("user_theme_assignments", {})
    theme_id = assignments.get(username)

    if not theme_id:
        return None  # Aucune affectation → on ne touche pas au thème existant

    for t in data.get("themes", []):
        if t["id"] == theme_id and t.get("active", False):
            return t

    return None  # Thème assigné mais désactivé → on ne force rien non plus


def apply_theme_css(theme: dict):
    """
    Injecte le CSS du thème dans la page Streamlit pour un changement TOTAL.
    Couvre la sidebar, le fond, les boutons, les inputs, les tableaux et les textes.
    """
    if not theme:
        return
    
    v = theme.get("css_vars", {})
    accent = theme.get("accent_color", "#4f8ef7")
    bg = theme.get("preview_color", "#0f111a")
    
    css = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800;900&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200');

    :root {{
        --bg-main: {v.get('--bg-main', bg)};
        --bg-sidebar: {v.get('--bg-sidebar', bg)};
        --bg-card: {v.get('--bg-card', 'rgba(255,255,255,0.05)')};
        --text-p: {v.get('--text-primary', '#1a1f3c')};
        --text-s: {v.get('--text-secondary', '#6b7299')};
        --accent: {accent};
        --accent-h: {v.get('--accent-hover', accent)};
        --font: 'Nunito', sans-serif;
        --shadow-neu: {v.get('--shadow-neu', '0 4px 12px rgba(0,0,0,0.1)')};
        --shadow-neu-inset: {v.get('--shadow-neu-inset', 'none')};
    }}

    .stApp {{
        background-color: var(--bg-main) !important;
        font-family: var(--font) !important;
    }}

    [data-testid="stSidebar"] {{
        background-color: var(--bg-sidebar) !important;
        border-right: 2px solid #d0d4e8 !important;
        box-shadow: 4px 0 15px rgba(0,0,0,0.05) !important;
    }}

    /* --- EFFET NEUMORPHIC SUR LES CARTES ET METRICS --- */
    [data-testid="stMetric"], .stMetric, .stMarkdown div[data-testid="stVerticalBlock"] > div {{
        background-color: var(--bg-card) !important;
        border-radius: 20px !important;
        padding: 20px !important;
        box-shadow: var(--shadow-neu) !important;
        border: none !important;
        margin-bottom: 15px !important;
    }}

    /* --- BOUTONS FLUFFY --- */
    .stButton > button {{
        background: linear-gradient(135deg, var(--accent), var(--accent-h)) !important;
        color: white !important;
        border: none !important;
        border-radius: 15px !important;
        padding: 12px 25px !important;
        font-weight: 800 !important;
        box-shadow: 4px 4px 10px rgba(91,108,249,0.3), -2px -2px 8px rgba(255,255,255,0.8) !important;
        transition: all 0.2s ease !important;
    }}

    .stButton > button:active {{
        transform: scale(0.97) !important;
        box-shadow: inset 3px 3px 8px rgba(0,0,0,0.2) !important;
    }}

    /* --- INPUTS INSET --- */
    .stTextInput input, .stSelectbox select, .stNumberInput input {{
        background-color: var(--bg-main) !important;
        box-shadow: var(--shadow-neu-inset) !important;
        border: none !important;
        border-radius: 12px !important;
        color: var(--text-p) !important;
        padding: 12px !important;
    }}

    /* --- CACHER LE MENU STREAMLIT (Look APK/App) --- */
    #MainMenu {visibility: hidden; display: none !important;}
    header {visibility: hidden; display: none !important;}
    footer {visibility: hidden; display: none !important;}
    [data-testid="stHeader"] {display: none !important;}
    [data-testid="stDecoration"] {display: none !important;}
    [data-testid="stStatusWidget"] {display: none !important;}
    .stDeployButton {display: none !important;}

    /* --- MOBILE RESPONSIVE TWEAKS --- */
    @media (max-width: 768px) {
        .main .block-container {
            padding: 1rem 0.5rem !important;
        }
        [data-testid="stMetric"] {
            padding: 12px !important;
        }
        .stButton > button {
            width: 100% !important;
            min-height: 48px !important;
            font-size: 16px !important;
        }
        /* Masquer certains éléments inutiles sur mobile pour gagner de la place */
        [data-testid="stSidebarNavSeparator"] {
            display: none !important;
        }
    }

    /* --- TITRES GRADIENT --- */
    h1, h2, h3 {{
        background: linear-gradient(135deg, #5b6cf9, #9b6fd4, #1ab8c4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: initial !important; /* Fix for invisible icons/text */
        color: var(--accent) !important;
        font-weight: 900 !important;
    }}

    /* Style for Material Icons to ensure they are visible and properly sized */
    .material-symbols-outlined {{
        font-variation-settings: 'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 24;
        vertical-align: middle;
        margin-right: 8px;
    }}
</style>

<!-- SPLASH SCREEN ANIMATION (APK Style) -->
<div id="app-splash-screen" style="position:fixed; inset:0; z-index:999999; background: #eef0f8; display:flex; flex-direction:column; align-items:center; justify-content:center; animation: fadeOutSplash 1s forwards 2.5s;">
    <div style="font-size: 80px; animation: pulseLogo 1.5s infinite;">💊</div>
    <h1 style="color: #1a1f3c; font-family: 'Nunito', sans-serif; font-weight: 900; margin-top: 20px;">DARPHARM PRO</h1>
    <p style="color: #6b7299; font-family: 'Nunito', sans-serif; font-weight: 700;">Initialisation sécurisée...</p>
    <div style="width: 200px; height: 4px; background: #d0d4e8; border-radius: 2px; overflow: hidden; margin-top: 20px;">
        <div style="width: 0%; height: 100%; background: #5b6cf9; animation: loadProgress 2.2s ease-in-out forwards;"></div>
    </div>
</div>

<script>
    setTimeout(function() {
        var splash = document.getElementById('app-splash-screen');
        if (splash) splash.style.display = 'none';
    }, 3500);
</script>

<style>
    @keyframes fadeOutSplash {{ from {{ opacity: 1; visibility: visible; }} to {{ opacity: 0; visibility: hidden; }} }}
    @keyframes pulseLogo {{ 0% {{ transform: scale(1); }} 50% {{ transform: scale(1.1); }} 100% {{ transform: scale(1); }} }}
    @keyframes loadProgress {{ 0% {{ width: 0%; }} 100% {{ width: 100%; }} }}
</style>
"""
    st.markdown(css, unsafe_allow_html=True)


def apply_user_theme(username: str):
    """
    Applique le thème personnalisé de l'utilisateur SEULEMENT s'il en a
    un affecté explicitement dans l'Admin Centrale.
    Si aucun thème n'est affecté, on ne fait rien pour ne pas écraser
    le thème statique de l'application (Clair, Sombre, Chic Animé…).
    """
    if not username:
        return
    data = load_themes_db()
    theme = get_user_theme(username, data)  # None si pas d'affectation explicite
    if theme:  # On n'applique le CSS que si une affectation existe
        apply_theme_css(theme)


def set_user_theme(username: str, theme_id: str, data: dict) -> dict:
    """Affecte un thème à un utilisateur et retourne la base mise à jour."""
    data.setdefault("user_theme_assignments", {})[username] = theme_id
    return data


def remove_user_theme(username: str, data: dict) -> dict:
    """Supprime l'affectation de thème d'un utilisateur (revient au défaut)."""
    data.setdefault("user_theme_assignments", {}).pop(username, None)
    return data


def toggle_theme_active(theme_id: str, data: dict) -> dict:
    """Active ou désactive un thème dans la base."""
    for t in data.get("themes", []):
        if t["id"] == theme_id:
            t["active"] = not t.get("active", False)
            break
    return data


def save_premium_dashboard_html(file_bytes: bytes, filename: str = "dashboard_premium.html") -> str:
    """
    Sauvegarde le fichier HTML du dashboard premium dans le dossier assets/.
    Retourne le chemin absolu du fichier sauvegardé.
    """
    assets_dir = os.path.join(os.getcwd(), "assets")
    os.makedirs(assets_dir, exist_ok=True)
    dest_path = os.path.join(assets_dir, filename)
    with open(dest_path, "wb") as f:
        f.write(file_bytes)
    return dest_path

def show_success_animation(title="Action Réussie !", message="Vos données ont été enregistrées avec succès."):
    """Affiche une animation de succès Premium avec confettis."""
    st.markdown(f"""
    <div id="successOverlay" style="position:fixed;inset:0;z-index:99999;background:rgba(238,240,248,0.9);display:flex;flex-direction:column;align-items:center;justify-content:center;font-family:'Nunito',sans-serif;animation:fadeIn 0.5s forwards;">
        <div style="font-size:80px;margin-bottom:20px;filter:drop-shadow(0 10px 20px rgba(0,0,0,0.1));animation:bounce 1s infinite alternate;">✅</div>
        <h2 style="color:#1e1a5e;font-weight:900;margin:0;text-align:center;">{title}</h2>
        <p style="color:#6b7299;font-weight:700;text-align:center;padding:0 20px;">{message}</p>
        <button onclick="this.parentElement.style.display='none'" style="margin-top:30px;background:linear-gradient(135deg,#5b6cf9,#3a47d5);color:white;border:none;padding:12px 40px;border-radius:15px;font-weight:900;cursor:pointer;box-shadow:0 10px 20px rgba(91,108,249,0.3);transition:all 0.2s;">CONTINUER</button>
    </div>
    <style>
        @keyframes fadeIn {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
        @keyframes bounce {{ from {{ transform: translateY(0); }} to {{ transform: translateY(-20px); }} }}
    </style>
    """, unsafe_allow_html=True)
    st.balloons()
