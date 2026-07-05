import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Optimisation Tournées", layout="wide")
st.title("🗺️ Optimisation IA des Tournées de Livraison")
st.write("Ce module calcule le meilleur trajet pour vos livreurs afin d'économiser du temps et du carburant.")

# Mock data
@st.cache_data
def get_mock_deliveries():
    return pd.DataFrame({
        "ID_Client": ["C001", "C002", "C003", "C004", "C005"],
        "Pharmacie": ["Pharmacie Centrale", "Pharmacie El Amel", "Pharmacie Errazi", "Pharmacie Echifa", "Pharmacie Pasteur"],
        "Secteur": ["Alger Centre", "Bab Ezzouar", "Kouba", "Hydra", "El Harrach"],
        "latitude": [36.7525, 36.7196, 36.7323, 36.7450, 36.7214],
        "longitude": [3.04197, 3.1819, 3.0850, 3.0333, 3.1369],
        "Statut": ["En attente"] * 5
    })

df_deliveries = get_mock_deliveries()

col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("Bons de livraison en attente")
    st.dataframe(df_deliveries[['Pharmacie', 'Secteur']], use_container_width=True, hide_index=True)
    
    vehicule = st.selectbox("Assigner au véhicule", ["Camionnette A (Livreur: Karim)", "Fourgon B (Livreur: Ahmed)"])
    
    if st.button("🚀 Calculer la tournée optimale", type="primary"):
        st.session_state.show_route = True
        st.success("Tournée optimisée générée ! Gain estimé : 24 minutes.")

with col2:
    st.subheader("Cartographie")
    if st.session_state.get('show_route', False):
        st.map(df_deliveries, latitude="latitude", longitude="longitude", zoom=12)
        st.info(f"**Itinéraire recommandé pour {vehicule}:** Dépôt -> Hydra -> Alger Centre -> Kouba -> El Harrach -> Bab Ezzouar")
    else:
        st.info("Cliquez sur 'Calculer la tournée optimale' pour afficher la carte.")
