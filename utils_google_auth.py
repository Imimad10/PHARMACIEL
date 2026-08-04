import streamlit as st
import requests
import urllib.parse


# ─── CREDENTIALS ─────────────────────────────────────────────────────────────
# Les identifiants OAuth2 sont lus UNIQUEMENT depuis st.secrets["google_oauth"].
# Ajoutez dans Streamlit Cloud > App settings > Secrets :
#   [google_oauth]
#   client_id     = "VOTRE_CLIENT_ID.apps.googleusercontent.com"
#   client_secret = "VOTRE_CLIENT_SECRET"
#   redirect_uri  = "https://votre-app.streamlit.app"
_DEFAULT_REDIRECT_URI = "https://darpharmsolutions.streamlit.app"


def get_google_oauth_creds():
    """Retourne (client_id, client_secret, redirect_uri) depuis st.secrets."""
    try:
        if "google_oauth" in st.secrets:
            creds = st.secrets["google_oauth"]
            return (
                creds.get("client_id", ""),
                creds.get("client_secret", ""),
                creds.get("redirect_uri", _DEFAULT_REDIRECT_URI),
            )
    except Exception:
        pass
    return "", "", _DEFAULT_REDIRECT_URI


# ─── GÉNÉRATION URL AUTORISATION ─────────────────────────────────────────────

def get_login_url(state: str = "login") -> str | None:
    """
    Construit l'URL d'autorisation Google OAuth2.
    state = 'login'  → connexion depuis la page d'accueil
    state = 'link'   → liaison depuis le profil d'un utilisateur déjà connecté
    """
    client_id, _, redirect_uri = get_google_oauth_creds()
    if not client_id:
        return None

    params = {
        "client_id":     client_id,
        "redirect_uri":  redirect_uri,
        "response_type": "code",
        "scope":         "openid email profile",
        "access_type":   "online",
        "prompt":        "select_account",
    }
    if state:
        params["state"] = state

    return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"


# ─── ÉCHANGE CODE → USER INFO ─────────────────────────────────────────────────

def get_user_info(code: str) -> tuple[dict | None, str | None]:
    """
    Échange le code d'autorisation contre un access_token,
    puis récupère les infos utilisateur via l'API Google v2.
    Retourne (user_info_dict, error_message_or_None).
    user_info_dict contient au minimum : email, name, picture, sub.
    """
    client_id, client_secret, redirect_uri = get_google_oauth_creds()
    if not client_id:
        return None, "Configuration OAuth2 manquante (client_id absent)."

    # 1. Échange du code contre un token
    token_url = "https://oauth2.googleapis.com/token"
    token_payload = {
        "code":          code,
        "client_id":     client_id,
        "client_secret": client_secret,
        "redirect_uri":  redirect_uri,
        "grant_type":    "authorization_code",
    }
    try:
        token_res = requests.post(token_url, data=token_payload, timeout=10)
        if token_res.status_code != 200:
            return None, f"Erreur Google Token ({token_res.status_code}): {token_res.text[:200]}"
        access_token = token_res.json().get("access_token")
        if not access_token:
            return None, "Aucun access_token reçu de Google."

        # 2. Récupération des infos utilisateur (API v2 — renvoie 'email' garanti)
        userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}
        user_res = requests.get(userinfo_url, headers=headers, timeout=10)
        if user_res.status_code != 200:
            return None, f"Erreur Google UserInfo ({user_res.status_code}): {user_res.text[:200]}"

        user_data = user_res.json()
        if "email" not in user_data:
            return None, "L'API Google n'a pas renvoyé d'email. Vérifiez les scopes OAuth."

        return user_data, None

    except requests.exceptions.Timeout:
        return None, "Délai d'attente dépassé lors de la connexion à Google. Réessayez."
    except Exception as exc:
        return None, f"Erreur interne OAuth2: {exc}"
