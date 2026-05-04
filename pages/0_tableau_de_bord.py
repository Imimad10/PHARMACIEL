import streamlit as st
import pandas as pd
import os
from tinydb import TinyDB, Query

st.title("📊 Tableau de Bord Central")
st.write("Bienvenue sur votre portail de pilotage. Voici un résumé de l'activité globale.")

# --- 1. COLLECTE DES DONNÉES ---
# Note: On récupère les infos essentielles de chaque module
def get_kpis():
    kpis = {}
    
    # Logistique (Expédition)
    if os.path.exists("db_pharmaciel.json"):
        db = TinyDB("db_pharmaciel.json")
        kpis['expeditions'] = len(db.table('expeditions').all())
        kpis['pointages'] = len(db.table('pointages').all())
    
    # Recouvrement
    if os.path.exists("data_recouvrement.csv"):
        try:
            df_rec = pd.read_csv("data_recouvrement.csv")
            kpis['recouvrement_total'] = df_rec['montant'].sum() if 'montant' in df_rec.columns else 0
        except: kpis['recouvrement_total'] = 0
        
    # Inventaire Détail
    if os.path.exists("data_inventaire_detail/saisie_detail.csv"):
        try:
            df_inv = pd.read_csv("data_inventaire_detail/saisie_detail.csv", sep=';')
            kpis['inventaire_saisies'] = len(df_inv)
        except: kpis['inventaire_saisies'] = 0
        
    return kpis

stats = get_kpis()

# --- 2. AFFICHAGE DES KPI ---
st.divider()
c1, c2, c3, c4 = st.columns(4)
c1.metric("📦 Expéditions", stats.get('expeditions', 0))
c2.metric("📝 Pointages", stats.get('pointages', 0))
c3.metric("💰 Recouvrement", f"{stats.get('recouvrement_total', 0):,.2f} DA")
c4.metric("🔍 Saisies Inventaire", stats.get('inventaire_saisies', 0))

# --- 3. RÉSUMÉ PAR MODULE ---
st.divider()
st.subheader("🚀 Accès Rapide & Alertes")

col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        st.write("### 🚛 Logistique & Expéditions")
        st.info(f"Dernière mise à jour : Aujourd'hui")
        if st.button("Aller à Logistique", key="goto_log"):
            st.switch_page("pages/1_expedition.py")

    with st.container(border=True):
        st.write("### 📦 Inventaires")
        st.write(f"Total saisies détaillées : **{stats.get('inventaire_saisies', 0)}**")
        if st.button("Aller à Inventaire Détail", key="goto_inv_det"):
            st.switch_page("pages/8_inventaire_detail.py")

with col2:
    with st.container(border=True):
        st.write("### 💰 Recouvrements")
        st.write(f"Volume financier traité : **{stats.get('recouvrement_total', 0):,.0f} DA**")
        if st.button("Aller à Recouvrement", key="goto_rec"):
            st.switch_page("pages/4_recouvrement.py")

    with st.container(border=True):
        st.write("### ⏳ Péremptions")
        st.warning("Vérifiez les produits approchant de la date limite.")
        if st.button("Aller à Péremptions", key="goto_per"):
            st.switch_page("pages/6_peremptions.py")

# --- 4. GRAPHES RÉCAPITULATIFS (Optionnel) ---
st.divider()
st.write("💡 *Utilisez les modules spécifiques pour des analyses détaillées et des rapports PDF.*")
