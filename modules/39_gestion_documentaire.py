import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Gestion Documentaire", layout="wide")
st.title("📜 Gestion Documentaire & Réglementaire")
st.markdown("Stockez et liez vos documents réglementaires (AMM, Certificats d'Analyse) aux numéros de lots.")

# Simulation de base de données
if 'doc_db' not in st.session_state:
    st.session_state.doc_db = []

tabs = st.tabs(["📄 Consulter les documents", "📤 Ajouter un document"])

with tabs[0]:
    st.subheader("Base Documentaire")
    if len(st.session_state.doc_db) > 0:
        df_docs = pd.DataFrame(st.session_state.doc_db)
        st.dataframe(df_docs, use_container_width=True, hide_index=True)
    else:
        st.info("Aucun document stocké pour le moment.")

with tabs[1]:
    st.subheader("Importer un nouveau document")
    col1, col2 = st.columns(2)
    with col1:
        doc_type = st.selectbox("Type de document", ["Certificat d'Analyse (Bulletin)", "Autorisation de Mise sur le Marché (AMM)", "Fiche Technique", "Autre"])
        lot_cible = st.text_input("Numéro de Lot concerné (facultatif)")
        produit = st.text_input("Produit concerné")
    
    with col2:
        date_exp = st.date_input("Date d'expiration du document (s'il y a lieu)")
        uploaded_file = st.file_uploader("Sélectionnez le PDF ou l'image", type=['pdf', 'png', 'jpg'])
        
    if st.button("Sauvegarder le document", type="primary"):
        if uploaded_file and produit:
            st.session_state.doc_db.append({
                "Date d'Ajout": datetime.now().strftime("%Y-%m-%d"),
                "Type": doc_type,
                "Produit": produit,
                "Lot": lot_cible,
                "Expiration": date_exp.strftime("%Y-%m-%d"),
                "Fichier": uploaded_file.name
            })
            st.success("Document sauvegardé et lié avec succès !")
        else:
            st.error("Veuillez fournir un produit et un fichier.")
