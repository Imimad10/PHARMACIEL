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

source_data = st.radio("📂 Source des données à analyser :", 
                      ["📝 Saisies Terrain (Inventaire)", "📑 Liste des Lots (Système)"], 
                      horizontal=True)

# --- BARRE DE DEPOT CIBLE ---
df_for_depots = load_gs_data("Master_Inventaire_Zone", "data_inventaire_detail/master_detail.csv", None)
depots_list = ["Tous"]
if not df_for_depots.empty:
    col_depot = next((c for c in df_for_depots.columns if str(c).lower() in ['depot', 'dépôt', 'zone']), None)
    if col_depot:
        depots_list += sorted([str(d) for d in df_for_depots[col_depot].dropna().unique() if str(d).strip()])

depot_cible = st.selectbox("🏢 Dépôt / Zone Cible :", depots_list, index=0, help="Filtre l'analyse pour un dépôt ou une zone spécifique.")

tab1, tab2, tab3 = st.tabs(["📊 Tableau de Bord (DDP)", "🏢 Analyse Multi-Dépôts (Fichier)", "🚚 Transfert & Rotation FEFO"])

with tab1:
    if source_data == "📝 Saisies Terrain (Inventaire)":
        st.subheader("Analyse des Saisies Manuelles")
        df_raw = load_gs_data(SAISIE_WORKSHEET, SAISIE_FALLBACK, COLS_SAISIE)
        date_col = 'ddp_saisi'
        
        # FILTRAGE PAR DEPOT CIBLE (Si colonne zone/depot existe)
        if depot_cible != "Tous" and not df_raw.empty:
            col_d = next((c for c in df_raw.columns if str(c).lower() in ['depot', 'dépôt', 'zone']), None)
            if col_d:
                df_raw = df_raw[df_raw[col_d].astype(str) == depot_cible]
    else:
        st.subheader("Analyse de la Liste Officielle des Lots")
        # On utilise le master de Liste des Lots
        MASTER_WORKSHEET = "Master_Inventaire_Zone"
        MASTER_FALLBACK = "data_inventaire_detail/master_detail.csv"
        df_raw = load_gs_data(MASTER_WORKSHEET, MASTER_FALLBACK, None)
        
        # Mappage des colonnes du Master vers le format attendu
        if not df_raw.empty:
            mapping = {
                'produit': 'designation', 'designation': 'designation',
                'n°lot': 'lot', 'lot': 'lot',
                'peremption': 'ddp', 'ddp': 'ddp',
                'qte_logi': 'qte_saisie', 'quantite': 'qte_saisie', 'stock_theorique': 'qte_saisie',
                'qte': 'qte_saisie', 'quantité': 'qte_saisie', 'stock': 'qte_saisie',
                'depot': 'depot', 'dépôt': 'depot', 'zone': 'depot', 'magasin': 'depot'
            }
            # Nettoyage minimaliste
            new_cols = []
            for c in df_raw.columns:
                norm = str(c).lower().strip()
                target = None
                for k, v in mapping.items():
                    if k in norm: target = v; break
                new_cols.append(target if target else norm)
            df_raw.columns = new_cols
            date_col = 'ddp'
            
            # FILTRAGE PAR DEPOT CIBLE
            if depot_cible != "Tous":
                col_d = next((c for c in df_raw.columns if str(c).lower() in ['depot', 'dépôt', 'zone']), None)
                if col_d:
                    df_raw = df_raw[df_raw[col_d].astype(str) == depot_cible]
        else:
            st.warning("⚠️ La Liste des Lots est vide ou non synchronisée.")

    if not df_raw.empty:
        df_res = analyze_peremptions(df_raw, date_col=date_col)
        if not df_res.empty:
            stats = df_res['Statut'].value_counts()
            # --- EXPORT & FILTRAGE INTERACTIF ---
            st.markdown("### 🖨️ Préparation du Rapport PDF")
            all_statuts = ["❌ Périmé", "⚠️ Critique (< 3 mois)", "🟠 Vigilance (3-6 mois)", "✅ OK (> 6 mois)"]
            if 'export_filter' not in st.session_state:
                st.session_state.export_filter = ["❌ Périmé", "⚠️ Critique (< 3 mois)"]

            selected_statuts = st.multiselect("Sélectionnez les statuts à inclure dans le rapport :", 
                                            all_statuts, 
                                            default=st.session_state.export_filter)
            st.session_state.export_filter = selected_statuts

            c1, c2, c3, c4 = st.columns(4)
            
            def draw_status_card(label, value, icon, color, is_selected):
                bg = color if is_selected else "var(--bg-card)"
                txt = "white" if is_selected else "var(--text-primary)"
                border = color if is_selected else "rgba(0,0,0,0.05)"
                
                st.markdown(f"""
                    <div style="
                        background-color: {bg}; 
                        color: {txt}; 
                        padding: 20px; 
                        border-radius: 24px; 
                        border: 2px solid {border};
                        box-shadow: var(--neu-shadow);
                        transition: all 0.3s ease;
                    ">
                        <div style="font-size: 1rem; font-weight: 800; display: flex; align-items: center; gap: 8px;">
                            <span>{icon}</span> {label}
                        </div>
                        <div style="font-size: 2.2rem; font-weight: 900; margin-top: 10px;">
                            {value}
                        </div>
                    </div>
                """, unsafe_allow_html=True)

            with c1:
                draw_status_card("Périmés", stats.get("❌ Périmé", 0), "❌", "#8B0000", "❌ Périmé" in selected_statuts)
            
            with c2:
                draw_status_card("Critiques (< 3m)", stats.get("⚠️ Critique (< 3 mois)", 0), "⚠️", "#FFD700", "⚠️ Critique (< 3 mois)" in selected_statuts)
                
            with c3:
                draw_status_card("Vigilance (3-6m)", stats.get("🟠 Vigilance (3-6 mois)", 0), "🟠", "#FF8C00", "🟠 Vigilance (3-6 mois)" in selected_statuts)
                
            with c4:
                draw_status_card("Sains", stats.get("✅ OK (> 6 mois)", 0), "✅", "#28a745", "✅ OK (> 6 mois)" in selected_statuts)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            df_to_export = df_res[df_res['Statut'].isin(selected_statuts)]
            if not df_to_export.empty:
                from utils_pdf import generate_inventory_report_pdf
                clean_source = source_data.replace("📝", "").replace("📑", "").strip()
                title_report = f"RAPPORT PEREMPTIONS - {clean_source}"
                
                cols_pdf = ['designation', 'lot', date_col, 'Statut']
                if 'qte_saisie' in df_res.columns: cols_pdf.append('qte_saisie')
                if 'depot' in df_res.columns: cols_pdf.append('depot')
                elif 'zone' in df_res.columns: cols_pdf.append('zone')
                
                if st.download_button("📥 Télécharger le Rapport PDF Filtré", 
                                    generate_inventory_report_pdf(df_to_export, title_report, cols_to_include=cols_pdf, orientation='L'), 
                                    f"Rapport_Peremptions_{datetime.now().strftime('%Y%m%d')}.pdf", 
                                    "application/pdf",
                                    use_container_width=True,
                                    type="primary"):
                    st.success("Rapport prêt !")
            else:
                st.info("Sélectionnez au moins un statut pour générer le rapport.")

            st.divider()
            
            col_list, col_action = st.columns([2, 1])
            with col_list:
                st.markdown("### 📋 Liste détaillée des produits")
                # Utiliser date_col dynamiquement
                cols_to_show = ['designation', 'lot', date_col, 'Statut', 'mois_restants']
                for c in ['qte_saisie', 'depot', 'zone']:
                    if c in df_res.columns and c not in cols_to_show:
                        cols_to_show.append(c)
                        
                df_sorted = df_res.sort_values('expiry_date')[cols_to_show]
                # Formater la date pour affichage
                df_sorted[date_col] = pd.to_datetime(df_sorted[date_col], errors='coerce').dt.strftime('%m/%Y')
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
                        - **Sécurité Patient** : Pour les traitements chroniques (Diabète, HTA), retirer de la vente si DDP < 4 mois pour éviter la péremption chez le patient.
                        - **Retour Labo** : Vérifier la convention de retour (si < 6 mois).
                        """)
                    
                    if is_ia_enabled():
                        st.markdown("### 🤖 Intervention IA")
                        st.info("Obtenez une stratégie de déstockage sur mesure.")
                        if st.button("🧠 Analyser et Proposer des Solutions", type="primary", use_container_width=True):
                            with st.spinner("L'IA analyse votre stock critique..."):
                                liste_prods = "\n".join([f"- {r['designation']} (Lot {r['lot']}) : {r['mois_restants']} mois restants" for _, r in critiques.head(15).iterrows()])
                                prompt = f"""Tu es Pharmacien Expert et Directeur Supply Chain. 
                                Voici une liste partielle de produits en risque de péremption :
                                {liste_prods}
                                
                                CONTEXTE CRITIQUE : Nous devons garantir la SÉCURITÉ PATIENT. Un patient chronique (diabète, HTA) qui achète une boîte de 30 comprimés ne doit pas voir son traitement périmer chez lui.
                                
                                Analyse cette liste et propose une stratégie de 'Vigilance Pharmaceutique' :
                                1. Quels produits sont les plus risqués pour les malades chroniques ?
                                2. Quelle marge de sécurité (en mois) préconises-tu pour éviter qu'un produit ne périme chez le patient ?
                                3. Quelles actions immédiates pour ces lots spécifiques (Retrait, échange, ou vente à l'unité) ?
                                
                                Sois précis, médicalement responsable et professionnel."""
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
            # Normalisation robuste des colonnes
            import unicodedata
            def norm_c(c):
                c = str(c).strip().lower()
                return ''.join(ch for ch in unicodedata.normalize('NFD', c) if unicodedata.category(ch) != 'Mn')
            
            # 1. Dépollution et dé-duplication initiale des colonnes
            cols_clean = []
            count = {}
            for col in df_ext.columns:
                col_norm = norm_c(col)
                if col_norm in count:
                    count[col_norm] += 1
                    cols_clean.append(f"{col_norm}_{count[col_norm]}")
                else:
                    count[col_norm] = 0
                    cols_clean.append(col_norm)
            df_ext.columns = cols_clean
            
            # 2. Recherche robuste du meilleur matching unique pour chaque cible
            target_cols = {}
            used_cols = set()
            
            def find_best_col(patterns_exact, patterns_contain):
                # 1er passage : correspondance exacte
                for c in df_ext.columns:
                    if c in used_cols:
                        continue
                    if c in patterns_exact:
                        return c
                # 2ème passage : sous-chaine
                for c in df_ext.columns:
                    if c in used_cols:
                        continue
                    if any(p in c for p in patterns_contain):
                        return c
                return None
            
            # Recherche par ordre d'importance Supply Chain
            ddp_col = find_best_col(
                ['ddp', 'peremption', 'exp', 'expiration', 'perime'], 
                ['ddp', 'peremp', 'expir', 'perim', 'exp']
            )
            if ddp_col:
                target_cols['ddp'] = ddp_col
                used_cols.add(ddp_col)
                
            prod_col = find_best_col(
                ['produit', 'designation', 'article', 'nom'], 
                ['produit', 'designation', 'article', 'nom', 'desc', 'description']
            )
            if prod_col:
                target_cols['produit'] = prod_col
                used_cols.add(prod_col)
                
            depot_col = find_best_col(
                ['depot', 'magasin', 'zone', 'emplacement'], 
                ['depot', 'magasin', 'zone', 'emplacement', 'site']
            )
            if depot_col:
                target_cols['depot'] = depot_col
                used_cols.add(depot_col)
                
            qte_col_found = find_best_col(
                ['quantite', 'qte', 'stock'], 
                ['quantite', 'qte', 'stock', 'physique', 'theorique', 'dispo']
            )
            if qte_col_found:
                target_cols['quantite'] = qte_col_found
                used_cols.add(qte_col_found)
                
            # Application du renommage
            rename_map = {}
            for target, original in target_cols.items():
                rename_map[original] = target
                
            # Éviter les conflits avec d'autres colonnes non-mappées qui auraient les mêmes noms cibles
            for c in df_ext.columns:
                if c not in rename_map:
                    if c in ['produit', 'depot', 'ddp', 'quantite']:
                        rename_map[c] = f"{c}_orig"
                        
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
with tab3:
    st.subheader("🚚 Optimisation Inter-Dépôts (Rotation Stratégique)")
    st.write("Comparez vos dépôts internes pour transférer les dates courtes vers la zone de vente.")

    MASTER_WORKSHEET = "Master_Inventaire_Zone"
    MASTER_FALLBACK = "data_inventaire_detail/master_detail.csv"
    df_fefo = load_gs_data(MASTER_WORKSHEET, MASTER_FALLBACK, None)

    if not df_fefo.empty:
        import unicodedata
        def normalize_str(s):
            s = str(s).lower().strip()
            return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')

        # Normalisation des colonnes existantes
        original_cols = df_fefo.columns.tolist()
        norm_cols = [normalize_str(c) for c in original_cols]
        
        # Mappage intelligent
        mapping = {
            'designation': ['produit', 'designation', 'article', 'nom'],
            'lot': ['lot', 'n°lot', 'batch'],
            'ddp': ['peremption', 'ddp', 'exp', 'date'],
            'quantite': ['quantite', 'qte', 'stock', 'theorique'],
            'depot': ['depot', 'zone', 'emplacement', 'magasin']
        }
        
        final_mapping = {}
        for target, keys in mapping.items():
            for i, nc in enumerate(norm_cols):
                if any(k in nc for k in keys):
                    final_mapping[original_cols[i]] = target
                    break
        
        df_fefo = df_fefo.rename(columns=final_mapping)
        
        # Vérification et Fallback Manuel
        if 'depot' not in df_fefo.columns or 'designation' not in df_fefo.columns:
            st.warning("⚠️ Colonnes non détectées automatiquement.")
            c_m1, c_m2 = st.columns(2)
            col_dep = c_m1.selectbox("Sélectionnez la colonne 'Dépôt' :", df_fefo.columns)
            col_des = c_m2.selectbox("Sélectionnez la colonne 'Produit' :", df_fefo.columns)
            if col_dep: df_fefo = df_fefo.rename(columns={col_dep: 'depot'})
            if col_des: df_fefo = df_fefo.rename(columns={col_des: 'designation'})

        if 'depot' in df_fefo.columns and 'designation' in df_fefo.columns:
            all_depots = sorted(df_fefo['depot'].dropna().unique().tolist())
            
            c_f1, c_f2 = st.columns(2)
            with c_f1:
                dep_vente = st.multiselect("🏪 Dépôt(s) de Vente (Cible)", all_depots, help="Les dépôts où les produits doivent être vendus en priorité.")
            with c_f2:
                dep_stock = st.multiselect("🏗️ Dépôt(s) de Stockage (Source)", [d for d in all_depots if d not in dep_vente], help="Les dépôts de réserve.")

            if dep_vente and dep_stock:
                df_fefo['expiry_date'] = df_fefo['ddp'].apply(parse_ddp)
                df_fefo = df_fefo.dropna(subset=['expiry_date'])
                
                # Groupement par désignation pour trouver les min DDP
                df_v = df_fefo[df_fefo['depot'].isin(dep_vente)].groupby('designation').agg({'expiry_date': 'min', 'quantite': 'sum'}).reset_index()
                df_s = df_fefo[df_fefo['depot'].isin(dep_stock)].groupby(['designation', 'lot', 'ddp']).agg({'expiry_date': 'min', 'quantite': 'sum'}).reset_index()
                
                # Merge pour comparer
                merged = pd.merge(df_s, df_v, on='designation', suffixes=('_stock', '_vente'))
                
                # Anomalie : Date en stock plus proche que date en vente
                anomalies = merged[merged['expiry_date_stock'] < merged['expiry_date_vente']].copy()
                
                if not anomalies.empty:
                    st.error(f"🚨 {len(anomalies)} lots critiques détectés en réserve !")
                    st.info("💡 Ces lots devraient être transférés en zone de vente car ils périment avant ceux déjà en rayon.")
                    
                    anomalies['DDP Stock'] = anomalies['expiry_date_stock'].dt.strftime('%m/%Y')
                    anomalies['DDP Vente'] = anomalies['expiry_date_vente'].dt.strftime('%m/%Y')
                    
                    disp_cols = ['designation', 'lot', 'DDP Stock', 'quantite_stock', 'DDP Vente']
                    st.dataframe(anomalies[disp_cols].rename(columns={
                        'designation': 'Produit', 
                        'quantite_stock': 'Quantité en Réserve',
                        'DDP Vente': 'DDP Actuelle en Vente'
                    }), use_container_width=True, hide_index=True)
                    
                    if st.button("📝 Générer l'Ordre de Transfert Urgent"):
                        from utils_pdf import generate_inventory_report_pdf
                        # On réutilise le générateur PDF avec les colonnes d'anomalie
                        pdf_data = anomalies[['designation', 'lot', 'DDP Stock', 'quantite_stock']].copy()
                        pdf_data.columns = ['Produit', 'Lot', 'Péremption', 'Quantité']
                        pdf_bytes = generate_inventory_report_pdf(pdf_data, "ORDRE DE TRANSFERT URGENT - ROTATION FEFO")
                        st.download_button("📥 Télécharger l'Ordre de Transfert (PDF)", pdf_bytes, "Transfert_Urgent_FEFO.pdf", type="primary")
                else:
                    st.success("✅ Rotation Optimale : Toutes les dates courtes sont déjà en zone de vente.")
            else:
                st.info("Sélectionnez les dépôts de vente et de stockage pour lancer l'analyse.")
        else:
            st.error("Structure de données incompatible (colonnes 'depot' ou 'designation' manquantes).")
    else:
        st.warning("Aucune donnée disponible dans le Master pour cette analyse.")
