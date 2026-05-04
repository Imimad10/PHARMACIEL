import streamlit as st
import pandas as pd
import os
import unicodedata
import io

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
    text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
    return text.lower().strip()

def clean_columns(df_to_clean):
    """Normalise les noms de colonnes pour correspondre au code"""
    mapping = {
        'produit': 'designation',
        'designation': 'designation',
        'n°lot': 'lot',
        'nlot': 'lot',
        'lot': 'lot',
        'qte_saisie': 'qte_saisie', # Sécurité pour la saisie
        'quantite_saisie': 'qte_saisie',
        'ddp': 'ddp',
        'ppa': 'ppa'
    }
    
    stock_keywords = ['quantit', 'depot', 'stock', 'theorique', 'qte']
    new_cols = []
    
    for col in df_to_clean.columns:
        norm_col = normalize_text(col)
        matched = False
        
        # 1. Mapping direct
        for key, target in mapping.items():
            if key in norm_col:
                new_cols.append(target)
                matched = True
                break
        
        # 2. Détection du stock théorique (Logipharm)
        if not matched and any(k in norm_col for k in stock_keywords) and 'stock_theorique' not in new_cols:
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
        st.metric("Total Articles en Stock", len(df_master))
    else:
        st.info("Importez un fichier Master (Logipharm) dans l'onglet Admin.")

# 2. SAISIE PAR LOT
with tabs[1]:
    st.subheader("📝 Saisie Inventaire")
    if df_master is not None:
        # Vérification colonnes Master
        if 'designation' not in df_master.columns or 'lot' not in df_master.columns:
            st.error("Colonnes 'Produit' ou 'Lot' introuvables dans le Master.")
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
                    qte_in = st.number_input("Quantité physique dénombrée", min_value=0.0, step=1.0)
                
                if st.form_submit_button("➕ Enregistrer la Saisie"):
                    new_entry = {
                        'designation': produit_sel,
                        'lot': lot_sel,
                        'qte_saisie': qte_in,
                        'date_saisie': pd.Timestamp.now().strftime("%d/%m/%Y %H:%M")
                    }
                    df_new = pd.DataFrame([new_entry])
                    
                    # Sauvegarde avec noms de colonnes explicites
                    if os.path.exists(SAISIE_PATH):
                        df_old = pd.read_csv(SAISIE_PATH, sep=';', encoding='utf-8-sig')
                        df_final = pd.concat([df_old, df_new], ignore_index=True)
                    else:
                        df_final = df_new
                    
                    df_final.to_csv(SAISIE_PATH, index=False, sep=';', encoding='utf-8-sig')
                    st.success("Saisie enregistrée avec succès.")
                    st.rerun()

# 3. CONFRONTATION
with tabs[2]:
    st.subheader("🔍 Analyse des Écarts")
    if user['role'] == "Admin":
        if os.path.exists(SAISIE_PATH) and df_master is not None:
            # Chargement et Nettoyage immédiat
            saisie = pd.read_csv(SAISIE_PATH, sep=';', encoding='utf-8-sig')
            saisie = clean_columns(saisie)

            # SÉCURITÉ : Vérifier si la colonne 'qte_saisie' existe après clean
            if 'qte_saisie' not in saisie.columns:
                st.error("Erreur de structure dans le fichier de saisie. 'qte_saisie' manquante.")
                if st.button("Réparer le fichier de saisie"):
                    os.remove(SAISIE_PATH)
                    st.rerun()
                st.stop()

            # Groupement par lot
            saisie_grouped = saisie.groupby(['designation', 'lot'])['qte_saisie'].sum().reset_index()
            saisie_grouped['lot'] = saisie_grouped['lot'].astype(str)
            df_master['lot'] = df_master['lot'].astype(str)
            
            # Fusion
            comp = pd.merge(df_master, saisie_grouped, on=['designation', 'lot'], how='left')
            comp['qte_saisie'] = comp['qte_saisie'].fillna(0)
            
            # Calcul de l'écart (Vérification stock_theorique)
            if 'stock_theorique' in comp.columns:
                comp['écart'] = comp['qte_saisie'] - comp['stock_theorique']
                st.dataframe(comp[['designation', 'lot', 'stock_theorique', 'qte_saisie', 'écart']], use_container_width=True)
            else:
                st.warning("La colonne de stock théorique est introuvable. Vérifiez l'import Logipharm.")

            # BOUTONS ACTIONS
            st.divider()
            c_arch, c_reset = st.columns(2)
            with c_arch:
                if st.button("📦 Archiver et Vider"):
                    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M")
                    saisie.to_csv(os.path.join(ARCHIVE_DIR, f"archive_{ts}.csv"), index=False, sep=';')
                    os.remove(SAISIE_PATH)
                    st.rerun()
            with c_reset:
                conf = st.checkbox("Confirmer la suppression")
                if st.button("🗑️ Vider le tableau", disabled=not conf):
                    if os.path.exists(SAISIE_PATH): os.remove(SAISIE_PATH)
                    st.rerun()
        else:
            st.info("Aucune saisie détectée.")
    else:
        st.warning("Accès restreint.")

# 4. ADMINISTRATION
with tabs[3]:
    if user['role'] == "Admin":
        st.header("⚙️ Import Master")
        file = st.file_uploader("Importer Excel Logipharm", type=["xlsx"])
        if file:
            with open(MASTER_PATH, "wb") as f:
                f.write(file.getbuffer())
            st.success("Fichier Master mis à jour.")
            st.rerun()
