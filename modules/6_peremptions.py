import streamlit as st
import pandas as pd
import os
from datetime import datetime
from utils import log_action
from utils_ia import ask_ai, is_ia_enabled

# --- CONFIGURATION ---
from utils_gsheets import load_gs_data
# --- CONFIGURATION ---
DATA_DIR = "data_inventaire"
SAISIE_WORKSHEET = "Saisie_Inventaire"
SAISIE_FALLBACK = os.path.join(DATA_DIR, "saisie.csv")
COLS_SAISIE = ["designation", "lot_master", "lot", "qte_saisie", "ddp_saisi", "ppa_saisi", "agent"]

def parse_ddp(ddp_str):
    if pd.isna(ddp_str) or ddp_str == "": return None
    ddp_str = str(ddp_str).strip()
    try:
        # Gérer format MM/AAAA
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
    # Si la colonne s'appelle ddp_saisi (format Inventaire)
    target_col = date_col
    if date_col not in df.columns and 'ddp_saisi' in df.columns:
        target_col = 'ddp_saisi'
        
    df['expiry_date'] = df[target_col].apply(parse_ddp)
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

tab1, tab2 = st.tabs(["📊 Tableau de Bord (DDP)", "🏢 Analyse Multi-Dépôts"])

with tab1:
    st.subheader("Vue Globale des Péremptions (DDP)")
    df_inv = load_gs_data(SAISIE_WORKSHEET, SAISIE_FALLBACK, COLS_SAISIE)
    if not df_inv.empty:
        # L'inventaire utilise 'ddp_saisi'
        df_res = analyze_peremptions(df_inv, date_col='ddp_saisi')
        if not df_res.empty:
            stats = df_res['Statut'].value_counts()
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("❌ Périmés", stats.get("❌ Périmé", 0))
            c2.metric("⚠️ Critiques (< 3m)", stats.get("⚠️ Critique (< 3 mois)", 0))
            c3.metric("🟠 Vigilance (3-6m)", stats.get("🟠 Vigilance (3-6 mois)", 0))
            c4.metric("✅ Sains", stats.get("✅ OK (> 6 mois)", 0))
            
            st.divider()
            
            col_list, col_action = st.columns([2, 1])
            with col_list:
                st.markdown("### 📋 Liste détaillée des produits")
                df_sorted = df_res.sort_values('expiry_date')[['designation', 'lot', 'ddp_saisi', 'Statut', 'mois_restants']]
                # Formater la date pour affichage
                df_sorted['ddp_saisi'] = pd.to_datetime(df_sorted['ddp_saisi']).dt.strftime('%d/%m/%Y')
                st.dataframe(df_sorted, use_container_width=True, hide_index=True)
                
            with col_action:
                st.markdown("### 💡 Solutions & Actions")
                critiques = df_res[df_res['Statut'].str.contains('Périmé|Critique', na=False)]
                if not critiques.empty:
                    st.warning(f"🚨 {len(critiques)} produit(s) nécessitent une action immédiate.")
                    with st.expander("📝 Suggestions Standards", expanded=True):
                        st.markdown("""
                        - **Promotion Rapide** : Remise commerciale agressive (Ex: -30%).
                        - **Rotation FEFO** : Transfert vers le point de vente le plus actif.
                        - **Retour Labo** : Vérifier la convention de retour (si < 6 mois).
                        - **Quarantaine** : Isoler physiquement les produits périmés pour destruction.
                        """)
                    
                    if is_ia_enabled():
                        st.markdown("### 🤖 Intervention IA")
                        st.info("Obtenez une stratégie de déstockage sur mesure.")
                        if st.button("🧠 Analyser et Proposer des Solutions", type="primary", use_container_width=True):
                            with st.spinner("L'IA analyse votre stock critique..."):
                                liste_prods = "\n".join([f"- {r['designation']} (Lot {r['lot']}) : {r['mois_restants']} mois restants" for _, r in critiques.head(15).iterrows()])
                                prompt = f"""Tu es Directeur Supply Chain en pharmacie. 
                                Voici une liste partielle de nos produits en risque de péremption :
                                {liste_prods}
                                
                                Propose 3 actions concrètes, innovantes et immédiates pour écouler ce stock ou minimiser les pertes. Sois concis et professionnel."""
                                reponse = ask_ai(prompt)
                                st.session_state['ia_ddp_advice'] = reponse
                        
                        if 'ia_ddp_advice' in st.session_state:
                            st.success(st.session_state['ia_ddp_advice'])
                else:
                    st.success("Aucun produit critique détecté. Votre stock est sain ! 🎉")
                    if is_ia_enabled():
                        st.markdown("### 🤖 Analyse Préventive IA")
                        st.info("Votre stock est sain, mais l'IA peut vous aider à optimiser votre gestion globale.")
                        if st.button("🧠 Générer un rapport d'optimisation préventif", use_container_width=True):
                            with st.spinner("L'IA prépare des conseils préventifs..."):
                                prompt = "Tu es expert en gestion de pharmacie. Mon stock ne contient actuellement aucun produit critique (tout périme dans plus de 6 mois). Donne moi 3 conseils stratégiques courts et innovants pour maintenir ce niveau d'excellence et optimiser ma trésorerie à long terme. Utilise des emojis."
                                st.success(ask_ai(prompt))
        else: st.info("Aucune donnée de péremption valide trouvée dans la saisie.")
    else: st.info("Aucun inventaire terrain trouvé sur la base centrale.")

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
            
            # Mappage flexible (évite les doublons)
            rename_map = {}
            found_targets = set()
            for c in df_ext.columns:
                target = None
                if ('produit' in c or 'designation' in c) and 'produit' not in found_targets: target = 'produit'
                elif ('depot' in c or 'magasin' in c) and 'depot' not in found_targets: target = 'depot'
                elif ('ddp' in c or 'peremption' in c or 'exp' in c) and 'ddp' not in found_targets: target = 'ddp'
                elif ('quantite' in c or 'stock' in c or 'qte' in c) and 'quantite' not in found_targets: target = 'quantite'
                
                if target:
                    rename_map[c] = target
                    found_targets.add(target)
            
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
                            raw = pdf.output(dest='S')
                            pdf_bytes = bytes(raw) if isinstance(raw, (bytes, bytearray)) else raw.encode('latin-1')
                            st.download_button("📥 Télécharger le Bon PDF", pdf_bytes, "Transfert_FEFO.pdf", type="primary")
                    else:
                        st.success("✅ Logique FEFO respectée : tous les produits en réserve périment après ceux en vente.")
                    
                    if is_ia_enabled():
                        st.write("---")
                        st.markdown("### 🤖 Consultant Logistique IA")
                        if st.button("🧠 Demander un avis stratégique sur la rotation", use_container_width=True, type="primary"):
                            with st.spinner("L'IA analyse vos flux de rotation..."):
                                if anomalies.empty:
                                    prompt = "Tu es expert en supply chain pharmaceutique. Je viens d'analyser mes flux FEFO entre le dépôt de stockage et la zone de vente. Tout est parfait, aucune anomalie. Propose 2 innovations logistiques concrètes pour aller encore plus loin dans la gestion des flux internes d'une pharmacie. Sois précis."
                                else:
                                    prompt = f"Tu es expert en supply chain pharmaceutique. J'ai détecté {len(anomalies)} anomalies FEFO (des produits en réserve qui périment AVANT ceux en rayon de vente). Propose une procédure opérationnelle très courte et stricte en 3 étapes pour que l'équipe corrige ça aujourd'hui et évite de répéter l'erreur."
                                st.info(ask_ai(prompt))
                                
                    st.divider()
                    st.write("### 🔍 Vue d'ensemble comparative")
                    full = pd.merge(df_vente, df_stock, on='produit', how='outer', suffixes=('_vente', '_stock'))
                    full['Vente'] = full['expiry_date_vente'].dt.strftime('%m/%Y')
                    full['Stock'] = full['expiry_date_stock'].dt.strftime('%m/%Y')
                    st.dataframe(full[['produit', 'Vente', 'Stock']].fillna("-"), use_container_width=True)
            else:
                st.error("Colonnes 'produit', 'depot' et 'ddp' requises.")
        except Exception as e: st.error(f"Erreur: {e}")
