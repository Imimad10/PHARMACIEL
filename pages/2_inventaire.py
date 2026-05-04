import streamlit as st
import pandas as pd
import os
import unicodedata

# --- 1. CONFIGURATION & CHEMINS ---
st.set_page_config(page_title="Darpharm Solution - Inventaire", layout="wide")

DATA_DIR = "data_inventaire"
MASTER_PATH = os.path.join(DATA_DIR, "master.xlsx")
SAISIE_PATH = os.path.join(DATA_DIR, "saisie.csv")
os.makedirs(DATA_DIR, exist_ok=True)

# --- 2. FONCTIONS TECHNIQUES ---
def normalize_text(text):
    if not isinstance(text, str): return str(text)
    return unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8').lower().strip()

def format_ddp(val):
    try:
        if pd.isna(val) or val == "": return ""
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
if os.path.exists(MASTER_PATH):
    try:
        df_master = clean_columns(pd.read_excel(MASTER_PATH))
        if 'ddp' in df_master.columns:
            df_master['ddp'] = df_master['ddp'].apply(format_ddp)
    except Exception as e:
        st.error(f"Erreur Master : {e}")

# --- 4. INTERFACE ---
tabs = st.tabs(["📊 Dashboard", "📝 Saisie Terrain", "🔍 Confrontation", "⚙️ Admin"])

with tabs[0]: # Dashboard
    if df_master is not None:
        st.metric("Articles Master", len(df_master))
    else:
        st.info("Importez un Master en Admin.")

with tabs[1]: # Saisie Terrain
    if df_master is not None:
        st.subheader("📝 Saisie")
        mode = st.radio("Mode :", ["🚀 Rapide", "📋 Détaillé"], horizontal=True)
        produits = sorted(df_master['designation'].unique().tolist())
        prod_sel = st.selectbox("🔍 Produit :", [""] + produits)
        
        if prod_sel:
            df_p = df_master[df_master['designation'] == prod_sel]
            lot_orig = st.selectbox("Lot Logipharm :", df_p['lot'].unique())
            info_m = df_p[df_p['lot'] == lot_orig].iloc[0]

            with st.form("form_saisie_v6"):
                c1, c2 = st.columns(2)
                ddp_m = str(info_m.get('ddp', ''))
                ppa_m = float(info_m.get('ppa', 0))
                shp_m = float(info_m.get('shp', 0))
                
                if mode == "🚀 Rapide":
                    qte = c1.number_input("Quantité", min_value=0.0, step=1.0)
                    lot_f, ddp_f, ppa_f, shp_f = lot_orig, ddp_m, ppa_m, shp_m
                else:
                    lot_f = c1.text_input("Lot Réel", value=str(lot_orig))
                    qte = c2.number_input("Quantité", min_value=0.0, step=1.0)
                    ddp_f = c1.text_input("DDP (MM/AAAA)", value=ddp_m)
                    ppa_f = c2.number_input("PPA", value=ppa_m)
                    shp_f = c1.number_input("SHP", value=shp_m)

                if st.form_submit_button("Enregistrer"):
                    new_line = pd.DataFrame([{
                        'designation': prod_sel, 'lot_master': str(lot_orig),
                        'lot': str(lot_f), 'qte_saisie': qte, 'ddp_saisi': ddp_f,
                        'ppa_saisi': ppa_f, 'shp_saisi': shp_f
                    }])
                    if os.path.exists(SAISIE_PATH):
                        old = pd.read_csv(SAISIE_PATH, sep=';')
                        new_line = pd.concat([old, new_line], ignore_index=True)
                    new_line.to_csv(SAISIE_PATH, index=False, sep=';')
                    st.success("Enregistré !")

with tabs[2]: # Confrontation avec ALERTES ROUGES
    st.subheader("🔍 Analyse des écarts")
    if os.path.exists(SAISIE_PATH) and df_master is not None:
        saisie = pd.read_csv(SAISIE_PATH, sep=';')
        
        # Sécurité structure
        if 'lot_master' not in saisie.columns:
            st.error("Fichier de saisie ancien. Réinitialisez en Admin.")
        else:
            s_grouped = saisie.groupby(['designation', 'lot_master']).agg({
                'qte_saisie': 'sum', 'ddp_saisi': 'first', 
                'ppa_saisi': 'first', 'shp_saisi': 'first'
            }).reset_index()
            
            df_master['lot'] = df_master['lot'].astype(str)
            s_grouped['lot_master'] = s_grouped['lot_master'].astype(str)
            
            res = pd.merge(df_master, s_grouped, left_on=['designation', 'lot'], right_on=['designation', 'lot_master'], how='left')
            res['qte_saisie'] = res['qte_saisie'].fillna(0)
            res['écart'] = res['qte_saisie'] - res.get('stock_theorique', 0)

            # --- FONCTION DE COLORATION ---
            def highlight_diff(row):
                styles = [''] * len(row)
                # Alerte DDP
                if str(row['ddp']) != str(row['ddp_saisi']) and row['qte_saisie'] > 0:
                    styles[row.index.get_loc('ddp_saisi')] = 'background-color: #ffcccc; color: red; font-weight: bold'
                # Alerte PPA
                if row.get('ppa') and row.get('ppa_saisi'):
                    if float(row['ppa']) != float(row['ppa_saisi']):
                        styles[row.index.get_loc('ppa_saisi')] = 'background-color: #ffcccc; color: red; font-weight: bold'
                # Alerte Ecart Stock
                if row['écart'] != 0:
                    styles[row.index.get_loc('écart')] = 'color: orange; font-weight: bold'
                return styles

            # Affichage avec style
            cols_to_show = ['designation', 'lot', 'ddp', 'ddp_saisi', 'ppa', 'ppa_saisi', 'stock_theorique', 'qte_saisie', 'écart']
            # On ne garde que les colonnes qui existent vraiment
            final_cols = [c for c in cols_to_show if c in res.columns]
            
            st.dataframe(res[final_cols].style.apply(highlight_diff, axis=1), use_container_width=True)

with tabs[3]: # Admin
    up = st.file_uploader("Importer Master", type="xlsx")
    if up:
        with open(MASTER_PATH, "wb") as f: f.write(up.getbuffer())
        st.rerun()
    if st.button("🔴 RESET TOTAL"):
        if os.path.exists(MASTER_PATH): os.remove(MASTER_PATH)
        if os.path.exists(SAISIE_PATH): os.remove(SAISIE_PATH)
        st.rerun()
