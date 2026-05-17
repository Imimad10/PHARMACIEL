import streamlit as st
import pandas as pd
import json
import os
from utils_ia import ask_ai, is_ia_enabled
from utils_gsheets import load_gs_data
from utils_sound import play_sound

st.set_page_config(page_title="Assistant IA - DarPharm", page_icon="🤖", layout="wide")

if not is_ia_enabled():
    st.error("⚠️ L'Intelligence Artificielle est désactivée. Veuillez contacter un administrateur.")
    st.stop()

st.title("🤖 Ask DarPharm - Votre Assistant Intelligent")
st.write("Posez vos questions sur vos stocks, vos livreurs, ou demandez de l'aide pour rédiger un document. L'IA a accès à la structure de vos données !")

# Charger un résumé léger des bases de données pour donner du contexte à l'IA
@st.cache_data(ttl=3600)
def build_context():
    context = "Tu es l'assistant IA stratégique de la plateforme 'DarPharm Solution'. Voici un état des lieux de l'entreprise :\n"
    
    # 1. Utilisateurs
    try:
        from utils_gsheets import DB_USERS_WORKSHEET, DB_USERS_FALLBACK
        df_u = load_gs_data(DB_USERS_WORKSHEET, DB_USERS_FALLBACK, ["username", "role"])
        context += f"- Ressources Humaines : {len(df_u)} collaborateurs.\n"
    except: pass
    
    # 2. Recouvrement
    try:
        df_r = load_gs_data("Recouvrement", "data_recouvrement.csv", ["Reste à payer", "Statut"])
        if not df_r.empty:
            df_r['Reste à payer'] = pd.to_numeric(df_r['Reste à payer'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
            total_du = df_r['Reste à payer'].sum()
            context += f"- Finances : Total à recouvrer de {total_du:,.2f} DA.\n"
    except: pass

    # 3. Inventaire
    try:
        df_i = load_gs_data("Saisie_Inventaire", "data_inventaire/saisie.csv", ["designation"])
        context += f"- Inventaire : {len(df_i)} lignes saisies en stock.\n"
    except: pass

    # 4. Clients
    try:
        df_c = load_gs_data("Base_Clients", "base_clients.csv", ["Nom Client"])
        context += f"- Clients : Portefeuille de {len(df_c)} clients.\n"
    except: pass

    # 5. Pointages
    try:
        df_p = load_gs_data("Pointages", "data/db_pointages.csv", ["reference"])
        context += f"- Logistique : {len(df_p)} factures pointées à ce jour.\n"
    except: pass

    # 6. Master Inventaire & IA Médicale Intégrée
    try:
        df_master = load_gs_data("Master_Inventaire_Zone", "data_inventaire_detail/master_detail.csv", [])
        if not df_master.empty:
            context += f"- Base Produits & Lots (Master Inventaire) : {len(df_master)} lots en stock partagé.\n"
            if "designation" in df_master.columns:
                top_products = df_master["designation"].dropna().unique()[:5].tolist()
                context += f"  Exemples de produits en stock : {', '.join(top_products)}\n"
            context += "- CONNAISSANCE MÉDICALE INTÉGRÉE : Tu es lié à l'IA médicale. Si l'utilisateur pose une question sur un médicament, fournis la classe thérapeutique, les interactions possibles, et les recommandations de santé.\n"
    except: pass

    # 7. Cerveau Global IA (Règles Apprises Partagées)
    try:
        df_rules = load_gs_data("IA_Rules", "data/db_ia_rules.csv", [])
        if not df_rules.empty:
            active_rules = df_rules[df_rules['actif'] == True]
            if not active_rules.empty:
                context += "- RÈGLES MÉTIER (Base d'apprentissage IA Partagée) :\n"
                for _, row in active_rules.iterrows():
                    context += f"  * Règle '{row['mot_cle']}' : {row['instruction']}\n"
    except: pass

    context += "\nTa mission : Analyser ces chiffres et ces règles pour aider le directeur à prendre des décisions. Tu es le cerveau central qui relie tous les modules. Sois visionnaire, précis et force de proposition. Utilise des emojis."
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
        play_sound("ai")  # Son doux à la réception de la réponse IA
        
    # Ajouter à l'historique
    st.session_state.messages_pharmaciel.append({"role": "assistant", "content": response})
