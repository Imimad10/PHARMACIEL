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
    text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
    return text.lower().strip()

def safe_float(val, default=0.0):
    try:
        if pd.isna(val): return default
        if isinstance(val, str):
            val = val.replace(' ', '').replace(',', '.')
        return float(val)
    except:
        return default

def clean_columns(df_to_clean):
    """Mapping spécifique pour Logipharm et uniformisation des noms de colonnes"""
    mapping = {
        'produit': 'designation',
        'designation': 'designation',
        'n°lot': 'lot',
        'nlot': 'lot',
        'n lot': 'lot',
        'lot': 'lot',
        'quantité dépôt': 'stock_theorique',
        'quantite depot': 'stock_theorique',
        'stock': 'stock_theorique',
        'ddp': 'ddp',
        'ppa': 'ppa',
        'shp': 'shp'
    }
    
    new_cols = []
    for col in df_to_clean.columns:
        norm_col = normalize_text(col)
        matched = False
        for key, target in mapping.items():
            if key in norm_col:
                new_cols.append(target)
                matched = True
                break
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
        st.error(f"Erreur lors du chargement du Master : {e}")
        return None

# --- VÉRIFICATION SESSION ---
if "current_user" not in st.session_state or st.session_state.current_user is None:
    st.warning("Veuillez vous connecter depuis la page principale.")
    st.stop()

user = st.session_state.current_user
df_master = load_data()

# --- INTERFACE ---
tabs = st.tabs(["📊 Dashboard", "📝 Saisie Terrain", "🔍 Confrontation (Lots)", "⚙️ Admin"])

# 1. TABLEAU DE BORD
with tabs[0]:
    st.subheader("État de l'inventaire")
    if df_master is not None:
        c1, c2 = st.columns(2)
        c1.metric("Lignes Master (Lots)", len(df_master))
        if os.path.exists(SAISIE_PATH):
            try:
                s_count = pd.read_csv(SAISIE_PATH, sep=';', encoding='utf-8-sig')
                c2.metric("Lots Saisis", len(s_count))
            except: c2.metric("Lots Saisis", 0)
    else:
        st.info("Importez un fichier Master pour commencer.")

# 2. SAISIE PAR LOT
with tabs[1]:
    st.subheader("📝 Saisie Inventaire")
    if df_master is not None:
        if 'designation' not in df_master.columns or 'lot' not in df_master.columns:
            st.error("Structure Master incorrecte (besoin de 'Produit' et 'Lot')")
            st.stop()

        liste_produits = sorted(df_master['designation'].unique().tolist())
        produit_sel = st.selectbox("🔍 Choisir un produit", [""] + liste_produits)

        if produit_sel:
            # On propose les lots existants pour ce produit dans le Master Logipharm
            df_lots = df_master[df_master['designation'] == produit_sel]
            lots_dispo = df_lots['lot'].astype(str).unique().tolist()
            
            with st.form("form_saisie_lot", clear_on_submit=True):
                col_a, col_b = st.columns(2)
                with col_a:
                    lot_sel = st.selectbox("📦 Numéro de Lot", lots_dispo)
                with col_b:
                    qte_in = st.number_input("Quantité physique", min_value=0.0, step=1.0)
                
                # Récupération automatique des infos du Master pour ce lot
                info_master = df_lots[df_lots['lot'].astype(str) == lot_sel].iloc[0]
                st.caption(f"Info Master : DDP {info_master.get('ddp','-')} | PPA {info_master.get('ppa', 0)}")

                if st.form_submit_button("➕ Enregistrer la ligne"):
                    new_entry = {
                        'designation': produit_sel,
                        'lot': lot_sel,
                        'qte_saisie': qte_in,
                        'saisi_par': user['username'],
                        'date_saisie': pd.Timestamp.now().strftime("%d/%m/%Y %H:%M")
                    }
                    df_new = pd.DataFrame([new_entry])
                    
                    if os.path.exists(SAISIE_PATH):
                        df_old = pd.read_csv(SAISIE_PATH, sep=';', encoding='utf-8-sig')
                        df_final = pd.concat([df_old, df_new], ignore_index=True)
                    else:
                        df_final = df_new
                        
                    df_final.to_csv(SAISIE_PATH, index=False, sep=';', encoding='utf-8-sig')
                    st.success(f"Lot {lot_sel} ajouté !")
                    st.rerun()

        st.divider()
        if os.path.exists(SAISIE_PATH):
            st.write("Dernières saisies :")
            st.dataframe(pd.read_csv(SAISIE_PATH, sep=';').tail(5), use_container_width=True)

# 3. CONFRONTATION PAR LOT (Correction du KeyError)
with tabs[2]:
    st.subheader("🔍 Analyse des Écarts par Lot")
    if user['role'] == "Admin":
        if os.path.exists(SAISIE_PATH) and df_master is not None:
            saisie = pd.read_csv(SAISIE_PATH, sep=';', encoding='utf-8-sig')
            
            # Sécurité : On nettoie aussi les colonnes du CSV de saisie
            saisie = clean_columns(saisie)

            if 'designation' in saisie.columns and 'lot' in saisie.columns:
                # Groupement par produit ET par lot
                saisie_grouped = saisie.groupby(['designation', 'lot'])['qte_saisie'].sum().reset_index()
                
                # Conversion en string pour éviter les erreurs de fusion (merge)
                saisie_grouped['lot'] = saisie_grouped['lot'].astype(str)
                df_master['lot'] = df_master['lot'].astype(str)
                
                # Fusion (Merge)
                comp = pd.merge(df_master, saisie_grouped, on=['designation', 'lot'], how='left')
                
                # Calculs
                comp['qte_saisie'] = comp['qte_saisie'].fillna(0)
                comp['écart'] = comp['qte_saisie'] - comp['stock_theorique']
                
                # Affichage du tableau
                st.dataframe(comp[['designation', 'lot', 'ddp', 'stock_theorique', 'qte_saisie', 'écart']], use_container_width=True)

                # --- ACTIONS DE GESTION ---
                st.divider()
                col_1, col_2 = st.columns(2)
                
                with col_1:
                    st.write("#### 📂 Archivage")
                    if st.button("📦 Archiver l'inventaire actuel", use_container_width=True):
                        ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M")
                        arch_path = os.path.join(ARCHIVE_DIR, f"archive_lot_{ts}.csv")
                        saisie.to_csv(arch_path, index=False, sep=';', encoding='utf-8-sig')
                        if os.path.exists(SAISIE_PATH): os.remove(SAISIE_PATH)
                        st.success(f"Archivé vers : {arch_path}")
                        st.rerun()

                with col_2:
                    st.write("#### 🗑️ Réinitialisation")
                    confirm = st.checkbox("Je confirme la suppression complète du tableau de saisie")
                    if st.button("⚠️ Vider tout l'inventaire", disabled=not confirm, use_container_width=True):
                        if os.path.exists(SAISIE_PATH): os.remove(SAISIE_PATH)
                        st.warning("Inventaire réinitialisé.")
                        st.rerun()
            else:
                st.error("Le fichier de saisie n'a pas les colonnes requises. Veuillez le réinitialiser.")
        else:
            st.info("Aucune donnée saisie pour le moment.")
    else:
        st.warning("Accès réservé à l'administrateur.")

# 4. ADMINISTRATION
with tabs[3]:
    if user['role'] == "Admin":
        st.header("⚙️ Import Master Logipharm")
        file = st.file_uploader("Fichier Excel Logipharm", type=["xlsx"])
        if file:
            with open(MASTER_PATH, "wb") as f:
                f.write(file.getbuffer())
            st.success("Fichier Master mis à jour avec succès.")
            st.rerun()
    else:
        st.warning("Accès restreint.")
