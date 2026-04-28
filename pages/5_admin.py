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

# Affichage des utilisateurs avec un mot de passe masqué
df_users = pd.DataFrame(users)
if not df_users.empty:
    df_display = df_users.copy()
    df_display['password'] = "********"
    st.dataframe(df_display[['username', 'role', 'pages', 'password']], use_container_width=True)

st.divider()

tab_add, tab_edit, tab_del = st.tabs(["➕ Ajouter un compte", "✏️ Modifier un compte", "🗑️ Supprimer un compte"])

MODULES_DISPO = ["Logistique", "Inventaire", "Suivi", "Recouvrement", "Pointage"]

with tab_add:
    st.subheader("Créer un nouvel utilisateur")
    with st.form("form_add_user"):
        u_name = st.text_input("Nom d'utilisateur")
        u_pwd = st.text_input("Mot de passe")
        u_role = st.selectbox("Rôle", ["Saisie", "Admin"])
        u_pages = st.multiselect("Accès aux modules", MODULES_DISPO)
        
        if st.form_submit_button("Créer l'utilisateur"):
            User = Query()
            if db_users.search(User.username == u_name):
                st.error("Ce nom d'utilisateur existe déjà !")
            elif u_name and u_pwd:
                db_users.insert({
                    'username': u_name,
                    'password': u_pwd,
                    'role': u_role,
                    'pages': u_pages
                })
                st.success(f"Utilisateur {u_name} créé !")
                st.rerun()
            else:
                st.error("Nom d'utilisateur et mot de passe requis.")

with tab_edit:
    st.subheader("Modifier les accès ou le mot de passe")
    
    # Sélection de l'utilisateur à modifier
    edit_target = st.selectbox("Sélectionner l'utilisateur", [u['username'] for u in users])
    
    if edit_target:
        # Récupération des données actuelles
        target_data = next((u for u in users if u['username'] == edit_target), None)
        
        with st.form("form_edit_user"):
            st.write(f"Modifications pour : **{edit_target}**")
            new_pwd = st.text_input("Nouveau mot de passe", value=target_data.get('password', ''))
            
            role_idx = 0 if target_data.get('role') == 'Saisie' else 1
            new_role = st.selectbox("Nouveau rôle", ["Saisie", "Admin"], index=role_idx)
            
            current_pages = [p for p in target_data.get('pages', []) if p in MODULES_DISPO]
            new_pages = st.multiselect("Accès aux modules", MODULES_DISPO, default=current_pages)
            
            if st.form_submit_button("Mettre à jour"):
                if new_pwd:
                    User = Query()
                    db_users.update({
                        'password': new_pwd,
                        'role': new_role,
                        'pages': new_pages
                    }, User.username == edit_target)
                    
                    # Si l'admin modifie son propre profil, on met à jour la session
                    if edit_target == st.session_state.current_user['username']:
                        st.session_state.current_user['password'] = new_pwd
                        st.session_state.current_user['role'] = new_role
                        st.session_state.current_user['pages'] = new_pages
                    
                    st.success(f"Profil de {edit_target} mis à jour !")
                    st.rerun()
                else:
                    st.error("Le mot de passe ne peut pas être vide.")

with tab_del:
    st.subheader("Supprimer définitivement un utilisateur")
    del_options = [u['username'] for u in users if u['username'] != st.session_state.current_user['username']]
    
    if not del_options:
        st.info("Aucun autre utilisateur à supprimer.")
    else:
        with st.form("form_del_user"):
            u_del = st.selectbox("Sélectionner l'utilisateur à supprimer", del_options)
            st.warning("⚠️ Cette action est irréversible.")
            if st.form_submit_button("Confirmer la suppression"):
                User = Query()
                db_users.remove(User.username == u_del)
                st.success(f"Utilisateur {u_del} supprimé.")
                st.rerun()
