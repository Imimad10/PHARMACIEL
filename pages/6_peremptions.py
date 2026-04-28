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
    st.subheader("Analyse de stock externe (Excel)")
    st.write("Déposez un fichier exporté de votre logiciel (colonnes attendues : **depot, quantité, ddp**)")
    
    file_up = st.file_uploader("Choisir un fichier Excel", type=["xlsx", "xls"])
    
    if file_up:
        df_ext = pd.read_excel(file_up)
        # Normalisation des colonnes
        df_ext.columns = [c.lower().strip() for c in df_ext.columns]
        
        needed = ['ddp', 'quantité'] 
        if all(c in df_ext.columns for c in needed):
            df_ext_res = analyze_peremptions(df_ext, date_col='ddp', qte_col='quantité')
            
            if not df_ext_res.empty:
                # Filtre par dépôt
                if 'depot' in df_ext_res.columns:
                    df_ext_res['depot'] = df_ext_res['depot'].astype(str).str.lower()
                    depots = ["Tous"] + sorted(df_ext_res['depot'].unique().tolist())
                    sel_depot = st.selectbox("Filtrer par Dépôt", depots)
                    if sel_depot != "Tous":
                        df_ext_res = df_ext_res[df_ext_res['depot'] == sel_depot]
                
                # Tri par date de péremption (Priorité de vente)
                df_ext_res = df_ext_res.sort_values('expiry_date')
                
                # Affichage des alertes critiques
                critiques = df_ext_res[df_ext_res['mois_restants'] <= 6]
                if not critiques.empty:
                    st.error(f"🚨 {len(critiques)} produits nécessitent une mise en vente prioritaire !")
                
                st.dataframe(df_ext_res, use_container_width=True)
                
                # Export
                import io
                buffer = io.BytesIO()
                df_ext_res.to_excel(buffer, index=False)
                st.download_button("📥 Télécharger l'analyse de priorité (.xlsx)", buffer.getvalue(), "Analyse_Priorite_Vente.xlsx")
                log_action(st.session_state.current_user['username'], "Analyse stock externe péremptions", "Péremptions")
            else:
                st.error("Aucune donnée de date valide dans le fichier.")
        else:
            st.error(f"Colonnes manquantes. Le fichier doit contenir au moins : {needed}")
