import streamlit as st
import pandas as pd
import os
import json
import unicodedata
from utils_ia import ask_ai, ask_ai_vision, is_ia_enabled, is_ia_scanner_enabled
import base64
import difflib

# --- CONFIGURATION ---
st.set_page_config(page_title="Inventaire Triple - Pharmaciel", layout="wide")

from utils_gsheets import load_gs_data, save_gs_data, show_sync_ui
# --- CONFIGURATION ---
st.set_page_config(page_title="Inventaire Triple - Pharmaciel", layout="wide")

MASTER_DIR = "data_inventaire_detail"
MASTER_WORKSHEET = "Master_Inventaire_Zone"
MASTER_FALLBACK = os.path.join(MASTER_DIR, "master_detail.csv")
INV_TRIPLE_WORKSHEET = "Inventaire_Triple"
INV_TRIPLE_FALLBACK = "data/db_inv_triple.csv"
os.makedirs(MASTER_DIR, exist_ok=True)

if 'current_user' not in st.session_state:
    st.warning("⚠️ Veuillez vous connecter depuis la page d'accueil.")
    st.stop()

COLS_MASTER = ["depot", "zone", "produit", "lot", "qte_logi", "colissage"]
COLS_INV_TRIPLE = ["produit", "lot", "tv", "tc", "mv", "mc", "col"]

show_sync_ui(MASTER_WORKSHEET, MASTER_FALLBACK, COLS_MASTER)
show_sync_ui(INV_TRIPLE_WORKSHEET, INV_TRIPLE_FALLBACK, COLS_INV_TRIPLE)

# --- STYLE CSS ---
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #ffffff;
        border-radius: 4px 4px 0 0;
        padding: 10px 20px;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] { background-color: #e7f3ff !important; color: #1877f2 !important; }
    .card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    .metric-card {
        background: #f1f8ff;
        padding: 15px;
        border-radius: 8px;
        border-left: 5px solid #1877f2;
    }
    </style>
""", unsafe_allow_html=True)

import re

def normalize_text(text):
    if not isinstance(text, str): return str(text)
    # Enlever les accents
    text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8').lower()
    # Remplacer les espaces multiples, retours à la ligne, etc. par un seul espace
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def robust_num(val):
    try:
        if pd.isna(val): return 0.0
        return float(val)
    except: return 0.0

@st.cache_data(ttl=3600)
def get_master_df():
    df = load_gs_data(MASTER_WORKSHEET, MASTER_FALLBACK, COLS_MASTER)
    if df.empty: return None
    
    # Nettoyage et mapping intelligent pour Excel
    mapping = {
        'dépôt': 'depot', 'depot': 'depot',
        'produit': 'produit', 'désignation': 'produit',
        'n°lot': 'lot', 'lot': 'lot', 'batch': 'lot',
        'quantité dépôt': 'qte_logi', 'qte.globale': 'qte_logi', 'quantité': 'qte_logi',
        'zone produit': 'zone', 'zone': 'zone',
        'colis': 'colissage', 'u/colis': 'colissage'
    }
    
    # On normalise les colonnes actuelles pour comparer
    current_cols = {normalize_text(c): c for c in df.columns}
    rename_dict = {}
    for key, target in mapping.items():
        if key in current_cols:
            rename_dict[current_cols[key]] = target
            
    df = df.rename(columns=rename_dict)
    
    # Si après renommage il manque des colonnes essentielles, on les crée vides
    for c in COLS_MASTER:
        if c not in df.columns: df[c] = ""
        
    df['produit'] = df['produit'].astype(str).str.upper()
    df['lot'] = df['lot'].astype(str).str.upper()
    df['qte_logi'] = df['qte_logi'].apply(robust_num)
    df['colissage'] = df['colissage'].apply(robust_num).replace(0, 1)
    return df[COLS_MASTER]

# --- INITIALISATION ---
df_master = get_master_df()
df_inv_triple = load_gs_data(INV_TRIPLE_WORKSHEET, INV_TRIPLE_FALLBACK, COLS_INV_TRIPLE)

# Reset forcé si changement de logique
if 'it_v9_zones' not in st.session_state:
    st.cache_data.clear()
    if 'inv_work_df' in st.session_state: del st.session_state.inv_work_df
    st.session_state.it_v9_zones = True
    st.rerun()

if "inv_work_df" not in st.session_state and df_master is not None:
    work_df = df_master.copy()
    work_df['Terrain (Vrac)'] = 0.0
    work_df['Terrain (Colis)'] = 0.0
    work_df['Mini (Colis)'] = 0.0
    
    # Fusion avec GSheets data
    if not df_inv_triple.empty:
        for _, entry in df_inv_triple.iterrows():
            mask = (work_df['produit'] == entry.get('produit')) & (work_df['lot'] == entry.get('lot'))
            if mask.any():
                work_df.loc[mask, 'Terrain (Vrac)'] = entry.get('tv', 0.0)
                work_df.loc[mask, 'Terrain (Colis)'] = entry.get('tc', 0.0)
                work_df.loc[mask, 'Mini (Colis)'] = entry.get('mc', 0.0)
                if 'col' in entry:
                    work_df.loc[mask, 'colissage'] = entry.get('col')
    
    st.session_state.inv_work_df = work_df

# --- INTERFACE ---
col_t1, col_t2 = st.columns([4, 1])
with col_t1:
    st.title("📋 Inventaire Triple & Confrontation Logipharm")
with col_t2:
    if st.button("♻️ Rafraîchir les données", use_container_width=True, help="Synchroniser avec les saisies des autres utilisateurs"):
        st.cache_data.clear()
        if 'inv_work_df' in st.session_state: del st.session_state.inv_work_df
        st.rerun()

if df_master is None:
    st.warning("⚠️ Aucun fichier Master détecté. Veuillez l'importer dans l'Admin Centrale.")
    tab_dash, tab_saisie, tab_analyse = None, None, None
else:
    user_role = st.session_state.current_user.get('role', 'Saisie')
    tab_titles = ["📈 Tableau de Bord", "⚡ Saisie & Grille", "📊 Analyse Écarts"]
    
    show_diag = user_role in ['Admin', 'Superviseur']
    show_gest = user_role == 'Admin'
    
    if show_diag: tab_titles.append("🔍 Diagnostic")
    if show_gest: tab_titles.append("⚙️ Gestion")
        
    # --- FICHES VIERGES ---
    with st.expander("🖨️ Impression des Fiches Terrain"):
        from utils_pdf import generate_blank_inventory_pdf
        st.write("Générer une fiche d'inventaire vierge basée sur le Master.")
        
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            type_fiche = st.radio("Type de Fiche :", ["Global", "Par Zone", "Par Dépôt"], horizontal=True, key="print_type_triple")
        
        df_print = df_master.copy()
        title_pdf = "Inventaire Triple"
        agents_str = ""
        
        with col_p2:
            if type_fiche == "Par Zone":
                zones = sorted([str(z) for z in df_print['zone'].dropna().unique()])
                sel_z = st.selectbox("Choisir Zone :", zones)
                df_print = df_print[df_print['zone'].astype(str) == sel_z]
                title_pdf += f" - Zone {sel_z}"
                
                # Récupération des agents affectés à cette zone
                from utils_gsheets import DB_USERS_WORKSHEET, DB_USERS_FALLBACK
                df_users = load_gs_data(DB_USERS_WORKSHEET, DB_USERS_FALLBACK, ["username", "nom", "prenom", "zone"])
                if not df_users.empty and 'zone' in df_users.columns:
                    target_z = str(sel_z).strip().upper()
                    u_df = df_users.copy()
                    u_df['zone_norm'] = u_df['zone'].astype(str).str.strip().str.upper()
                    zone_users = u_df[u_df['zone_norm'] == target_z]
                    if not zone_users.empty:
                        names = [f"{u['nom']} {u['prenom']}".strip() or u['username'] for _, u in zone_users.iterrows()]
                        agents_str = "Agents affectés : " + ", ".join(names)

            elif type_fiche == "Par Dépôt":
                depots = sorted([str(d) for d in df_print['depot'].dropna().unique()])
                sel_d = st.selectbox("Choisir le Dépôt :", depots)
                df_print = df_print[df_print['depot'].astype(str) == sel_d]
                title_pdf += f" - Dépôt {sel_d}"
        
        # Tri alphabétique
        df_print = df_print.sort_values(by='produit')
        
        cols_to_print = [('produit', 'Produit', 55), ('lot', 'Lot', 28)]
        pdf_bytes = generate_blank_inventory_pdf(df_print, "Triple", cols_to_print, subtitle=agents_str)
        
        st.download_button(
            "📥 Télécharger la Fiche Vierge (PDF)",
            pdf_bytes,
            f"Fiche_Vierge_Triple_{type_fiche}.pdf",
            "application/pdf",
            use_container_width=True,
            key="btn_print_triple"
        )

    tabs = st.tabs(tab_titles)
    
    # Assignation robuste par nom
    tab_dash = tabs[tab_titles.index("📈 Tableau de Bord")]
    tab_saisie = tabs[tab_titles.index("⚡ Saisie & Grille")]
    tab_analyse = tabs[tab_titles.index("📊 Analyse Écarts")]
    tab_diag = tabs[tab_titles.index("🔍 Diagnostic")] if show_diag else None
    tab_gest = tabs[tab_titles.index("⚙️ Gestion")] if show_gest else None

# --- FONCTION FILTRAGE ZONES ---
def get_user_data():
    df = st.session_state.inv_work_df.copy()
    user_role = st.session_state.current_user.get('role', 'Saisie')
    user_zone = str(st.session_state.current_user.get('zone', 'Aucune')).strip().upper()
    
    if user_role not in ['Admin', 'Superviseur']:
        if user_zone == 'AUCUNE' or not user_zone:
            # Si aucune zone assignée, on retourne un DF vide
            return df.iloc[0:0]
            
        if 'zone' in df.columns:
            # Filtre robuste : si la zone assignée (ex: "A") est contenue dans la zone Excel (ex: "1 a", "a")
            df = df[df['zone'].astype(str).str.upper().str.contains(user_zone, na=False, regex=False)]
    return df

# --- TABLEAU DE BORD ---
if df_master is not None and tab_dash:
    with tab_dash:
        st.subheader("📈 Tableau de Bord - Inventaire")
        dash_df = get_user_data()
        
        if dash_df.empty:
            st.info("Aucune donnée disponible ou aucune zone ne vous est assignée.")
        else:
            total_items = len(dash_df)
            
            # Un item est considéré "compté" s'il a une quantité saisie
            dash_df['Saisi'] = (dash_df['Terrain (Vrac)'] > 0) | (dash_df['Terrain (Colis)'] > 0) | (dash_df['Mini (Colis)'] > 0)
            items_counted = dash_df['Saisi'].sum()
            progress = (items_counted / total_items) * 100 if total_items > 0 else 0
            
            st.markdown(f"**Progression du comptage ({items_counted} / {total_items} produits)**")
            st.progress(progress / 100)
            
            c1, c2, c3 = st.columns(3)
            c1.metric("📦 Produits Totaux (Votre zone)", total_items)
            c2.metric("✅ Produits Comptés", items_counted)
            c3.metric("⏳ Reste à compter", total_items - items_counted)
            
            st.divider()
            st.write("### 📍 Répartition par Zone")
            zone_counts = dash_df.groupby('zone')['produit'].count().reset_index()
            zone_counts.columns = ['Zone', 'Nombre de Produits']
            st.dataframe(zone_counts, use_container_width=True)

# Tab admin supprimé. La gestion des zones et de l'import master se fait dans Admin Centrale.

# --- SAISIE ---
if df_master is not None and tab_saisie:
    with tab_saisie:
        st.markdown("### ⚡ Saisie Libre & Grille")
        
        # --- AI VISION SCANNER ---
        if is_ia_scanner_enabled():
            with st.expander("📷 Scanner la marchandise avec l'IA", expanded=False):
                c_img1, c_img2 = st.columns(2)
                img_cam = c_img1.camera_input("Prendre une photo du produit", key="cam_triple")
                img_file = c_img2.file_uploader("Ou importer une image", type=['jpg', 'jpeg', 'png'], key="file_up_triple")
                img_to_use = img_cam if img_cam else img_file
                
                if img_to_use and st.button("🔍 Identifier et Extraire", use_container_width=True, type="primary"):
                    base64_img = base64.b64encode(img_to_use.getvalue()).decode("utf-8")
                    prompt = 'Extrais les informations de ce produit ou vignette. Renvoie UNIQUEMENT un objet JSON avec les clés exactes : "designation" (nom du médicament/produit), "lot" (numéro de lot). Si invisible, mets "".'
                    with st.spinner("L'IA analyse l'image..."):
                        resp = ask_ai_vision(prompt, base64_img)
                        try:
                            match = re.search(r'```json(.*?)```', resp, re.DOTALL)
                            if match: resp = match.group(1)
                            else:
                                start = resp.find('{')
                                end = resp.rfind('}') + 1
                                if start != -1 and end != 0: resp = resp[start:end]
                            
                            data = json.loads(resp)
                            st.session_state['ai_scan_triple'] = data
                            st.success(f"✅ Détection : {data.get('designation')} (Lot: {data.get('lot')})")
                        except Exception as e:
                            st.error("Lecture échouée. Essayez une image plus nette.")

        ai_data_triple = st.session_state.get('ai_scan_triple', {})

        # Filtres
        f1, f2, f3 = st.columns(3)
        disp_df = get_user_data()
        
        if disp_df.empty:
            st.warning("Aucun produit à afficher. Vérifiez qu'une zone vous a été assignée.")
        else:
            depots = ["Tous"] + sorted(disp_df['depot'].dropna().unique().tolist()) if 'depot' in disp_df.columns else ["Tous"]
            sel_depot = f1.selectbox("Filtrer Dépôt", depots)
            
            zones = ["Toutes"] + sorted(disp_df['zone'].dropna().unique().tolist()) if 'zone' in disp_df.columns else ["Toutes"]
            sel_zone = f2.selectbox("Filtrer Zone", zones)
            
            search_def = ""
            if ai_data_triple.get('designation'):
                # Nettoyage et matching intelligent pour la recherche par défaut
                target_raw = str(ai_data_triple['designation']).upper()
                def normalize_name(text):
                    t = str(text).upper().replace(' ', '')
                    t = re.sub(r'1000MG', '1G', t)
                    t = re.sub(r'1000UI', '1MUI', t)
                    return t
                target_norm = normalize_name(target_raw)
                nums_target = set(re.findall(r'\d+', target_norm))
                
                best_match = None
                best_score = 0
                prods = disp_df['produit'].dropna().unique().tolist()
                for s in prods:
                    s_norm = normalize_name(s)
                    ratio = difflib.SequenceMatcher(None, target_norm, s_norm).ratio()
                    nums_candidate = set(re.findall(r'\d+', s_norm))
                    if nums_target and not nums_target.intersection(nums_candidate): ratio -= 0.4
                    if nums_target and nums_target.intersection(nums_candidate): ratio += 0.2
                    if ratio > best_score:
                        best_score = ratio
                        best_match = s
                if best_match and best_score > 0.4:
                    search_def = best_match

            search = st.text_input("Recherche Produit / Lot", value=search_def)
            if search and ai_data_triple:
                if st.button("❌ Effacer la recherche (Scan)"):
                    if 'ai_scan_triple' in st.session_state: del st.session_state['ai_scan_triple']
                    st.rerun()
            
            # Filtrage sécurisé
            if sel_depot != "Tous" and 'depot' in disp_df.columns: 
                disp_df = disp_df[disp_df['depot'] == sel_depot]
            if sel_zone != "Toutes" and 'zone' in disp_df.columns: 
                disp_df = disp_df[disp_df['zone'] == sel_zone]
            if search: 
                disp_df = disp_df[disp_df['produit'].str.contains(search, case=False, na=False) | disp_df['lot'].str.contains(search, case=False, na=False)]
            
            # Calculs
            c = disp_df['colissage']
            disp_df['Total Réel'] = disp_df['Terrain (Vrac)'] + (disp_df['Terrain (Colis)'] * c) + (disp_df['Mini (Colis)'] * c)
            disp_df['Écart'] = disp_df['Total Réel'] - disp_df['qte_logi']
            
            # Grille
            mcols = ['depot', 'zone', 'produit', 'lot', 'qte_logi', 'colissage', 'Terrain (Vrac)', 'Terrain (Colis)', 'Mini (Colis)', 'Total Réel', 'Écart']
            # Sécurité si une colonne manque
            mcols = [c for c in mcols if c in disp_df.columns]
            disp_df = disp_df[mcols]
            
            edited = st.data_editor(
                disp_df,
                column_config={
                    "depot": st.column_config.TextColumn("Dépôt", disabled=True),
                    "zone": st.column_config.TextColumn("Zone", disabled=True),
                    "produit": st.column_config.TextColumn("Produit", disabled=True),
                "lot": st.column_config.TextColumn("Lot", disabled=True),
                "qte_logi": st.column_config.NumberColumn("Stock Logi", disabled=True, help="Quantité Dépôt du Master"),
                "colissage": st.column_config.NumberColumn("U/Colis ✏️", disabled=False, min_value=1, help="Modifiable si l'export Logipharm est faux"),
                "Total Réel": st.column_config.NumberColumn("Total", disabled=True),
                "Écart": st.column_config.NumberColumn("Écart", disabled=True, format="%+.0f"),
            },
            num_rows="fixed",
            key="editor_v7",
            use_container_width=True
        )
        
        if st.button("💾 Enregistrer les modifications", type="primary"):
            # Comparaison pour ne sauvegarder que les lignes modifiées
            try:
                # pandas compare() faille si les types ne sont pas strictement identiques, on utilise un check manuel
                # On compare edited et disp_df sur les colonnes modifiables
                cols_to_check = ['Terrain (Vrac)', 'Terrain (Colis)', 'Mini (Colis)', 'colissage']
                
                # S'assurer que les index sont alignés
                changed_indices = []
                for idx in edited.index:
                    if idx in disp_df.index:
                        for col in cols_to_check:
                            if col in edited.columns and col in disp_df.columns:
                                if edited.loc[idx, col] != disp_df.loc[idx, col]:
                                    changed_indices.append(idx)
                                    break
                                    
                if not changed_indices:
                    st.info("Aucune modification détectée.")
                else:
                    for idx in changed_indices:
                        row = edited.loc[idx]
                        # Update session state
                        st.session_state.inv_work_df.loc[idx, 'Terrain (Vrac)'] = row['Terrain (Vrac)']
                        st.session_state.inv_work_df.loc[idx, 'Terrain (Colis)'] = row['Terrain (Colis)']
                        st.session_state.inv_work_df.loc[idx, 'Mini (Colis)'] = row['Mini (Colis)']
                        if 'colissage' in row:
                            st.session_state.inv_work_df.loc[idx, 'colissage'] = row['colissage']
                        
                        # Update df_inv_triple for saving
                        new_entry = {
                            'produit': row['produit'], 'lot': row['lot'],
                            'tv': float(row['Terrain (Vrac)']), 'tc': float(row['Terrain (Colis)']),
                            'mv': 0.0, 'mc': float(row['Mini (Colis)']), # mv conservé à 0 pour la BDD
                            'col': float(row['colissage']) if 'colissage' in row else 1.0
                        }
                        
                        # Upsert in df_inv_triple
                        mask = (df_inv_triple['produit'] == row['produit']) & (df_inv_triple['lot'] == row['lot'])
                        if mask.any():
                            for k, v in new_entry.items():
                                df_inv_triple.loc[mask, k] = v
                        else:
                            df_inv_triple = pd.concat([df_inv_triple, pd.DataFrame([new_entry])], ignore_index=True)
                    
                    save_gs_data(df_inv_triple, INV_TRIPLE_WORKSHEET, INV_TRIPLE_FALLBACK)
                    st.success(f"✅ {len(changed_indices)} modification(s) enregistrée(s) sur GSheets !")
                    st.rerun()
            except Exception as e:
                st.error(f"Erreur lors de la sauvegarde: {e}")

# --- ANALYSE ---
if df_master is not None and tab_analyse:
    with tab_analyse:
        st.subheader("📊 Analyse des Écarts")
        res_df = get_user_data()
        
        if res_df.empty:
            st.warning("Aucune donnée à analyser pour vos zones.")
        else:
            c = res_df['colissage']
            res_df['Total'] = res_df['Terrain (Vrac)'] + (res_df['Terrain (Colis)'] * c) + (res_df['Mini (Colis)'] * c)
            res_df['Ecart'] = res_df['Total'] - res_df['qte_logi']
            
            diff = res_df[res_df['Ecart'] != 0].copy()
            
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("📦 Nombre d'écarts", len(diff))
            col_m2.metric("🔴 Manquants (Valeur négative)", len(diff[diff['Ecart'] < 0]))
            col_m3.metric("🟢 Excédents (Valeur positive)", len(diff[diff['Ecart'] > 0]))
            
            st.write("Détail des écarts (Surligné en rouge = Manquant, Vert = Surplus) :")
            
            def highlight_ecart(row):
                if row['Ecart'] < 0: return ['background-color: rgba(255, 99, 132, 0.2)'] * len(row)
                elif row['Ecart'] > 0: return ['background-color: rgba(75, 192, 192, 0.2)'] * len(row)
                return [''] * len(row)
                
            disp_diff = diff[['depot', 'zone', 'produit', 'lot', 'qte_logi', 'colissage', 'Total', 'Ecart']]
            # Si zone n'existe pas, on l'enlève
            disp_diff = disp_diff[[col for col in disp_diff.columns if col in diff.columns]]
            
            st.dataframe(disp_diff.style.apply(highlight_ecart, axis=1), use_container_width=True)

            # --- ANALYSE IA ---
            if is_ia_enabled():
                st.markdown("---")
                st.container(border=True)
                st.subheader("🤖 Assistant IA d'Analyse (BETA)")
                st.info("L'Intelligence Artificielle peut analyser vos écarts pour détecter des anomalies récurrentes (vols, erreurs de lot, problèmes de colissage).")
                if st.button("🧠 Générer un rapport d'analyse IA", use_container_width=True, type="primary"):
                    with st.spinner("L'IA examine vos données (cela peut prendre quelques secondes)..."):
                        # On limite à 20 écarts pour ne pas surcharger le prompt
                        ecarts_json = diff[['produit', 'lot', 'qte_logi', 'Total', 'Ecart']].head(20).to_dict('records')
                        prompt = f"Tu es un expert en logistique pharmaceutique. Voici les écarts de stock constatés aujourd'hui : {ecarts_json}. Identifie les causes probables (erreur de conversion unité/colis, erreur de saisie, péremption, etc.) et donne 3 conseils précis pour régler ces écarts."
                        reponse = ask_ai(prompt)
                        st.success("✅ Analyse terminée")
                        st.write(reponse)

# --- DIAGNOSTIC ---
if df_master is not None and tab_diag:
    with tab_diag:
        st.subheader("🔍 Diagnostic Technique des Colonnes")
        st.info("Cet onglet permet de vérifier si les colonnes de votre fichier Excel ont été correctement identifiées par le système.")
        
        c1, c2 = st.columns(2)
        with c1:
            st.write("**Colonnes brutes détectées :**")
            st.write(list(df_master.columns))
        
        with c2:
            st.write("**Aperçu des données critiques :**")
            st.dataframe(df_master[['depot', 'produit', 'lot', 'qte_logi']].head(), use_container_width=True)
            
        st.divider()
        st.write("### 🛠️ Structure complète du Master")
        st.dataframe(df_master, use_container_width=True)

# --- GESTION ---
if df_master is not None and tab_gest:
    with tab_gest:
        st.subheader("⚙️ Gestion de l'Inventaire Triple")
        st.write("Espace réservé aux administrateurs pour la clôture et la maintenance.")
        
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.markdown("### 📥 Rapports & Exports")
            if st.button("📄 Générer Rapport PDF des Écarts", use_container_width=True):
                # Calcul des écarts pour le rapport
                res_df = st.session_state.inv_work_df.copy()
                c = res_df['colissage']
                res_df['Total'] = res_df['Terrain (Vrac)'] + (res_df['Terrain (Colis)'] * c) + (res_df['Mini (Colis)'] * c)
                res_df['Ecart'] = res_df['Total'] - res_df['qte_logi']
                diff_df = res_df[res_df['Ecart'] != 0].copy()
                
                if diff_df.empty:
                    st.success("Aucun écart à signaler ! L'inventaire est parfait.")
                else:
                    from utils_pdf import generate_inventory_report_pdf
                    pdf_bytes = generate_inventory_report_pdf(diff_df, "RAPPORT D'INVENTAIRE TRIPLE")
                    st.download_button(
                        "📥 Télécharger le Rapport PDF",
                        pdf_bytes,
                        "Rapport_Ecarts_Triple.pdf",
                        "application/pdf",
                        use_container_width=True
                    )

        with col_g2:
            st.markdown("### ⚠️ Maintenance")
            
            # Utilisation de st.expander pour sécuriser les boutons destructifs
            with st.expander("🗑️ Actions Destructives"):
                st.warning("Ces actions modifient définitivement les données sur Google Sheets.")
                
                if st.button("🔄 Réinitialiser les Saisies (Vider)", use_container_width=True):
                    # On ne vide que les saisies, pas le Master
                    empty_saisie = pd.DataFrame(columns=COLS_INV_TRIPLE)
                    save_gs_data(empty_saisie, INV_TRIPLE_WORKSHEET, INV_TRIPLE_FALLBACK)
                    st.cache_data.clear()
                    if 'inv_work_df' in st.session_state: del st.session_state.inv_work_df
                    st.success("✅ Toutes les saisies terrain ont été effacées.")
                    st.rerun()

                if st.button("🔴 Supprimer tout (Saisies + Master)", use_container_width=True):
                    save_gs_data(pd.DataFrame(columns=COLS_INV_TRIPLE), INV_TRIPLE_WORKSHEET, INV_TRIPLE_FALLBACK)
                    save_gs_data(pd.DataFrame(columns=COLS_MASTER), MASTER_WORKSHEET, MASTER_FALLBACK)
                    st.cache_data.clear()
                    if 'inv_work_df' in st.session_state: del st.session_state.inv_work_df
                    st.success("✅ Inventaire et Master supprimés.")
                    st.rerun()

        st.divider()
        st.info("💡 Les modifications effectuées ici ne ciblent que les feuilles (worksheets) spécifiées ('Inventaire_Triple' ou 'Master_Inventaire_Zone') et ne touchent pas au reste de votre document Google Sheets.")
