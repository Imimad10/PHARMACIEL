import streamlit as st
import pandas as pd
import os
import unicodedata

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

# --- 3. CHARGEMENT DES DONNÉES ---
df_master = None
if os.path.exists(st.session_state.MASTER_PATH):
    try:
        df_master = clean_columns(pd.read_excel(st.session_state.MASTER_PATH))
        if 'ddp' in df_master.columns:
            df_master['ddp'] = df_master['ddp'].apply(format_ddp)
    except Exception as e:
        st.error(f"Erreur chargement Master : {e}")

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
        produits = sorted(df_master['designation'].unique().tolist())
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

# --- ONGLET 2 : CONFRONTATION (CORRIGÉ POUR VALUEERROR ET ALERTES) ---
with tabs[2]:
    st.subheader("🔍 Analyse des écarts")
    if os.path.exists(st.session_state.SAISIE_PATH) and df_master is not None:
        try:
            saisie = pd.read_csv(st.session_state.SAISIE_PATH, sep=';')
            if 'lot_master' not in saisie.columns:
                st.error("Structure obsolète. Cliquez sur RESET en Admin.")
            else:
                # Groupement pour éviter les doublons
                s_grouped = saisie.groupby(['designation', 'lot_master']).agg({
                    'qte_saisie': 'sum', 'ddp_saisi': 'first', 'ppa_saisi': 'first'
                }).reset_index()
                
                # Merge propre
                df_m_clean = df_master.copy()
                df_m_clean['lot'] = df_m_clean['lot'].astype(str)
                s_grouped['lot_master'] = s_grouped['lot_master'].astype(str)
                
                res = pd.merge(df_m_clean, s_grouped, left_on=['designation', 'lot'], right_on=['designation', 'lot_master'], how='left')
                res['qte_saisie'] = res['qte_saisie'].fillna(0)
                res['stock_theorique'] = pd.to_numeric(res['stock_theorique'], errors='coerce').fillna(0)
                res['écart'] = res['qte_saisie'] - res['stock_theorique']

                def style_compare(row):
                    styles = [''] * len(row)
                    # Alerte Rouge si DDP différente
                    if str(row['ddp']) != str(row['ddp_saisi']) and row['qte_saisie'] > 0:
                        if 'ddp_saisi' in row.index:
                            styles[row.index.get_loc('ddp_saisi')] = 'background-color: #ffcccc; color: red; font-weight: bold'
                    # Alerte Rouge si PPA différent
                    if 'ppa' in row.index and 'ppa_saisi' in row.index:
                        if float(row['ppa']) != float(row['ppa_saisi']) and row['qte_saisie'] > 0:
                            styles[row.index.get_loc('ppa_saisi')] = 'background-color: #ffcccc; color: red; font-weight: bold'
                    return styles

                show_cols = ['designation', 'lot', 'ddp', 'ddp_saisi', 'ppa', 'ppa_saisi', 'stock_theorique', 'qte_saisie', 'écart']
                actual_cols = [c for c in show_cols if c in res.columns]
                st.dataframe(res[actual_cols].style.apply(style_compare, axis=1), use_container_width=True)
        except Exception as e:
            st.error(f"Erreur d'analyse : {e}")
    else:
        st.info("Aucune saisie à comparer.")

# --- ONGLET 3 : ADMIN ---
with tabs[3]:
    st.subheader("⚙️ Gestion des fichiers")
    up = st.file_uploader("Importer Master (Excel)", type="xlsx")
    if up:
        with open(st.session_state.MASTER_PATH, "wb") as f:
            f.write(up.getbuffer())
        st.success("Master mis à jour !")
        st.rerun()
    
    if st.button("🔴 RESET TOTAL (Vider tout)"):
        if os.path.exists(st.session_state.MASTER_PATH): os.remove(st.session_state.MASTER_PATH)
        if os.path.exists(st.session_state.SAISIE_PATH): os.remove(st.session_state.SAISIE_PATH)
        st.rerun()
