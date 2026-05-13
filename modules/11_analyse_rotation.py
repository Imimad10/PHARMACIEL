import streamlit as st
import pandas as pd
import plotly.express as px
import os
from utils_ia import ask_ai, is_ia_enabled
from utils_sound import play_sound

# --- CONFIGURATION ---
st.set_page_config(page_title="Rotation des Stocks", layout="wide")

st.title("📈 Analyse de la Rotation des Stocks (Slow-Moving)")
st.write("Identifiez les produits immobilisés qui ne tournent pas assez vite pour optimiser votre trésorerie.")

tab_import, tab_analyse = st.tabs(["📊 Import des Données", "🔍 Analyse de Rotation"])

with tab_import:
    st.info("💡 **Nouveauté** : Si votre fichier contient déjà une colonne 'Rotation', importez-le simplement dans 'Stock Actuel'.")
    
    col1, col2 = st.columns(2)
    with col1:
        file_stock = st.file_uploader("1. Importez votre Stock Actuel / Liste des Lots", type=["csv", "xlsx"])
    with col2:
        file_sales = st.file_uploader("2. Importez Rapport de Ventes (Optionnel si rotation incluse)", type=["csv", "xlsx"])

    if file_stock:
        try:
            # Chargement Stock
            if file_stock.name.endswith('.csv'): df_stock = pd.read_csv(file_stock)
            else: df_stock = pd.read_excel(file_stock)
            
            # Nettoyage noms colonnes
            df_stock.columns = [c.strip().upper() for c in df_stock.columns]
            st.session_state.df_stock_rot = df_stock
            
            if "ROTATION" in df_stock.columns:
                st.success("✅ Colonne 'ROTATION' détectée ! Vous pouvez passer directement à l'analyse.")
                st.session_state.rotation_directe = True
            else:
                st.session_state.rotation_directe = False
                if file_sales:
                    if file_sales.name.endswith('.csv'): df_sales = pd.read_csv(file_sales)
                    else: df_sales = pd.read_excel(file_sales)
                    df_sales.columns = [c.strip().upper() for c in df_sales.columns]
                    st.session_state.df_sales_rot = df_sales
                    st.success("✅ Fichiers Stock et Ventes chargés.")

        except Exception as e:
            st.error(f"Erreur lors de la lecture : {e}")

# --- ANALYSE ---
with tab_analyse:
    if "df_stock_rot" in st.session_state:
        df_st = st.session_state.df_stock_rot
        is_direct = st.session_state.get("rotation_directe", False)
        
        if is_direct:
            st.subheader("🚀 Analyse basée sur votre colonne 'ROTATION'")
            
            col_prod = st.selectbox("Colonne Désignation", [c for c in df_st.columns if "PRODUIT" in c or "DESIGNATION" in c] or df_st.columns)
            col_rot = "ROTATION"
            col_qty = st.selectbox("Colonne Quantité", [c for c in df_st.columns if "QTE" in c or "QUANTITE" in c or "STOCK" in c] or df_st.columns)
            
            # Classification & Filtres
            st.markdown("#### 🛠️ Filtres & Options d'Export")
            col_f1, col_f2 = st.columns([2, 1])
            with col_f1:
                threshold = st.slider("Seuil Slow-Moving (Rotation < X)", 0.0, 50.0, 1.0, step=0.1)
                df_res = df_st.copy()
                df_res['STATUT_ROTATION'] = df_res[col_rot].apply(lambda x: "🟥 Dormant" if x < threshold else ("🟧 Actif" if x < threshold*5 else "🟩 Star"))
                
                selected_status = st.multiselect(
                    "Filtrer par statut de rotation :",
                    ["🟥 Dormant", "🟧 Actif", "🟩 Star"],
                    default=["🟥 Dormant"]
                )
                df_filtered = df_res[df_res['STATUT_ROTATION'].isin(selected_status)].sort_values(by=col_rot)
            
            with col_f2:
                include_ia = st.checkbox("Inclure l'analyse IA dans le PDF", value=True)
                if st.button("📄 Télécharger le Rapport PDF", use_container_width=True, type="primary"):
                    if not df_filtered.empty:
                        from utils_pdf import generate_rotation_report_pdf
                        ia_text = st.session_state.get("ia_analysis_text", "") if include_ia else ""
                        pdf_bytes = generate_rotation_report_pdf(
                            df_filtered[[col_prod, col_qty, col_rot, 'STATUT_ROTATION']],
                            module_name="Analyse Rotation",
                            ia_analysis=ia_text
                        )
                        st.download_button(
                            "📥 Cliquez ici pour enregistrer le PDF",
                            data=pdf_bytes,
                            file_name=f"Rapport_Rotation_{datetime.now().strftime('%d_%m_%Y')}.pdf",
                            mime="application/pdf"
                        )
                    else:
                        st.warning("Aucune donnée à exporter avec les filtres actuels.")

            st.divider()
            
            # KPI
            c1, c2, c3 = st.columns(3)
            dormants = len(df_res[df_res[col_rot] < threshold])
            c1.metric("Produits Dormants", dormants, delta=f"{dormants/len(df_res)*100:.1f}% du stock", delta_color="inverse")
            c2.metric("Rotation Moyenne", round(df_res[col_rot].mean(), 2))
            c3.metric("Top Rotation", round(df_res[col_rot].max(), 2))
            
            # Graphique (sur les données filtrées)
            fig = px.histogram(df_filtered, x=col_rot, color="STATUT_ROTATION", 
                               title=f"Distribution de la Rotation ({', '.join(selected_status)})",
                               color_discrete_map={"🟥 Dormant": "#ef4444", "🟧 Actif": "#f59e0b", "🟩 Star": "#10b981"},
                               template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
            
            st.dataframe(df_filtered[[col_prod, col_qty, col_rot, 'STATUT_ROTATION']], use_container_width=True)
            
            if is_ia_enabled():
                if st.button("🤖 Analyse Stratégique IA (Slow-Moving)"):
                    list_dormants = df_res[df_res[col_rot] < threshold][col_prod].head(15).tolist()
                    prompt = f"""En tant qu'expert logistique DarPharm, analyse ces produits ayant une rotation critique (< {threshold}) : {list_dormants}.
                    Explique pourquoi ces produits dorment (ex: prix trop élevé, saisonnalité, concurrence) et propose un plan d'action de déstockage urgent."""
                    with st.chat_message("assistant"):
                        analysis = ask_ai(prompt)
                        st.write(analysis)
                        st.session_state["ia_analysis_text"] = analysis
                    play_sound("ai")

        elif "df_sales_rot" in st.session_state:
            # Logique classique (Croisement Stock/Ventes)
            df_sl = st.session_state.df_sales_rot
            st.subheader("🛠️ Croisement Stock & Ventes")
            
            col_st = st.selectbox("Désignation (Stock)", df_st.columns)
            col_sl = st.selectbox("Désignation (Ventes)", df_sl.columns)
            col_qty_st = st.selectbox("Quantité Stock", df_st.columns)
            col_qty_sl = st.selectbox("Quantité Vendue", df_sl.columns)
            
            if st.button("🚀 Calculer la Rotation"):
                df_sl_agg = df_sl.groupby(col_sl)[col_qty_sl].sum().reset_index()
                df_merged = pd.merge(df_st, df_sl_agg, left_on=col_st, right_on=col_sl, how='left').fillna(0)
                df_merged['Rotation'] = df_merged[col_qty_sl] / (df_merged[col_qty_st] + 0.1)
                
                fig = px.scatter(df_merged, x=col_qty_st, y=col_qty_sl, hover_name=col_st, size='Rotation', color='Rotation')
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(df_merged.sort_values(by='Rotation'))
    else:
        st.warning("Veuillez importer vos données dans le premier onglet.")
