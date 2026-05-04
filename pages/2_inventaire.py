import streamlit as st
import pandas as pd
import os
import unicodedata
import io

# --- CONFIGURATION ---
st.set_page_config(page_title="Darpharm Solution - Gestion Arrivages", layout="wide")

DATA_DIR = "data_inventaire"
ARCHIVE_DIR = os.path.join(DATA_DIR, "archives")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True)

MASTER_PATH = os.path.join(DATA_DIR, "master.xlsx")
SAISIE_PATH = os.path.join(DATA_DIR, "saisie.csv")

# --- FONCTIONS DE NETTOYAGE ---

def normalize_text(text):
    if not isinstance(text, str): return str(text)
    text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
    return text.lower().strip()

def clean_columns(df_to_clean):
    mapping = {
        'produit': 'designation',
        'designation': 'designation',
        'n°lot': 'lot',
        'nlot': 'lot',
        'lot': 'lot',
        'qte_saisie': 'qte_saisie',
        'ddp': 'ddp',
        'ppa': 'ppa'
    }
    stock_keywords = ['quantit', 'depot', 'stock', 'theorique', 'qte']
    new_cols = []
    for col in df_to_clean.columns:
        norm_col = normalize_text(col)
        matched = False
        for key, target in mapping.items():
            if key in norm_col:
                new_cols.append(target)
                matched = True
                break
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

# --- SESSION ---
if "current_user" not in st.session_state:
    st.warning("Veuillez vous connecter.")
    st.stop()

user = st.session_state.current_user
df_master = load_data()

# --- INTERFACE ---
tabs = st.tabs(["📊 Dashboard", "📝 Saisie Terrain", "🔍 Confrontation (Lots)", "⚙️ Admin"])

# 1. TABLEAU DE BORD (Mise à jour avec Réinitialisation Master)
with tabs[0]:
    st.subheader("📦 Gestion du Master & Arrivages")
    
    if df_master is not None:
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Total Articles (Master)", len(df_master))
        with c2:
            # Option pour réinitialiser le Master en cas de nouvel arrivage
            st.write("**Nouvel Arrivage ?**")
            confirm_reset_master = st.checkbox("Confirmer la suppression du Master actuel")
            if st.button("🗑️ Réinitialiser le Master (Logipharm)", disabled=not confirm_reset_master, use_container_width=True):
                if os.path.exists(MASTER_PATH):
                    os.remove(MASTER_PATH)
                st.success("Le Master a été supprimé. Vous pouvez charger le nouveau fichier dans 'Admin'.")
                st.rerun()
        
        st.divider()
        st.write("### Aperçu des stocks théoriques actuels")
        st.dataframe(df_master.head(10), use_container_width=True)
    else:
        st.warning("⚠️ Aucun Master détecté. Veuillez charger un export Logipharm dans l'onglet 'Admin'.")
        if st.button("Aller à l'onglet Admin"):
            # Note: Streamlit ne permet pas de changer d'onglet par code facilement, 
            # mais ce bouton informe l'utilisateur.
            pass

# 2. SAISIE PAR LOT
with tabs[1]:
    st.subheader("📝 Saisie Inventaire")
    if df_master is not None:
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
                    qte_in = st.number_input("Quantité dénombrée", min_value=0.0, step=1.0)
                
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
                    st.success("Saisie enregistrée.")
                    st.rerun()

# 3. CONFRONTATION
with tabs[2]:
    st.subheader("🔍 Confrontation")
    if user['role'] == "Admin":
        if os.path.exists(SAISIE_PATH) and df_master is not None:
            saisie = pd.read_csv(SAISIE_PATH, sep=';', encoding='utf-8-sig')
            saisie = clean_columns(saisie)
            
            saisie_grouped = saisie.groupby(['designation', 'lot'])['qte_saisie'].sum().reset_index()
            saisie_grouped['lot'] = saisie_grouped['lot'].astype(str)
            df_master['lot'] = df_master['lot'].astype(str)
            
            comp = pd.merge(df_master, saisie_grouped, on=['designation', 'lot'], how='left')
            comp['qte_saisie'] = comp['qte_saisie'].fillna(0)
            
            if 'stock_theorique' in comp.columns:
                comp['écart'] = comp['qte_saisie'] - comp['stock_theorique']
                st.dataframe(comp[['designation', 'lot', 'stock_theorique', 'qte_saisie', 'écart']], use_container_width=True)
            
            st.divider()
            if st.button("📦 Archiver la Saisie (Vider le comptage uniquement)"):
                ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M")
                saisie.to_csv(os.path.join(ARCHIVE_DIR, f"archive_{ts}.csv"), index=False, sep=';')
                os.remove(SAISIE_PATH)
                st.rerun()
        else:
            st.info("En attente de saisie ou de Master.")
    else:
        st.warning("Accès restreint.")

# 4. ADMINISTRATION
with tabs[3]:
    if user['role'] == "Admin":
        st.header("⚙️ Import Logipharm")
        file = st.file_uploader("Nouveau Master Logipharm (XLSX)", type=["xlsx"])
        if file:
            with open(MASTER_PATH, "wb") as f:
                f.write(file.getbuffer())
            st.success("Nouveau Master chargé ! Les produits et lots sont mis à jour.")
            st.rerun()
