import streamlit as st
import pandas as pd
import os
from datetime import datetime
from utils import log_action

# --- CONFIGURATION ---
DATA_DIR = "data_inventaire"
SAISIE_PATH = os.path.join(DATA_DIR, "saisie.csv")

def parse_ddp(ddp_str):
    """Parse various DDP formats into a datetime object."""
    if pd.isna(ddp_str) or ddp_str == "": return None
    ddp_str = str(ddp_str).strip()
    try:
        # Format MM/AA
        if '/' in ddp_str:
            parts = ddp_str.split('/')
            if len(parts) == 2:
                m = int(parts[0])
                y = int(parts[1])
                if y < 100: y += 2000
                return datetime(y, m, 1)
        # Format date excel ou autre
        return pd.to_datetime(ddp_str)
    except:
        return None

def analyze_peremptions(df, date_col='ddp', qte_col='qte_saisie'):
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

tab1, tab2 = st.tabs(["📋 Inventaire Terrain", "📥 Import Stock Excel"])

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
                
                st.divider()
                filtre = st.selectbox("Filtrer par statut (Terrain)", ["Tous", "❌ Périmé", "⚠️ Critique (< 3 mois)", "🟠 Vigilance (3-6 mois)"])
                df_show = df_res if filtre == "Tous" else df_res[df_res['Statut'] == filtre]
                st.dataframe(df_show.sort_values('expiry_date'), use_container_width=True)
            else:
                st.info("Aucune donnée valide.")
        else:
            st.warning("Colonne 'ddp' manquante.")
    else:
        st.info("Aucun inventaire terrain trouvé.")

with tab2:
    st.subheader("📥 Import & Comparaison de Stocks")
    st.write("Comparez les dates de péremption entre deux dépôts pour les mêmes produits.")
    
    file_up = st.file_uploader("Choisir le fichier Excel de stock", type=["xlsx", "xls"])
    
    if file_up:
        try:
            df_ext = pd.read_excel(file_up)
            
            # Normalisation robuste des colonnes (gestion des accents et casses)
            import unicodedata
            def clean_col(c):
                c = str(c).strip().lower()
                return ''.join(ch for ch in unicodedata.normalize('NFD', c) if unicodedata.category(ch) != 'Mn')
            
            df_ext.columns = [clean_col(c) for c in df_ext.columns]
            
            # Vérification des colonnes essentielles
            # Dans le screenshot : Produit, Depot, DDP (ou ddp)
            expected = {'produit', 'depot', 'ddp'}
            missing = expected - set(df_ext.columns)
            
            if not missing:
                # Nettoyage des données
                df_ext['expiry_date'] = df_ext['ddp'].apply(parse_ddp)
                df_ext = df_ext.dropna(subset=['expiry_date', 'depot', 'produit'])
                
                # Liste des dépôts uniques
                all_depots = sorted(df_ext['depot'].unique().tolist())
                
                col1, col2 = st.columns(2)
                with col1:
                    depot_p = st.selectbox("🏗️ Dépôt Principal", all_depots, key="dp")
                
                with col2:
                    # Exclure le dépôt principal du deuxième choix
                    other_depots = [d for d in all_depots if d != depot_p]
                    depot_s = st.selectbox("🏢 Deuxième Dépôt (Comparaison)", other_depots, key="ds")
                
                if depot_p and depot_s:
                    # Filtrer les données pour les deux dépôts
                    df_p = df_ext[df_ext['depot'] == depot_p].copy()
                    df_s = df_ext[df_ext['depot'] == depot_s].copy()
                    
                    # On veut comparer les produits par désignation (produit)
                    # On prend la date la plus proche pour chaque produit dans chaque dépôt et la quantité totale
                    qte_col = 'quantite' if 'quantite' in df_ext.columns else None
                    # Note: clean_col turned 'Quantité' into 'quantite'
                    
                    agg_dict = {'expiry_date': 'min'}
                    if qte_col: agg_dict[qte_col] = 'sum'
                    
                    p_data = df_p.groupby('produit').agg(agg_dict).reset_index()
                    s_data = df_s.groupby('produit').agg(agg_dict).reset_index()
                    
                    # Fusionner pour comparer
                    comparison = pd.merge(p_data, s_data, on='produit', how='inner', suffixes=('_p', '_s'))
                    
                    if not comparison.empty:
                        now = datetime.now()
                        comparison['mois_restants_s'] = comparison['expiry_date_s'].apply(lambda d: (d.year - now.year) * 12 + d.month - now.month)
                        
                        # Fonction d'alerte
                        def get_alert(row):
                            if row['mois_restants_s'] <= 3: return "🚨 CRITIQUE"
                            if row['mois_restants_s'] <= 6: return "⚠️ PROCHE"
                            return "✅ OK"
                        
                        comparison['Statut DS'] = comparison.apply(get_alert, axis=1)
                        
                        # Formater les dates pour l'affichage
                        comparison['Date DP'] = comparison['expiry_date_p'].dt.strftime('%m/%Y')
                        comparison['Date DS'] = comparison['expiry_date_s'].dt.strftime('%m/%Y')
                        
                        st.write(f"### 🔍 Comparaison : {depot_p} vs {depot_s}")
                        
                        # Metrics
                        c1, c2, c3 = st.columns(3)
                        c1.metric("Produits Communs", len(comparison))
                        crit_count = len(comparison[comparison['Statut DS'] == "🚨 CRITIQUE"])
                        c2.metric("Alertes Critiques (DS)", crit_count, delta=-crit_count if crit_count > 0 else 0, delta_color="inverse")
                        c3.metric("Alertes Proches (DS)", len(comparison[comparison['Statut DS'] == "⚠️ PROCHE"]))
                        
                        # Colonnes à afficher
                        cols_to_show = ['produit', 'Date DP', 'Date DS']
                        rename_dict = {'produit': 'Désignation', 'Date DP': f'Date ({depot_p})', 'Date DS': f'Date ({depot_s})'}
                        
                        if qte_col:
                            comparison[f'Qte_{depot_p}'] = comparison[f'{qte_col}_p']
                            comparison[f'Qte_{depot_s}'] = comparison[f'{qte_col}_s']
                            cols_to_show.extend([f'Qte_{depot_p}', f'Qte_{depot_s}'])
                        
                        cols_to_show.append('Statut DS')
                        
                        display_df = comparison[cols_to_show].rename(columns=rename_dict)
                        
                        # Style
                        def color_alert(val):
                            if "🚨" in val: return 'background-color: #ff4b4b; color: white; font-weight: bold'
                            if "⚠️" in val: return 'background-color: #ffa500; color: black; font-weight: bold'
                            return ''

                        st.dataframe(
                            display_df.style.map(color_alert, subset=['Statut DS']),
                            use_container_width=True,
                            hide_index=True
                        )
                        
                        # Export
                        import io
                        buffer = io.BytesIO()
                        comparison.to_excel(buffer, index=False)
                        st.download_button(f"📥 Télécharger la comparaison ({depot_p} vs {depot_s})", buffer.getvalue(), f"Comparaison_{depot_p}_{depot_s}.xlsx")
                        
                        log_action(st.session_state.current_user['username'], f"Comparaison péremptions {depot_p} vs {depot_s}", "Péremptions")

                        # --- PHASE 4: ORDRE DE TRANSFERT ---
                        st.divider()
                        st.subheader("📋 Automatisation des Transferts")
                        st.write(f"Suggérer le transfert des produits critiques de **{depot_s}** vers **{depot_p}**.")
                        
                        df_transfert = comparison[comparison['Statut DS'].isin(["🚨 CRITIQUE", "⚠️ PROCHE"])].copy()
                        
                        if not df_transfert.empty:
                            from fpdf import FPDF
                            def generate_transfer_pdf(df, ds, dp):
                                pdf = FPDF()
                                pdf.add_page()
                                pdf.set_font("Arial", 'B', 16)
                                pdf.cell(0, 10, f"ORDRE DE TRANSFERT - Darpharm Solution", 0, 1, 'C')
                                pdf.set_font("Arial", '', 11)
                                pdf.cell(0, 8, f"Date: {datetime.now().strftime('%d/%m/%Y')}", 0, 1, 'R')
                                pdf.ln(10)
                                
                                pdf.set_font("Arial", 'B', 12)
                                pdf.cell(0, 8, f"ORIGINE : {ds}", 0, 1, 'L')
                                pdf.cell(0, 8, f"DESTINATION : {dp}", 0, 1, 'L')
                                pdf.ln(5)
                                
                                pdf.set_font("Arial", 'B', 10)
                                pdf.cell(80, 8, "Désignation", 1)
                                pdf.cell(30, 8, "Date Exp.", 1)
                                pdf.cell(30, 8, "Qte à Transf.", 1)
                                pdf.cell(50, 8, "Observations", 1)
                                pdf.ln()
                                
                                pdf.set_font("Arial", '', 9)
                                for _, row in df.iterrows():
                                    pdf.cell(80, 8, str(row['produit'])[:40].encode('latin-1', 'replace').decode('latin-1'), 1)
                                    pdf.cell(30, 8, row['Date DS'], 1)
                                    qte = f"{row[f'{qte_col}_s']}" if qte_col else "N/A"
                                    pdf.cell(30, 8, qte, 1)
                                    obs = "URGENT (PROCHE)" if "CRITIQUE" in row['Statut DS'] else "Vigilance"
                                    pdf.cell(50, 8, obs, 1)
                                    pdf.ln()
                                
                                return pdf.output(dest='S').encode('latin-1', 'replace')

                            c_t1, c_t2 = st.columns([2, 1])
                            with c_t1:
                                st.info(f"Il y a {len(df_transfert)} produits à transférer en priorité de {depot_s} vers {depot_p}.")
                            with c_t2:
                                pdf_t_bytes = generate_transfer_pdf(df_transfert, depot_s, depot_p)
                                st.download_button(
                                    "📥 Générer Bon de Transfert (PDF)", 
                                    pdf_t_bytes, 
                                    f"Transfert_{depot_s}_to_{depot_p}.pdf",
                                    mime="application/pdf"
                                )
                        else:
                            st.success(f"Tous les produits de {depot_s} sont en sécurité (dates éloignées).")

                    else:
                        st.info("Aucun produit commun trouvé entre ces deux dépôts.")
            else:
                st.error(f"Colonnes manquantes dans le fichier Excel : {', '.join(missing)}")
                st.info("Colonnes détectées : " + ", ".join(df_ext.columns))
                
        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier : {e}")
