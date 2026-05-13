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
            "id": "theme_sunset",
            "name": "Sunset Orange",
            "description": "Thème chaleureux — tons orangés et dynamiques",
            "preview_color": "#431407",
            "accent_color": "#f97316",
            "active": False,
            "css_vars": {
                "--bg-main": "#431407",
                "--bg-sidebar": "#7c2d12",
                "--bg-card": "#9a3412",
                "--text-primary": "#fff7ed",
                "--text-secondary": "#fed7aa",
                "--accent": "#f97316",
                "--accent-hover": "#ea580c"
            }
        }
    ],
    "user_theme_assignments": {}
}


def load_themes_db() -> dict:
    """Charge la base de données des thèmes depuis le fichier JSON."""
    if os.path.exists(THEMES_DB_PATH):
        try:
            with open(THEMES_DB_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                # S'assurer que les clés nécessaires existent
                if "themes" not in data:
                    data["themes"] = THEMES_DEFAULT["themes"]
                if "user_theme_assignments" not in data:
                    data["user_theme_assignments"] = {}
                return data
        except Exception:
            pass
    return THEMES_DEFAULT.copy()


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
    
    # Construction d'un CSS complet et "agressif" (!important partout pour gagner sur Streamlit)
    css = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap');

    :root {{
        --bg-main: {v.get('--bg-main', bg)};
        --bg-sidebar: {v.get('--bg-sidebar', bg)};
        --bg-card: {v.get('--bg-card', 'rgba(255,255,255,0.05)')};
        --text-p: {v.get('--text-primary', '#f8fafc')};
        --text-s: {v.get('--text-secondary', '#94a3b8')};
        --accent: {accent};
        --accent-h: {v.get('--accent-hover', accent)};
        --font: 'Plus Jakarta Sans', sans-serif;
    }}

    /* --- FOND GLOBAL --- */
    .stApp {{
        background-color: var(--bg-main) !important;
        background-image: none !important;
        font-family: var(--font) !important;
    }}

    /* --- SIDEBAR --- */
    [data-testid="stSidebar"] {{
        background-color: var(--bg-sidebar) !important;
        border-right: 1px solid rgba(255,255,255,0.05) !important;
    }}
    [data-testid="stSidebar"] * {{
        color: var(--text-p) !important;
        font-family: var(--font) !important;
    }}
    [data-testid="stSidebarNav"] span {{
        color: var(--text-p) !important;
    }}

    /* --- TEXTES & TITRES --- */
    h1, h2, h3, h4, h5, h6, p, label, span, li {{
        color: var(--text-p) !important;
        font-family: var(--font) !important;
    }}
    .stMarkdown {{ color: var(--text-p) !important; }}
    small {{ color: var(--text-s) !important; }}

    /* --- BOUTONS --- */
    .stButton > button {{
        background: var(--accent) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0.6rem 1.2rem !important;
        font-weight: 700 !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
        width: 100%;
    }}
    .stButton > button:hover {{
        background: var(--accent-h) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 20px rgba(0,0,0,0.2) !important;
    }}

    /* --- INPUTS & WIDGETS --- */
    .stTextInput input, .stSelectbox select, .stTextArea textarea, .stNumberInput input {{
        background-color: var(--bg-card) !important;
        color: var(--text-p) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        border-radius: 10px !important;
        padding: 10px !important;
    }}
    .stTextInput input:focus {{
        border-color: var(--accent) !important;
        box-shadow: 0 0 0 2px var(--accent) !important;
    }}

    /* --- CARTES & METRICS --- */
    [data-testid="stMetric"], .stMetric {{
        background-color: var(--bg-card) !important;
        border: 1px solid rgba(255,255,255,0.05) !important;
        border-radius: 16px !important;
        padding: 15px !important;
    }}
    [data-testid="stMetricValue"] {{
        color: var(--accent) !important;
        font-weight: 800 !important;
    }}

    /* --- TABLEAUX --- */
    .stDataFrame, [data-testid="stTable"] {{
        background-color: var(--bg-card) !important;
        border-radius: 12px !important;
        border: 1px solid rgba(255,255,255,0.05) !important;
    }}

    /* --- TABS --- */
    .stTabs [data-baseweb="tab-list"] {{
        background-color: transparent !important;
        gap: 10px !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        background-color: var(--bg-card) !important;
        border-radius: 8px 8px 0 0 !important;
        color: var(--text-s) !important;
        border: none !important;
    }}
    .stTabs [data-baseweb="tab"][aria-selected="true"] {{
        color: var(--accent) !important;
        border-bottom: 3px solid var(--accent) !important;
    }}

    /* --- SCROLLBARS --- */
    ::-webkit-scrollbar {{ width: 8px; height: 8px; }}
    ::-webkit-scrollbar-track {{ background: var(--bg-main); }}
    ::-webkit-scrollbar-thumb {{ background: var(--accent); border-radius: 10px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: var(--accent-h); }}

    /* Correction pour les boites de dialogue */
    .stDialog > div:first-child {{
        background-color: var(--bg-main) !important;
        border: 1px solid var(--accent) !important;
    }}
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
