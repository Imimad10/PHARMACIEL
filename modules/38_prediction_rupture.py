import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config(page_title="Prédiction Rupture", layout="wide")
st.title("🔮 Prédiction de Rupture de Stock (IA)")
st.markdown("Ce module analyse l'historique des ventes pour estimer la date d'épuisement des stocks restants.")

@st.cache_data
def get_mock_predictions():
    return pd.DataFrame({
        "Produit": ["Sérum Salé", "Doliprane 1000", "Amoxicilline", "Spasfon", "Bétadine"],
        "Stock Actuel": [200, 1500, 50, 400, 10],
        "Vitesse de rotation (unités/jour)": [15, 100, 20, 5, 2],
        "Jours restants estimés": [13, 15, 2, 80, 5]
    }).sort_values("Jours restants estimés")

df_pred = get_mock_predictions()

col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Alertes Haut Risque")
    df_alert = df_pred[df_pred['Jours restants estimés'] <= 15].copy()
    def highlight_critical(val):
        if isinstance(val, (int, float)) and val <= 7:
            return "background-color: #ffcccc; color: red;"
        return ""

    # Utiliser .map() au lieu de .applymap() (déprécié en Pandas 2.1+)
    st.dataframe(
        df_alert.style.map(highlight_critical, subset=['Jours restants estimés']),
        use_container_width=True,
        hide_index=True
    )

with col2:
    st.subheader("Actions Recommandées")
    for idx, row in df_alert.iterrows():
        if row['Jours restants estimés'] <= 7:
            st.error(f"⚠️ **{row['Produit']}**: Rupture dans {row['Jours restants estimés']} jours. [Commander]")
        else:
            st.warning(f"⚠️ **{row['Produit']}**: Rupture dans {row['Jours restants estimés']} jours.")
            
    if st.button("Générer un bon de commande automatique"):
        st.success("Bon de commande généré pour les articles critiques !")
