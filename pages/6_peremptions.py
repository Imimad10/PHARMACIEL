import streamlit as st
import pandas as pd
import os
from datetime import datetime
from utils import log_action

# --- CONFIGURATION ---
DATA_DIR = "data_inventaire"
SAISIE_PATH = os.path.join(DATA_DIR, "saisie.csv")

def parse_ddp(ddp_str):
    """Parse MM/AA format into a datetime object."""
    try:
        # On suppose le format MM/AA
        parts = ddp_str.split('/')
        if len(parts) == 2:
            m = int(parts[0])
            y = int(parts[1])
            # Ajouter 2000 si y est sur 2 chiffres
            if y < 100: y += 2000
            # On prend le dernier jour du mois par simplicité ou le 1er
            return datetime(y, m, 1)
    except:
        return None
    return None

st.title("⏳ Gestion des Péremptions")
st.write("Analyse des dates de péremption basées sur l'inventaire terrain.")

if os.path.exists(SAISIE_PATH):
    df = pd.read_csv(SAISIE_PATH, sep=';', encoding='utf-8-sig')
    
    if 'ddp' in df.columns:
        # Calcul des dates
        now = datetime.now()
        df['expiry_date'] = df['ddp'].apply(parse_ddp)
        
        # Supprimer les lignes où la DDP est invalide pour l'analyse
        df_valid = df.dropna(subset=['expiry_date']).copy()
        
        if not df_valid.empty:
            # Calcul du nombre de mois restant
            df_valid['mois_restants'] = df_valid['expiry_date'].apply(lambda d: (d.year - now.year) * 12 + d.month - now.month)
            
            # Catégorisation
            def categorize(m):
                if m < 0: return "❌ Périmé"
                if m <= 3: return "⚠️ Critique (< 3 mois)"
                if m <= 6: return "🟠 Vigilance (3-6 mois)"
                return "✅ OK (> 6 mois)"
            
            df_valid['Statut'] = df_valid['mois_restants'].apply(categorize)
            
            # Statistiques
            c1, c2, c3, c4 = st.columns(4)
            stats = df_valid['Statut'].value_counts()
            c1.metric("Périmés", stats.get("❌ Périmé", 0))
            c2.metric("Critiques", stats.get("⚠️ Critique (< 3 mois)", 0))
            c3.metric("Vigilance", stats.get("🟠 Vigilance (3-6 mois)", 0))
            c4.metric("Sains", stats.get("✅ OK (> 6 mois)", 0))
            
            st.divider()
            
            # Filtres
            filtre = st.selectbox("Filtrer par statut", ["Tous", "❌ Périmé", "⚠️ Critique (< 3 mois)", "🟠 Vigilance (3-6 mois)"])
            
            df_show = df_valid.copy()
            if filtre != "Tous":
                df_show = df_show[df_show['Statut'] == filtre]
            
            # Affichage
            st.subheader(f"Détail des produits : {filtre}")
            cols_show = ['designation', 'lot', 'ddp', 'qte_saisie', 'Statut', 'saisi_par']
            st.dataframe(df_show[cols_show].sort_values('expiry_date'), use_container_width=True)
            
            # Export
            import io
            buffer = io.BytesIO()
            df_show[cols_show].to_excel(buffer, index=False)
            if st.download_button(
                label=f"📥 Exporter la liste ({filtre})",
                data=buffer.getvalue(),
                file_name=f"Peremptions_{filtre.replace(' ', '_')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ):
                log_action(st.session_state.current_user['username'], f"Export liste péremptions ({filtre})", "Péremptions")
        else:
            st.info("Aucune date de péremption valide trouvée dans les saisies.")
    else:
        st.warning("La colonne 'ddp' est manquante dans les données d'inventaire.")
else:
    st.info("Veuillez d'abord effectuer une saisie dans le module Inventaire.")
