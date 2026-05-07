import streamlit as st
import pandas as pd
import os
import unicodedata
from datetime import datetime
from tinydb import TinyDB, Query
from utils import log_action

# --- 1. CONFIGURATION ---
DATA_DIR = "data_inventaire_detail"
MASTER_PATH = os.path.join(DATA_DIR, "master_detail.xlsx")
os.makedirs(DATA_DIR, exist_ok=True)

db = TinyDB('db_pharmaciel.json')
table_inv = db.table('inventaire_triple')

# st.set_page_config(page_title="Inventaire Triple - Darpharm", layout="wide", page_icon="📋")

def normalize_text(text):
    if not isinstance(text, str): return str(text)
    return unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8').lower().strip()

def robust_num(s):
    if pd.isna(s) or s == "": return 0.0
    try: return float(str(s).replace('\xa0', '').replace(' ', '').replace(',', '.'))
    except: return 0.0

# --- 2. CHARGEMENT MASTER ---
@st.cache_data(ttl=60)
def load_master():
    if not os.path.exists(MASTER_PATH): return None
    try:
        df = pd.read_excel(MASTER_PATH)
        # Normalisation basique des colonnes
        mapping = {
            'designation': 'produit', 'produit': 'produit', 'article': 'produit',
            'lot': 'lot', 'n°lot': 'lot', 'batch': 'lot',
            'ppa': 'ppa', 'shp': 'shp', 'stock': 'shp', 'ddp': 'ddp', 'exp': 'ddp'
        }
        # Attribution des nouveaux noms avec gestion des doublons
        used_names = {}
        final_cols = []
        for col in df.columns:
            norm = normalize_text(col)
            mapped_name = norm
            for k, v in mapping.items():
                if k in norm:
                    mapped_name = v
                    break
            
            # Gestion des doublons pour éviter que df['col'] devienne un DataFrame
            if mapped_name in used_names:
                used_names[mapped_name] += 1
                mapped_name = f"{mapped_name}_{used_names[mapped_name]}"
            else:
                used_names[mapped_name] = 0
            final_cols.append(mapped_name)
            
        df.columns = final_cols
        
        # Nettoyage types
        for col in ['produit', 'lot']:
            if col in df.columns: df[col] = df[col].astype(str).str.upper().str.strip()
        if 'shp' in df.columns: df['shp'] = df['shp'].apply(robust_num)
        if 'ppa' in df.columns: df['ppa'] = df['ppa'].apply(robust_num)
        return df
    except Exception as e: 
        st.error(f"Erreur technique lors de la lecture de l'Excel : {e}")
        return None

df_master = load_master()

# --- 3. INITIALISATION SESSION STATE ---
if 'it_prod' not in st.session_state: st.session_state.it_prod = ""
if 'it_lot' not in st.session_state: st.session_state.it_lot = ""
if 'it_terrain' not in st.session_state: st.session_state.it_terrain = {"vrac": 0.0, "colis": 0.0, "ddp": "", "ppa": 0.0}
if 'it_mini' not in st.session_state: st.session_state.it_mini = {"vrac": 0.0, "colis": 0.0}

st.header("📋 Inventaire Triple & Confrontation", divider="orange")

tabs = st.tabs(["📍 Saisie Terrain", "🏢 Saisie Mini Stock", "📊 Saisie Finale & Confrontation", "⚙️ Administration"])

# --- ONGLET 1 : SAISIE TERRAIN ---
with tabs[0]:
    st.subheader("📍 Étape 1 : Zone de Préparation (Terrain)")
    
    if df_master is not None:
        prods = sorted(df_master['produit'].unique().tolist())
        col1, col2 = st.columns(2)
        
        with col1:
            it_prod = st.selectbox("Produit :", [""] + prods, key="it_prod_sel")
        
        if it_prod:
            lots = sorted(df_master[df_master['produit'] == it_prod]['lot'].unique().tolist())
            with col2:
                it_lot = st.selectbox("Lot Master :", lots, key="it_lot_sel")
            
            if it_lot:
                # Pré-remplissage auto depuis le master
                info_m = df_master[(df_master['produit'] == it_prod) & (df_master['lot'] == it_lot)].iloc[0]
                
                with st.form("form_terrain"):
                    c1, c2 = st.columns(2)
                    lot_reel = c1.text_input("🏷️ Lot Réel", value=it_lot)
                    ddp_reel = c2.text_input("📅 DDP (MM/AAAA)", value=str(info_m.get('ddp', '')))
                    ppa_reel = c1.number_input("💰 PPA Saisi", value=robust_num(info_m.get('ppa', 0.0)))
                    
                    st.divider()
                    st.markdown("##### 📍 Quantités Terrain (Préparation)")
                    cq1, cq2 = st.columns(2)
                    vrac_p = cq1.number_input("📦 Vrac (Prépa)", min_value=0.0, step=1.0)
                    colis_p = cq2.number_input("📦 Colis Fermé (Prépa)", min_value=0.0, step=1.0)
                    
                    total_terrain = vrac_p + colis_p
                    st.info(f"💡 Total Terrain calculé : **{total_terrain}**")
                    
                    if st.form_submit_button("✅ Enregistrer Étape 1"):
                        # Validation DDP
                        valid_date = True
                        if ddp_reel and "/" in ddp_reel:
                            try:
                                parts = ddp_reel.split("/")
                                if len(parts) == 2 and len(parts[0]) == 2 and len(parts[1]) == 4: pass
                                else: valid_date = False
                            except: valid_date = False
                        
                        if not valid_date:
                            st.error("Format DDP invalide. Utilisez MM/AAAA (ex: 05/2026)")
                        else:
                            st.session_state.it_prod = it_prod
                            st.session_state.it_lot = lot_reel
                            st.session_state.it_terrain = {
                                "vrac": vrac_p, "colis": colis_p, 
                                "ddp": ddp_reel, "ppa": ppa_reel, 
                                "lot_master": it_lot
                            }
                            st.success(f"Étape 1 validée pour {it_prod} ! Passez à l'onglet Mini Stock.")
    else:
        st.error("⚠️ Fichier Master introuvable. Veuillez l'importer dans l'onglet **Administration** de ce module.")

# --- ONGLET 2 : SAISIE MINI STOCK ---
with tabs[1]:
    st.subheader("🏢 Étape 2 : Zone Fond de Salle (Mini Stock)")
    
    if not st.session_state.it_prod:
        st.warning("⚠️ Veuillez d'abord valider l'Étape 1 (Saisie Terrain).")
    else:
        st.markdown(f"**Produit :** `{st.session_state.it_prod}` | **Lot :** `{st.session_state.it_lot}`")
        st.warning("⚠️ **Remarque :** Veuillez saisir la qte des **BOITES** et pas le nombre des colis.")
        
        with st.form("form_mini"):
            cq1, cq2 = st.columns(2)
            vrac_m = cq1.number_input("📦 Vrac (Mini Stock)", min_value=0.0, step=1.0)
            colis_m = cq2.number_input("📦 Colis Fermé (Mini Stock)", min_value=0.0, step=1.0)
            
            total_mini = vrac_m + colis_m
            st.info(f"💡 Total Mini Stock calculé : **{total_mini}**")
            
            if st.form_submit_button("✅ Enregistrer Étape 2"):
                st.session_state.it_mini = {"vrac": vrac_m, "colis": colis_m}
                st.success("Étape 2 validée ! Passez à la Confrontation Finale.")

# --- ONGLET 3 : CONFRONTATION ---
with tabs[2]:
    st.subheader("📊 Étape 3 : Saisie Finale & Confrontation")
    
    if df_master is not None:
        with st.expander("🖨️ Impression des Fiches Terrain (Triple)"):
            from utils_pdf import generate_blank_inventory_pdf
            st.write("Générer une fiche vierge avec colonnes pour Terrain et Mini Stock.")
            
            # On imprime tout le master par défaut, ou on peut filtrer par produit si besoin
            # Mais une fiche vierge est généralement globale
            cols_to_print = [('produit', 'Produit', 58), ('lot', 'Lot', 25)]
            pdf_bytes = generate_blank_inventory_pdf(df_master, "Inventaire Triple", cols_to_print)
            
            st.download_button(
                "📥 Télécharger la Fiche Vierge Triple",
                pdf_bytes,
                "Fiche_Vierge_Triple.pdf",
                "application/pdf"
            )
        st.divider()
    # 1. Traitement de la saisie actuelle
    if st.session_state.it_prod and st.session_state.it_mini['vrac'] + st.session_state.it_mini['colis'] >= 0:
        st.markdown("### 📥 Validation de la saisie en cours")
        
        t_terrain = st.session_state.it_terrain['vrac'] + st.session_state.it_terrain['colis']
        t_mini = st.session_state.it_mini['vrac'] + st.session_state.it_mini['colis']
        total_global = t_terrain + t_mini
        
        # Récupération SHP (Master)
        shp_master = 0.0
        if df_master is not None:
            m_match = df_master[(df_master['produit'] == st.session_state.it_prod) & 
                                (df_master['lot'] == st.session_state.it_terrain['lot_master'])]
            if not m_match.empty:
                shp_master = robust_num(m_match.iloc[0].get('shp', 0.0))
        
        # Affichage récapitulatif
        col_res1, col_res2, col_res3, col_res4 = st.columns(4)
        col_res1.metric("Détail (Terrain)", t_terrain)
        col_res2.metric("Mini Stock", t_mini)
        col_res3.metric("Total Saisi", total_global)
        col_res4.metric("SHP (Théorique)", shp_master, delta=total_global - shp_master)
        
        if st.button("💾 Enregistrer Définitivement en Base", type="primary", use_container_width=True):
            table_inv.insert({
                "date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                "produit": st.session_state.it_prod,
                "lot": st.session_state.it_lot,
                "lot_master": st.session_state.it_terrain['lot_master'],
                "detail_terrain": t_terrain,
                "mini_stock": t_mini,
                "total": total_global,
                "ppa": st.session_state.it_terrain['ppa'],
                "shp": shp_master,
                "ddp": st.session_state.it_terrain['ddp'],
                "agent": st.session_state.current_user.get('username', 'Inconnu')
            })
            log_action(st.session_state.current_user['username'], f"Inventaire Triple: {st.session_state.it_prod}", "Inventaire")
            st.success("✅ Données enregistrées avec succès !")
            # Reset
            st.session_state.it_prod = ""
            st.rerun()

    st.divider()
    
    # 2. Tableau récapitulatif de toutes les saisies
    st.markdown("### 📑 Tableau Récapitulatif & Confrontation")
    data_saved = table_inv.all()
    if data_saved:
        df_final = pd.DataFrame(data_saved)
        
        # Calcul de l'écart pour le style
        df_final['Ecart'] = df_final['total'] - df_final['shp']
        
        def highlight_diff(row):
            return ['background-color: #ff4b4b; color: white' if row['Ecart'] != 0 else '' for _ in row]

        # Configuration des colonnes pour correspondre exactement à la demande
        st.dataframe(
            df_final[['produit', 'lot', 'detail_terrain', 'mini_stock', 'total', 'ppa', 'shp', 'ddp', 'Ecart']],
            column_config={
                "produit": "Produit",
                "lot": "Lot",
                "detail_terrain": "Détail (Terrain)",
                "mini_stock": "Mini Stock",
                "total": "Total Saisi",
                "ppa": "PPA",
                "shp": "SHP (Master)",
                "ddp": "DDP",
                "Ecart": st.column_config.NumberColumn("Écart", format="%.0f")
            },
            use_container_width=True,
            hide_index=True
        )
        
        # Actions Admin
        if st.session_state.current_user.get('role') == 'Admin':
            if st.button("🗑️ Vider l'historique des confrontations"):
                table_inv.truncate()
                st.rerun()
    else:
        st.info("Aucune donnée enregistrée dans le tableau final pour le moment.")

# --- ONGLET 4 : ADMINISTRATION ---
with tabs[3]:
    st.subheader("⚙️ Gestion des données Master")
    st.write("Importez ici le fichier Master (Excel) contenant la liste des produits, lots et stocks théoriques.")
    
    up = st.file_uploader("📁 Choisir le fichier Master (Excel)", type="xlsx", key="up_triple")
    if up:
        st.warning("⚠️ Le fichier est chargé mais pas encore enregistré. Cliquez sur le bouton ci-dessous pour valider.")
        if st.button("🚀 Valider l'importation et mettre à jour la base"):
            try:
                # Création du dossier si inexistant
                os.makedirs(DATA_DIR, exist_ok=True)
                with open(MASTER_PATH, "wb") as f:
                    f.write(up.getbuffer())
                
                # Test de lecture immédiat
                test_df = pd.read_excel(MASTER_PATH)
                if not test_df.empty:
                    st.cache_data.clear()
                    st.success(f"✅ Fichier '{up.name}' importé avec succès ! ({len(test_df)} lignes détectées)")
                    st.rerun()
                else:
                    st.error("Le fichier semble vide.")
            except Exception as e:
                st.error(f"Échec de l'importation : {e}")

    st.divider()
    if st.session_state.current_user.get('role') == 'Admin':
        st.subheader("🗑️ Nettoyage des données")
        if st.button("🔴 Supprimer le fichier Master"):
            if os.path.exists(MASTER_PATH):
                os.remove(MASTER_PATH)
                st.cache_data.clear()
                st.success("Fichier Master supprimé.")
                st.rerun()
            else:
                st.info("Aucun Master à supprimer.")
        
        if st.button("🗑️ Vider toutes les confrontations enregistrées", type="primary"):
            table_inv.truncate()
            st.success("Historique vidé.")
            st.rerun()
