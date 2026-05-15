import streamlit as st
import pandas as pd
from utils_gsheets import load_gs_data
from utils_themes import load_themes_db, apply_theme_css

st.set_page_config(page_title="Base de Données IA - Pharmaciel", layout="wide")

_tdb = load_themes_db()
fluffy = next((t for t in _tdb["themes"] if t["id"] == "theme_darpharm_fluffy"), None)
apply_theme_css(fluffy)

st.markdown("""
<div style="background: linear-gradient(135deg, #5b6cf9 0%, #a272ff 100%); padding: 20px; border-radius: 15px; margin-bottom: 25px; color: white;">
    <h1 style="margin: 0; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);">🧠 Base d'Apprentissage IA</h1>
    <p style="margin: 0; opacity: 0.9;">Registre global de toutes les extractions et lectures effectuées par l'IA sur l'ensemble de la plateforme.</p>
</div>
""", unsafe_allow_html=True)

DB_IA_SCANS = "data/db_ia_scans.csv"
COLS_IA_SCANS = ["date_scan", "designation", "lot", "ddp", "ppa", "shp", "couleur"]

# Permet d'actualiser la vue en temps réel
if st.button("🔄 Actualiser les données"):
    st.rerun()

df_ia = load_gs_data("IA_Scans", DB_IA_SCANS, COLS_IA_SCANS)

if not df_ia.empty:
    # Quelques statistiques rapides
    st.markdown("### 📊 Statistiques de l'IA")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total des Scans Validés", len(df_ia))
    with col2:
        st.metric("Produits Uniques Identifiés", df_ia['designation'].nunique())
    with col3:
        if 'date_scan' in df_ia.columns and not df_ia['date_scan'].empty:
            st.metric("Dernier Scan le", str(df_ia['date_scan'].max()).split(' ')[0])
            
    st.divider()
    
    st.subheader("📚 Données Collectées (Toute la plateforme)")
    
    # Filtres
    recherche = st.text_input("🔍 Rechercher un produit ou un lot dans la base IA...")
    df_show = df_ia.copy()
    if recherche:
        df_show = df_show[df_show.apply(lambda row: row.astype(str).str.contains(recherche, case=False).any(), axis=1)]
        
    st.dataframe(df_show.sort_values("date_scan", ascending=False), use_container_width=True, height=500)
    
    csv = df_ia.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Exporter la base globale IA (CSV)", csv, "base_ia_globale.csv", "text/csv", type="primary")
else:
    st.info("La base de données de l'IA est actuellement vide. Les données apparaitront ici dès que l'IA sera utilisée dans l'application.")
