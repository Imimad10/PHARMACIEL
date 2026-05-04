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

def clean_columns(df):
    mapping = {
        'produit': 'designation', 'designation': 'designation',
        'n°lot': 'lot', 'nlot': 'lot', 'lot': 'lot'
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
    except Exception as e:
        st.error(f"Erreur Master : {e}")

# --- 4. INTERFACE (ONGLETS) ---
tabs = st.tabs(["📊 Dashboard", "📝 Saisie Terrain", "🔍 Confrontation", "⚙️ Admin"])

# --- ONGLET DASHBOARD ---
with tabs[0]:
    st.subheader("📦 Arrivages & Master")
    if df_master is not None:
        st.metric("Total Articles dans le Master", len(df_master))
        with st.expander("🔄 Zone Arrivage (Remplacer le Master)"):
            confirm = st.checkbox("Je confirme vouloir supprimer le Master actuel")
            if st.button("🗑️ Supprimer le Master", disabled=not confirm):
                os.remove(MASTER_PATH)
                st.rerun()
    else:
        st.warning("⚠️ Aucun Master trouvé. Allez dans l'onglet 'Admin'.")

# --- ONGLET SAISIE TERRAIN ---
with tabs[1]:
    st.subheader("📝 Mode de Saisie")
    if df_master is not None:
        mode = st.radio("Choisir le mode :", ["🚀 Rapide", "📋 Détaillé"], horizontal=True, key="mode_sel")
        
        produits = sorted(df_master['designation'].unique().tolist())
        prod_sel = st.selectbox("🔍 Rechercher un produit :", [""] + produits, key="search_prod")
        
        if prod_sel != "":
            df_p = df_master[df_master['designation'] == prod_sel]
            lot_orig = st.selectbox("Choisir le lot Logipharm :", df_p['lot'].unique(), key="lot_sel")
            info_m = df_p[df_p['lot'] == lot_orig].iloc[0]

            with st.form("form_saisie_v4", clear_on_submit=True):
                col1, col2 = st.columns(2)
                lot_final = lot_orig
                ddp_final = str(info_m.get('ddp', ''))

                if mode == "🚀 Rapide":
                    qte_s = col1.number_input("Quantité dénombrée", min_value=0.0, step=1.0)
                else:
                    lot_final = col1.text_input("Modifier N° Lot", value=str(lot_orig))
                    qte_s = col2.number_input("Quantité dénombrée", min_value=0.0, step=1.0)
                    ddp_final = col1.text_input("Modifier DDP", value=ddp_final)

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
    else:
        st.info("Veuillez charger un fichier Excel dans l'onglet Admin.")

# --- ONGLET CONFRONTATION ---
with tabs[2]:
    st.subheader("🔍 Analyse")
    if os.path.exists(SAISIE_PATH) and df_master is not None:
        try:
            saisie = pd.read_csv(SAISIE_PATH, sep=';')
            
            # SECURITÉ ANTI-ERREUR 'lot_master'
            if 'lot_master' not in saisie.columns:
                st.error("⚠️ Structure de saisie ancienne détectée (manque 'lot_master').")
                if st.button("Réinitialiser les saisies pour corriger"):
                    os.remove(SAISIE_PATH)
                    st.rerun()
                st.stop()

            s_grouped = saisie.groupby(['designation', 'lot_master']).agg({'qte_saisie': 'sum'}).reset_index()
            
            df_master['lot'] = df_master['lot'].astype(str)
            s_grouped['lot_master'] = s_grouped['lot_master'].astype(str)
            
            comp = pd.merge(df_master, s_grouped, left_on=['designation', 'lot'], right_on=['designation', 'lot_master'], how='left')
            comp['qte_saisie'] = comp['qte_saisie'].fillna(0)
            comp['écart'] = comp['qte_saisie'] - comp.get('stock_theorique', 0)
            
            st.dataframe(comp[['designation', 'lot', 'stock_theorique', 'qte_saisie', 'écart']], use_container_width=True)
            
        except Exception as e:
            st.error(f"Erreur lors de l'analyse : {e}")
    else:
        st.info("En attente de saisies terrain...")

# --- ONGLET ADMIN ---
with tabs[3]:
    st.header("⚙️ Administration")
    up = st.file_uploader("Charger un nouvel export Logipharm (Excel)", type="xlsx")
    if up:
        with open(MASTER_PATH, "wb") as f:
            f.write(up.getbuffer())
        st.success("✅ Master mis à jour !")
        st.rerun()
    
    st.divider()
    if st.button("🔴 Urgence : Supprimer TOUTES les données (Master + Saisies)"):
        if os.path.exists(MASTER_PATH): os.remove(MASTER_PATH)
        if os.path.exists(SAISIE_PATH): os.remove(SAISIE_PATH)
        st.rerun()
