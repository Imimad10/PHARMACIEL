import streamlit as st
import requests
import urllib.parse

def get_google_oauth_creds():
    try:
        creds = st.secrets["google_oauth"]
        return creds["client_id"], creds["client_secret"], creds["redirect_uri"]
    except Exception:
        return None, None, None

def get_login_url(state="login"):
    client_id, _, redirect_uri = get_google_oauth_creds()
    if not client_id:
        return None
    auth_url = "https://accounts.google.com/o/oauth2/v2/auth"
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account"
    }
    return f"{auth_url}?{urllib.parse.urlencode(params)}"

def get_user_info(code):
    client_id, client_secret, redirect_uri = get_google_oauth_creds()
    if not client_id:
        return None, "Configuration OAuth manquante dans les Secrets."

    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }
    try:
        res = requests.post(token_url, data=data)
        if res.status_code != 200:
            return None, f"Erreur Google Auth (Token): {res.text}"
        access_token = res.json().get("access_token")

        userinfo_url = "https://www.googleapis.com/oauth2/v3/userinfo"
        headers = {"Authorization": f"Bearer {access_token}"}
        user_res = requests.get(userinfo_url, headers=headers)
        if user_res.status_code != 200:
            return None, f"Erreur Google Auth (UserInfo): {user_res.text}"
        
        return user_res.json(), None
    except Exception as e:
        return None, f"Erreur interne OAuth2: {str(e)}"
