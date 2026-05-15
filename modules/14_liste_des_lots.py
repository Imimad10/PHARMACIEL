import streamlit as st
import os
import unicodedata
from datetime import datetime
from utils_gsheets import load_gs_data, save_gs_data, show_sync_ui, DB_USERS_WORKSHEET, DB_USERS_FALLBACK
from utils_ia import ask_ai, is_ia_enabled

# --- 1. CONFIGURATION ---
DATA_DIR = "data_inventaire_detail"
MASTER_WORKSHEET = "Master_Inventaire_Zone"
MASTER_FALLBACK = os.path.join(DATA_DIR, "master_detail.csv")
COLS_MASTER = ["depot", "designation", "lot", "zone", "ddp", "ppa", "shp", "stock_theorique"]
show_sync_ui(MASTER_WORKSHEET, MASTER_FALLBACK, COLS_MASTER)

# --- 2. FONCTIONS TECHNIQUES ---
def normalize_text(text):
    if not isinstance(text, str): return str(text)
    return unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8').lower().strip()

def clean_cols_v5(df):
    mapping = {
        'produit': 'designation', 'designation': 'designation', 'article': 'designation', 'libelle': 'designation',
        'n°lot': 'lot', 'nlot': 'lot', 'lot': 'lot', 'batch': 'lot',
        'peremption': 'ddp', 'ddp': 'ddp', 'exp': 'ddp', 'date': 'ddp',
        'ppa': 'ppa', 'shp': 'shp', 'zone': 'zone', 'emplacement': 'zone', 'sector': 'zone',
        'depot': 'depot', 'dépôt': 'depot', 'qte_logi': 'stock_theorique', 'quantite': 'stock_theorique'
    }
    # Mots-clés élargis pour le stock
    stock_keywords = ['quantit', 'stock', 'theorique', 'qte', 'dispo', 'logi', 'theor']
    new_cols = []
    found = set()
    
    # 1. Nettoyage des noms de colonnes originaux
    original_cols = [str(c).strip() for c in df.columns]
    
    for col in original_cols:
        norm = normalize_text(col)
        target = None
        
        # Mapping direct
        for k, v in mapping.items():
            if k == norm and v not in found:
                target = v; found.add(v); break
        
        # Mapping par mot-clé (si pas trouvé en direct)
        if not target:
            for k, v in mapping.items():
                if k in norm and v not in found:
                    target = v; found.add(v); break
        
        # Détection stock par mots-clés génériques
        if not target and any(key in norm for key in stock_keywords) and 'stock_theorique' not in found:
            target = 'stock_theorique'; found.add(target)
            
        new_cols.append(target if target else norm)
    
    df.columns = new_cols
    
    # Formatage de la DDP (Mois/Année uniquement)
    if 'ddp' in df.columns:
        def format_date(val):
            if pd.isna(val) or val == "": return val
            try:
                # Si c'est déjà un objet datetime
                if isinstance(val, (datetime, pd.Timestamp)):
                    return val.strftime('%m/%Y')
                # Si c'est une chaîne, on tente la conversion
                dt = pd.to_datetime(val, errors='coerce')
                if pd.notna(dt):
                    return dt.strftime('%m/%Y')
                return str(val)
            except:
                return str(val)
        df['ddp'] = df['ddp'].apply(format_date)
        
    return df

@st.cache_data(ttl=60)
def load_master_v5(path, mtime):
    try:
        df = pd.read_excel(path, engine='openpyxl')
        df = clean_cols_v5(df)
        req = ['designation', 'lot', 'zone']
        if not all(c in df.columns for c in req): return f"Colonnes manquantes : {[c for c in req if c not in df.columns]}"
        if 'ddp' in df.columns:
            df['ddp'] = pd.to_datetime(df['ddp'], errors='coerce').dt.strftime('%m/%Y').fillna(df['ddp'].astype(str))
        
        for col in ['designation', 'lot', 'zone']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.upper().str.strip()
        
        return df
    except Exception as e: return str(e)

# --- 3. UI ---
st.title("📑 Liste des Lots")

if "current_user" not in st.session_state or st.session_state.current_user is None:
    st.warning("Veuillez vous connecter.")
    st.stop()

user = st.session_state.current_user
user_zone = user.get('zone', 'Aucune')
is_admin = user.get('role') in ["Admin", "Superviseur"]

df_master = load_gs_data(MASTER_WORKSHEET, MASTER_FALLBACK, None)
if not df_master.empty:
    df_master = clean_cols_v5(df_master)
else:
    df_master = None

if df_master is None:
    st.info("Aucun Master Détail trouvé sur GSheets. Veuillez l'importer depuis l'onglet Admin de 'Inventaire Détail'.")
    st.stop()

# Filtrer par zone si non-admin
if not is_admin and user_zone != "Aucune":
    df_filtered = df_master[df_master['zone'] == user_zone]
    st.sidebar.success(f"📍 Affichage restreint à votre zone : **{user_zone}**")
else:
    df_filtered = df_master
    if is_admin:
        st.sidebar.info("👑 Vue Globale (Toutes Zones)")

tabs = st.tabs(["📋 Liste des Lots", "📊 Tableau de Bord", "⚙️ Admin"])

with tabs[0]:
    st.subheader("Consultation des Produits et Lots")
    
    col_search, col_depot, col_zone = st.columns([2, 1, 1])
    search_term = col_search.text_input("🔍 Rechercher un produit ou un lot :", "")
    
    if is_admin:
        # Filtre Dépôt
        depots_opt = ["Tous"] + sorted([str(d) for d in df_master['depot'].unique() if pd.notna(d)]) if 'depot' in df_master.columns else ["Tous"]
        depot_filter = col_depot.selectbox("Filtrer par Dépôt :", depots_opt)
        
        # Filtre Zone
        zones_opt = ["Toutes"] + sorted([str(z) for z in df_master['zone'].unique() if pd.notna(z)])
        zone_filter = col_zone.selectbox("Filtrer par Zone :", zones_opt)
        
        # Application des filtres
        df_display = df_filtered.copy()
        if 'depot' in df_display.columns and depot_filter != "Tous":
            df_display = df_display[df_display['depot'] == depot_filter]
        if zone_filter != "Toutes":
            df_display = df_display[df_display['zone'] == zone_filter]
    else:
        df_display = df_filtered.copy()
        
    if search_term:
        df_display = df_display[
            df_display['designation'].str.contains(search_term, case=False, na=False) |
            df_display['lot'].str.contains(search_term, case=False, na=False)
        ]
        
    st.write(f"Affichage de **{len(df_display)}** résultats.")
    
    # Restreindre l'affichage aux colonnes désirées
    cols_to_show = ['depot', 'designation', 'lot', 'zone', 'stock_theorique', 'ddp', 'ppa', 'shp']
    
    # Sécurité : Si stock_theorique n'est pas trouvé, chercher une colonne alternative
    if 'stock_theorique' not in df_display.columns:
        for c in df_display.columns:
            if any(k in str(c).lower() for k in ['qte', 'stock', 'quantit']):
                cols_to_show.append(c)
                break

    cols_to_show = [c for c in cols_to_show if c in df_display.columns]
    
    # Renommer pour l'affichage utilisateur
    rename_map = {
        'stock_theorique': 'Quantité', 
        'depot': 'Dépôt', 
        'designation': 'Désignation', 
        'lot': 'Lot', 
        'zone': 'Zone', 
        'ddp': 'DDP', 
        'ppa': 'PPA', 
        'shp': 'SHP'
    }
    # Ajouter les colonnes dynamiques au rename_map si besoin
    for c in cols_to_show:
        if c not in rename_map:
            if any(k in str(c).lower() for k in ['qte', 'stock', 'quantit']):
                rename_map[c] = 'Quantité'
            else:
                rename_map[c] = str(c).capitalize()

    df_final = df_display[cols_to_show].rename(columns=rename_map)
    
    st.dataframe(df_final, use_container_width=True, hide_index=True)

    # --- EXPORT PDF (ZONÉ) ---
    st.divider()
    if not df_final.empty:
        if st.button("📥 Générer Rapport PDF (Ma Zone)", use_container_width=True, type="primary"):
            from fpdf import FPDF
            import io
            
            # Création du PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            
            title = f"Inventaire des Lots - Zone: {user_zone}" if not is_admin else f"Inventaire des Lots - Vue: {zone_filter if 'zone_filter' in locals() else 'Globale'}"
            pdf.cell(0, 10, title, 0, 1, 'C')
            pdf.set_font("Arial", '', 10)
            pdf.cell(0, 10, f"Généré le : {datetime.now().strftime('%d/%m/%Y %H:%M')}", 0, 1, 'R')
            pdf.ln(5)
            
            # En-têtes du tableau
            pdf.set_fill_color(200, 220, 255)
            pdf.set_font("Arial", 'B', 8)
            cols = ['Désignation', 'Lot', 'Zone', 'Quantité', 'DDP']
            col_widths = [80, 30, 25, 25, 30]
            
            for i in range(len(cols)):
                pdf.cell(col_widths[i], 8, cols[i], 1, 0, 'C', 1)
            pdf.ln()
            
            # Données
            pdf.set_font("Arial", '', 7)
            for _, row in df_final.iterrows():
                # On s'assure que les données tiennent dans les cellules
                desig = str(row.get('Désignation', ''))[:45]
                lot = str(row.get('Lot', ''))
                zn = str(row.get('Zone', ''))
                qte = str(row.get('Quantité', '0'))
                ddp = str(row.get('DDP', ''))
                
                # Encodage sécurisé pour FPDF
                def clean(t): return str(t).encode('latin-1', 'replace').decode('latin-1')
                
                pdf.cell(col_widths[0], 7, clean(desig), 1)
                pdf.cell(col_widths[1], 7, clean(lot), 1, 0, 'C')
                pdf.cell(col_widths[2], 7, clean(zn), 1, 0, 'C')
                pdf.cell(col_widths[3], 7, clean(qte), 1, 0, 'C')
                pdf.cell(col_widths[4], 7, clean(ddp), 1, 1, 'C')
            
            # Sortie PDF
            pdf_output = pdf.output(dest='S')
            # Compatibilité fpdf/fpdf2
            pdf_bytes = bytes(pdf_output) if isinstance(pdf_output, (bytes, bytearray)) else pdf_output.encode('latin-1')
            
            st.download_button(
                label="✅ Télécharger le fichier PDF",
                data=pdf_bytes,
                file_name=f"Inventaire_Lots_{user_zone}_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )

with tabs[1]:
    st.subheader("📊 Tableau de Bord")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Produits Distincts", df_filtered['designation'].nunique())
    c2.metric("Total Lots Différents", len(df_filtered))
    
    if 'stock_theorique' in df_filtered.columns:
        # Conversion numérique propre
        df_filtered['stock_theorique'] = pd.to_numeric(df_filtered['stock_theorique'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        total_stock = df_filtered['stock_theorique'].sum()
        c3.metric("Stock Théorique Cumulé", f"{total_stock:,.0f}")
    elif 'qte_logi' in df_filtered.columns:
        df_filtered['qte_logi'] = pd.to_numeric(df_filtered['qte_logi'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
        total_stock = df_filtered['qte_logi'].sum()
        c3.metric("Stock Théorique Cumulé", f"{total_stock:,.0f}")
    
    st.divider()
    if is_admin:
        st.write("#### Répartition par Zone")
        zone_counts = df_filtered['zone'].value_counts().reset_index()
        zone_counts.columns = ['Zone', 'Nombre de Lots']
        st.bar_chart(zone_counts, x='Zone', y='Nombre de Lots')
    else:
        st.write(f"**Zone active :** {user_zone}")
        st.write("Seules les données de votre zone sont affichées.")
        
    if is_ia_enabled():
        st.divider()
        st.markdown("### 🤖 Assistant IA - Analyse des Risques")
        st.info("L'Intelligence Artificielle peut scanner rapidement vos lots pour détecter les risques de péremption imminente.")
        if st.button("🧠 Scanner les Lots Critiques", use_container_width=True, type="primary"):
            with st.spinner("L'IA examine vos dates de péremption et stocks..."):
                # Prendre un échantillon si trop grand
                if 'ddp' in df_filtered.columns and 'stock_theorique' in df_filtered.columns:
                    data_to_analyze = df_filtered[['designation', 'lot', 'ddp', 'stock_theorique']].head(30).to_dict('records')
                    prompt = f"Tu es un pharmacien expert en gestion de stock. Voici un échantillon des lots actuels : {data_to_analyze}. Identifie immédiatement s'il y a des risques de péremption (DDP proche). Propose 3 actions commerciales innovantes pour liquider les stocks à risque (ex: création de bundles, promotions ciblées). Sois concis et utilise des emojis."
                    st.success(ask_ai(prompt))
                else:
                    st.warning("Les colonnes DDP (Date de Péremption) ou Stock Théorique sont manquantes pour l'analyse.")

with tabs[2]:
    if is_admin:
        st.subheader("👥 Affectation des Zones aux Utilisateurs")
        df_u = load_gs_data(DB_USERS_WORKSHEET, DB_USERS_FALLBACK, ["username", "role", "pages", "zone"])
        
        # Filtrer les utilisateurs qui ont accès à "Liste des Lots" ou "Inventaire Détail"
        target_users = df_u['username'].tolist() if not df_u.empty else []
        
        col_u1, col_u2, col_u3 = st.columns([2, 1, 1])
        target_user = col_u1.selectbox("Sélectionner un utilisateur :", target_users)
        
        if target_user:
            u_record = df_u[df_u['username'] == target_user].iloc[0]
            current_z = u_record.get('zone', 'Aucune')
            
            z_list = ["Aucune"] + sorted([str(z) for z in df_master['zone'].unique() if pd.notna(z)])
            new_z = col_u2.selectbox(f"Assigner Zone (Actuelle: {current_z})", z_list, index=z_list.index(current_z) if current_z in z_list else 0)
            
            if col_u3.button("✅ Confirmer l'affectation", use_container_width=True):
                df_u.loc[df_u['username'] == target_user, 'zone'] = new_z
                save_gs_data(df_u, DB_USERS_WORKSHEET, DB_USERS_FALLBACK)
                st.success(f"Zone de **{target_user}** mise à jour : **{new_z}**")
                st.rerun()
            
        st.divider()
        st.info("Pour importer ou gérer le fichier Master, veuillez vous rendre dans l'onglet Admin du module **Inventaire Détail**.")
    else:
        st.warning("Accès réservé aux Administrateurs et Superviseurs.")
