import streamlit as st
import pandas as pd
import plotly.express as px
from tinydb import TinyDB, Query
from datetime import datetime
import os
from utils_ia import ask_ai, is_ia_enabled

# Configuration
db = TinyDB('db_pharmaciel.json')
table_pointage = db.table('pointages')

st.title("📊 Tableau de Bord Performance")

# --- 0. SCANNEUR QR ---
with st.expander("🔍 Scanner une Feuille de Route (QR Code)", expanded=False):
    st.write("Utilisez votre caméra pour scanner le QR Code présent sur la feuille de route.")
    cam_input = st.camera_input("Scanner le QR")
    
    if cam_input:
        try:
            import cv2
            import numpy as np
            # Conversion de l'image pour OpenCV
            file_bytes = np.asarray(bytearray(cam_input.read()), dtype=np.uint8)
            opencv_image = cv2.imdecode(file_bytes, 1)
            
            # Détection et Décodage
            detector = cv2.QRCodeDetector()
            data, bbox, _ = detector.detectAndDecode(opencv_image)
            
            if data:
                st.success(f"✅ QR Code détecté !")
                st.code(data)
                # On peut essayer d'extraire des infos si le format est standard
                if "Livreur:" in data:
                    st.info("Informations de la tournée extraites avec succès.")
            else:
                st.warning("Aucun QR Code valide détecté. Assurez-vous qu'il soit bien visible et éclairé.")
        except Exception as e:
            st.error(f"Erreur lors du scan : {e}")

# --- 1. CHARGEMENT DES DONNÉES ---
data_p = table_pointage.all()
if not data_p:
    st.info("Aucune donnée de pointage disponible pour le moment. Commencez à pointer des factures pour voir les analyses.")
    st.stop()

df_p = pd.DataFrame(data_p)
df_p['date_dt'] = pd.to_datetime(df_p['date_pointage'], format="%d/%m/%Y %H:%M")

# --- 2. FILTRES ---
col_f1, col_f2 = st.columns(2)
with col_f1:
    # Filtre par mois
    df_p['mois'] = df_p['date_dt'].dt.strftime('%B %Y')
    mois_list = ["Tous"] + sorted(df_p['mois'].unique().tolist())
    mois_sel = st.selectbox("📅 Filtrer par Mois", mois_list)

if mois_sel != "Tous":
    df_p = df_p[df_p['mois'] == mois_sel]

# --- 3. KPIs ---
st.divider()
c1, c2, c3, c4 = st.columns(4)

total_factures = len(df_p)
total_livreurs = df_p['livreur'].nunique()
total_clients = df_p['client'].nunique()
derniere_activite = df_p['date_dt'].max().strftime("%d/%m %H:%M")

c1.metric("Factures Pointées", total_factures)
c2.metric("Livreurs Actifs", total_livreurs)
c3.metric("Clients Servis", total_clients)
c4.metric("Dernier Pointage", derniere_activite)

# --- 3.5 ASSISTANT IA GLOBAL ---
if is_ia_enabled():
    st.divider()
    st.subheader("🤖 Assistant IA Global")
    st.write("Demandez à l'IA d'analyser vos performances :")
    
    question = st.text_input("Que voulez-vous savoir ? (ex: 'Qui est le meilleur livreur ce mois-ci ?')")
    if st.button("✨ Demander à l'IA", use_container_width=True):
        with st.spinner("L'IA réfléchit..."):
            # Préparation du contexte des données
            top_liv = df_p['livreur'].value_counts().head(5).to_dict() if not df_p.empty else "Aucun"
            top_reg = df_p['region'].value_counts().head(5).to_dict() if not df_p.empty else "Aucune"
            
            context = f"""
            Voici les données actuelles du mois sélectionné :
            - Total des factures traitées : {total_factures}
            - Nombre de livreurs actifs : {total_livreurs}
            - Top 5 livreurs (avec nombre de factures) : {top_liv}
            - Top 5 régions : {top_reg}
            - Dernière activité : {derniere_activite}
            """
            
            prompt = f"""
            Tu es l'expert analyste IA de la plateforme Darpharm Solution.
            En te basant UNIQUEMENT sur les données suivantes, réponds à la question de l'utilisateur de manière concise et professionnelle.
            Données : {context}
            
            Question de l'utilisateur : {question}
            """
            
            reponse = ask_ai(prompt)
            st.info(reponse)

# --- 4. ANALYSES GRAPHIQUES ---
st.divider()
col_g1, col_g2 = st.columns(2)

with col_g1:
    st.subheader("🚚 Activité par Livreur")
    df_liv = df_p.groupby('livreur').size().reset_index(name='Nombre')
    fig_liv = px.bar(df_liv, x='livreur', y='Nombre', color='Nombre', 
                     color_continuous_scale='Reds', template="plotly_dark")
    st.plotly_chart(fig_liv, use_container_width=True)

with col_g2:
    st.subheader("📍 Répartition par Secteur")
    df_reg = df_p.groupby('region').size().reset_index(name='Nombre')
    fig_reg = px.pie(df_reg, values='Nombre', names='region', hole=0.4,
                     color_discrete_sequence=px.colors.sequential.RdBu)
    st.plotly_chart(fig_reg, use_container_width=True)

# --- 5. ANALYSE TEMPORELLE ---
st.subheader("📈 Évolution du Pointage (Volume Journalier)")
df_day = df_p.groupby(df_p['date_dt'].dt.date).size().reset_index(name='Nombre')
fig_day = px.area(df_day, x='date_dt', y='Nombre', line_shape='spline',
                  color_discrete_sequence=['#ff4b4b'])
st.plotly_chart(fig_day, use_container_width=True)

# --- 6. TABLEAU RÉCAPITULATIF ---
with st.expander("📄 Voir les détails des données filtrées"):
    st.dataframe(df_p.sort_values('date_dt', ascending=False), use_container_width=True)
