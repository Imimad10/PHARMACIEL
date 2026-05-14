import streamlit as st
import pandas as pd
from utils_gsheets import load_gs_data

def global_search(query):
    if not query or len(query) < 2:
        return None
    
    results = {}
    query = query.lower()

    # 1. Search in Clients
    try:
        df_clients = load_gs_data("Base_Clients", "base_clients.csv", ["Nom Client", "Région", "Secteur"])
        res_clients = df_clients[df_clients.apply(lambda row: query in str(row).lower(), axis=1)]
        if not res_clients.empty:
            results["Clients"] = res_clients
    except: pass

    # 2. Search in Products (Catalogue)
    try:
        df_prod = load_gs_data("Catalogue_Produits", "catalogue_pharmnet.csv", ["Désignation", "PPA"])
        res_prod = df_prod[df_prod.apply(lambda row: query in str(row).lower(), axis=1)]
        if not res_prod.empty:
            results["Produits"] = res_prod
    except: pass

    # 3. Search in Invoices (Pointages)
    try:
        df_p = load_gs_data("Pointages", "data/db_pointages.csv", ["reference", "client", "date_pointage"])
        res_p = df_p[df_p.apply(lambda row: query in str(row).lower(), axis=1)]
        if not res_p.empty:
            results["Factures (Pointages)"] = res_p
    except: pass

    # 4. Search in Recouvrement
    try:
        df_r = load_gs_data("Recouvrement", "data_recouvrement.csv", ["Facture", "Client", "Statut", "Reste à payer"])
        res_r = df_r[df_r.apply(lambda row: query in str(row).lower(), axis=1)]
        if not res_r.empty:
            results["Recouvrement"] = res_r
    except: pass

    return results

def show_search_bar():
    with st.sidebar:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("""
            <div style="background: rgba(91, 108, 249, 0.05); padding: 12px; border-radius: 15px; border: 1px solid rgba(91, 108, 249, 0.1); margin-bottom: 10px;">
                <p style="font-weight: 800; margin-bottom: 5px; font-size: 0.75rem; color: #5b6cf9; letter-spacing: 1px; display: flex; align-items: center;">
                    🔍 RECHERCHE UNIVERSELLE
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        # Style spécifique pour la barre de recherche sidebar pour forcer la visibilité
        st.markdown("""
            <style>
                [data-testid="stSidebar"] .stTextInput input {
                    background: white !important;
                    color: #1a1c21 !important;
                    border: 1px solid #5b6cf933 !important;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.05) !important;
                }
                [data-testid="stSidebar"] .stTextInput input::placeholder {
                    color: #94a3b8 !important;
                }
                [data-testid="stSidebar"] .stTextInput input:focus {
                    border-color: #5b6cf9 !important;
                    box-shadow: 0 0 12px rgba(91, 108, 249, 0.2) !important;
                }
            </style>
        """, unsafe_allow_html=True)
        
        search_query = st.text_input("", placeholder="Tapez ici pour chercher...", key="global_search_input", label_visibility="collapsed")
        
        if search_query:
            with st.spinner("Recherche..."):
                results = global_search(search_query)
                if results:
                    for category, df in results.items():
                        with st.expander(f"📌 {category} ({len(df)})", expanded=True):
                            st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.sidebar.warning("Aucun résultat trouvé.")
