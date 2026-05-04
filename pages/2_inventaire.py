import streamlit as st
import pandas as pd
import os
import unicodedata
import io
from utils_ia import ask_ai, is_ia_enabled

# --- CONFIGURATION ---
st.set_page_config(page_title="Darpharm Solution - Gestion par Lot", layout="wide")

DATA_DIR = "data_inventaire"
ARCHIVE_DIR = os.path.join(DATA_DIR, "archives")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True)

MASTER_PATH = os.path.join(DATA_DIR, "master.xlsx")
SAISIE_PATH = os.path.join(DATA_DIR, "saisie.csv")

# --- FONCTIONS DE TRAITEMENT ---

def normalize_text(text):
    if not isinstance(text, str): return str(text)
    # Enlève les accents et met en minuscule
    text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
    return text.lower().strip()

def clean_columns(df_to_clean):
    """Mapping ultra-flexible pour les colonnes Logipharm"""
    mapping = {
        'produit': 'designation',
        'designation': 'designation',
        'n°lot': 'lot',
        'nlot': 'lot',
        'lot': 'lot',
        'ddp': 'ddp',
        'peremption': 'ddp',
        'ppa': 'ppa',
        'shp': 'shp'
    }
    
    # Mots-clés pour identifier la colonne de Stock (Théorique)
    stock_keywords = ['quantit', 'depot', 'stock', 'theorique', 'qte']
    
    new_cols = []
    for col in df_to_clean.columns:
        norm_col = normalize_text(col)
        matched = False
        
        # 1. Vérification du mapping standard
        for key, target in mapping.items():
            if key in norm_col:
                new_cols.append(target)
                matched = True
                break
        
        # 2. Vérification spécifique pour le stock (si non encore trouvé)
        if not matched:
            if any(k in norm_col for k in stock_keywords):
                new_cols.append('stock_theorique')
                matched = True
        
        if not matched:
            new_cols.append(norm_col)
            
    df_to_clean.columns = new_cols
    return df_to_clean

def load_data():
    if not os.path.exists(MASTER_PATH): return None
    try:
        df_loaded = pd.read_excel(MASTER_PATH)
        return clean_columns(df_loaded)
    except Exception as e:
        st.error(f"Erreur Master : {e}")
        return None

# --- VÉRIFICATION SESSION ---
if "current_user" not in st.session_state:
    st.warning("Veuillez vous connecter.")
    st.stop()

user = st.session_state.current_user
df_master = load_data()

# --- INTERFACE ---
tabs = st.tabs(["📊 Dashboard", "📝 Saisie Terrain", "🔍 Confrontation (Lots)", "⚙️ Admin"])

# 1. TABLEAU DE BORD
with tabs[0]:
    if df_master is not None:
        c1, c2 = st.columns(2)
        c1.metric("Lignes Master (Lots)", len(df_master))
        if os.path.exists(SAISIE_PATH):
            try:
                s_count = pd.read_csv(SAISIE_PATH, sep=';', encoding='utf-8-sig')
                c2.metric("Lots Saisis", len(s_count))
            except: c2.metric("Lots Saisis", 0)

# 2. SAISIE PAR LOT
with tabs[1]:
    st.subheader("📝 Saisie Inventaire")
    if df_master is not None:
        # Vérification critique des colonnes
        if 'designation' not in df_master.columns or 'lot' not in df_master.columns:
            st.error(f"Colonnes manquantes dans le Master. Trouvées : {list(df_master.columns)}")
            st.stop()

        liste_produits = sorted(df_master['designation'].unique().tolist())
        produit_sel = st.selectbox("🔍 Choisir un produit", [""] + liste_produits)

        if produit_sel:
            df_lots = df_master[df_master['designation'] == produit_sel]
            lots_dispo = df_lots['lot'].astype(str).unique().tolist()
            
            with st.form("form_saisie_lot", clear_on_submit=True):
                c_a, c_b = st.columns(2)
                with c_a:
                    lot_sel = st.selectbox("📦 Numéro de Lot", lots_dispo)
                with c_b:
                    qte_in = st.number_input("Quantité physique", min_value=0.0, step=1.0)
                
                if st.form_submit_button("➕ Enregistrer"):
                    new_entry = {
                        'designation': produit_sel,
                        'lot': lot_sel,
                        'qte_saisie': qte_in,
                        'date_saisie': pd.Timestamp.now().strftime("%d/%m/%Y %H:%M")
                    }
                    df_new = pd.DataFrame([new_entry])
                    if os.path.exists(SAISIE_PATH):
                        df_old = pd.read_csv(SAISIE_PATH, sep=';', encoding='utf-8-sig')
                        df_final = pd.concat([df_old, df_new], ignore_index=True)
                    else:
                        df_final = df_new
                    df_final.to_csv(SAISIE_PATH, index=False, sep=';', encoding='utf-8-sig')
                    st.success("Enregistré !")
                    st.rerun()

# 3. CONFRONTATION (Correction de la KeyError)
with tabs[2]:
    st.subheader("🔍 Analyse des Écarts par Lot")
    if user['role'] == "Admin":
        if os.path.exists(SAISIE_PATH) and df_master is not None:
            saisie = pd.read_csv(SAISIE_PATH, sep=';', encoding='utf-8-sig')
            saisie = clean_columns(saisie)

            if 'stock_theorique' not in df_master.columns:
                st.error("Impossible de trouver la colonne de quantité dans votre fichier Excel.")
                st.info(f"Colonnes détectées : {list(df_master.columns)}")
                st.stop()

            # Groupement et Fusion
            saisie_grouped = saisie.groupby(['designation', 'lot'])['qte_saisie'].sum().reset_index()
            saisie_grouped['lot'] = saisie_grouped['lot'].astype(str)
            df_master['lot'] = df_master['lot'].astype(str)
            
            comp = pd.merge(df_master, saisie_grouped, on=['designation', 'lot'], how='left')
            comp['qte_saisie'] = comp['qte_saisie'].fillna(0)
            
            # CALCUL DE L'ÉCART
            comp['écart'] = comp['qte_saisie'] - comp['stock_theorique']
            
            # Affichage
            st.dataframe(comp[['designation', 'lot', 'stock_theorique', 'qte_saisie', 'écart']], use_container_width=True)

            # ARCHIVAGE ET RESET
            st.divider()
            c_1, c_2 = st.columns(2)
            with c_1:
                if st.button("📦 Archiver l'inventaire", use_container_width=True):
                    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M")
                    saisie.to_csv(os.path.join(ARCHIVE_DIR, f"archive_{ts}.csv"), index=False, sep=';')
                    os.remove(SAISIE_PATH)
                    st.rerun()
            with c_2:
                confirm = st.checkbox("Confirmer la suppression")
                if st.button("🗑️ Vider le tableau", disabled=not confirm, use_container_width=True):
                    if os.path.exists(SAISIE_PATH): os.remove(SAISIE_PATH)
                    st.rerun()
        else:
            st.info("Aucune saisie.")
    else:
        st.warning("Accès réservé.")

# 4. ADMINISTRATION
with tabs[3]:
    if user['role'] == "Admin":
        st.header("⚙️ Import Master")
        file = st.file_uploader("Excel Logipharm", type=["xlsx"])
        if file:
            with open(MASTER_PATH, "wb") as f:
                f.write(file.getbuffer())
            st.success("Master mis à jour.")
            st.rerun()
