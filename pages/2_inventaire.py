import streamlit as st
import pandas as pd
import os
import unicodedata

# --- 1. CONFIGURATION ---
st.set_page_config(page_title="Darpharm Solution - Inventaire", layout="wide")

DATA_DIR = "data_inventaire"
MASTER_PATH = os.path.join(DATA_DIR, "master.xlsx")
SAISIE_PATH = os.path.join(DATA_DIR, "saisie.csv")
os.makedirs(DATA_DIR, exist_ok=True)

# --- 2. FONCTIONS ---
def normalize_text(text):
    if not isinstance(text, str): return str(text)
    return unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8').lower().strip()

def clean_columns(df):
    mapping = {'produit': 'designation', 'n°lot': 'lot', 'nlot': 'lot', 'lot_master': 'lot_master', 'qte_saisie': 'qte_saisie'}
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
    except:
        st.error("Erreur lors de la lecture du Master Excel.")

# --- 4. CRÉATION DES ONGLETS (IMPORTANT : DOIT ÊTRE ICI) ---
tabs = st.tabs(["📊 Dashboard", "📝 Saisie Terrain", "🔍 Confrontation", "⚙️ Admin"])

# --- 5. CONTENU DES ONGLETS ---

with tabs[0]: # Dashboard
    st.subheader("📦 Arrivages & Master")
    if df_master is not None:
        st.metric("Total Articles", len(df_master))
        if st.checkbox("🔄 Mode Arrivage : Remplacer le Master"):
            if st.button("🗑️ Supprimer Master actuel"):
                os.remove(MASTER_PATH)
                st.rerun()
    else:
        st.info("Importez un fichier Excel dans l'onglet Admin.")

with tabs[1]: # Saisie
    if df_master is not None:
        st.subheader("📝 Mode de Saisie")
        mode = st.radio("Mode :", ["🚀 Rapide", "📋 Détaillé"], horizontal=True)
        # ... Reste du code de saisie (identique au précédent) ...
    else:
        st.warning("Master manquant.")

with tabs[2]: # Confrontation
    st.subheader("🔍 Analyse")
    if os.path.exists(SAISIE_PATH) and df_master is not None:
        try:
            saisie = pd.read_csv(SAISIE_PATH, sep=';', encoding='utf-8-sig')
            if 'lot_master' not in saisie.columns:
                st.error("Fichier de saisie incompatible.")
                if st.button("Réinitialiser Saisie"):
                    os.remove(SAISIE_PATH)
                    st.rerun()
            else:
                # ... Logique de calcul (identique au précédent) ...
                st.write("Tableau des écarts prêt.")
        except Exception as e:
            st.error(f"Erreur : {e}")

with tabs[3]: # ADMIN (Zone Drag & Drop)
    st.header("⚙️ Admin")
    file = st.file_uploader("Importer Excel Logipharm", type=["xlsx"])
    if file:
        with open(MASTER_PATH, "wb") as f:
            f.write(file.getbuffer())
        st.success("Master mis à jour !")
        st.rerun()
