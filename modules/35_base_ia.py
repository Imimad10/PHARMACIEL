import streamlit as st
import pandas as pd
import uuid
import json
from datetime import datetime
from utils_gsheets import load_gs_data, save_gs_data
from utils_themes import load_themes_db, apply_theme_css
from utils_ia import ask_ai, is_ia_enabled

st.set_page_config(page_title="Base de Données IA - Pharmaciel", layout="wide")

_tdb = load_themes_db()
fluffy = next((t for t in _tdb["themes"] if t["id"] == "theme_darpharm_fluffy"), None)
apply_theme_css(fluffy)

st.markdown("""
<div style="background: linear-gradient(135deg, #5b6cf9 0%, #a272ff 100%); padding: 20px; border-radius: 15px; margin-bottom: 25px; color: white;">
    <h1 style="margin: 0; text-shadow: 1px 1px 2px rgba(0,0,0,0.2);">🧠 Centre d'Apprentissage IA</h1>
    <p style="margin: 0; opacity: 0.9;">Consultez ce que l'IA a collecté, analysez ses découvertes et entraînez-la pour de meilleures performances futures.</p>
</div>
""", unsafe_allow_html=True)

DB_IA_SCANS = "data/db_ia_scans.csv"
COLS_IA_SCANS = ["date_scan", "designation", "lot", "ddp", "ppa", "shp", "couleur"]

DB_IA_RULES = "data/db_ia_rules.csv"
COLS_IA_RULES = ["id", "mot_cle", "instruction", "date_creation", "actif"]

df_ia = load_gs_data("IA_Scans", DB_IA_SCANS, COLS_IA_SCANS)
df_rules = load_gs_data("IA_Rules", DB_IA_RULES, COLS_IA_RULES)

tabs = st.tabs(["📚 Données Collectées", "📈 Analyses & Déductions", "🎓 Entraîner l'IA (Règles)"])

with tabs[0]:
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("🔄 Actualiser les données", use_container_width=True):
            st.rerun()

    if not df_ia.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total des Scans Validés", len(df_ia))
        c2.metric("Produits Uniques Identifiés", df_ia['designation'].nunique())
        if 'date_scan' in df_ia.columns and not df_ia['date_scan'].empty:
            c3.metric("Dernier Scan le", str(df_ia['date_scan'].max()).split(' ')[0])
                
        st.divider()
        
        recherche = st.text_input("🔍 Rechercher un produit ou un lot dans la base IA...")
        df_show = df_ia.copy()
        if recherche:
            df_show = df_show[df_show.apply(lambda row: row.astype(str).str.contains(recherche, case=False).any(), axis=1)]
            
        st.dataframe(df_show.sort_values("date_scan", ascending=False), use_container_width=True, height=500)
        
        csv = df_ia.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Exporter la base globale IA (CSV)", csv, "base_ia_globale.csv", "text/csv", type="primary")
    else:
        st.info("La base de données de l'IA est actuellement vide.")

with tabs[1]:
    st.subheader("Ce que l'IA a appris du stock")
    if df_ia.empty:
        st.warning("Pas assez de données pour générer des analyses.")
    else:
        c1, c2 = st.columns([2, 1])
        with c1:
            st.markdown("Top 10 des produits les plus fréquemment scannés :")
            top_prods = df_ia['designation'].value_counts().head(10).reset_index()
            top_prods.columns = ['Produit', 'Nombre de scans']
            st.dataframe(top_prods, use_container_width=True)
            
        with c2:
            st.markdown("Répartition par Couleur Vignette :")
            top_colors = df_ia['couleur'].value_counts().reset_index()
            top_colors.columns = ['Couleur', 'Quantité']
            st.dataframe(top_colors, use_container_width=True)
            
        st.divider()
        st.markdown("### 🤖 Demander à l'IA d'analyser ses propres données")
        if is_ia_enabled():
            if st.button("🧠 Générer le rapport d'Intelligence", type="primary"):
                with st.spinner("Analyse approfondie en cours... (Lecture de la base de données IA)"):
                    sample_data = df_ia.tail(100).to_dict(orient="records")
                    prompt = f"""
                    Tu es l'IA de DarPharm. Voici un échantillon de tes 100 dernières lectures de vignettes (JSON) :
                    {json.dumps(sample_data, ensure_ascii=False)}
                    
                    Rédige un rapport très professionnel de 3 paragraphes pour l'administrateur :
                    1. Résume ce que tu as vu récemment (types de produits, tendances, fréquence des couleurs).
                    2. Identifie s'il y a des anomalies récurrentes ou des choses remarquables (ex: des dates de péremption courtes, un laboratoire dominant).
                    3. Propose une "Règle Métier" pertinente que l'admin devrait t'apprendre pour que tu sois encore plus performant à l'avenir.
                    """
                    try:
                        rep = ask_ai(prompt)
                        st.success("Analyse terminée !")
                        st.info(rep)
                    except Exception as e:
                        st.error(f"Erreur lors de l'analyse : {e}")
        else:
            st.warning("L'IA n'est pas activée ou la clé API est manquante.")

with tabs[2]:
    st.subheader("Entraîner l'IA pour le futur")
    st.markdown("Si l'IA fait des erreurs répétitives sur certains produits ou labos, vous pouvez lui donner des **règles strictes** qu'elle devra appliquer automatiquement lors de ses prochaines lectures.")
    
    with st.expander("➕ Ajouter une nouvelle règle d'apprentissage", expanded=True):
        with st.form("form_add_rule"):
            mot_cle = st.text_input("Mot-clé déclencheur (ex: 'LAVIDA', 'ASPEGIC', 'SAIDAL')")
            instruction = st.text_area("Instruction stricte à donner à l'IA", placeholder="Exemple : Si tu vois ce mot-clé, le SHP est TOUJOURS de 1.5 DA, et tu dois ignorer le logo du laboratoire.")
            
            if st.form_submit_button("🎓 Enseigner cette règle à l'IA", type="primary", use_container_width=True):
                if mot_cle and instruction:
                    new_rule = pd.DataFrame([{
                        "id": str(uuid.uuid4())[:8],
                        "mot_cle": mot_cle.upper(),
                        "instruction": instruction,
                        "date_creation": datetime.now().strftime("%Y-%m-%d"),
                        "actif": True
                    }])
                    df_rules = pd.concat([df_rules, new_rule], ignore_index=True)
                    save_gs_data(df_rules, "IA_Rules", DB_IA_RULES)
                    st.success("Nouvelle règle ajoutée ! L'IA s'en souviendra lors du prochain pointage.")
                    st.rerun()
                else:
                    st.error("Veuillez remplir tous les champs.")

    if not df_rules.empty:
        st.markdown("### Règles actuellement en mémoire :")
        
        # Modification dynamique des statuts
        edited_rules = st.data_editor(
            df_rules,
            use_container_width=True,
            column_config={
                "id": st.column_config.TextColumn("ID", disabled=True),
                "mot_cle": st.column_config.TextColumn("Mot Clé", disabled=True),
                "instruction": st.column_config.TextColumn("Instruction / Apprentissage"),
                "date_creation": st.column_config.TextColumn("Date", disabled=True),
                "actif": st.column_config.CheckboxColumn("Actif")
            }
        )
        if st.button("💾 Sauvegarder les modifications des règles", use_container_width=True):
            save_gs_data(edited_rules, "IA_Rules", DB_IA_RULES)
            st.success("Modifications enregistrées.")
            st.rerun()
    else:
        st.info("L'IA n'a reçu aucune règle métier personnalisée pour le moment.")
