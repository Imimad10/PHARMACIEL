"""
Configuration centralisée des établissements : DarPharm & Pharmaciel.
Chaque établissement a son propre Google Sheets, ses propres utilisateurs,
et ses propres rôles/permissions. Les données sont complètement isolées.
"""

# ─── CONFIG PAR ÉTABLISSEMENT ────────────────────────────────────────────────
ETABLISSEMENTS = {
    "darpharm": {
        "id": "darpharm",
        "nom": "DarPharm",
        "nom_complet": "DarPharm® Solutions",
        "subtitle": "Grossiste & Distribution Pharmaceutique",
        "icon": "🏭",
        "emoji": "💊",
        "color_primary": "#1877f2",
        "color_secondary": "#0f3460",
        "color_gradient": "linear-gradient(135deg, #1877f2 0%, #0f3460 100%)",
        "color_bg": "#f0f2f5",
        "gs_url_secret_key": "GS_URL",
        "gs_url_fallback": "https://docs.google.com/spreadsheets/d/1tJDJCtk7cCNSBIfQLKS9J2oH95VcaNMoCVPX8V_cDc/edit",
        "users_worksheet": "Utilisateurs",
        "users_fallback": "data/db_users.json",
        "setup_key": "setup_done_darpharm",
    },
    "pharmaciel": {
        "id": "pharmaciel",
        "nom": "Pharmaciel",
        "nom_complet": "Pharmaciel® Pro",
        "subtitle": "Filiale — Distribution & Répartition",
        "icon": "🏪",
        "emoji": "🌿",
        "color_primary": "#6B46C1",
        "color_secondary": "#2D6A4F",
        "color_gradient": "linear-gradient(135deg, #6B46C1 0%, #2D6A4F 100%)",
        "color_bg": "#f5f0ff",
        "gs_url_secret_key": "GS_URL_PHARMACIEL",
        "gs_url_fallback": None,   # Cloud obligatoire — pas de fallback local
        "users_worksheet": "Utilisateurs",
        "users_fallback": None,    # Idem
        "setup_key": "setup_done_pharmaciel",
    },
}

# ─── UTILISATEURS MULTI-ÉTABLISSEMENTS ───────────────────────────────────────
# Ces utilisateurs peuvent choisir DarPharm OU Pharmaciel au login.
# Tous les autres sont automatiquement redirigés vers leur seul établissement.
MULTI_ETABLISSEMENT_USERNAMES = ["admin_imad", "Imad", "Ayoub", "Islem", "Seif"]

# ─── UTILISATEURS DARPHARM-ONLY (exclus de Pharmaciel) ───────────────────────
DARPHARM_ONLY_USERNAMES = [
    "Karim", "Rami", "Idris", "Aymen", "Kheiro",
    "Rabeh", "Yacine", "Aek", "Aymenk", "Mustapha"
]

# ─── UTILISATEURS PHARMACIEL-ONLY ────────────────────────────────────────────
PHARMACIEL_ONLY_USERNAMES = ["Karime", "Malek"]
