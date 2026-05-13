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
    Injecte le CSS du thème dans la page Streamlit via st.markdown.
    """
    if not theme:
        return
    vars_css = "\n".join(
        f"    {k}: {v};" for k, v in theme.get("css_vars", {}).items()
    )
    accent = theme.get("accent_color", "#4f8ef7")
    bg = theme.get("preview_color", "#1a1a2e")

    css = f"""
<style>
    /* === THEME: {theme.get('name', 'Default')} === */
    :root {{
{vars_css}
    }}

    /* App background */
    .stApp {{
        background-color: var(--bg-main, {bg}) !important;
        color: var(--text-primary, #eaeaea) !important;
    }}

    /* Sidebar */
    section[data-testid="stSidebar"] {{
        background-color: var(--bg-sidebar, {bg}) !important;
    }}
    section[data-testid="stSidebar"] * {{
        color: var(--text-primary, #eaeaea) !important;
    }}

    /* Cards / Containers */
    div[data-testid="stVerticalBlock"] > div[style*="background"],
    div.stMetric, div[data-testid="metric-container"] {{
        background-color: var(--bg-card, rgba(255,255,255,0.05)) !important;
        border-radius: 12px;
        padding: 8px;
    }}

    /* Buttons */
    .stButton > button {{
        background-color: var(--accent, {accent}) !important;
        color: #fff !important;
        border: none !important;
        border-radius: 8px !important;
        transition: background 0.2s ease;
    }}
    .stButton > button:hover {{
        background-color: var(--accent-hover, {accent}) !important;
        filter: brightness(1.1);
    }}

    /* Tabs */
    .stTabs [data-baseweb="tab"] {{
        color: var(--text-secondary, #a0aec0) !important;
    }}
    .stTabs [data-baseweb="tab"][aria-selected="true"] {{
        color: var(--accent, {accent}) !important;
        border-bottom-color: var(--accent, {accent}) !important;
    }}

    /* Text */
    p, h1, h2, h3, h4, label, span, .stMarkdown {{
        color: var(--text-primary, #eaeaea) !important;
    }}

    /* Inputs */
    .stTextInput input, .stSelectbox select, .stTextArea textarea {{
        background-color: var(--bg-card, rgba(255,255,255,0.05)) !important;
        color: var(--text-primary, #eaeaea) !important;
        border-color: var(--accent, {accent}) !important;
        border-radius: 8px;
    }}

    /* DataFrames */
    .stDataFrame {{
        border-radius: 10px;
        overflow: hidden;
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
