import google.generativeai as genai
import anthropic
from openai import OpenAI
import streamlit as st
import os
from utils_gsheets import load_gs_data

def get_setting(name):
    """Récupère un paramètre depuis la base de données GSheets."""
    WORKSHEET = "Settings"
    FALLBACK = "data/db_settings.csv"
    df = load_gs_data(WORKSHEET, FALLBACK, ["name", "value"])
    if not df.empty:
        res = df[df['name'] == name]
        if not res.empty:
            return str(res['value'].values[0])
    return None

def is_ia_enabled():
    """Vérifie si l'IA est activée globalement dans les réglages."""
    return get_setting('ia_global_enabled') != 'False' # True par défaut

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
            
            # Détection dynamique du meilleur modèle disponible
            try:
                available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                # Priorité : Flash 1.5 -> Pro 1.5 -> Pro 1.0
                target_model = None
                for candidate in ["1.5-flash", "1.5-pro", "gemini-pro"]:
                    match = next((m for m in available_models if candidate in m), None)
                    if match:
                        target_model = match.replace("models/", "")
                        break
                
                if not target_model:
                    target_model = "gemini-1.5-flash"
                
                model = genai.GenerativeModel(target_model)
                response = model.generate_content(prompt)
                return response.text
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "quota" in err_msg.lower():
                    return "⚠️ Quota Gemini épuisé (Limite gratuite atteinte). Veuillez réessayer dans une minute ou utiliser un autre moteur (Claude/OpenAI) dans l'Administration."
                return f"Erreur IA (Gemini - Auto) : {err_msg}"
            
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
            
        elif provider == 'Grok (xAI)':
            api_key = get_setting('grok_api_key') or st.secrets.get("GROK_API_KEY")
            if not api_key: return fallback_msg
            client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
            response = client.chat.completions.create(
                model="grok-beta",
                messages=[{"role": "user", "content": prompt}]
            )
            return response.choices[0].message.content
            
    except Exception as e:
        return f"Erreur IA ({provider}) : {str(e)}"
    
    return fallback_msg
