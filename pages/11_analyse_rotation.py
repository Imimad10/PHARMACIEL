import streamlit as st
import pandas as pd
import plotly.express as px
import os

# --- CONFIGURATION ---
st.set_page_config(page_title="Rotation des Stocks", layout="wide")

st.title("📈 Analyse de la Rotation des Stocks (Slow-Moving)")
st.write("Identifiez les produits immobilisés qui ne tournent pas assez vite pour optimiser votre trésorerie.")

tab_import, tab_analyse = st.tabs(["📊 Import des Données", "🔍 Analyse Slow-Moving"])

with tab_import:
    st.info("Pour analyser la rotation, nous avons besoin de croiser votre stock actuel avec vos ventes sur une période donnée (ex: les 3 derniers mois).")
    
    col1, col2 = st.columns(2)
    with col1:
        file_stock = st.file_uploader("1. Importez votre Stock Actuel (CSV/Excel)", type=["csv", "xlsx"])
    with col2:
        file_sales = st.file_uploader("2. Importez votre Rapport de Ventes (CSV/Excel)", type=["csv", "xlsx"])

    if file_stock and file_sales:
        try:
            # Chargement Stock
            if file_stock.name.endswith('.csv'): df_stock = pd.read_csv(file_stock)
            else: df_stock = pd.read_excel(file_stock)
            
            # Chargement Ventes
            if file_sales.name.endswith('.csv'): df_sales = pd.read_csv(file_sales)
            else: df_sales = pd.read_excel(file_sales)
            
            # Nettoyage noms colonnes
            df_stock.columns = [c.strip().upper() for c in df_stock.columns]
            df_sales.columns = [c.strip().upper() for c in df_sales.columns]
            
            st.success("✅ Fichiers chargés avec succès !")
            st.session_state.df_stock_rot = df_stock
            st.session_state.df_sales_rot = df_sales
        except Exception as e:
            st.error(f"Erreur lors de la lecture : {e}")

# --- ANALYSE ---
with tab_analyse:
    if "df_stock_rot" in st.session_state and "df_sales_rot" in st.session_state:
        df_st = st.session_state.df_stock_rot
        df_sl = st.session_state.df_sales_rot
        
        st.subheader("Configuration de l'Analyse")
        col_st = st.selectbox("Colonne 'Désignation' dans Stock", df_st.columns)
        col_sl = st.selectbox("Colonne 'Désignation' dans Ventes", df_sl.columns)
        col_qty_st = st.selectbox("Colonne 'Quantité Stock'", df_st.columns)
        col_qty_sl = st.selectbox("Colonne 'Quantité Vendue'", df_sl.columns)
        
        if st.button("🚀 Lancer l'Analyse de Rotation"):
            # Agrégation des ventes
            df_sl_agg = df_sl.groupby(col_sl)[col_qty_sl].sum().reset_index()
            
            # Fusion
            df_merged = pd.merge(df_st, df_sl_agg, left_on=col_st, right_on=col_sl, how='left').fillna(0)
            
            # Calcul du ratio de rotation (Ventes / Stock)
            # On évite la division par zéro
            df_merged['Ratio_Rotation'] = df_merged[col_qty_sl] / (df_merged[col_qty_st] + 0.1)
            
            # Définition du Slow-Moving (ex: moins de 5% du stock vendu sur la période)
            threshold = st.slider("Seuil de rotation critique (%)", 0, 100, 5) / 100
            df_slow = df_merged[df_merged['Ratio_Rotation'] < threshold].sort_values(by=col_qty_st, ascending=False)
            
            st.divider()
            st.subheader(f"⚠️ Produits Slow-Moving (Rotation < {threshold*100:.0f}%)")
            st.write(f"Nous avons identifié **{len(df_slow)}** produits qui dorment en stock.")
            
            # Graphique
            fig = px.scatter(df_slow.head(50), x=col_qty_st, y=col_qty_sl, size=col_qty_st, 
                             hover_name=col_st, title="Stock vs Ventes (Top 50 Slow-Moving)",
                             color="Ratio_Rotation", color_continuous_scale="Reds_r", template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(df_slow[[col_st, col_qty_st, col_qty_sl, 'Ratio_Rotation']], use_container_width=True)
            
            # Recommandation IA
            from utils_ia import ask_ai, is_ia_enabled
            if is_ia_enabled():
                if st.button("🤖 Demander conseil à l'IA sur ces produits"):
                    list_items = df_slow[col_st].head(10).tolist()
                    prompt = f"Voici une liste de produits pharmaceutiques qui ne se vendent pas assez (Slow-moving) : {list_items}. Quelles stratégies de déstockage ou promotions suggères-tu pour un grossiste ?"
                    st.info(ask_ai(prompt))
    else:
        st.warning("Veuillez d'abord importer les données de stock et de ventes dans le premier onglet.")
