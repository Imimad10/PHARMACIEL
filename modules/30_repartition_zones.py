import streamlit as st
import pandas as pd
import os
import re
from utils_gsheets import load_gs_data, save_gs_data, show_sync_ui

# --- 1. CONFIGURATION ---
DATA_DIR = "data_repartition"
MASTER_WORKSHEET = "Master_Inventaire_Zone" # Source de vérité
MASTER_FALLBACK = "data_inventaire_detail/master_detail.csv"
COLS_REPARTITION = ["designation", "lot", "zone", "dosage", "is_frigo"]

# --- 2. FONCTIONS DE RÉPARTITION ---

def clean_repartition_cols(df):
    mapping = {
        'designation': ['designation', 'produit', 'article', 'libelle', 'nom'],
        'lot': ['lot', 'n°lot', 'nlot', 'batch'],
        'zone': ['zone', 'emplacement', 'sector'],
        'rotation': ['rotation', 'ventes', 'flux', 'freq', 'sorties']
    }
    
    new_cols = {}
    found_cols = []
    
    for target, alternatives in mapping.items():
        for col in df.columns:
            if any(alt in str(col).lower() for alt in alternatives):
                new_cols[col] = target
                found_cols.append(target)
                break
    
    return df.rename(columns=new_cols), found_cols

def extract_dosage(designation):
    """Extrait le dosage d'une désignation (ex: 500MG, 1G, 10MG/ML)."""
    # Regex pour capturer les dosages classiques
    pattern = r'(\d+\s?(?:MG|G|ML|UG|UI|%|MCG)(?:\/\d+\s?ML)?)'
    match = re.search(pattern, str(designation).upper())
    if match:
        return match.group(1).replace(" ", "")
    return "BASE"

def get_base_name(designation):
    """Récupère le nom du produit sans le dosage."""
    dosage = extract_dosage(designation)
    name = str(designation).upper()
    if dosage != "BASE":
        name = name.replace(dosage, "").strip()
    # Nettoyage des caractères spéciaux restants en fin de nom
    name = re.sub(r'\s{2,}', ' ', name)
    return name

def is_frigo_product(designation):
    """Détecte si un produit doit aller au frigo."""
    keywords = ["FRIGO", "FRESH", "COLD", "INSU", "VACCIN", "SERUM", "COLD-CHAIN", "2-8C"]
    return any(k in str(designation).upper() for k in keywords)

def perform_smart_repartition(df, consider_rotation=False):
    """Algorithme de répartition équitable en 4 zones + Frigo."""
    if df.empty: return df
    
    # 1. Préparation des métadonnées
    df['dosage'] = df['designation'].apply(extract_dosage)
    df['base_name'] = df['designation'].apply(get_base_name)
    df['is_frigo'] = df['designation'].apply(is_frigo_product)
    
    # Gestion de la rotation
    rot_col = None
    for c in df.columns:
        if "ROTATION" in str(c).upper() or "VENTE" in str(c).upper():
            rot_col = c
            df[c] = pd.to_numeric(df[c], errors='coerce').fillna(0)
            break
    
    if consider_rotation and rot_col:
        df['_weight'] = df[rot_col]
    else:
        df['_weight'] = 1 # Poids uniforme par produit
        
    # 2. Séparation Frigo
    frigo_mask = df['is_frigo'] == True
    df.loc[frigo_mask, 'new_zone'] = "CHAMBRE FROIDE"
    
    # 3. Répartition Zones 1-4
    normal_df = df[~frigo_mask].copy()
    
    # On groupe par nom de produit pour traiter les dosages
    groups = normal_df.groupby('base_name')
    
    # zone_weights stocke soit le nombre de produits, soit la somme des rotations
    zone_weights = {"ZONE 1": 0.0, "ZONE 2": 0.0, "ZONE 3": 0.0, "ZONE 4": 0.0}
    zones = ["ZONE 1", "ZONE 2", "ZONE 3", "ZONE 4"]
    
    # On itère sur les produits pour répartir les dosages
    for name, group in groups:
        dosages = sorted(group['dosage'].unique())
        
        current_product_zones = [] # Zones déjà occupées par d'autres dosages de ce produit
        
        for i, d in enumerate(dosages):
            # Stratégie : On cherche la zone qui a le poids total le plus faible actuellement
            # MAIS on essaie de ne pas mettre deux dosages du même produit dans la même zone
            # (Contrainte Anti-Confusion prioritaire)
            
            # On trie les zones par poids croissant
            sorted_zones = sorted(zones, key=lambda z: zone_weights[z])
            
            # On prend la zone la moins chargée qui n'est pas déjà utilisée par ce produit
            target_zone = None
            for z in sorted_zones:
                if z not in current_product_zones:
                    target_zone = z
                    break
            
            if not target_zone: target_zone = sorted_zones[0] # Fallback
            
            # Marquer tous les lots de ce produit/dosage dans la zone choisie
            mask = (df['base_name'] == name) & (df['dosage'] == d) & (~df['is_frigo'])
            df.loc[mask, 'new_zone'] = target_zone
            
            # Mise à jour du poids de la zone
            weight_to_add = group[group['dosage'] == d]['_weight'].sum()
            zone_weights[target_zone] += weight_to_add
            current_product_zones.append(target_zone)

    return df

# --- 3. UI ---

st.title("🧩 Répartition Intelligente des Stocks")
st.info("Ce module optimise le rangement du dépôt. Règle : Les différents dosages d'un même produit sont séparés dans 4 zones distinctes (Anti-Confusion).")

# Chargement des données
df_master_raw = load_gs_data(MASTER_WORKSHEET, MASTER_FALLBACK)

if df_master_raw.empty:
    st.warning("Aucune donnée trouvée dans le Master Inventaire.")
    st.stop()

# Nettoyage et détection des colonnes
df_master, found_cols = clean_repartition_cols(df_master_raw)

if 'designation' not in found_cols:
    st.error("🚨 Impossible de trouver la colonne 'Désignation' ou 'Produit' dans votre fichier source.")
    st.info(f"Colonnes détectées : {list(df_master_raw.columns)}")
    st.stop()

tabs = st.tabs(["⚡ Calculateur", "📊 Statistiques", "⚙️ Paramètres"])

with tabs[0]:
    st.subheader("Optimisation des Emplacements")
    
    col_opt1, col_opt2 = st.columns(2)
    with col_opt1:
        use_rot = st.checkbox("🔥 Prendre en compte la rotation (Équilibrage de charge)", value=True, help="Si coché, l'algorithme répartira les produits pour que chaque zone ait un volume de travail (ventes) équivalent.")
    
    if st.button("🚀 CALCULER LA RÉPARTITION OPTIMALE", type="primary", use_container_width=True):
        with st.spinner("Analyse des dosages et équilibrage des zones..."):
            df_result = perform_smart_repartition(df_master.copy(), consider_rotation=use_rot)
            st.session_state.temp_repartition = df_result
            st.success("Répartition calculée avec succès !")

    if "temp_repartition" in st.session_state:
        df_res = st.session_state.temp_repartition
        st.write("#### ✨ Aperçu du Nouveau Plan de Rangement")
        
        # Comparaison
        cols_disp = ['designation', 'dosage', 'is_frigo', 'zone', 'new_zone']
        if '_weight' in df_res.columns: cols_disp.append('_weight')
        
        df_display = df_res[cols_disp].copy()
        df_display.columns = ['Désignation', 'Dosage', 'Frigo', 'Zone Actuelle', 'Nouvelle Zone', 'Poids (Rotation)'] if '_weight' in df_res.columns else ['Désignation', 'Dosage', 'Frigo', 'Zone Actuelle', 'Nouvelle Zone']
        
        st.dataframe(df_display.head(50), use_container_width=True, hide_index=True)
        
        c_act1, c_act2 = st.columns(2)
        with c_act1:
            if st.button("💾 APPLIQUER ET ENREGISTRER SUR LE CLOUD", use_container_width=True, type="primary"):
                df_final = df_res.copy()
                df_final['zone'] = df_final['new_zone']
                cols_to_drop = ['dosage', 'base_name', 'is_frigo', 'new_zone', '_weight']
                df_final = df_final.drop(columns=[c for c in cols_to_drop if c in df_final.columns])
                save_gs_data(df_final, MASTER_WORKSHEET, MASTER_FALLBACK, force_cloud=True)
                st.success("✅ La nouvelle répartition a été enregistrée !")
                st.balloons()
        
        with c_act2:
            from utils_ia import ask_ai, is_ia_enabled
            if is_ia_enabled():
                if st.button("🤖 ANALYSE STRATÉGIQUE IA", use_container_width=True):
                    with st.spinner("L'IA analyse l'équilibre de votre dépôt..."):
                        z_summary = df_res.groupby('new_zone')['_weight'].sum().to_dict()
                        prompt = f"Analyse cette répartition logistique (Somme de rotation par zone) : {z_summary}. Est-ce équilibré ? Donne 2 conseils pour améliorer la fluidité du picking dans le dépôt. Sois très bref."
                        st.info(ask_ai(prompt))

with tabs[1]:
    if "temp_repartition" in st.session_state:
        df_res = st.session_state.temp_repartition
        st.subheader("📊 Analyse de l'Équilibre")
        
        c1, c2 = st.columns(2)
        
        # Stats par zone
        zone_stats = df_res.groupby('new_zone').agg({
            'designation': 'count',
            '_weight': 'sum'
        }).reset_index()
        zone_stats.columns = ['Zone', 'Nb Produits', 'Charge Totale (Rotation)']
        
        with c1:
            st.write("**📦 Volume de Produits**")
            st.bar_chart(zone_stats, x='Zone', y='Nb Produits')
        
        with c2:
            st.write("**🔥 Charge de Travail (Rotation)**")
            st.bar_chart(zone_stats, x='Zone', y='Charge Totale (Rotation)')
            
        st.divider()
        st.write("#### 🧪 Vérification Anti-Confusion")
        multi_dosage = df_res.groupby('base_name').filter(lambda x: x['dosage'].nunique() > 1)
        if not multi_dosage.empty:
            sample = multi_dosage[['base_name', 'dosage', 'new_zone']].drop_duplicates().sort_values('base_name')
            st.dataframe(sample.head(20), use_container_width=True, hide_index=True)

with tabs[2]:
    st.subheader("Configuration des Mots-clés")
    st.write("Détection automatique du dosage via REGEX (mg, g, ml, ui...).")
    st.write("Détection Frigo via : `FRIGO, FRESH, COLD, INSU, VACCIN, SERUM`")
    
    show_sync_ui(MASTER_WORKSHEET, MASTER_FALLBACK, ["designation", "lot", "zone"])
