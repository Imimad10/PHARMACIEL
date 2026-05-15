import streamlit as st
import pandas as pd
from tinydb import TinyDB, Query
from datetime import datetime
import unicodedata
import os
from utils import log_action

# --- CONFIGURATION ET BASE DE DONNÉES ---
from utils_gsheets import load_gs_data, save_gs_data, show_sync_ui
# --- CONFIGURATION ET BASE DE DONNÉES ---
DATA_DIR = "data_pointage"
LOGIPHARM_WORKSHEET = "Logipharm_Export"
LOGIPHARM_FALLBACK = os.path.join(DATA_DIR, "current_export.csv")
HISTORIQUE_WORKSHEET = "Historique_Pointage"
HISTORIQUE_FALLBACK = "data/db_pointage_hist.csv"

show_sync_ui(LOGIPHARM_WORKSHEET, LOGIPHARM_FALLBACK, [])
show_sync_ui(HISTORIQUE_WORKSHEET, HISTORIQUE_FALLBACK, ['date_dispatch', 'valide_par', 'reference', 'client', 'region', 'colis', 'statut'])

# Assurer l'existence du dossier data
os.makedirs(DATA_DIR, exist_ok=True)
COLS_HIST = ['date_dispatch', 'valide_par', 'reference', 'client', 'region', 'colis', 'statut']

st.header("📦 Pointage Expéditeur", divider="blue")

# Définition des onglets
tabs_labels = ["📝 En attente de Dispatching", "🚚 Commandes Validées", "📊 Historique Global", "⚙️ Administration"]
tab_pointage, tab_valides, tab_historique, tab_admin = st.tabs(tabs_labels)

# --- FONCTION DE NETTOYAGE DES COLONNES ---
def clean_col(c):
    c = str(c).strip().lower()
    return ''.join(ch for ch in unicodedata.normalize('NFD', c) if unicodedata.category(ch) != 'Mn')

# --- CHARGEMENT DES DONNÉES PERSISTANTES ---
def load_current_data():
    # On définit les colonnes qu'on s'attend à trouver (flexibilité)
    df = load_gs_data(LOGIPHARM_WORKSHEET, LOGIPHARM_FALLBACK, [])
    if not df.empty:
        df.columns = [clean_col(c) for c in df.columns]
        return df
    return None

# --- ONGLET ADMINISTRATION (UPLOAD) ---
with tab_admin:
    st.subheader("⚙️ Configuration du module")
    
    # Vérification du rôle admin (basé sur la session state définie dans app.py)
    is_user_admin = False
    try:
        if st.session_state.current_user.get('role') == 'Admin':
            is_user_admin = True
    except:
        pass

    if is_user_admin:
        uploaded_file = st.file_uploader("📤 Mettre à jour la base LogiPharm (Excel)", type=['xlsx', 'xls'])
        if uploaded_file:
            df_up = pd.read_excel(uploaded_file)
            save_gs_data(df_up, LOGIPHARM_WORKSHEET, LOGIPHARM_FALLBACK)
            st.success("✅ Base LogiPharm synchronisée sur GSheets !")
            log_action(st.session_state.current_user['username'], "Mise à jour GSheets LogiPharm", "Pointage Expéditeur")
            st.rerun()
        
        st.divider()
        if st.button("🗑️ Vider l'historique complet (GSheets)", type="primary"):
            save_gs_data(pd.DataFrame(columns=COLS_HIST), HISTORIQUE_WORKSHEET, HISTORIQUE_FALLBACK)
            st.success("Historique vidé sur GSheets.")
            st.rerun()
    else:
        st.warning("🔒 L'importation de fichiers est réservée aux administrateurs.")

# --- ONGLET POINTAGE ---
with tab_pointage:
    df_raw = load_current_data()
    
    if df_raw is not None:
        # Recherche des colonnes importantes
        cols_trouvees = {}
        for col in df_raw.columns:
            if 'client' in col: cols_trouvees['client'] = col
            elif 'region' in col: cols_trouvees['region'] = col
            elif 'ref' in col: cols_trouvees['reference'] = col
            elif 'colis' in col: cols_trouvees['colis'] = col
            elif 'date' in col: cols_trouvees['date'] = col

        if 'client' in cols_trouvees and 'region' in cols_trouvees and 'reference' in cols_trouvees:
            # Préparation du dataframe propre
            df_clean = pd.DataFrame()
            df_clean['Client'] = df_raw[cols_trouvees['client']]
            df_clean['Région'] = df_raw[cols_trouvees['region']]
            df_clean['Référence'] = df_raw[cols_trouvees['reference']]
            df_clean['Colis'] = pd.to_numeric(df_raw[cols_trouvees['colis']] if 'colis' in cols_trouvees else 0, errors='coerce').fillna(0).astype(int)
            
            # 1. RECHERCHE DE RÉGION PAR CLIENT
            st.write("### 🔍 Trouver la région d'un client")
            c_search_1, c_search_2 = st.columns([2, 1])
            with c_search_1:
                client_to_find = st.selectbox("Sélectionner un client pour voir sa région", 
                                              [""] + sorted(df_clean['Client'].unique().tolist()))
            with c_search_2:
                if client_to_find:
                    reg_found = df_clean[df_clean['Client'] == client_to_find]['Région'].iloc[0]
                    st.info(f"📍 Région : **{reg_found}**")

            st.divider()
            
            # 2. FILTRE PAR RÉGION
            st.write("### 🚚 Dispatching par zone")
            liste_regions = ["Toutes les régions"] + sorted(df_clean['Région'].dropna().unique().tolist())
            region_sel = st.selectbox("📍 Choisir la zone d'expédition pour commencer", liste_regions)

            # --- LOGIQUE DE DÉTECTION DES DOUBLONS AVEC HORAIRE ---
            # Récupérer l'historique
            df_history = load_gs_data(HISTORIQUE_WORKSHEET, HISTORIQUE_FALLBACK, COLS_HIST)
            hist_map = {}
            if not df_history.empty:
                hist_map = {str(row['reference']): row.to_dict() for _, row in df_history.iterrows()}

            def get_status_info(ref):
                ref_str = str(ref)
                if ref_str in hist_map:
                    item = hist_map[ref_str]
                    date_v = item.get('date_dispatch', 'Inconnue')
                    user_v = item.get('valide_par', 'N/A')
                    return True, f"✅ Validé le {date_v} par {user_v}"
                return False, "⏳ En attente"

            # Appliquer le statut
            status_results = df_clean['Référence'].apply(get_status_info)
            df_clean['deja_expedie'] = [x[0] for x in status_results]
            df_clean['Statut Info'] = [x[1] for x in status_results]

            # --- FILTRAGE ---
            df_filtre = df_clean.copy()
            if region_sel != "Toutes les régions":
                df_filtre = df_filtre[df_filtre['Région'] == region_sel]

            # FILTRE : On ne garde que ce qui n'est pas encore validé
            df_filtre = df_filtre[df_filtre['deja_expedie'] == False]

            # Barre de recherche globale (Client/Réf)
            search_query = st.text_input("🔍 Recherche rapide (Client ou N° de commande)")
            if search_query:
                mask = df_filtre.astype(str).apply(lambda x: x.str.contains(search_query, case=False, na=False)).any(axis=1)
                df_filtre = df_filtre[mask]

            # --- SÉCURITÉ : Pas de référence = Pas de validation ---
            # On ajoute une colonne pour indiquer si la validation est permise
            df_filtre['Peut_Valider'] = df_filtre['Référence'].apply(lambda x: pd.notna(x) and str(x).strip() != "")

            # Sélection globale (uniquement pour ceux qui peuvent valider)
            if 'sel_all_exp' not in st.session_state: st.session_state.sel_all_exp = False
            if st.button("✅ Sélectionner tout le secteur" if not st.session_state.sel_all_exp else "⬜ Désélectionner tout"):
                st.session_state.sel_all_exp = not st.session_state.sel_all_exp
                st.rerun()

            # --- DATA EDITOR ---
            df_view = df_filtre.copy()
            # Initialisation de la case à cocher (Sécurisée contre TypeError)
            if st.session_state.sel_all_exp:
                df_view.insert(0, "Vérifié", df_view['Peut_Valider'])
            else:
                df_view.insert(0, "Vérifié", False)

            edited_df = st.data_editor(
                df_view,
                column_config={
                    "Vérifié": st.column_config.CheckboxColumn("Vérifié", default=False),
                    "Client": st.column_config.TextColumn("Client", disabled=True),
                    "Région": st.column_config.TextColumn("Région", disabled=True),
                    "Référence": st.column_config.TextColumn("Référence (Obligatoire)", disabled=True),
                    "Colis": st.column_config.NumberColumn("Colis", disabled=True),
                    "Peut_Valider": None,
                    "deja_expedie": None,
                    "Statut Info": None
                },
                hide_index=True,
                use_container_width=True,
                key=f"editor_exp_{region_sel}_{st.session_state.sel_all_exp}"
            )

            # Validation
            if st.button("🚀 Valider le chargement / dispatching", type="primary", use_container_width=True):
                # On ne valide que si 'Vérifié' est coché ET qu'il y a une référence
                factures_to_validate = edited_df[(edited_df['Vérifié'] == True) & (edited_df['Peut_Valider'] == True)]
                
                if not factures_to_validate.empty:
                    current_user = st.session_state.current_user.get('username', 'Inconnu')
                    now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
                    
                    new_entries = []
                    for _, row in factures_to_validate.iterrows():
                        new_entries.append({
                            'date_dispatch': now_str,
                            'valide_par': current_user,
                            'reference': str(row['Référence']),
                            'client': str(row['Client']),
                            'region': str(row['Région']),
                            'colis': int(row['Colis']),
                            'statut': "Dispatché"
                        })
                    
                    df_history = pd.concat([df_history, pd.DataFrame(new_entries)], ignore_index=True)
                    save_gs_data(df_history, HISTORIQUE_WORKSHEET, HISTORIQUE_FALLBACK)
                    
                    st.success(f"✅ {len(factures_to_validate)} colis validés !")
                    log_action(current_user, f"Dispatching de {len(factures_to_validate)} commandes sur GSheets", "Pointage Expéditeur")
                    st.balloons()
                    st.rerun()
                else:
                    st.warning("Aucun nouveau colis sélectionné pour la validation.")

            # Stats
            st.divider()
            c1, c2, c3 = st.columns(3)
            colis_total = df_filtre['Colis'].sum()
            pointes = edited_df[edited_df['Vérifié'] == True]['Colis'].sum() if not edited_df.empty else 0
            c1.metric("Lignes (Secteur)", len(df_filtre))
            c2.metric("Colis (Secteur)", colis_total)
            c3.metric("Prêt à partir", f"{pointes} / {colis_total}")

        else:
            st.error("Colonnes LogiPharm manquantes dans le fichier (Client, Région, Référence).")
    else:
        st.info("👋 Bienvenue. Veuillez demander à l'administrateur d'uploader le dernier export LogiPharm dans l'onglet 'Administration'.")

# --- ONGLET COMMANDES VALIDÉES (AUJOURD'HUI) ---
with tab_valides:
    st.subheader("🚚 Commandes expédiées aujourd'hui")
    df_hist_today = load_gs_data(HISTORIQUE_WORKSHEET, HISTORIQUE_FALLBACK, COLS_HIST)
    if not df_hist_today.empty:
        today_str = datetime.now().strftime("%d/%m/%Y")
        # Filtrage par date du jour
        df_today = df_hist_today[df_hist_today['date_dispatch'].str.contains(today_str, na=False)]
        if not df_today.empty:
            st.dataframe(df_today.sort_values('date_dispatch', ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("Aucune commande n'a été validée aujourd'hui.")
    else:
        st.info("Aucune donnée d'expédition disponible.")

# --- HISTORIQUE GLOBAL ---
with tab_historique:
    st.subheader("📊 Archive complète des validations")
    df_hist_view = load_gs_data(HISTORIQUE_WORKSHEET, HISTORIQUE_FALLBACK, COLS_HIST)
    if not df_hist_view.empty:
        st.dataframe(df_hist_view.sort_values('date_dispatch', ascending=False), use_container_width=True, hide_index=True)
    else:
        st.write("L'historique est actuellement vide.")
