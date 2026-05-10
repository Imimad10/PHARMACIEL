import google.generativeai as genai
import os
import streamlit as st
from utils_ia import get_setting

# Use the same logic as the app
api_key = get_setting('gemini_api_key') or st.secrets.get("GEMINI_API_KEY")
if not api_key:
    print("API Key not found")
else:
    genai.configure(api_key=api_key)
    try:
        print("Listing models...")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"Name: {m.name}, Display Name: {m.display_name}")
        
        model_name = "gemini-1.5-flash"
        print(f"\nTrying to initialize model: {model_name}")
        model = genai.GenerativeModel(model_name)
        print("Success initializing model")
        
        # Try a simple generation
        response = model.generate_content("Hello")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
