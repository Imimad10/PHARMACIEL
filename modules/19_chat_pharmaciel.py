import streamlit as st
import pandas as pd
import json
import os
from utils_ia import ask_ai, is_ia_enabled
from utils_gsheets import load_gs_data

st.set_page_config(page_title="Assistant IA - DarPharm", page_icon="🤖", layout="wide")

if not is_ia_enabled():
    st.error("⚠️ L'Intelligence Artificielle est désactivée. Veuillez contacter un administrateur.")
    st.stop()

st.title("🤖 Ask DarPharm - Votre Assistant Intelligent")
st.write("Posez vos questions sur vos stocks, vos livreurs, ou demandez de l'aide pour rédiger un document. L'IA a accès à la structure de vos données !")

# Charger un résumé léger des bases de données pour donner du contexte à l'IA
@st.cache_data(ttl=3600)
def build_context():
    context = "Tu es l'assistant IA de la plateforme logistique/pharmaceutique 'DarPharm Pro'. Voici un résumé de l'état actuel de l'entreprise :\n"
    
    # 1. Utilisateurs
    try:
        from utils_gsheets import DB_USERS_WORKSHEET, DB_USERS_FALLBACK
        df_u = load_gs_data(DB_USERS_WORKSHEET, DB_USERS_FALLBACK, ["username", "role", "zone", "depot"])
        context += f"- Équipe : {len(df_u)} utilisateurs enregistrés.\n"
    except: pass
    
    # 2. Litiges
    try:
        df_l = load_gs_data("Litiges", "data/data_litiges.csv", ["Statut"])
        en_cours = len(df_l[df_l['Statut'] == 'En cours'])
        context += f"- Litiges Fournisseurs : {en_cours} litiges en cours.\n"
    except: pass

    # 3. Péremptions
    try:
        df_p = load_gs_data("Peremptions", "data/db_peremptions.csv", ["Statut"])
        crit = len(df_p[df_p['Statut'] == 'Alerte Rouge'])
        context += f"- Péremptions : {crit} produits en alerte rouge (périmés ou très proches).\n"
    except: pass

    context += "\nRéponds toujours de manière professionnelle, concise et orientée solution. Si l'utilisateur te demande de rédiger un email, fais-le."
    return context

context = build_context()

# Initialisation de l'historique de chat
if "messages_pharmaciel" not in st.session_state:
    st.session_state.messages_pharmaciel = [
        {"role": "assistant", "content": "Bonjour ! Je suis l'assistant DarPharm. Comment puis-je vous aider aujourd'hui ?"}
    ]

# Affichage des messages
for message in st.session_state.messages_pharmaciel:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Zone de saisie
if prompt := st.chat_input("Posez votre question à l'assistant DarPharm..."):
    # Ajouter message utilisateur
    st.session_state.messages_pharmaciel.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Réponse de l'IA
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        
        # Construction du prompt complet (contexte + historique récent + question)
        full_prompt = context + "\n\nHistorique récent:\n"
        # Prendre les 4 derniers messages pour la mémoire
        for msg in st.session_state.messages_pharmaciel[-5:-1]:
            full_prompt += f"{msg['role'].upper()}: {msg['content']}\n"
        full_prompt += f"\nUSER: {prompt}\nASSISTANT:"

        with st.spinner("L'assistant réfléchit..."):
            response = ask_ai(full_prompt)
            
        message_placeholder.markdown(response)
        
    # Ajouter à l'historique
    st.session_state.messages_pharmaciel.append({"role": "assistant", "content": response})
