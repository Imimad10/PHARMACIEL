import streamlit as st
import pandas as pd
from tinydb import TinyDB, Query

# Sécurité
if "current_user" not in st.session_state or st.session_state.current_user is None or st.session_state.current_user.get('role') != 'Admin':
    st.error("Accès refusé.")
    st.stop()

st.title("⚙️ Administration Centrale - Pharmaciel")
st.write("Gérez les utilisateurs, leurs rôles et leurs accès aux différentes pages de l'application.")

db_users = TinyDB('data/db_users.json')
users = db_users.all()

st.subheader("👥 Liste des Utilisateurs")

# Affichage des utilisateurs
df_users = pd.DataFrame(users)
if not df_users.empty:
    st.dataframe(df_users[['username', 'role', 'pages']], use_container_width=True)

st.divider()

col1, col2 = st.columns(2)

with col1:
    st.subheader("➕ Ajouter / Modifier un Utilisateur")
    with st.form("user_form"):
        u_name = st.text_input("Nom d'utilisateur")
        u_pwd = st.text_input("Mot de passe")
        u_role = st.selectbox("Rôle", ["Saisie", "Admin"])
        u_pages = st.multiselect("Accès aux modules", ["Logistique", "Inventaire", "Suivi", "Recouvrement", "Pointage"])
        
        if st.form_submit_button("Sauvegarder"):
            if u_name and u_pwd:
                User = Query()
                db_users.upsert({
                    'username': u_name,
                    'password': u_pwd,
                    'role': u_role,
                    'pages': u_pages
                }, User.username == u_name)
                st.success(f"Utilisateur {u_name} sauvegardé !")
                st.rerun()
            else:
                st.error("Le nom d'utilisateur et le mot de passe sont obligatoires.")

with col2:
    st.subheader("🗑️ Supprimer un Utilisateur")
    with st.form("del_form"):
        u_del = st.selectbox("Sélectionner l'utilisateur à supprimer", [u['username'] for u in users if u['username'] != st.session_state.current_user['username']])
        if st.form_submit_button("Supprimer"):
            User = Query()
            db_users.remove(User.username == u_del)
            st.warning(f"Utilisateur {u_del} supprimé.")
            st.rerun()
