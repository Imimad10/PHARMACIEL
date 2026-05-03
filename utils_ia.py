import google.generativeai as genai
import streamlit as st
import os
from tinydb import TinyDB, Query

def get_gemini_model():
    """Configure and return the Gemini 1.5 Flash model."""
    api_key = None
    
    # 1. Vérifier la configuration Administrateur (Base de données)
    if os.path.exists('data/db_settings.json'):
        db_settings = TinyDB('data/db_settings.json')
        Setting = Query()
        ia_setting = db_settings.search(Setting.name == 'gemini_api_key')
        if ia_setting and ia_setting[0]['value']:
            api_key = ia_setting[0]['value']

    # 2. Secours : Vérifier les secrets Streamlit
    if not api_key:
        try:
            api_key = st.secrets.get("GEMINI_API_KEY")
        except:
            pass

    if not api_key:
        return None
        
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-1.5-flash-latest')

def ask_ai(prompt, fallback_msg="⚠️ L'IA n'est pas configurée. Allez dans Administration Centrale > Configuration IA."):
    """Sends a text prompt to Gemini and returns the response."""
    model = get_gemini_model()
    if not model:
        return fallback_msg
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Erreur IA : {str(e)}"
