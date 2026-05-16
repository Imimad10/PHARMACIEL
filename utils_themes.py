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
        },
        {
            "id": "theme_usmh_yellow",
            "name": "USMH - El Harrach",
            "description": "Jaune et Noir — L'esprit de Maison Carrée",
            "preview_color": "#facc15",
            "accent_color": "#facc15",
            "active": True,
            "css_vars": {
                "--bg-main": "#111827",
                "--bg-sidebar": "#000000",
                "--bg-card": "#1f2937",
                "--text-primary": "#ffffff",
                "--text-secondary": "#9ca3af",
                "--accent": "#facc15",
                "--accent-hover": "#eab308"
            }
        },
        {
            "id": "theme_crb_red",
            "name": "CRB - Belouizdad",
            "description": "Rouge et Blanc — Le Chabab de Laquiba",
            "preview_color": "#dc2626",
            "accent_color": "#dc2626",
            "active": True,
            "css_vars": {
                "--bg-main": "#ffffff",
                "--bg-sidebar": "#dc2626",
                "--bg-card": "#fee2e2",
                "--text-primary": "#111827",
                "--text-secondary": "#4b5563",
                "--accent": "#dc2626",
                "--accent-hover": "#b91c1c"
            }
        },
        {
            "id": "theme_usma_black_red",
            "name": "USMA - Alger",
            "description": "Noir et Rouge — Soustara et les Rouge et Noir",
            "preview_color": "#000000",
            "accent_color": "#ef4444",
            "active": True,
            "css_vars": {
                "--bg-main": "#000000",
                "--bg-sidebar": "#111827",
                "--bg-card": "#ef444422",
                "--text-primary": "#ffffff",
                "--text-secondary": "#d1d5db",
                "--accent": "#ef4444",
                "--accent-hover": "#dc2626"
            }
        },
        {
            "id": "theme_executive_white",
            "name": "Executive White",
            "description": "Thème blanc pur — Style Apple, épuré et ultra-professionnel",
            "preview_color": "#ffffff",
            "accent_color": "#7c3aed",
            "active": True,
            "css_vars": {
                "--bg-main": "#f8f9fa",
                "--bg-sidebar": "#ffffff",
                "--bg-card": "#ffffff",
                "--text-primary": "#1d1d1f",
                "--text-secondary": "#6e6e73",
                "--accent": "#7c3aed",
                "--accent-hover": "#5b21b6",
                "--sidebar-header": "#1d1d1f",
                "--sidebar-text": "#1d1d1f",
                "--shadow-neu": "0 10px 30px rgba(0,0,0,0.03)",
                "--shadow-neu-inset": "inset 0 2px 4px rgba(0,0,0,0.05)"
            }
        },
        {
            "id": "theme_glass_pro",
            "name": "Glass Pro",
            "description": "Effet Glassmorphism — Transparence, flou et modernité",
            "preview_color": "#e2e8f0",
            "accent_color": "#3b82f6",
            "active": True,
            "css_vars": {
                "--bg-main": "linear-gradient(135deg, #f0f4f8 0%, #d9e2ec 100%)",
                "--bg-sidebar": "rgba(255, 255, 255, 0.4)",
                "--bg-card": "rgba(255, 255, 255, 0.6)",
                "--text-primary": "#102a43",
                "--text-secondary": "#334e68",
                "--accent": "#3b82f6",
                "--accent-hover": "#2563eb",
                "--backdrop-blur": "20px",
                "--shadow-neu": "0 8px 32px 0 rgba(31, 38, 135, 0.1)"
            }
        },
        {
            "id": "theme_midnight_gold",
            "name": "Midnight Gold",
            "description": "Thème luxueux — Bleu minuit et or pour un rendu prestige",
            "preview_color": "#0f172a",
            "accent_color": "#fbbf24",
            "active": True,
            "css_vars": {
                "--bg-main": "#0f172a",
                "--bg-sidebar": "#1e293b",
                "--bg-card": "#1e293b",
                "--text-primary": "#f8fafc",
                "--text-secondary": "#94a3b8",
                "--accent": "#fbbf24",
                "--accent-hover": "#f59e0b",
                "--sidebar-header": "#fbbf24",
                "--shadow-neu": "0 10px 25px rgba(0,0,0,0.4)"
            }
        },
        {
            "id": "theme_nordic_clean",
            "name": "Nordic Clean",
            "description": "Minimalisme nordique — Tons gris, bleus froids et clarté",
            "preview_color": "#f1f5f9",
            "accent_color": "#64748b",
            "active": True,
            "css_vars": {
                "--bg-main": "#f8fafc",
                "--bg-sidebar": "#f1f5f9",
                "--bg-card": "#ffffff",
                "--text-primary": "#334155",
                "--text-secondary": "#64748b",
                "--accent": "#64748b",
                "--accent-hover": "#475569",
                "--shadow-neu": "0 1px 3px rgba(0,0,0,0.12)"
            }
        },
        {
            "id": "theme_mca_green_red",
            "name": "MCA - Mouloudia",
            "description": "Vert et Rouge — Le Doyen d'Algérie",
            "preview_color": "#16a34a",
            "accent_color": "#16a34a",
            "active": True,
            "css_vars": {
                "--bg-main": "#064e3b",
                "--bg-sidebar": "#991b1b",
                "--bg-card": "#065f46",
                "--text-primary": "#ffffff",
                "--text-secondary": "#d1fae5",
                "--accent": "#16a34a",
                "--accent-hover": "#15803d"
            }
        },
        {
            "id": "theme_pharmaciel_luxe",
            "name": "Pharmaciel Luxe",
            "description": "Signature Pharmaciel — Dégradé Violet & Vert avec effet Glassmorphism",
            "preview_color": "#6B46C1",
            "accent_color": "#10B981",
            "active": True,
            "css_vars": {
                "--bg-main": "linear-gradient(135deg, #2D1B69 0%, #064E3B 100%)",
                "--bg-sidebar": "rgba(255, 255, 255, 0.05)",
                "--bg-card": "rgba(255, 255, 255, 0.1)",
                "--text-primary": "#FFFFFF",
                "--text-secondary": "#A7F3D0",
                "--accent": "#10B981",
                "--accent-hover": "#34D399",
                "--backdrop-blur": "25px",
                "--sidebar-header": "#10B981",
                "--shadow-neu": "0 10px 40px rgba(0,0,0,0.3)"
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
        --sidebar-header-color: {v.get('--sidebar-header', accent)};
        --sidebar-text-color: {v.get('--sidebar-text', v.get('--text-primary', '#1a1f3c'))};
        --backdrop-blur: {v.get('--backdrop-blur', '0px')};
    }}

    .stApp {{
        background: var(--bg-main) !important;
        background-color: var(--bg-main) !important;
        font-family: var(--font) !important;
    }}

    [data-testid="stSidebar"] {{
        background-color: var(--bg-sidebar) !important;
        backdrop-filter: blur(var(--backdrop-blur)) !important;
        -webkit-backdrop-filter: blur(var(--backdrop-blur)) !important;
        border-right: 1px solid rgba(0,0,0,0.05) !important;
        box-shadow: 4px 0 15px rgba(0,0,0,0.03) !important;
    }}

    /* --- EFFET NEUMORPHIC SUR LES METRICS --- */
    [data-testid="stMetric"], .stMetric {{
        background-color: var(--bg-card) !important;
        border-radius: 20px !important;
        padding: 20px !important;
        box-shadow: var(--shadow-neu) !important;
        border: 1px solid rgba(255,255,255,0.1) !important;
        margin-bottom: 15px !important;
    }}

    /* --- BOUTONS --- */
    .stButton > button {{
        background: linear-gradient(135deg, var(--accent), var(--accent-h)) !important;
        color: white !important;
        border: none !important;
        border-radius: 15px !important;
        padding: 12px 25px !important;
        font-weight: 800 !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1) !important;
        transition: all 0.3s ease !important;
    }}

    .stButton > button:hover {{
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 25px rgba(0,0,0,0.15) !important;
    }}

    /* --- INPUTS --- */
    .stTextInput input, .stSelectbox select, .stNumberInput input {{
        background-color: var(--bg-card) !important;
        border: 1px solid rgba(0,0,0,0.05) !important;
        border-radius: 12px !important;
        color: var(--text-p) !important;
        padding: 12px !important;
    }}

    /* --- SIDEBAR CUSTOMIZATION --- */
    [data-testid="stSidebarNav"] {{
        padding-top: 20px !important;
    }}

    /* Section Headers */
    [data-testid="stSidebarNav"] li div {{
        background: transparent !important;
        padding: 25px 15px 8px 15px !important;
        color: var(--sidebar-header-color) !important;
        font-weight: 900 !important;
        font-size: 0.75rem !important;
        text-transform: uppercase !important;
        letter-spacing: 2px !important;
        border: none !important;
        opacity: 0.9 !important;
    }}

    /* Navigation Items (Links) */
    [data-testid="stSidebarNav"] li a {{
        background: transparent !important;
        border-radius: 12px !important;
        margin: 4px 12px !important;
        padding: 10px 15px !important;
        transition: all 0.2s ease !important;
        color: var(--sidebar-text-color) !important;
        text-decoration: none !important;
    }}

    [data-testid="stSidebarNav"] li a span {{
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        color: var(--sidebar-text-color) !important;
    }}

    /* Hover State */
    [data-testid="stSidebarNav"] li a:hover {{
        background: rgba(0,0,0,0.03) !important;
        transform: translateX(5px);
    }}

    /* Active Page State */
    [data-testid="stSidebarNav"] li a[aria-current="page"] {{
        background: var(--accent) !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
    }}
    
    [data-testid="stSidebarNav"] li a[aria-current="page"] span {{
        font-weight: 800 !important;
        color: white !important;
    }}

    /* Force visibility of h1, h2, h3 */
    h1, h2, h3 {{
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
