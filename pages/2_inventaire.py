import streamlit as st
import pandas as pd
import os

# --- CONFIGURATION ---
# st.set_page_config(page_title="Pharmaciel Pro", layout="wide")
DATA_DIR = "data_inventaire"
os.makedirs(DATA_DIR, exist_ok=True)
MASTER_PATH = os.path.join(DATA_DIR, "master.xlsx")
SAISIE_PATH = os.path.join(DATA_DIR, "saisie.csv")
USERS_PATH = os.path.join(DATA_DIR, "users.csv")

# --- FONCTIONS ---
def clean_columns(df_to_clean):
    df_to_clean.columns = df_to_clean.columns.astype(str).str.lower().str.strip()
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

# --- SIDEBAR ---
with st.sidebar:
    st.title("🛡️ Contrôle")
    st.write(f"Utilisateur : **{user['username']}**")
    st.divider()

df_master = load_data()

# --- INTERFACE (Définition des onglets ici) ---
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
    else: st.info("Chargez un Master dans l'onglet Administration.")

# 2. SAISIE
with tabs[1]:
    st.subheader("📝 Saisie Inventaire")
    if df_master is not None:
        c_m1, c_m2, c_m3 = st.columns([1, 1, 1])
        with c_m1:
            mode = st.radio("Méthode d'inventaire", ["⚡ Rapide (Qte uniquement)", "📑 Détaillé (Complet)"])
        with c_m2:
            all_labs = sorted(df_master['laboratoire'].unique().tolist()) if 'laboratoire' in df_master.columns else []
            selected_labs = st.multiselect("🧪 Filtrer par Labo", all_labs)
        with c_m3:
            search = st.text_input("🔍 Scanner (Douchette) / Rechercher")

        df_work = df_master.copy()
        if selected_labs:
            df_work = df_work[df_work['laboratoire'].isin(selected_labs)]
        if search:
            df_work = df_work[df_work['designation'].str.contains(search, case=False, na=False)]
        
        if 'qte_saisie' not in df_work.columns:
            df_work['qte_saisie'] = 0.0

        q_theo_col = find_quantity_col(df_master)
        
        if mode == "⚡ Rapide (Qte uniquement)":
            cols_to_show = ['designation', 'qte_saisie']
            disabled_cols = ['designation']
        else:
            cols_to_show = list(df_work.columns)
            if q_theo_col in cols_to_show:
                cols_to_show.remove(q_theo_col)
            disabled_cols = ['designation']

        edited = st.data_editor(df_work[cols_to_show], use_container_width=True, key=f"edit_{mode}", disabled=disabled_cols)
        
        if st.button("💾 Enregistrer l'inventaire"):
            to_save = edited[edited['qte_saisie'] > 0].copy()
            if not to_save.empty:
                to_save['saisi_par'] = user['username']
                try:
                    if os.path.exists(SAISIE_PATH):
                        old = pd.read_csv(SAISIE_PATH, sep=';', encoding='utf-8-sig')
                        to_save = pd.concat([old, to_save]).drop_duplicates(subset=['designation'], keep='last')
                    to_save.to_csv(SAISIE_PATH, index=False, sep=';', encoding='utf-8-sig')
                    st.success(f"✅ Enregistrement réussi !")
                except PermissionError:
                    st.error("Fermez le fichier 'saisie.csv' !")

# 3. CONFRONTATION
with tabs[2]:
    st.subheader("🔍 Analyse des écarts")
    if user['role'] == "Admin":
        if os.path.exists(SAISIE_PATH) and df_master is not None:
            saisie = pd.read_csv(SAISIE_PATH, sep=';', encoding='utf-8-sig')
            saisie = clean_columns(saisie)
            q_theo_col = find_quantity_col(df_master)
            if q_theo_col and 'designation' in df_master.columns:
                comp = pd.merge(df_master, saisie[['designation', 'qte_saisie']], on='designation', how='inner')
                comp['écart'] = comp['qte_saisie'] - comp[q_theo_col]
                st.dataframe(comp[['designation', 'laboratoire', q_theo_col, 'qte_saisie', 'écart']], use_container_width=True)
                
                # EXPORT EXCEL
                import io
                buffer = io.BytesIO()
                comp.to_excel(buffer, index=False)
                st.download_button(
                    label="📥 Exporter les écarts en Excel",
                    data=buffer.getvalue(),
                    file_name="Ecarts_Inventaire.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )
                
                if st.button("🗑️ Reset Inventaire"):
                    os.remove(SAISIE_PATH)
                    st.rerun()
        else: st.info("Aucune donnée.")
    else: st.warning("Accès restreint.")

# 4. ADMINISTRATION
with tabs[3]:
    if user['role'] == "Admin":
        st.header("⚙️ Configuration Admin")
        up = st.file_uploader("Upload Master Excel", type=["xlsx"])
        if up:
            with open(MASTER_PATH, "wb") as f: f.write(up.getbuffer())
            st.success("Fichier Master importé avec succès.")
            st.rerun()
        st.info("💡 Note : La gestion des utilisateurs se fait désormais dans le menu principal 'Administration Centrale'.")
    else:
        st.warning("Accès restreint.")
