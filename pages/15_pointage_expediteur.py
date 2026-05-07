import streamlit as st
import pandas as pd
from tinydb import TinyDB, Query
from datetime import datetime
import unicodedata
from utils import log_action

# --- CONFIGURATION ET BASE DE DONNÉES ---
db = TinyDB('db_pharmaciel.json')
table_expedition = db.table('pointages_expediteur')

st.header("📦 Pointage Expéditeur", divider="blue")

tab_pointage, tab_historique = st.tabs(["📝 Vérification et Dispatching", "📊 Historique des Expéditions"])

with tab_pointage:
    st.write("Ce module permet à l'expéditeur de vérifier les colis par rapport à la base LogiPharm et de les dispatcher par zone d'expédition.")

    # 1. Importation du fichier Excel
    uploaded_file = st.file_uploader("Importer l'export LogiPharm (Excel)", type=['xlsx', 'xls'])

    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            
            # Normalisation robuste des colonnes
            def clean_col(c):
                c = str(c).strip().lower()
                return ''.join(ch for ch in unicodedata.normalize('NFD', c) if unicodedata.category(ch) != 'Mn')
            
            df.columns = [clean_col(c) for c in df.columns]
            
            # Recherche des colonnes importantes (selon image fournie)
            cols_trouvees = {}
            for col in df.columns:
                if 'client' in col: cols_trouvees['client'] = col
                elif 'region' in col: cols_trouvees['region'] = col
                elif 'ref' in col: cols_trouvees['reference'] = col
                elif 'colis' in col: cols_trouvees['colis'] = col
                elif 'date' in col: cols_trouvees['date'] = col
                
            if 'client' in cols_trouvees and 'region' in cols_trouvees and 'reference' in cols_trouvees:
                
                # Préparation du dataframe propre
                df_clean = pd.DataFrame()
                df_clean['Client'] = df[cols_trouvees['client']]
                df_clean['Région'] = df[cols_trouvees['region']]
                df_clean['Référence'] = df[cols_trouvees['reference']]
                
                if 'colis' in cols_trouvees:
                    df_clean['Colis'] = pd.to_numeric(df[cols_trouvees['colis']], errors='coerce').fillna(0).astype(int)
                else:
                    df_clean['Colis'] = 0
                    
                if 'date' in cols_trouvees:
                    df_clean['Date'] = df[cols_trouvees['date']]
                else:
                    df_clean['Date'] = ""

                # Récupérer les colis déjà expédiés pour ne pas les pointer deux fois
                existing_refs = {item['reference'] for item in table_expedition.all()}
                df_clean['deja_expedie'] = df_clean['Référence'].astype(str).isin(existing_refs)

                # --- FILTRES ---
                col_a, col_b = st.columns(2)
                
                with col_a:
                    liste_regions = ["Toutes les régions"] + sorted(df_clean['Région'].dropna().unique().tolist())
                    region_sel = st.selectbox("📍 Filtrer par Zone d'Expédition (Région)", liste_regions)
                
                with col_b:
                    recherche_client = st.text_input("🔍 Rechercher un client ou une référence")

                # --- LOGIQUE DE FILTRAGE ---
                df_filtre = df_clean.copy()
                
                if region_sel != "Toutes les régions":
                    df_filtre = df_filtre[df_filtre['Région'] == region_sel]
                    
                if recherche_client:
                    mask = df_filtre.astype(str).apply(lambda x: x.str.contains(recherche_client, case=False, na=False)).any(axis=1)
                    df_filtre = df_filtre[mask]

                # Gestion de la sélection globale
                if 'sel_all_exp' not in st.session_state: st.session_state.sel_all_exp = False
                
                c_act1, c_act2 = st.columns([1, 4])
                with c_act1:
                    if st.button("✅ Tout Sélectionner" if not st.session_state.sel_all_exp else "⬜ Tout Désélectionner"):
                        st.session_state.sel_all_exp = not st.session_state.sel_all_exp
                        st.rerun()

                st.divider()
                st.subheader(f"📊 Colis à vérifier ({len(df_filtre)} lignes)")
                
                # --- AFFICHAGE ET POINTAGE ---
                df_view = df_filtre.copy()
                df_view.insert(0, "Prêt (Dispatcher)", st.session_state.sel_all_exp & ~df_view['deja_expedie'])
                
                # Statut pour affichage
                df_view['Statut'] = df_view['deja_expedie'].apply(lambda x: "📦 Déjà Expédié" if x else "⏳ En attente")
                
                # Formatter
                edited_df = st.data_editor(
                    df_view,
                    column_config={
                        "Prêt (Dispatcher)": st.column_config.CheckboxColumn("Vérifié", default=False),
                        "Statut": st.column_config.TextColumn("Statut", disabled=True),
                        "Client": st.column_config.TextColumn("Client", disabled=True),
                        "Région": st.column_config.TextColumn("Région", disabled=True),
                        "Référence": st.column_config.TextColumn("Référence", disabled=True),
                        "Colis": st.column_config.NumberColumn("Nombre de Colis", disabled=True),
                        "Date": st.column_config.TextColumn("Date", disabled=True),
                        "deja_expedie": None
                    },
                    hide_index=True,
                    use_container_width=True,
                    key=f"editor_expediteur_{region_sel}_{st.session_state.sel_all_exp}"
                )
                
                # Bouton d'enregistrement
                if st.button("🚀 Valider le Dispatching des colis sélectionnés", type="primary"):
                    factures_ok = edited_df[edited_df['Prêt (Dispatcher)'] == True]
                    
                    if not factures_ok.empty:
                        for _, row in factures_ok.iterrows():
                            # Ne pas ré-ajouter si déjà expédié
                            if not row['deja_expedie']:
                                table_expedition.insert({
                                    'date_dispatch': datetime.now().strftime("%d/%m/%Y %H:%M"),
                                    'reference': str(row['Référence']),
                                    'client': str(row['Client']),
                                    'region': str(row['Région']),
                                    'colis': int(row['Colis']),
                                    'statut': "Dispatché"
                                })
                        
                        try:
                            log_action(st.session_state.current_user['username'], f"Dispatching de {len(factures_ok)} commandes", "Pointage Expéditeur")
                        except:
                            pass
                            
                        st.success(f"✅ {len(factures_ok)} commandes validées et dispatchées vers leurs zones d'expédition !")
                        st.balloons()
                    else:
                        st.warning("Veuillez cocher les colis que vous avez vérifiés avant de valider.")

                # Statistiques
                st.divider()
                st.write("### 📈 Statistiques de la vue actuelle")
                colis_total = df_filtre['Colis'].sum()
                
                lignes_pointees = edited_df[edited_df['Prêt (Dispatcher)'] == True]
                colis_pointes = lignes_pointees['Colis'].sum() if not lignes_pointees.empty else 0
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Lignes Totales", len(df_filtre))
                c2.metric("Lignes Vérifiées", len(lignes_pointees))
                c3.metric("Colis Vérifiés / Total", f"{colis_pointes} / {colis_total}")
                    
            else:
                st.error(f"Colonnes nécessaires introuvables. Le fichier contient : {list(df.columns)}")
                st.info("Le fichier Excel LogiPharm doit contenir au moins les colonnes : Client, Région, Référence, Colis.")
                
        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier : {e}")

with tab_historique:
    st.subheader("📊 Historique du Dispatching (Expéditeur)")
    data_hist = table_expedition.all()
    if data_hist:
        df_hist = pd.DataFrame(data_hist)
        
        # Filtres d'historique
        h_col1, h_col2 = st.columns(2)
        with h_col1:
            liste_reg_hist = ["Toutes les régions"] + sorted(df_hist['region'].dropna().unique().tolist())
            hist_region = st.selectbox("Filtrer par région", liste_reg_hist, key="hist_reg")
        with h_col2:
            hist_search = st.text_input("Rechercher dans l'historique", key="hist_search")
            
        df_hist_view = df_hist.copy()
        if hist_region != "Toutes les régions":
            df_hist_view = df_hist_view[df_hist_view['region'] == hist_region]
        if hist_search:
            mask = df_hist_view.astype(str).apply(lambda x: x.str.contains(hist_search, case=False, na=False)).any(axis=1)
            df_hist_view = df_hist_view[mask]
            
        st.dataframe(df_hist_view.sort_values('date_dispatch', ascending=False), use_container_width=True)
        
        try:
            if st.session_state.current_user.get('role') == 'Admin':
                st.divider()
                if st.button("🗑️ Vider tout l'historique (Admin)", type="primary"):
                    table_expedition.truncate()
                    st.success("Historique de dispatching vidé avec succès.")
                    st.rerun()
        except:
            pass
    else:
        st.write("Aucun historique pour le moment.")
