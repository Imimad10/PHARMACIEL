import streamlit as st
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Portail B2B - PHARMACIEL", layout="wide")

st.title("🌐 Portail B2B / Commandes Clients")
st.markdown("### Catalogue et prise de commande en ligne")

# Initialisation du panier
if 'b2b_cart' not in st.session_state:
    st.session_state.b2b_cart = []

tabs = st.tabs(["🛒 Catalogue & Commande", "📦 Mon Panier", "historique des commandes"])

# Données fictives pour le catalogue
@st.cache_data
def get_mock_catalog():
    return pd.DataFrame({
        "ID_Produit": ["P001", "P002", "P003", "P004"],
        "Désignation": ["Paracétamol 1g", "Ibuprofène 400mg", "Sirop Toux", "Vitamine C"],
        "Laboratoire": ["Sanofi", "Pfizer", "Bayer", "Upsa"],
        "Stock_Dispo": [1500, 800, 300, 0],
        "Prix_Unitaire": [250.00, 320.00, 450.00, 180.00]
    })

df_catalog = get_mock_catalog()

with tabs[0]:
    st.subheader("Recherche de produits")
    search = st.text_input("Rechercher un produit (Nom, Laboratoire)...")
    
    df_display = df_catalog.copy()
    if search:
        df_display = df_display[df_display['Désignation'].str.contains(search, case=False) | df_display['Laboratoire'].str.contains(search, case=False)]
    
    st.dataframe(df_display, use_container_width=True, hide_index=True)
    
    st.divider()
    st.subheader("Ajouter au panier")
    col1, col2, col3 = st.columns(3)
    with col1:
        prod_sel = st.selectbox("Produit", df_catalog[df_catalog['Stock_Dispo'] > 0]['Désignation'].tolist())
    with col2:
        qte = st.number_input("Quantité", min_value=1, step=1)
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("➕ Ajouter", use_container_width=True):
            prix = df_catalog[df_catalog['Désignation'] == prod_sel]['Prix_Unitaire'].values[0]
            st.session_state.b2b_cart.append({
                "Produit": prod_sel,
                "Quantité": qte,
                "Prix Unitaire": prix,
                "Total": qte * prix
            })
            st.success(f"{qte}x {prod_sel} ajouté au panier !")

with tabs[1]:
    st.subheader("Mon Panier Actuel")
    if len(st.session_state.b2b_cart) > 0:
        df_cart = pd.DataFrame(st.session_state.b2b_cart)
        st.dataframe(df_cart, use_container_width=True, hide_index=True)
        
        total_cmd = df_cart['Total'].sum()
        st.metric("Total Commande (DZD)", f"{total_cmd:,.2f}")
        
        if st.button("✅ Valider la commande", type="primary"):
            st.success("Commande validée avec succès ! Notre équipe logistique s'en charge.")
            st.session_state.b2b_cart = []
            st.balloons()
    else:
        st.info("Votre panier est vide.")

with tabs[2]:
    st.subheader("Historique")
    st.write("Aucune commande passée récemment.")
