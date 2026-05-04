import streamlit as st
import pandas as pd
import os
import unicodedata
import io
from utils_ia import ask_ai, is_ia_enabled

# --- CONFIGURATION ---
st.set_page_config(page_title="Darpharm Solution - Mode Lot", layout="wide")
DATA_DIR = "data_inventaire"
ARCHIVE_DIR = os.path.join(DATA_DIR, "archives")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True)

MASTER_PATH = os.path.join(DATA_DIR, "master.xlsx")
SAISIE_PATH = os.path.join(DATA_DIR, "saisie.csv")

# --- FONCTIONS UTILITAIRES ---

def normalize_text(text):
    if not isinstance(text, str): return str(text)
    text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
    return text.lower().strip()

def clean_columns(df_to_clean):
    # Mapping adapté spécifiquement à l'export Logipharm (image_9b9137.png)
    mapping = {
        'produit': 'designation',
        'n°lot': 'lot',
        'nlot': 'lot',
        'quantité dépôt': 'stock_theorique',
        'quantite depot': 'stock_theorique',
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
        st.error(f"Erreur Master : {e}")
        return None

# --- INITIALISATION ---
if "current_user" not in st.session_state:
    st.warning("Veuillez vous connecter.")
    st.stop()

user = st.session_state.current_user
df_master = load_data()

# --- INTERFACE ---
tabs = st.tabs(["📊 Tableau de Bord", "📝 Saisie par Lot", "🔍 Confrontation détaillée", "⚙️ Administration"])

# 1. TABLEAU DE BORD
with tabs[0]:
    if df_master is not None:
        c1, c2 = st.columns(2)
        c1.metric("Lignes Master (Lots)", len(df_master))
        if os.path.exists(SAISIE_PATH):
            s_count = pd.read_csv(SAISIE_PATH, sep=';', encoding='utf-8-sig')
            c2.metric("Lots Saisis", len(s_count))
    else:
        st.info("Importez le fichier Logipharm dans Administration.")

# 2. SAISIE (Modifiée pour forcer la sélection du lot)
with tabs[1]:
    st.subheader("📝 Saisie par Lot")
    if df_master is not None:
        liste_produits = sorted(df_master['designation'].unique().tolist())
        produit_sel = st.selectbox("🔍 Sélectionner le produit", [""] + liste_produits)

        if produit_sel:
            # Filtrer les lots disponibles pour ce produit dans le master
            lots_disponibles = df_master[df_master['designation'] == produit_sel]['lot'].astype(str).tolist()
            
            with st.form("form_saisie_lot", clear_on_submit=True):
                col_l1, col_l2 = st.columns(2)
                with col_l1:
                    lot_sel = st.selectbox("📦 Sélectionner le Lot (Master)", lots_disponibles)
                with col_l2:
                    qte_in = st.number_input("Quantité dénombrée", min_value=0.0, step=1.0)
                
                # Récupérer infos auto pour ce lot spécifique
                info_lot = df_master[(df_master['designation'] == produit_sel) & (df_master['lot'].astype(str) == lot_sel)].iloc[0]
                
                st.info(f"Info Master pour ce lot : DDP: {info_lot.get('ddp','?')} | PPA: {info_lot.get('ppa',0)}")

                if st.form_submit_button("➕ Valider le lot"):
                    if qte_in >= 0:
                        new_entry = {
                            'designation': produit_sel,
                            'lot': lot_sel,
                            'qte_saisie': qte_in,
                            'ddp': info_lot.get('ddp',''),
                            'ppa': info_lot.get('ppa',0),
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
                        st.success(f"Lot {lot_sel} enregistré.")
                        st.rerun()

# 3. CONFRONTATION (La fusion se fait maintenant sur Designation ET Lot)
with tabs[2]:
    st.subheader("🔍 Analyse des écarts par Lot")
    if user['role'] == "Admin":
        if os.path.exists(SAISIE_PATH) and df_master is not None:
            saisie = pd.read_csv(SAISIE_PATH, sep=';', encoding='utf-8-sig')
            
            # On groupe la saisie par Produit + Lot (au cas où on saisit le même lot en plusieurs fois)
            saisie_grouped = saisie.groupby(['designation', 'lot'])['qte_saisie'].sum().reset_index()
            saisie_grouped['lot'] = saisie_grouped['lot'].astype(str)
            df_master['lot'] = df_master['lot'].astype(str)

            # Fusion sur les DEUX colonnes
            comp = pd.merge(df_master, saisie_grouped, on=['designation', 'lot'], how='left')
            
            comp['qte_saisie'] = comp['qte_saisie'].fillna(0)
            comp['écart'] = comp['qte_saisie'] - comp['stock_theorique']
            
            # Mise en forme
            def color_ecart(val):
                color = 'red' if val < 0 else 'green' if val > 0 else 'black'
                return f'color: {color}'

            st.dataframe(comp[['designation', 'lot', 'ddp', 'stock_theorique', 'qte_saisie', 'écart']].style.applymap(color_ecart, subset=['écart']), use_container_width=True)

            # --- BOUTONS ARCHIVE / RESET ---
            st.divider()
            c_a1, c_a2 = st.columns(2)
            with c_a1:
                if st.button("📦 Archiver l'inventaire Lot"):
                    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M")
                    saisie.to_csv(os.path.join(ARCHIVE_DIR, f"archive_lots_{ts}.csv"), index=False, sep=';')
                    os.remove(SAISIE_PATH)
                    st.rerun()
            with c_a2:
                conf = st.checkbox("Confirmer Reset Lot")
                if st.button("🗑️ Tout effacer", disabled=not conf):
                    os.remove(SAISIE_PATH)
                    st.rerun()
        else:
            st.info("Pas de saisie détectée.")

# 4. ADMINISTRATION
with tabs[3]:
    if user['role'] == "Admin":
        st.write("### Import Logipharm")
        up = st.file_uploader("Fichier Excel Logipharm", type=["xlsx"])
        if up:
            with open(MASTER_PATH, "wb") as f: f.write(up.getbuffer())
            st.success("Master Logipharm chargé !")
            st.rerun()
