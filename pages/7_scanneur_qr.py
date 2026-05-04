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

st.title("🔍 Scanneur QR & Performance")

# --- 0. SCANNEUR QR ---
with st.container(border=True):
    st.subheader("📸 Scanner une Feuille de Route")
    st.write("Utilisez votre caméra pour scanner le QR Code présent sur la feuille de route.")
    cam_input = st.camera_input("Prendre une photo du QR")
    
    if cam_input:
        try:
            import cv2
            import numpy as np
            file_bytes = np.asarray(bytearray(cam_input.read()), dtype=np.uint8)
            opencv_image = cv2.imdecode(file_bytes, 1)
            detector = cv2.QRCodeDetector()
            data, bbox, _ = detector.detectAndDecode(opencv_image)
            
            if data:
                st.success(f"✅ QR Code détecté !")
                st.code(data)
                if "Livreur:" in data:
                    st.info("Informations de la tournée extraites avec succès.")
            else:
                st.warning("Aucun QR Code valide détecté. Assurez-vous qu'il soit bien visible.")
        except Exception as e:
            st.error(f"Erreur lors du scan : {e}")

# --- 1. CHARGEMENT DES DONNÉES ---
data_p = table_pointage.all()
if not data_p:
    st.info("En attente de données de pointage pour l'analyse de performance.")
    st.stop()

df_p = pd.DataFrame(data_p)
df_p['date_dt'] = pd.to_datetime(df_p['date_pointage'], format="%d/%m/%Y %H:%M", errors='coerce')

# --- 2. FILTRES ---
col_f1, col_f2 = st.columns(2)
with col_f1:
    df_p['mois'] = df_p['date_dt'].dt.strftime('%B %Y')
    mois_list = ["Tous"] + sorted(df_p['mois'].unique().tolist())
    mois_sel = st.selectbox("📅 Période", mois_list)

if mois_sel != "Tous":
    df_p = df_p[df_p['mois'] == mois_sel]

# --- 3. KPIs ---
st.divider()
c1, c2, c3 = st.columns(3)
c1.metric("Factures Pointées", len(df_p))
c2.metric("Livreurs Actifs", df_p['livreur'].nunique())
c3.metric("Clients Servis", df_p['client'].nunique())

# --- ANALYSES GRAPHIQUES ---
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
    fig_reg = px.pie(df_reg, values='Nombre', names='region', hole=0.4)
    st.plotly_chart(fig_reg, use_container_width=True)

# Assistant IA
if is_ia_enabled():
    with st.expander("🤖 Assistant IA Performance", expanded=False):
        question = st.text_input("Posez une question sur les performances :")
        if st.button("Analyser"):
            with st.spinner("Analyse en cours..."):
                top_liv = df_p['livreur'].value_counts().head(3).to_dict()
                context = f"Données du mois : {len(df_p)} factures, Top livreurs : {top_liv}"
                prompt = f"Analyse ces données de performance : {context}. Réponds à : {question}"
                st.info(ask_ai(prompt))
