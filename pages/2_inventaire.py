import streamlit as st
import pandas as pd
import os
import unicodedata
import io
from utils_ia import ask_ai, is_ia_enabled

# --- CONFIGURATION ---
st.set_page_config(page_title="Darpharm Solution", layout="wide")
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

def safe_float(val, default=0.0):
    try:
        if pd.isna(val): return default
        if isinstance(val, str):
            val = val.replace(' ', '').replace(',', '.')
        return float(val)
    except:
        return default

def clean_columns(df_to_clean):
    mapping = {
        'designation': 'designation',
        'produit': 'designation',
        'article': 'designation',
        'lot': 'lot',
        'ddp': 'ddp',
        'peremption': 'ddp',
        'ppa': 'ppa',
        'shp': 'shp',
        'laboratoire': 'laboratoire',
        'labo': 'laboratoire'
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

def find_quantity_col(df_check):
    keywords = ['quantit', 'depot', 'stock', 'qte', 'globale']
    for col in df_check.columns:
        if any(key in col for key in keywords):
            return col
    return None

# --- INITIALISATION ET SESSION ---
if "current_user" not in st.session_state or st.session_state.current_user is None:
    st.warning("Veuillez vous connecter depuis la page principale.")
    st.stop()

user = st.session_state.current_user
df_master = load_data()

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Contrôle")
    st.write(f"Utilisateur : **{user['username']}**")
    st.write(f"Rôle : `{user['role']}`")
    st.divider()

# --- INTERFACE PRINCIPALE ---
tabs = st.tabs(["📊 Tableau de Bord", "📝 Saisie", "🔍 Confrontation", "⚙️ Administration"])

# 1. TABLEAU DE BORD
with tabs[0]:
    st.subheader("Vue d'ensemble")
    if df_master is not None:
        c1, c2 = st.columns(2)
        c1.metric("Produits au Master", len(df_master))
        if os.path.exists(SAISIE_PATH):
            try:
                s_count = pd.read_csv(SAISIE_PATH, sep=';', encoding='utf-8-sig')
                c2.metric("Lignes Saisies", len(s_count))
            except: c2.metric("Lignes Saisies", 0)
        else:
            c2.metric("Lignes Saisies", 0)
    else:
        st.info("Chargez un Master dans l'onglet Administration.")

# 2. SAISIE
with tabs[1]:
    st.subheader("📝 Saisie Inventaire")
    if df_master is not None:
        if 'designation' not in df_master.columns:
            st.error("⚠️ Colonne 'Désignation' introuvable.")
            st.stop()
            
        liste_produits = sorted(df_master['designation'].unique().tolist())
        
        c_m1, c_m2 = st.columns([1, 2])
        with c_m1:
            mode = st.radio("Méthode", ["⚡ Rapide", "📑 Détaillé"])
        with c_m2:
            produit_sel = st.selectbox("🔍 Produit", [""] + liste_produits)

        if produit_sel:
            info_master = df_master[df_master['designation'] == produit_sel].iloc[0]
            
            with st.form("form_saisie", clear_on_submit=True):
                st.write(f"Saisie : **{produit_sel}**")
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    qte_in = st.number_input("Quantité", min_value=0.0, step=1.0)
                
                if mode == "📑 Détaillé":
                    with col2: lot_in = st.text_input("Lot", value=str(info_master.get('lot', '')))
                    with col3: ddp_in = st.text_input("DDP", value=str(info_master.get('ddp', '')))
                    with col4: ppa_in = st.number_input("PPA", value=safe_float(info_master.get('ppa', 0.0)))
                    with col5: shp_in = st.text_input("SHP", value=str(info_master.get('shp', '')))
                else:
                    lot_in = str(info_master.get('lot', 'N/A'))
                    ddp_in = str(info_master.get('ddp', 'N/A'))
                    ppa_in = safe_float(info_master.get('ppa', 0.0))
                    shp_in = str(info_master.get('shp', 'N/A'))
                    st.info(f"Auto : Lot {lot_in} | DDP {ddp_in} | PPA {ppa_in}")

                if st.form_submit_button("➕ Ajouter"):
                    if qte_in > 0:
                        new_entry = {
                            'designation': produit_sel,
                            'qte_saisie': qte_in,
                            'lot': lot_in, 'ddp': ddp_in, 'ppa': ppa_in, 'shp': shp_in,
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
                        st.success("Ajouté !")
                        st.rerun()

        st.divider()
        if os.path.exists(SAISIE_PATH):
            df_view = pd.read_csv(SAISIE_PATH, sep=';', encoding='utf-8-sig')
            st.dataframe(df_view.sort_index(ascending=False), use_container_width=True)
            if st.button("🗑️ Supprimer dernière ligne"):
                df_view.drop(df_view.index[-1]).to_csv(SAISIE_PATH, index=False, sep=';', encoding='utf-8-sig')
                st.rerun()

# 3. CONFRONTATION (Avec boutons Archivage et Reset)
with tabs[2]:
    st.subheader("🔍 Confrontation & Écarts")
    if user['role'] == "Admin":
        if os.path.exists(SAISIE_PATH) and df_master is not None:
            saisie = pd.read_csv(SAISIE_PATH, sep=';', encoding='utf-8-sig')
            q_theo_col = find_quantity_col(df_master)
            
            if q_theo_col:
                # Calcul des écarts
                saisie_grouped = saisie.groupby('designation')['qte_saisie'].sum().reset_index()
                comp = pd.merge(df_master, saisie_grouped, on='designation', how='left')
                
                for c in ['qte_saisie', q_theo_col]:
                    comp[c] = pd.to_numeric(comp[c], errors='coerce').fillna(0)
                
                comp['écart'] = comp['qte_saisie'] - comp[q_theo_col]
                
                # Affichage
                st.write("### Synthèse des écarts")
                st.dataframe(comp[['designation', q_theo_col, 'qte_saisie', 'écart']], use_container_width=True)
                
                # --- ACTIONS DE GESTION ---
                st.divider()
                st.subheader("📦 Fin de session d'inventaire")
                
                col_arch, col_reset = st.columns(2)
                
                with col_arch:
                    st.write("**Archivage**")
                    if st.button("📦 Archiver l'inventaire actuel", use_container_width=True):
                        ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M")
                        arch_name = os.path.join(ARCHIVE_DIR, f"archive_{ts}.csv")
                        saisie.to_csv(arch_name, index=False, sep=';', encoding='utf-8-sig')
                        if os.path.exists(SAISIE_PATH): os.remove(SAISIE_PATH)
                        st.success(f"Inventaire archivé : {arch_name}")
                        st.rerun()
                
                with col_reset:
                    st.write("**Remise à zéro**")
                    confirm = st.checkbox("Confirmer la suppression totale")
                    if st.button("🗑️ Réinitialiser (Vider tout)", disabled=not confirm, use_container_width=True):
                        if os.path.exists(SAISIE_PATH): os.remove(SAISIE_PATH)
                        st.warning("Données de saisie supprimées.")
                        st.rerun()

            # --- IA ---
            if is_ia_enabled():
                with st.expander("🤖 Assistant IA"):
                    if st.button("Analyser les écarts"):
                        ecarts = comp[comp['écart'] != 0][['designation', 'écart']].head(10).to_dict('records')
                        st.write(ask_ai(f"Analyse ces écarts pharma : {ecarts}"))
        else:
            st.info("Aucune donnée de saisie.")
    else:
        st.warning("Accès Admin requis.")

# 4. ADMINISTRATION
with tabs[3]:
    if user['role'] == "Admin":
        st.header("⚙️ Config Master")
        up = st.file_uploader("Charger Master (XLSX)", type=["xlsx"])
        if up:
            with open(MASTER_PATH, "wb") as f: f.write(up.getbuffer())
            st.success("Master mis à jour.")
            st.rerun()
    else:
        st.warning("Accès restreint.")
