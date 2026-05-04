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
    """Transforme n'importe quelle date en format MM/AAAA"""
    try:
        if pd.isna(val) or val == "": return ""
        dt = pd.to_datetime(val)
        return dt.strftime('%m/%Y')
    except:
        return str(val)

def clean_columns(df):
    mapping = {
        'produit': 'designation', 'designation': 'designation',
        'n°lot': 'lot', 'nlot': 'lot', 'lot': 'lot', 'peremption': 'ddp', 'ddp': 'ddp'
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
        # Conversion forcée de la DDP du master en format lisible MM/AAAA
        if 'ddp' in df_master.columns:
            df_master['ddp'] = df_master['ddp'].apply(format_ddp)
    except Exception as e:
        st.error(f"Erreur Master : {e}")

# --- 4. INTERFACE ---
tabs = st.tabs(["📊 Dashboard", "📝 Saisie Terrain", "🔍 Confrontation", "⚙️ Admin"])

with tabs[0]: # Dashboard
    if df_master is not None:
        st.metric("Articles chargés", len(df_master))
    else:
        st.info("Veuillez charger le Master en Admin.")

with tabs[1]: # Saisie Terrain
    st.subheader("📝 Mode de Saisie")
    if df_master is not None:
        mode = st.radio("Choisir le mode :", ["🚀 Rapide", "📋 Détaillé"], horizontal=True, key="mode_sel")
        produits = sorted(df_master['designation'].unique().tolist())
        prod_sel = st.selectbox("🔍 Rechercher un produit :", [""] + produits, key="search_prod")
        
        if prod_sel != "":
            df_p = df_master[df_master['designation'] == prod_sel]
            lot_orig = st.selectbox("Choisir le lot Logipharm :", df_p['lot'].unique(), key="lot_sel")
            info_m = df_p[df_p['lot'] == lot_orig].iloc[0]

            with st.form("form_saisie_v5", clear_on_submit=True):
                col1, col2 = st.columns(2)
                lot_final = lot_orig
                # On récupère la DDP déjà formatée en MM/AAAA
                ddp_master = str(info_m.get('ddp', ''))

                if mode == "🚀 Rapide":
                    qte_s = col1.number_input("Quantité dénombrée", min_value=0.0, step=1.0)
                    ddp_final = ddp_master
                else:
                    lot_final = col1.text_input("Modifier N° Lot", value=str(lot_orig))
                    qte_s = col2.number_input("Quantité dénombrée", min_value=0.0, step=1.0)
                    ddp_final = col1.text_input("Modifier DDP (MM/AAAA)", value=ddp_master)

                if st.form_submit_button("💾 VALIDER LA SAISIE"):
                    new_row = pd.DataFrame([{
                        'designation': prod_sel, 
                        'lot_master': str(lot_orig),
                        'lot': str(lot_final), 
                        'qte_saisie': qte_s, 
                        'ddp_saisi': ddp_final
                    }])
                    if os.path.exists(SAISIE_PATH):
                        current_saisie = pd.read_csv(SAISIE_PATH, sep=';')
                        new_row = pd.concat([current_saisie, new_row], ignore_index=True)
                    new_row.to_csv(SAISIE_PATH, index=False, sep=';')
                    st.success(f"✅ Ajouté : {prod_sel}")

with tabs[2]: # Confrontation
    if os.path.exists(SAISIE_PATH) and df_master is not None:
        try:
            saisie = pd.read_csv(SAISIE_PATH, sep=';')
            if 'lot_master' not in saisie.columns:
                st.error("Structure obsolète. Veuillez réinitialiser en Admin.")
            else:
                s_grouped = saisie.groupby(['designation', 'lot_master']).agg({'qte_saisie': 'sum', 'ddp_saisi': 'first'}).reset_index()
                df_master['lot'] = df_master['lot'].astype(str)
                s_grouped['lot_master'] = s_grouped['lot_master'].astype(str)
                comp = pd.merge(df_master, s_grouped, left_on=['designation', 'lot'], right_on=['designation', 'lot_master'], how='left')
                comp['qte_saisie'] = comp['qte_saisie'].fillna(0)
                comp['écart'] = comp['qte_saisie'] - comp.get('stock_theorique', 0)
                
                # On affiche la DDP saisie pour comparer avec celle du Master
                st.dataframe(comp[['designation', 'lot', 'ddp', 'ddp_saisi', 'stock_theorique', 'qte_saisie', 'écart']], use_container_width=True)
        except Exception as e:
            st.error(f"Erreur : {e}")

with tabs[3]: # Admin
    up = st.file_uploader("Charger export Logipharm (Excel)", type="xlsx")
    if up:
        with open(MASTER_PATH, "wb") as f:
            f.write(up.getbuffer())
        st.success("Master mis à jour !")
        st.rerun()
