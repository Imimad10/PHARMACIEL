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
        st.write("---")
        st.markdown('<p style="font-weight: 800; margin-bottom: -15px; font-size: 0.9rem;"><span class="material-symbols-outlined" style="font-size: 18px; vertical-align: bottom;">search</span> RECHERCHE UNIVERSELLE</p>', unsafe_allow_html=True)
        search_query = st.text_input("", placeholder="Client, Facture, Produit...", key="global_search_input", label_visibility="collapsed")
        if search_query:
            results = global_search(search_query)
            if results:
                for category, df in results.items():
                    with st.expander(f"📌 {category} ({len(df)})", expanded=True):
                        st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.sidebar.warning("Aucun résultat trouvé.")
