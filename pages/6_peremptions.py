import streamlit as st
import pandas as pd
import os
from datetime import datetime
from utils import log_action
from utils_ia import ask_ai, is_ia_enabled

# --- CONFIGURATION ---
DATA_DIR = "data_inventaire"
SAISIE_PATH = os.path.join(DATA_DIR, "saisie.csv")

def parse_ddp(ddp_str):
    if pd.isna(ddp_str) or ddp_str == "": return None
    ddp_str = str(ddp_str).strip()
    try:
        if '/' in ddp_str:
            parts = ddp_str.split('/')
            if len(parts) == 2:
                m, y = int(parts[0]), int(parts[1])
                if y < 100: y += 2000
                return datetime(y, m, 1)
        return pd.to_datetime(ddp_str)
    except: return None

def analyze_peremptions(df, date_col='ddp'):
    now = datetime.now()
    df['expiry_date'] = df[date_col].apply(parse_ddp)
    df_valid = df.dropna(subset=['expiry_date']).copy()
    if not df_valid.empty:
        df_valid['mois_restants'] = df_valid['expiry_date'].apply(lambda d: (d.year - now.year) * 12 + d.month - now.month)
        def categorize(m):
            if m < 0: return "❌ Périmé"
            if m <= 3: return "⚠️ Critique (< 3 mois)"
            if m <= 6: return "🟠 Vigilance (3-6 mois)"
            return "✅ OK (> 6 mois)"
        df_valid['Statut'] = df_valid['mois_restants'].apply(categorize)
        return df_valid
    return pd.DataFrame()

st.title("⏳ Gestion des Péremptions")

tab1, tab2 = st.tabs(["📋 Inventaire Terrain", "🏢 Analyse Multi-Dépôts"])

with tab1:
    st.subheader("Analyse de l'inventaire manuel")
    if os.path.exists(SAISIE_PATH):
        df_inv = pd.read_csv(SAISIE_PATH, sep=';', encoding='utf-8-sig')
        if 'ddp' in df_inv.columns:
            df_res = analyze_peremptions(df_inv)
            if not df_res.empty:
                stats = df_res['Statut'].value_counts()
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Périmés", stats.get("❌ Périmé", 0))
                c2.metric("Critiques", stats.get("⚠️ Critique (< 3 mois)", 0))
                c3.metric("Vigilance", stats.get("🟠 Vigilance (3-6 mois)", 0))
                c4.metric("Sains", stats.get("✅ OK (> 6 mois)", 0))
                st.dataframe(df_res.sort_values('expiry_date'), use_container_width=True)
            else: st.info("Aucune donnée valide.")
        else: st.warning("Colonne 'ddp' manquante.")
    else: st.info("Aucun inventaire terrain trouvé.")

with tab2:
    st.subheader("🔄 Analyse Stratégique FEFO (Vente vs Stockage)")
    st.write("Identifiez les produits qui périment plus vite en réserve qu'en zone de vente.")
    
    file_up = st.file_uploader("Importer fichier de Stock Multi-Dépôts (Excel)", type=["xlsx", "xls"])
    if file_up:
        try:
            df_ext = pd.read_excel(file_up)
            # Normalisation colonnes
            # Normalisation robuste des colonnes
            import unicodedata
            def norm_c(c):
                c = str(c).strip().lower()
                return ''.join(ch for ch in unicodedata.normalize('NFD', c) if unicodedata.category(ch) != 'Mn')
            
            df_ext.columns = [norm_c(c) for c in df_ext.columns]
            
            # Mappage flexible
            rename_map = {}
            for c in df_ext.columns:
                if 'produit' in c or 'designation' in c: rename_map[c] = 'produit'
                if 'depot' in c or 'magasin' in c: rename_map[c] = 'depot'
                if 'ddp' in c or 'peremption' in c or 'exp' in c: rename_map[c] = 'ddp'
                if 'quantite' in c or 'stock' in c or 'qte' in c: rename_map[c] = 'quantite'
            df_ext = df_ext.rename(columns=rename_map)

            if all(c in df_ext.columns for c in ['produit', 'depot', 'ddp']):
                df_ext['expiry_date'] = df_ext['ddp'].apply(parse_ddp)
                df_ext = df_ext.dropna(subset=['expiry_date', 'depot', 'produit'])
                all_depots = sorted(df_ext['depot'].unique().tolist())
                qte_col = 'quantite' if 'quantite' in df_ext.columns else None

                col_v, col_s = st.columns(2)
                with col_v:
                    dv = st.multiselect("🏪 Dépôts de Vente", all_depots, default=[d for d in all_depots if "principal" in d.lower() or "vente" in d.lower()])
                with col_s:
                    ds = st.multiselect("🏗️ Dépôts de Stockage", all_depots, default=[d for d in all_depots if "stock" in d.lower() or "transfert" in d.lower()])

                if dv and ds:
                    # Agrégation
                    df_vente = df_ext[df_ext['depot'].isin(dv)].groupby('produit').agg({'expiry_date': 'min'}).reset_index()
                    agg_s = {'expiry_date': 'min'}
                    if qte_col: agg_s[qte_col] = 'sum'
                    df_stock = df_ext[df_ext['depot'].isin(ds)].groupby('produit').agg(agg_s).reset_index()
                    
                    # Analyse FEFO
                    fefo = pd.merge(df_vente, df_stock, on='produit', suffixes=('_vente', '_stock'))
                    anomalies = fefo[fefo['expiry_date_stock'] < fefo['expiry_date_vente']].copy()
                    
                    if not anomalies.empty:
                        st.warning(f"🚨 {len(anomalies)} Anomalies de rotation détectées !")
                        anomalies['DDP Vente'] = anomalies['expiry_date_vente'].dt.strftime('%m/%Y')
                        anomalies['DDP Stock'] = anomalies['expiry_date_stock'].dt.strftime('%m/%Y')
                        st.dataframe(anomalies[['produit', 'DDP Vente', 'DDP Stock']].rename(columns={'produit':'Désignation'}), use_container_width=True, hide_index=True)
                        
                        if st.button("📝 Générer Bon de Transfert Prioritaire"):
                            from fpdf import FPDF
                            pdf = FPDF()
                            pdf.add_page(); pdf.set_font("Arial", 'B', 14)
                            pdf.cell(0, 10, "TRANSFERT PRIORITAIRE FEFO (RESERVE -> VENTE)", 0, 1, 'C')
                            pdf.set_font("Arial", 'B', 10)
                            pdf.cell(85, 8, "Designation", 1); pdf.cell(25, 8, "DDP Vente", 1); pdf.cell(25, 8, "DDP Stock", 1); pdf.cell(55, 8, "Action", 1, ln=1)
                            pdf.set_font("Arial", '', 9)
                            for _, row in anomalies.iterrows():
                                pdf.cell(85, 8, str(row['produit'])[:40].encode('latin-1','replace').decode('latin-1'), 1)
                                pdf.cell(25, 8, row['DDP Vente'], 1); pdf.cell(25, 8, row['DDP Stock'], 1); pdf.cell(55, 8, "TRANSFERT URGENT", 1, ln=1)
                            st.download_button("📥 Télécharger le Bon PDF", pdf.output(dest='S').encode('latin-1'), "Transfert_FEFO.pdf", type="primary")
                    else:
                        st.success("✅ Logique FEFO respectée : tous les produits en réserve périment après ceux en vente.")
                    
                    st.divider()
                    st.write("### 🔍 Vue d'ensemble comparative")
                    full = pd.merge(df_vente, df_stock, on='produit', how='outer', suffixes=('_vente', '_stock'))
                    full['Vente'] = full['expiry_date_vente'].dt.strftime('%m/%Y')
                    full['Stock'] = full['expiry_date_stock'].dt.strftime('%m/%Y')
                    st.dataframe(full[['produit', 'Vente', 'Stock']].fillna("-"), use_container_width=True)
            else:
                st.error("Colonnes 'produit', 'depot' et 'ddp' requises.")
        except Exception as e: st.error(f"Erreur: {e}")
