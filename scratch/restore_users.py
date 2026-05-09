import pandas as pd
import os
import streamlit as st
from utils_gsheets import load_gs_data, save_gs_data, DB_USERS_WORKSHEET, DB_USERS_FALLBACK

# Simulation de l'environnement Streamlit pour que les secrets fonctionnent
if not st.secrets:
    import toml
    secrets_path = os.path.join(".streamlit", "secrets.toml")
    if os.path.exists(secrets_path):
        st.secrets.update(toml.load(secrets_path))
    else:
        print("Erreur : Fichier secrets.toml introuvable.")

def restore_users():
    cols = ["username", "password", "role", "pages", "nom", "prenom", "zone"]
    
    print("Chargement des utilisateurs actuels...")
    # On force le cloud pour être sûr de ne pas écraser avec une version locale obsolète
    df = load_gs_data(DB_USERS_WORKSHEET, DB_USERS_FALLBACK, cols, force_cloud=True)
    
    new_users = [
        {'username': 'Idris', 'password': '123', 'role': 'Saisie', 'pages': ['Logistique', 'Suivi', 'Inventaire Détail'], 'nom': 'Idris', 'prenom': '', 'zone': 'Aucune'},
        {'username': 'Yacine', 'password': '123', 'role': 'Saisie', 'pages': ['Logistique', 'Suivi', 'Inventaire Détail'], 'nom': 'Yacine', 'prenom': '', 'zone': 'Aucune'},
        {'username': 'Sidali', 'password': '123', 'role': 'Saisie', 'pages': ['Logistique', 'Suivi', 'Inventaire Détail'], 'nom': 'Sidali', 'prenom': '', 'zone': 'Aucune'},
        {'username': 'Bilel', 'password': '123', 'role': 'Saisie', 'pages': ['Logistique', 'Suivi', 'Inventaire Détail'], 'nom': 'Bilel', 'prenom': '', 'zone': 'Aucune'},
        {'username': 'Mahdi', 'password': '123', 'role': 'Saisie', 'pages': ['Logistique', 'Suivi', 'Inventaire Détail'], 'nom': 'Mahdi', 'prenom': '', 'zone': 'Aucune'},
        {'username': 'Kader', 'password': '123', 'role': 'Saisie', 'pages': ['Logistique', 'Suivi', 'Inventaire Détail'], 'nom': 'Kader', 'prenom': '', 'zone': 'Aucune'},
    ]
    
    added_count = 0
    for nu in new_users:
        if df.empty or nu['username'] not in df['username'].values:
            df = pd.concat([df, pd.DataFrame([nu])], ignore_index=True)
            print(f"Ajout de : {nu['username']}")
            added_count += 1
        else:
            print(f"Utilisateur déjà présent : {nu['username']}")
            # Mise à jour du MDP si déjà présent ? Le user a demandé "mdp 123"
            df.loc[df['username'] == nu['username'], 'password'] = '123'
    
    if added_count > 0 or True: # On force la sauvegarde pour appliquer les MDP 123
        print("Sauvegarde vers Google Sheets...")
        save_gs_data(df, DB_USERS_WORKSHEET, DB_USERS_FALLBACK, force_cloud=True)
        print("Opération terminée avec succès !")
    else:
        print("Aucun changement nécessaire.")

if __name__ == "__main__":
    # Mock streamlit secrets if needed for local execution
    # Mais utils_gsheets utilise st.secrets, donc il faut que Streamlit soit "conscient"
    # Le plus simple est de lancer via 'streamlit run' ou d'injecter manuellement les secrets
    restore_users()
