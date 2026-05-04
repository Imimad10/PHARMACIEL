import streamlit as st
import pandas as pd
import os
import unicodedata
from utils_ia import ask_ai, is_ia_enabled

# --- 1. CONFIGURATION & CHEMINS ---
if "DATA_DIR" not in st.session_state:
    st.session_state.DATA_DIR = "data_inventaire"
    st.session_state.MASTER_PATH = os.path.join(st.session_state.DATA_DIR, "master.xlsx")
    st.session_state.SAISIE_PATH = os.path.join(st.session_state.DATA_DIR, "saisie.csv")

os.makedirs(st.session_state.DATA_DIR, exist_ok=True)

# --- 2. FONCTIONS TECHNIQUES ---
def normalize_text(text):
    if not isinstance(text, str): return str(text)
    return unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8').lower().strip()

def find_quantity_col(df_check):
    keywords = ['quantit', 'depot', 'stock', 'qte', 'globale']
    for col in df_check.columns:
        if any(key in col for key in keywords):
            return col
    return None

def format_ddp(val):
    try:
        if pd.isna(val) or val == "" or val == "None": return ""
        dt = pd.to_datetime(val)
        return dt.strftime('%m/%Y')
    except:
        return str(val)

def clean_columns(df):
    mapping = {
        'produit': 'designation', 'designation': 'designation',
        'n°lot': 'lot', 'nlot': 'lot', 'lot': 'lot', 
        'peremption': 'ddp', 'ddp': 'ddp', 'exp': 'ddp',
        'ppa': 'ppa', 'shp': 'shp'
    }
    stock_keywords = ['quantit', 'depot', 'stock', 'theorique', 'qte']
    new_cols = []
    for col in df.columns:
        norm = normalize_text(col)
        matched = False
        for k, v in mapping.items():
            if k in norm:
                new_cols.append(v)
                matched = True
                break
        if not matched and any(key in norm for key in stock_keywords):
            new_cols.append('stock_theorique')
            matched = True
        if not matched: new_cols.append(norm)
    df.columns = new_cols
    return df

# --- 3. CHARGEMENT DES DONNÉES (OPTIMISÉ AVEC CACHE) ---
if "current_user" not in st.session_state or st.session_state.current_user is None:
    st.warning("Veuillez vous connecter depuis la page principale.")
    st.stop()

user = st.session_state.current_user

@st.cache_data(ttl=3600)
def load_and_clean_master(file_path, mtime):
    try:
        df = pd.read_excel(file_path)
        # Nettoyage des colonnes
        df = clean_columns(df)
        
        # Vectorisation du formatage DDP (beaucoup plus rapide que .apply)
        if 'ddp' in df.columns:
            # Conversion en datetime (coerce gère les erreurs en NaT)
            dates = pd.to_datetime(df['ddp'], errors='coerce')
            # Formater uniquement les dates valides
            mask = dates.notna()
            df['ddp'] = df['ddp'].astype(str) # Par défaut on garde le texte
            df.loc[mask, 'ddp'] = dates[mask].dt.strftime('%m/%Y')
            
        return df
    except Exception as e:
        st.error(f"Erreur chargement Master : {e}")
        return None

df_master = None
if os.path.exists(st.session_state.MASTER_PATH):
    mtime = os.path.getmtime(st.session_state.MASTER_PATH)
    df_master = load_and_clean_master(st.session_state.MASTER_PATH, mtime)

# --- 4. INTERFACE (DÉFINITION DES TABS) ---
# CRITIQUE : Cette ligne doit être AVANT l'utilisation de tabs[x]
tabs = st.tabs(["📊 Dashboard", "📝 Saisie Terrain", "🔍 Confrontation", "⚙️ Admin"])

# --- ONGLET 0 : DASHBOARD ---
with tabs[0]:
    st.subheader("📦 État de l'inventaire")
    if df_master is not None:
        st.metric("Articles dans le Master", len(df_master))
    else:
        st.warning("⚠️ Aucun Master détecté. Allez dans l'onglet Admin.")

# --- ONGLET 1 : SAISIE TERRAIN ---
with tabs[1]:
    if df_master is not None:
        st.subheader("📝 Enregistrement")
        mode = st.radio("Mode :", ["🚀 Rapide", "📋 Détaillé"], horizontal=True)
        produits = sorted([str(p) for p in df_master['designation'].unique() if pd.notna(p)])
        prod_sel = st.selectbox("🔍 Choisir Produit :", [""] + produits)
        
        if prod_sel:
            df_p = df_master[df_master['designation'] == prod_sel]
            lot_orig = st.selectbox("Lot Master :", df_p['lot'].unique())
            info_m = df_p[df_p['lot'] == lot_orig].iloc[0]

            with st.form("form_saisie_v7", clear_on_submit=True):
                c1, c2 = st.columns(2)
                ddp_m = str(info_m.get('ddp', ''))
                ppa_m = float(info_m.get('ppa', 0)) if 'ppa' in info_m else 0.0
                
                if mode == "🚀 Rapide":
                    qte = c1.number_input("Quantité", min_value=0.0, step=1.0)
                    lot_f, ddp_f, ppa_f = lot_orig, ddp_m, ppa_m
                else:
                    lot_f = c1.text_input("Lot Réel", value=str(lot_orig))
                    qte = c2.number_input("Quantité", min_value=0.0, step=1.0)
                    ddp_f = c1.text_input("DDP (MM/AAAA)", value=ddp_m)
                    ppa_f = c2.number_input("PPA Saisi", value=ppa_m)

                if st.form_submit_button("💾 Valider"):
                    new_line = pd.DataFrame([{
                        'designation': prod_sel, 'lot_master': str(lot_orig),
                        'lot': str(lot_f), 'qte_saisie': qte, 'ddp_saisi': ddp_f,
                        'ppa_saisi': ppa_f
                    }])
                    if os.path.exists(st.session_state.SAISIE_PATH):
                        old = pd.read_csv(st.session_state.SAISIE_PATH, sep=';')
                        new_line = pd.concat([old, new_line], ignore_index=True)
                    new_line.to_csv(st.session_state.SAISIE_PATH, index=False, sep=';')
                    st.success(f"Enregistré : {prod_sel}")
    else:
        st.info("En attente du Master...")

# --- ONGLET 2 : CONFRONTATION ---
with tabs[2]:
    st.subheader("🔍 Analyse des écarts")
    if user['role'] == "Admin":
        if os.path.exists(st.session_state.SAISIE_PATH) and df_master is not None:
            try:
                saisie = pd.read_csv(st.session_state.SAISIE_PATH, sep=';', encoding='utf-8-sig')
                q_theo_col = find_quantity_col(df_master)
                
                if q_theo_col and 'designation' in df_master.columns:
                    mode_conf = st.radio("Mode d'analyse :", ["⚡ Rapide (Global par produit)", "🔬 Détaillé (Par Lot & Métadonnées)"], horizontal=True)
                    
                    # Fonction de nettoyage numérique robuste (gère '1 287,50')
                    def robust_numeric(s):
                        if pd.isna(s): return 0.0
                        if isinstance(s, str):
                            s = s.replace('\xa0', '').replace(' ', '').replace(',', '.')
                        return pd.to_numeric(s, errors='coerce')

                    # Nettoyage numérique
                    saisie['qte_saisie'] = saisie['qte_saisie'].apply(robust_numeric).fillna(0)
                    df_master[q_theo_col] = df_master[q_theo_col].apply(robust_numeric).fillna(0)
                    if 'ppa' in df_master.columns:
                        df_master['ppa'] = df_master['ppa'].apply(robust_numeric).fillna(0)
                    if 'ppa_saisi' in saisie.columns:
                        saisie['ppa_saisi'] = saisie['ppa_saisi'].apply(robust_numeric).fillna(0)
                    
                    if "Rapide" in mode_conf:
                        # --- MODE RAPIDE ---
                        # Sécurisation des types pour le merge
                        saisie['designation'] = saisie['designation'].astype(str).str.strip()
                        df_master['designation'] = df_master['designation'].astype(str).str.strip()
                        
                        saisie_grouped = saisie.groupby('designation')['qte_saisie'].sum().reset_index()
                        master_grouped = df_master.groupby('designation')[q_theo_col].sum().reset_index()
                        
                        comp = pd.merge(master_grouped, saisie_grouped, on='designation', how='outer').fillna(0)
                        comp['écart'] = comp['qte_saisie'] - comp[q_theo_col]
                        
                        st.write("### Récapitulatif Global")
                        st.dataframe(comp[['designation', q_theo_col, 'qte_saisie', 'écart']], use_container_width=True)
                    
                    else:
                        # --- MODE DÉTAILLÉ ---
                        # Préparation et sécurisation des types
                        saisie['designation'] = saisie['designation'].astype(str).str.strip()
                        saisie['lot_master'] = saisie['lot_master'].astype(str).str.strip()
                        
                        master_sub = df_master[['designation', 'lot', q_theo_col, 'ddp', 'ppa']].copy()
                        master_sub.columns = ['designation', 'lot_master', 'stock_theorique', 'ddp_master', 'ppa_master']
                        master_sub['designation'] = master_sub['designation'].astype(str).str.strip()
                        master_sub['lot_master'] = master_sub['lot_master'].astype(str).str.strip()
                        
                        # Fusion avec la saisie
                        comp_det = pd.merge(master_sub, saisie, on=['designation', 'lot_master'], how='outer').fillna({'qte_saisie': 0, 'stock_theorique': 0})
                        comp_det['écart'] = comp_det['qte_saisie'] - comp_det['stock_theorique']
                        
                        # Fonction de stylage
                        def highlight_diffs(row):
                            style = ['' for _ in row.index]
                            red_cell = 'background-color: #9e1a1a; color: white;'
                            
                            # Comparaison DDP
                            if str(row.get('ddp_saisi')) != str(row.get('ddp_master')) and pd.notna(row.get('ddp_saisi')):
                                style[row.index.get_loc('ddp_saisi')] = red_cell
                            # Comparaison PPA
                            if float(row.get('ppa_saisi', 0)) != float(row.get('ppa_master', 0)) and row.get('ppa_saisi') != 0:
                                style[row.index.get_loc('ppa_saisi')] = red_cell
                            # Comparaison Lot (si l'utilisateur a changé le lot réel par rapport au lot master)
                            if str(row.get('lot')) != str(row.get('lot_master')) and pd.notna(row.get('lot')):
                                style[row.index.get_loc('lot')] = red_cell
                            # Comparaison Quantité
                            if row['écart'] != 0:
                                style[row.index.get_loc('qte_saisie')] = red_cell
                                style[row.index.get_loc('écart')] = red_cell
                                
                            return style

                        st.write("### Analyse Minitieuse des Lots")
                        st.caption("💡 Les cellules en rouge indiquent une différence avec les données du Master.")
                        
                        cols_view = ['designation', 'lot_master', 'lot', 'stock_theorique', 'qte_saisie', 'écart', 'ddp_master', 'ddp_saisi', 'ppa_master', 'ppa_saisi']
                        # Filtrer uniquement les colonnes qui existent
                        actual_cols = [c for c in cols_view if c in comp_det.columns]
                        
                        st.dataframe(comp_det[actual_cols].style.apply(highlight_diffs, axis=1), use_container_width=True)

                    # EXPORT EXCEL
                    import io
                    buffer = io.BytesIO()
                    if "Rapide" in mode_conf: comp.to_excel(buffer, index=False)
                    else: comp_det.to_excel(buffer, index=False)
                    
                    st.download_button(
                        label="📥 Exporter l'analyse en Excel",
                        data=buffer.getvalue(),
                        file_name=f"Analyse_Inventaire_{'Rapide' if 'Rapide' in mode_conf else 'Detaillee'}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                # --- ANALYSE IA ---
                if is_ia_enabled():
                    st.divider()
                    with st.expander("🤖 Assistant IA Inventaire"):
                        if st.button("📊 Analyser les écarts", use_container_width=True):
                            with st.spinner("L'IA analyse vos données..."):
                                df_target = comp if "Rapide" in mode_conf else comp_det
                                ecarts = df_target[df_target['écart'] != 0].head(20).to_dict('records')
                                prompt = f"Voici un extrait des écarts d'inventaire : {ecarts}. Analyse les causes possibles et suggère des corrections."
                                st.write(ask_ai(prompt))
            except Exception as e:
                st.error(f"Erreur d'analyse : {e}")
        else: st.info("Aucune donnée de saisie trouvée ou Master manquant.")
    else: st.warning("Accès restreint à l'administrateur.")

# --- ONGLET 3 : ADMIN ---
with tabs[3]:
    st.subheader("⚙️ Gestion des fichiers")
    up = st.file_uploader("Importer Master (Excel)", type="xlsx")
    if up:
        with open(st.session_state.MASTER_PATH, "wb") as f:
            f.write(up.getbuffer())
        st.success("Master mis à jour !")
        st.rerun()
    
    st.divider()
    col_del1, col_del2 = st.columns(2)
    
    if col_del1.button("🗑️ Vider Inventaire (Saisie)", type="secondary", use_container_width=True):
        if os.path.exists(st.session_state.SAISIE_PATH):
            os.remove(st.session_state.SAISIE_PATH)
            st.success("Saisies effacées.")
            st.rerun()
            
    if col_del2.button("🔴 Supprimer Master", type="primary", use_container_width=True):
        if os.path.exists(st.session_state.MASTER_PATH):
            os.remove(st.session_state.MASTER_PATH)
            st.success("Master supprimé.")
            st.rerun()
