import streamlit as st
import pandas as pd
import os
from utils_ia import ask_ai, is_ia_enabled

# --- CONFIGURATION ---
# st.set_page_config(page_title="Darpharm Solution", layout="wide")
DATA_DIR = "data_inventaire"
os.makedirs(DATA_DIR, exist_ok=True)
MASTER_PATH = os.path.join(DATA_DIR, "master.xlsx")
SAISIE_PATH = os.path.join(DATA_DIR, "saisie.csv")

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
        # Initialiser la liste des produits pour le selectbox
        liste_produits = sorted(df_master['designation'].unique().tolist())
        
        c_m1, c_m2 = st.columns([1, 2])
        with c_m1:
            mode = st.radio("Méthode d'inventaire", ["⚡ Rapide (Qte uniquement)", "📑 Détaillé (Complet)"])
        with c_m2:
            produit_sel = st.selectbox("🔍 Sélectionner un produit", [""] + liste_produits)

        if produit_sel:
            # Récupérer les infos du master pour ce produit
            info_master = df_master[df_master['designation'] == produit_sel].iloc[0]
            
            with st.form("form_saisie_inventaire", clear_on_submit=True):
                st.write(f"Saisie pour : **{produit_sel}**")
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    qte_in = st.number_input("Quantité", min_value=0.0, step=1.0)
                
                if mode == "📑 Détaillé (Complet)":
                    with col2:
                        lot_in = st.text_input("Lot", value=str(info_master.get('lot', '')))
                    with col3:
                        ddp_in = st.text_input("DDP (MM/AA)", value=str(info_master.get('ddp', '')))
                    with col4:
                        ppa_in = st.number_input("PPA", value=float(info_master.get('ppa', 0.0)))
                    with col5:
                        shp_in = st.text_input("SHP", value=str(info_master.get('shp', '')))
                else:
                    # En mode rapide, on prend les valeurs du master
                    lot_in = str(info_master.get('lot', 'N/A'))
                    ddp_in = str(info_master.get('ddp', 'N/A'))
                    ppa_in = float(info_master.get('ppa', 0.0))
                    shp_in = str(info_master.get('shp', 'N/A'))
                    st.info(f"Lot: {lot_in} | DDP: {ddp_in} | PPA: {ppa_in}")

                submit_saisie = st.form_submit_button("➕ Ajouter à l'inventaire")

                if submit_saisie:
                    if qte_in > 0:
                        new_entry = {
                            'designation': produit_sel,
                            'qte_saisie': qte_in,
                            'lot': lot_in,
                            'ddp': ddp_in,
                            'ppa': ppa_in,
                            'shp': shp_in,
                            'saisi_par': user['username'],
                            'date_saisie': pd.Timestamp.now().strftime("%d/%m/%Y %H:%M")
                        }
                        
                        # Sauvegarde
                        df_new = pd.DataFrame([new_entry])
                        if os.path.exists(SAISIE_PATH):
                            df_old = pd.read_csv(SAISIE_PATH, sep=';', encoding='utf-8-sig')
                            df_final = pd.concat([df_old, df_new], ignore_index=True)
                        else:
                            df_final = df_new
                        
                        df_final.to_csv(SAISIE_PATH, index=False, sep=';', encoding='utf-8-sig')
                        st.success(f"✅ Ajouté : {produit_sel} (Qte: {qte_in})")
                        st.rerun()
                    else:
                        st.error("La quantité doit être supérieure à 0.")

        st.divider()
        st.subheader("📋 Historique de saisie (Détail des lots)")
        if os.path.exists(SAISIE_PATH):
            df_saisie_view = pd.read_csv(SAISIE_PATH, sep=';', encoding='utf-8-sig')
            st.dataframe(df_saisie_view.sort_index(ascending=False), use_container_width=True)
            
            if st.button("🗑️ Supprimer la dernière ligne"):
                df_saisie_view = df_saisie_view.drop(df_saisie_view.index[-1])
                df_saisie_view.to_csv(SAISIE_PATH, index=False, sep=';', encoding='utf-8-sig')
                st.rerun()
        else:
            st.info("Aucune saisie pour le moment.")

# 3. CONFRONTATION
with tabs[2]:
    st.subheader("🔍 Analyse des écarts (Minitieuse)")
    if user['role'] == "Admin":
        if os.path.exists(SAISIE_PATH) and df_master is not None:
            saisie = pd.read_csv(SAISIE_PATH, sep=';', encoding='utf-8-sig')
            saisie = clean_columns(saisie)
            q_theo_col = find_quantity_col(df_master)
            
            if q_theo_col and 'designation' in df_master.columns:
                # Grouper la saisie par produit pour avoir la quantité totale (tous lots confondus)
                saisie_grouped = saisie.groupby('designation')['qte_saisie'].sum().reset_index()
                
                # Fusionner avec le Master
                comp = pd.merge(df_master, saisie_grouped, on='designation', how='left')
                comp['qte_saisie'] = comp['qte_saisie'].fillna(0)
                comp['écart'] = comp['qte_saisie'] - comp[q_theo_col]
                
                st.write("### Tableau Récapitulatif")
                st.dataframe(comp[['designation', 'laboratoire', q_theo_col, 'qte_saisie', 'écart']], use_container_width=True)
                
                # EXPORT EXCEL
                import io
                buffer = io.BytesIO()
                comp.to_excel(buffer, index=False)
                st.download_button(
                    label="📥 Exporter les écarts en Excel",
                    data=buffer.getvalue(),
                    file_name="Ecarts_Inventaire_Detaille.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary"
                )
                
                st.divider()
                st.write("### Détail par Lot (Saisie terrain)")
                st.dataframe(saisie, use_container_width=True)

                if st.button("🗑️ Réinitialiser tout l'inventaire"):
                    os.remove(SAISIE_PATH)
                    st.rerun()
            
            # --- ANALYSE IA ---
            if is_ia_enabled():
                st.divider()
                with st.expander("🤖 Assistant IA Inventaire"):
                    if st.button("📊 Analyser les écarts", use_container_width=True):
                        with st.spinner("L'IA analyse vos données..."):
                            ecarts = comp[comp['écart'] != 0][['designation', 'écart']].to_dict('records')
                            prompt = f"Voici les écarts d'inventaire détectés : {ecarts}. Donne-moi un résumé des 3 plus gros problèmes et suggère des actions correctives pour un dépôt pharmaceutique."
                            st.write(ask_ai(prompt))
        else: st.info("Aucune donnée de saisie trouvée.")
    else: st.warning("Accès restreint à l'administrateur.")

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
