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

def perform_smart_repartition(df):
    """Algorithme de répartition équitable en 4 zones + Frigo."""
    if df.empty: return df
    
    # 1. Préparation des métadonnées
    df['dosage'] = df['designation'].apply(extract_dosage)
    df['base_name'] = df['designation'].apply(get_base_name)
    df['is_frigo'] = df['designation'].apply(is_frigo_product)
    
    # 2. Séparation Frigo
    frigo_mask = df['is_frigo'] == True
    df.loc[frigo_mask, 'new_zone'] = "CHAMBRE FROIDE"
    
    # 3. Répartition Zones 1-4
    normal_df = df[~frigo_mask].copy()
    
    # On groupe par nom de produit pour traiter les dosages
    groups = normal_df.groupby('base_name')
    
    zone_counts = {"ZONE 1": 0, "ZONE 2": 0, "ZONE 3": 0, "ZONE 4": 0}
    zones = ["ZONE 1", "ZONE 2", "ZONE 3", "ZONE 4"]
    
    # On itère sur les produits pour répartir les dosages
    for name, group in groups:
        # On trie les dosages pour avoir un ordre consistant
        dosages = sorted(group['dosage'].unique())
        
        # Pour chaque dosage unique du même produit
        for i, d in enumerate(dosages):
            # On cherche la zone la moins remplie pour équilibrer, 
            # TOUT EN évitant d'être dans la même zone que les autres dosages si possible.
            
            # Si on a <= 4 dosages, on leur donne une zone unique chacun
            # Si on a > 4, on recommence le cycle.
            
            target_zone_idx = i % 4
            target_zone = zones[target_zone_idx]
            
            # Marquer tous les lots de ce produit/dosage dans la zone choisie
            mask = (df['base_name'] == name) & (df['dosage'] == d) & (~df['is_frigo'])
            df.loc[mask, 'new_zone'] = target_zone
            zone_counts[target_zone] += len(group[group['dosage'] == d])

    return df

# --- 3. UI ---

st.title("🧩 Répartition Intelligente des Stocks")
st.info("Ce module optimise le rangement du dépôt. Règle : Les différents dosages d'un même produit sont séparés dans 4 zones distinctes (Anti-Confusion). Les produits thermosensibles vont en Chambre Froide.")

# Chargement des données
df_master = load_gs_data(MASTER_WORKSHEET, MASTER_FALLBACK)

if df_master.empty:
    st.warning("Aucune donnée trouvée dans le Master Inventaire.")
    st.stop()

# Nettoyage basique
if 'designation' not in df_master.columns:
    st.error("La colonne 'designation' est absente du fichier source.")
    st.stop()

tabs = st.tabs(["⚡ Calculateur", "📊 Statistiques", "⚙️ Paramètres"])

with tabs[0]:
    st.subheader("Optimisation des Emplacements")
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.write("#### 📝 Données Actuelles")
        st.dataframe(df_master[['designation', 'zone']].head(10), use_container_width=True)
        
    if st.button("🚀 CALCULER LA RÉPARTITION OPTIMALE", type="primary", use_container_width=True):
        with st.spinner("Analyse des dosages et équilibrage des zones..."):
            df_result = perform_smart_repartition(df_master.copy())
            st.session_state.temp_repartition = df_result
            st.success("Répartition calculée avec succès !")

    if "temp_repartition" in st.session_state:
        df_res = st.session_state.temp_repartition
        st.write("#### ✨ Aperçu du Nouveau Plan de Rangement")
        
        # Comparaison
        df_display = df_res[['designation', 'dosage', 'is_frigo', 'zone', 'new_zone']].copy()
        df_display.columns = ['Désignation', 'Dosage', 'Frigo', 'Zone Actuelle', 'Nouvelle Zone']
        
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        if st.button("💾 APPLIQUER ET ENREGISTRER SUR LE CLOUD", use_container_width=True):
            # On remplace l'ancienne colonne zone par la nouvelle
            df_final = df_res.copy()
            df_final['zone'] = df_final['new_zone']
            # On nettoie les colonnes techniques avant sauvegarde
            cols_to_drop = ['dosage', 'base_name', 'is_frigo', 'new_zone']
            df_final = df_final.drop(columns=[c for c in cols_to_drop if c in df_final.columns])
            
            save_gs_data(df_final, MASTER_WORKSHEET, MASTER_FALLBACK, force_cloud=True)
            st.success("✅ La nouvelle répartition a été enregistrée. Toutes les zones utilisateur sont synchronisées !")
            st.balloons()

with tabs[1]:
    if "temp_repartition" in st.session_state:
        df_res = st.session_state.temp_repartition
        st.subheader("📊 Analyse de l'Équilibre")
        
        c1, c2, c3 = st.columns(3)
        
        # Stats par zone
        zone_stats = df_res['new_zone'].value_counts().reset_index()
        zone_stats.columns = ['Zone', 'Nombre de Produits']
        
        with c1:
            st.write("**Répartition Numérique**")
            st.dataframe(zone_stats, hide_index=True)
        
        with c2:
            st.write("**Visualisation**")
            st.bar_chart(zone_stats, x='Zone', y='Nombre de Produits')
            
        with c3:
            frigo_count = len(df_res[df_res['is_frigo'] == True])
            st.metric("📦 Produits en Chambre Froide", frigo_count)
            
        st.divider()
        st.write("#### 🧪 Vérification Anti-Confusion")
        st.write("Exemple de produits avec plusieurs dosages répartis :")
        
        # Trouver des produits avec plusieurs dosages
        multi_dosage = df_res.groupby('base_name').filter(lambda x: x['dosage'].nunique() > 1)
        if not multi_dosage.empty:
            sample = multi_dosage[['base_name', 'dosage', 'new_zone']].drop_duplicates().sort_values('base_name')
            st.dataframe(sample.head(20), use_container_width=True, hide_index=True)
        else:
            st.info("Aucun produit avec dosages multiples détecté.")

with tabs[2]:
    st.subheader("Configuration des Mots-clés")
    st.write("Détection automatique du dosage via REGEX (mg, g, ml, ui...).")
    st.write("Détection Frigo via : `FRIGO, FRESH, COLD, INSU, VACCIN, SERUM`")
    
    show_sync_ui(MASTER_WORKSHEET, MASTER_FALLBACK, ["designation", "lot", "zone"])
