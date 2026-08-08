import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime
from utils_ia import ask_ai, is_ia_enabled
from utils_sound import play_sound

# --- CONFIGURATION ---
st.set_page_config(page_title="Rotation des Stocks", layout="wide")

st.title("📈 Analyse de la Rotation des Stocks (Slow-Moving)")
st.write("Identifiez les produits immobilisés qui ne tournent pas assez vite pour optimiser votre trésorerie.")

tab_import, tab_analyse, tab_stagnant = st.tabs(["📊 Import des Données", "🔍 Analyse de Rotation", "⏳ Produits Stagnants (Arrivage)"])

with tab_import:
    st.info("💡 **Nouveauté** : Utilisez les données de la base centrale ou importez un fichier manuellement.")
    
    col_db1, col_db2 = st.columns(2)
    with col_db1:
        if st.button("📥 Charger Master Inventaire (Liste des Lots)", use_container_width=True, type="primary"):
            from utils_gsheets import load_gs_data
            df_master = load_gs_data("Master_Inventaire_Zone", "data_inventaire_detail/master_detail.csv", [])
            if not df_master.empty:
                df_master.columns = [str(c).strip().upper() for c in df_master.columns]
                st.session_state.df_stock_rot = df_master
                if "ROTATION" in df_master.columns:
                    st.session_state.rotation_directe = True
                else:
                    st.session_state.rotation_directe = False
                st.success("✅ Base Centrale chargée !")
            else:
                st.error("❌ Base Centrale vide. Importez via Admin Centrale d'abord.")
    
    with col_db2:
        if st.button("📥 Charger Master Ventes", use_container_width=True, type="primary"):
            from utils_gsheets import load_gs_data
            df_ventes = load_gs_data("Analyse_Ventes_Perf", "data/db_ventes_performance.csv", [])
            if not df_ventes.empty:
                df_ventes.columns = [str(c).strip().upper() for c in df_ventes.columns]
                st.session_state.df_sales_rot = df_ventes
                st.success("✅ Base Ventes chargée !")
            else:
                st.error("❌ Base Ventes vide. Importez via Admin Centrale d'abord.")
                
    st.divider()
    st.write("Ou importez manuellement :")
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
                df_st[col_st] = df_st[col_st].astype(str)
                df_sl_agg[col_sl] = df_sl_agg[col_sl].astype(str)
                df_merged = pd.merge(df_st, df_sl_agg, left_on=col_st, right_on=col_sl, how='left').fillna(0)
                df_merged['Rotation'] = df_merged[col_qty_sl] / (df_merged[col_qty_st] + 0.1)
                
                fig = px.scatter(df_merged, x=col_qty_st, y=col_qty_sl, hover_name=col_st, size='Rotation', color='Rotation')
                st.plotly_chart(fig, use_container_width=True)
                st.dataframe(df_merged.sort_values(by='Rotation'))
    else:
        st.warning("Veuillez importer vos données dans le premier onglet.")

# --- ONGLET 3 : PRODUITS STAGNANTS (ARRIVAGE) ---
with tab_stagnant:
    if "df_stock_rot" in st.session_state:
        df_st = st.session_state.df_stock_rot
        st.subheader("⏳ Analyse de Stagnation par Âge & Rotation")
        
        # Trouver les colonnes de date, de quantité et de prix potentielles
        date_cols = [c for c in df_st.columns if any(x in str(c).upper() for x in ["ARRIVAGE", "DATE", "CREATION", "DDP", "DDF"])]
        qty_cols = [c for c in df_st.columns if any(x in str(c).upper() for x in ["QTE", "QUANTITE", "STOCK"])]
        price_cols = [c for c in df_st.columns if any(x in str(c).upper() for x in ["PPA", "PRIX", "ACHAT"])]
        
        col_st1, col_st2 = st.columns(2)
        with col_st1:
            sel_date_col = st.selectbox("Sélectionner la colonne Date (Arrivage / Création)", date_cols or df_st.columns, key="sel_date_col")
            sel_qty_col = st.selectbox("Sélectionner la colonne Quantité (Stock)", qty_cols or df_st.columns, key="sel_qty_col")
        with col_st2:
            sel_price_col = st.selectbox("Sélectionner la colonne Prix (Optionnel, pour calcul valeur)", ["Aucun"] + price_cols + list(df_st.columns), key="sel_price_col")
            
        # Paramètres d'analyse
        st.markdown("#### ⚙️ Paramètres des Seuils de Stagnation")
        c_param1, c_param2 = st.columns(2)
        with c_param1:
            seuil_jours = c_param1.slider("Âge minimum du stock (jours)", 15, 730, 180, step=15, help="Les produits restés en stock plus de X jours sont considérés comme anciens.")
        with c_param2:
            seuil_rot = c_param2.slider("Taux de rotation maximum (stagnant)", 0.0, 10.0, 1.0, step=0.1, help="Taux de rotation sous lequel le produit est considéré stagnant.")
            
        # Traitement des données
        df_stag = df_st.copy()
        
        # Conversion de la date
        df_stag["DATE_PARSED"] = pd.to_datetime(df_stag[sel_date_col], errors='coerce')
        # Si aucun lot n'a de date, on calcule l'âge par rapport à aujourd'hui
        df_stag["AGE_JOURS"] = (datetime.now() - df_stag["DATE_PARSED"]).dt.days.fillna(0).astype(int)
        
        # Récupération ou calcul de la rotation
        if "ROTATION" not in df_stag.columns:
            # Si on a calculé la rotation par croisement de ventes
            if "df_sales_rot" in st.session_state:
                df_sl = st.session_state.df_sales_rot
                col_st_name = [c for c in df_stag.columns if "PRODUIT" in c or "DESIGNATION" in c][0] if [c for c in df_stag.columns if "PRODUIT" in c or "DESIGNATION" in c] else df_stag.columns[0]
                col_sl_name = [c for c in df_sl.columns if "PRODUIT" in c or "DESIGNATION" in c or "ARTICLE" in c][0] if [c for c in df_sl.columns if "PRODUIT" in c or "DESIGNATION" in c or "ARTICLE" in c] else df_sl.columns[0]
                col_qty_sl = [c for c in df_sl.columns if "QTE" in c or "QUANTITE" in c or "VENTE" in c][0] if [c for c in df_sl.columns if "QTE" in c or "QUANTITE" in c or "VENTE" in c] else df_sl.columns[0]
                
                df_sl_agg = df_sl.groupby(col_sl_name)[col_qty_sl].sum().reset_index()
                df_stag[col_st_name] = df_stag[col_st_name].astype(str)
                df_sl_agg[col_sl_name] = df_sl_agg[col_sl_name].astype(str)
                df_stag = pd.merge(df_stag, df_sl_agg, left_on=col_st_name, right_on=col_sl_name, how='left').fillna(0)
                df_stag['ROTATION'] = df_stag[col_qty_sl] / (df_stag[sel_qty_col] + 0.1)
            else:
                df_stag['ROTATION'] = 0.0
                st.info("ℹ️ Pour un calcul plus précis de la rotation, chargez le Master Ventes dans l'onglet Import.")
                
        # Filtre stagnant
        mask_stagnant = (df_stag["AGE_JOURS"] >= seuil_jours) & (df_stag["ROTATION"] <= seuil_rot)
        df_stagnant_final = df_stag[mask_stagnant].copy()
        
        # Calcul de la valeur stagnante
        valeur_totale_stagnante = 0.0
        valeur_col_str = ""
        if sel_price_col != "Aucun":
            try:
                df_stag["PRIX_NUM"] = pd.to_numeric(df_stag[sel_price_col], errors='coerce').fillna(0.0)
                df_stag["QTE_NUM"] = pd.to_numeric(df_stag[sel_qty_col], errors='coerce').fillna(0.0)
                df_stag["VALEUR_STAGNANTE"] = df_stag["PRIX_NUM"] * df_stag["QTE_NUM"]
                valeur_totale_stagnante = df_stag[mask_stagnant]["VALEUR_STAGNANTE"].sum()
                valeur_col_str = f"{valeur_totale_stagnante:,.2f} DA"
            except:
                valeur_col_str = "Erreur de calcul"
        else:
            valeur_col_str = "Non configuré"
            
        # KPI Cards
        st.markdown("#### 📊 Indicateurs de Performance Logistique")
        c_kpi1, c_kpi2, c_kpi3 = st.columns(3)
        c_kpi1.metric("Produits Stagnants Critiques", f"{len(df_stagnant_final)} articles", f"{(len(df_stagnant_final) / len(df_stag) * 100) if len(df_stag) > 0 else 0:.1f}% du total")
        c_kpi2.metric("Valeur Financière Dormante", valeur_col_str)
        c_kpi3.metric("Âge Moyen de Stagnation", f"{int(df_stagnant_final['AGE_JOURS'].mean()) if not df_stagnant_final.empty else 0} jours")
        
        # Graphique Plotly de Dispersion (Quadrant)
        st.markdown("#### 🗺️ Quadrant de Stagnation (Âge vs Rotation)")
        df_stag["Quadrant"] = "Star / Actif"
        df_stag.loc[(df_stag["AGE_JOURS"] >= seuil_jours) & (df_stag["ROTATION"] <= seuil_rot), "Quadrant"] = "🟥 Stagnant Critique"
        df_stag.loc[(df_stag["AGE_JOURS"] < seuil_jours) & (df_stag["ROTATION"] <= seuil_rot), "Quadrant"] = "🟧 Nouveau / Lent"
        df_stag.loc[(df_stag["AGE_JOURS"] >= seuil_jours) & (df_stag["ROTATION"] > seuil_rot), "Quadrant"] = "🟨 Ancien mais Actif"
        df_stag.loc[(df_stag["AGE_JOURS"] < seuil_jours) & (df_stag["ROTATION"] > seuil_rot), "Quadrant"] = "🟩 Vedette Rapide"
        
        prod_col_name = [c for c in df_st.columns if "PRODUIT" in c or "DESIGNATION" in c][0] if [c for c in df_st.columns if "PRODUIT" in c or "DESIGNATION" in c] else df_st.columns[0]
        
        fig_quad = px.scatter(
            df_stag,
            x="AGE_JOURS",
            y="ROTATION",
            color="Quadrant",
            size=df_stag[sel_qty_col].clip(lower=1),
            hover_name=prod_col_name,
            hover_data=[sel_qty_col],
            title="Cartographie Âge du Stock vs Taux de Rotation",
            labels={"AGE_JOURS": "Âge du Stock (Jours depuis arrivage)", "ROTATION": "Taux de Rotation"},
            color_discrete_map={
                "🟥 Stagnant Critique": "#ef4444",
                "🟧 Nouveau / Lent": "#f59e0b",
                "🟨 Ancien mais Actif": "#3b82f6",
                "🟩 Vedette Rapide": "#10b981",
                "Star / Actif": "#10b981"
            },
            template="plotly_dark"
        )
        fig_quad.add_vline(x=seuil_jours, line_dash="dash", line_color="#ef4444", annotation_text="Seuil Âge")
        fig_quad.add_hline(y=seuil_rot, line_dash="dash", line_color="#ef4444", annotation_text="Seuil Rotation")
        st.plotly_chart(fig_quad, use_container_width=True)
        
        # Liste des produits stagnants
        st.markdown("#### 📋 Liste détaillée des produits stagnants critiques")
        show_cols = [prod_col_name, sel_date_col, "AGE_JOURS", sel_qty_col, "ROTATION"]
        if sel_price_col != "Aucun" and "VALEUR_STAGNANTE" in df_stagnant_final.columns:
            show_cols.append("VALEUR_STAGNANTE")
            
        st.dataframe(
            df_stagnant_final[show_cols].sort_values(by="AGE_JOURS", ascending=False),
            use_container_width=True,
            hide_index=True
        )
        
        # Plan d'action IA
        if is_ia_enabled():
            if st.button("🤖 Générer un Plan de Déstockage IA (Date & Rotation)", key="btn_ia_stagnant"):
                list_stagnants = df_stagnant_final[prod_col_name].head(15).tolist()
                prompt = f"""En tant que consultant en logistique DarPharm, propose un plan d'action d'optimisation financière pour ces {len(df_stagnant_final)} produits stagnants critiques (présents en stock depuis plus de {seuil_jours} jours avec une rotation inférieure à {seuil_rot}) :
                Exemples : {list_stagnants}.
                Propose des stratégies précises : remises dégressives, offres groupées, négociations de retour fournisseur, ou stimulation des commerciaux avec primes."""
                with st.chat_message("assistant"):
                    analysis = ask_ai(prompt)
                    st.write(analysis)
                play_sound("ai")
    else:
        st.warning("Veuillez d'abord charger ou importer vos données dans le premier onglet.")
