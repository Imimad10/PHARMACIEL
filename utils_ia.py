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

def is_ia_scanner_enabled():
    """Vérifie si le scanner photo IA est activé."""
    return is_ia_enabled() and get_setting('ia_scanner_enabled') != 'False'

def ask_ai(prompt, fallback_msg="⚠️ L'IA n'est pas configurée. Allez dans Administration Centrale > Configuration IA."):
    """Envoie un prompt au fournisseur d'IA actif et retourne la réponse."""
    provider = get_setting('active_ai_provider')
    if not provider:
        provider = 'OpenRouter' # Défaut
    
    # --- PERSONNALISATION IA PAR ÉTABLISSEMENT ---
    from utils_gsheets import get_active_etablissement
    etab = get_active_etablissement()
    if etab == "pharmaciel":
        system_context = "Tu es l'IA de Pharmaciel Pro, filiale de distribution pharmaceutique. Ton ton est professionnel, précis et orienté vers la répartition de proximité."
    else:
        system_context = "Tu es l'IA de DarPharm Solutions, grossiste répartiteur leader. Ton ton est stratégique, orienté vers la logistique de masse et la performance opérationnelle."
    
    full_prompt = f"{system_context}\n\nQuestion utilisateur : {prompt}"
        
    try:
        if provider == 'Gemini (Google)':
            api_key = get_setting('gemini_api_key') or st.secrets.get("GEMINI_API_KEY")
            if not api_key: return fallback_msg
            import google.generativeai as genai
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
                response = model.generate_content(full_prompt)
                return response.text
            except Exception as e:
                err_msg = str(e)
                if "429" in err_msg or "quota" in err_msg.lower():
                    return "⚠️ Quota Gemini épuisé (Limite gratuite atteinte). Veuillez réessayer dans une minute ou utiliser un autre moteur (Claude/OpenAI) dans l'Administration."
                return f"Erreur IA (Gemini - Auto) : {err_msg}"
            
        elif provider == 'Claude (Anthropic)':
            api_key = get_setting('anthropic_api_key') or st.secrets.get("ANTHROPIC_API_KEY")
            if not api_key: return fallback_msg
            import anthropic
            client = anthropic.Anthropic(api_key=api_key)
            message = client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=1000,
                messages=[{"role": "user", "content": full_prompt}]
            )
            return message.content[0].text
            
        elif provider == 'ChatGPT (OpenAI)':
            api_key = get_setting('openai_api_key') or st.secrets.get("OPENAI_API_KEY")
            if not api_key: return fallback_msg
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": full_prompt}]
            )
            return response.choices[0].message.content
            
        elif provider == 'Grok (xAI)':
            api_key = get_setting('grok_api_key') or st.secrets.get("GROK_API_KEY")
            if not api_key: return fallback_msg
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
            response = client.chat.completions.create(
                model="grok-beta",
                messages=[{"role": "user", "content": full_prompt}]
            )
            return response.choices[0].message.content
            
        elif provider == 'OpenRouter':
            api_key = get_setting('openrouter_api_key') or st.secrets.get("OPENROUTER_API_KEY")
            if not api_key: return fallback_msg
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
            response = client.chat.completions.create(
                model="openai/gpt-4o-mini", # Modèle par défaut pour OpenRouter, très rapide et qualitatif
                messages=[{"role": "user", "content": full_prompt}]
            )
            return response.choices[0].message.content
            
    except Exception as e:
        return f"Erreur IA ({provider}) : {str(e)}"
    
    return fallback_msg

def ask_ai_vision(prompt, base64_image, fallback_msg="⚠️ L'IA Vision n'est pas configurée."):
    """Envoie un prompt et une image base64 au fournisseur d'IA actif (OpenRouter/OpenAI supportés)."""
    provider = get_setting('active_ai_provider')
    if not provider:
        provider = 'OpenRouter'
        
    try:
        if provider in ['OpenRouter', 'ChatGPT (OpenAI)']:
            if provider == 'OpenRouter':
                api_key = get_setting('openrouter_api_key') or st.secrets.get("OPENROUTER_API_KEY")
                base_url = "https://openrouter.ai/api/v1"
                model = "openai/gpt-4o-mini" # Modèle supportant la vision sur OpenRouter
            else:
                api_key = get_setting('openai_api_key') or st.secrets.get("OPENAI_API_KEY")
                base_url = None
                model = "gpt-4o"
                
            if not api_key: return fallback_msg
            
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url=base_url)
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ]
            )
            return response.choices[0].message.content
        else:
            return "⚠️ La vision IA n'est pas encore implémentée pour ce moteur. Veuillez sélectionner OpenRouter ou OpenAI dans l'Admin."
    except Exception as e:
        return f"Erreur IA Vision ({provider}) : {str(e)}"
