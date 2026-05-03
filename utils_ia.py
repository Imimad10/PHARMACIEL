import google.generativeai as genai
import anthropic
from openai import OpenAI
import streamlit as st
import os
from tinydb import TinyDB, Query

def get_setting(name):
    """Récupère un paramètre depuis la base de données."""
    if os.path.exists('data/db_settings.json'):
        db_settings = TinyDB('data/db_settings.json')
        Setting = Query()
        res = db_settings.search(Setting.name == name)
        if res and res[0]['value']:
            return res[0]['value']
    return None

def ask_ai(prompt, fallback_msg="⚠️ L'IA n'est pas configurée. Allez dans Administration Centrale > Configuration IA."):
    """Envoie un prompt au fournisseur d'IA actif et retourne la réponse."""
    provider = get_setting('active_ai_provider')
    if not provider:
        provider = 'Gemini (Google)' # Défaut
        
    try:
        if provider == 'Gemini (Google)':
            api_key = get_setting('gemini_api_key') or st.secrets.get("GEMINI_API_KEY")
            if not api_key: return fallback_msg
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            response = model.generate_content(prompt)
            return response.text
            
        elif provider == 'Claude (Anthropic)':
            api_key = get_setting('anthropic_api_key') or st.secrets.get("ANTHROPIC_API_KEY")
            if not api_key: return fallback_msg
            client = anthropic.Anthropic(api_key=api_key)
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            return message.content[0].text
            
        elif provider == 'ChatGPT (OpenAI)':
            api_key = get_setting('openai_api_key') or st.secrets.get("OPENAI_API_KEY")
            if not api_key: return fallback_msg
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
            
    except Exception as e:
        return f"Erreur IA ({provider}) : {str(e)}"
    
    return fallback_msg
