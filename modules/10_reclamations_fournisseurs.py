import streamlit as st
import pandas as pd
from datetime import datetime
import os
import io
from PIL import Image
from utils import log_action
from utils_gsheets import load_gs_data, save_gs_data, show_sync_ui
from generator_pdf import generate_reclam_pdf, generate_multi_reclam_pdf

# --- CONFIGURATION ---
WORKSHEET_NAME = "Litiges"
FALLBACK_PATH = 'data/data_litiges.csv'
PHOTO_DIR = 'data/photos_litiges/'
os.makedirs(PHOTO_DIR, exist_ok=True)

COLUMNS = ["Date", "Heure", "Facture", "Fournisseur", "Agent", "Produit", "Lot", "Quantite", "Type", "Priorite", "Statut", "Commentaire", "Photo_Path", "Date_Resolution"]

st.set_page_config(page_title="Litiges Fournisseurs", layout="wide", page_icon="📦")
show_sync_ui(WORKSHEET_NAME, FALLBACK_PATH, COLUMNS)

# --- CHARGEMENT DES DONNÉES ---
df_litiges = load_gs_data(WORKSHEET_NAME, FALLBACK_PATH, COLUMNS)
df_litiges['Statut'] = df_litiges['Statut'].astype(str)
df_litiges['Date_Resolution'] = df_litiges['Date_Resolution'].astype(str)

def get_delay(start_date, end_date):
    try:
        if not end_date or end_date == "None":
            end_date = datetime.now().strftime("%Y-%m-%d")
        d1 = datetime.strptime(str(start_date), "%Y-%m-%d")
        d2 = datetime.strptime(str(end_date), "%Y-%m-%d")
        return (d2 - d1).days
    except: return 0

st.title("📦 DARPHARM - Gestion des Litiges & Réclamations")
st.write("Système synchronisé pour le suivi des anomalies de réception et litiges fournisseurs.")

tab_new, tab_list, tab_stats, tab_prods = st.tabs(["➕ Nouveau Rapport", "📋 Suivi des Litiges", "📊 Statistiques", "📦 Base Produits"])

# --- CHARGEMENT DYNAMIQUE DES PRODUITS ---
df_prods = load_gs_data("Base_Produits", "data_produits.csv", ["Désignation"])
liste_prods = sorted([str(p).upper().strip() for p in df_prods["Désignation"].unique() if pd.notna(p) and str(p).strip() != ""])

if "temp_litiges" not in st.session_state:
    st.session_state.temp_litiges = []

# --- ONGLET 1 : NOUVELLE RÉCLAMATION ---
with tab_new:
    # 1. En-tête commune
    st.subheader("📝 Informations Générales")
    c_h1, c_h2 = st.columns(2)
    fournisseur = c_h1.text_input("Fournisseur / Laboratoire", placeholder="Ex: Sanofi, Biopharm...")
    num_facture = c_h2.text_input("N° Facture / BL")
    
    st.divider()
    
    # 2. Ajout d'un article
    st.subheader("🔍 Ajouter un article à la réclamation")
    with st.form("form_add_litige_item", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            if liste_prods:
                produit = st.selectbox("Désignation du Produit", options=liste_prods, index=None, placeholder="Rechercher le produit...")
            else:
                produit = st.text_input("Désignation du Produit (Veuillez importer une base)")
            lot = st.text_input("N° Lot")
            quantite = st.number_input("Quantité concernée", min_value=1, step=1)
            
        with col2:
            type_litige = st.selectbox("Motif de réclamation", [
                "Manquant", "Produit Cassé", "Périmé / Date courte", 
                "Erreur Prix", "Vignette Abîmée", "Erreur Livraison", "Autre"
            ])
            priorite = st.select_slider("Urgence", options=["Normal", "Important", "Critique"])
            uploaded_photo = st.file_uploader("📸 Photo de preuve (Optionnel)", type=["jpg", "jpeg", "png"])
            commentaire = st.text_area("Observations détaillées")

        if st.form_submit_button("➕ Ajouter cet article à la liste"):
            if fournisseur and produit:
                # Gestion photo
                photo_path = ""
                if uploaded_photo:
                    now = datetime.now()
                    photo_filename = f"reclam_{now.strftime('%Y%m%d_%H%M%S')}.jpg"
                    photo_path = os.path.join(PHOTO_DIR, photo_filename)
                    img = Image.open(uploaded_photo)
                    img = img.convert('RGB')
                    img.save(photo_path, quality=80)
                
                new_item = {
                    "Produit": produit.upper(),
                    "Lot": lot,
                    "Quantite": quantite,
                    "Type": type_litige,
                    "Priorite": priorite,
                    "Commentaire": commentaire,
                    "Photo_Path": photo_path
                }
                st.session_state.temp_litiges.append(new_item)
                st.success(f"Article ajouté : {produit}")
                st.rerun()
            else:
                st.error("Veuillez remplir le Fournisseur et le Produit.")

    # 3. Liste temporaire et validation finale
    if st.session_state.temp_litiges:
        st.divider()
        st.subheader(f"📋 Articles à réclamer ({len(st.session_state.temp_litiges)})")
        
        for i, item in enumerate(st.session_state.temp_litiges):
            col_a, col_b, col_c = st.columns([3, 1, 0.5])
            col_a.write(f"**{item['Produit']}** (Lot: {item['Lot']}) - {item['Quantite']} x {item['Type']}")
            if col_c.button("🗑️", key=f"del_temp_{i}"):
                st.session_state.temp_litiges.pop(i)
                st.rerun()
        
        st.divider()
        if st.button("🚀 ENREGISTRER & SYNCHRONISER TOUT", type="primary", use_container_width=True):
            now = datetime.now()
            new_rows = []
            for item in st.session_state.temp_litiges:
                new_rows.append({
                    "Date": now.strftime("%Y-%m-%d"),
                    "Heure": now.strftime("%H:%M"),
                    "Facture": num_facture,
                    "Fournisseur": fournisseur.upper(),
                    "Agent": st.session_state.current_user['username'],
                    "Produit": item['Produit'],
                    "Lot": item['Lot'],
                    "Quantite": item['Quantite'],
                    "Type": item['Type'],
                    "Priorite": item['Priorite'],
                    "Statut": "En cours",
                    "Commentaire": item['Commentaire'],
                    "Photo_Path": item['Photo_Path'],
                    "Date_Resolution": ""
                })
            
            df_litiges = pd.concat([df_litiges, pd.DataFrame(new_rows)], ignore_index=True)
            save_gs_data(df_litiges, WORKSHEET_NAME, FALLBACK_PATH)
            
            st.session_state.temp_litiges = []
            st.success("✅ Tous les litiges ont été enregistrés et synchronisés !")
            log_action(st.session_state.current_user['username'], f"Multi-Litiges: {fournisseur} - {len(new_rows)} articles", "Litiges")
            st.rerun()

# --- ONGLET 2 : LISTE ET PDF ---
with tab_list:
    if df_litiges.empty:
        st.info("Aucun litige enregistré.")
    else:
        # --- SECTION : RAPPORT GROUPÉ ---
        with st.expander("📊 Générer un Rapport Groupé (Multi-articles)", expanded=False):
            st.info("Sélectionnez une facture pour générer un PDF contenant tous les articles concernés.")
            all_invoices = sorted(df_litiges['Facture'].dropna().unique().tolist())
            selected_inv = st.selectbox("Choisir le N° de Facture", [""] + all_invoices)
            
            if selected_inv:
                df_group = df_litiges[df_litiges['Facture'] == selected_inv]
                
                include_resolved = st.checkbox("Inclure les réclamations déjà réglées", value=False)
                if not include_resolved:
                    df_group = df_group[df_group['Statut'] != "Réglée"]
                
                st.write(f"Nombre d'articles trouvés : **{len(df_group)}**")
                
                if st.button("📄 Télécharger Rapport Groupé PDF", type="primary"):
                    items_list = df_group.to_dict('records')
                    # On renomme les clés pour matcher le générateur
                    formatted_items = []
                    for it in items_list:
                        formatted_items.append({
                            'date': it['Date'],
                            'fournisseur': it['Fournisseur'],
                            'facture': it['Facture'],
                            'agent': it['Agent'],
                            'produit': it['Produit'],
                            'lot': it['Lot'],
                            'quantite': it['Quantite'],
                            'type': it['Type'],
                            'commentaire': it['Commentaire'],
                            'Photo_Path': it['Photo_Path']
                        })
                    
                    pdf_bytes = generate_multi_reclam_pdf(formatted_items)
                    st.download_button(
                        label="📥 Cliquer pour télécharger le PDF Groupé",
                        data=pdf_bytes,
                        file_name=f"Rapport_Litiges_{selected_inv}.pdf",
                        mime="application/pdf"
                    )

        st.divider()
        # Filtres rapides
        f_fourn = st.text_input("🔍 Rechercher par Fournisseur ou Produit").upper()
        df_view = df_litiges.copy()
        if f_fourn:
            df_view = df_view[df_view['Fournisseur'].str.contains(f_fourn) | df_view['Produit'].str.contains(f_fourn)]
        
        st.write(f"Affichage de **{len(df_view)}** dossiers.")
        
        for i, row in df_view.iterrows():
            with st.expander(f"📄 {row['Date']} - {row['Fournisseur']} - {row['Produit']} ({row['Statut']})"):
                c1, c2, c3 = st.columns([2, 2, 1])
                with c1:
                    st.write(f"**Motif:** {row['Type']}")
                    st.write(f"**Facture:** {row['Facture']}")
                    st.write(f"**Lot/Qte:** {row['Lot']} / {row['Quantite']}")
                with c2:
                    st.write(f"**Agent:** {row['Agent']}")
                    st.write(f"**Priorité:** {row['Priorite']}")
                    if row['Photo_Path'] and os.path.exists(row['Photo_Path']):
                        st.image(row['Photo_Path'], width=150)
                with c3:
                    # Bouton Génération PDF
                    pdf_data = {
                        "date": row['Date'],
                        "fournisseur": row['Fournisseur'],
                        "produit": row['Produit'],
                        "lot": row['Lot'],
                        "quantite": row['Quantite'],
                        "type": row['Type'],
                        "agent": row['Agent'],
                        "commentaire": row['Commentaire']
                    }
                    pdf_bytes = generate_reclam_pdf(pdf_data, row['Photo_Path'])
                    st.download_button(
                        label="📥 Télécharger PDF",
                        data=pdf_bytes,
                        file_name=f"Reclam_{row['Fournisseur']}_{row['Date']}.pdf",
                        mime="application/pdf",
                        key=f"btn_pdf_{i}",
                        use_container_width=True
                    )
                    
                    # Partage WhatsApp et Viber
                    import urllib.parse
                    msg = f"📦 *RÉCLAMATION DARPHARM*\n\n"
                    msg += f"Bonjour, nous vous signalons une anomalie :\n"
                    msg += f"▪️ *Facture:* {row['Facture']}\n"
                    msg += f"▪️ *Produit:* {row['Produit']} (Lot: {row['Lot']})\n"
                    msg += f"▪️ *Qté:* {row['Quantite']}\n"
                    msg += f"▪️ *Motif:* {row['Type']}\n\n"
                    msg += f"Merci de traiter cette réclamation. (Rapport PDF à suivre)"
                    msg_encoded = urllib.parse.quote(msg)
                    
                    c_wa, c_vi = st.columns(2)
                    c_wa.link_button("💬 WA", f"https://wa.me/?text={msg_encoded}", use_container_width=True)
                    c_vi.link_button("💜 Viber", f"viber://forward?text={msg_encoded}", use_container_width=True)
                    
                    if row['Statut'] == "En cours":
                        if st.button("✅ Régler", key=f"btn_regler_{i}", use_container_width=True):
                            df_litiges.at[i, 'Statut'] = "Réglée"
                            df_litiges.at[i, 'Date_Resolution'] = datetime.now().strftime("%Y-%m-%d")
                            save_gs_data(df_litiges, WORKSHEET_NAME, FALLBACK_PATH)
                            st.success("Dossier clôturé.")
                            st.rerun()

# --- ONGLET 3 : STATS ---
with tab_stats:
    if not df_litiges.empty:
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Litiges", len(df_litiges))
        c2.metric("En cours", len(df_litiges[df_litiges['Statut'] == "En cours"]))
        c3.metric("Résolus", len(df_litiges[df_litiges['Statut'] == "Réglée"]))
        
        st.divider()
        st.subheader("Répartition par Motif")
        df_motif = df_litiges['Type'].value_counts().reset_index()
        st.bar_chart(df_motif, x='Type', y='count')

# --- ONGLET 4 : BASE PRODUITS ---
with tab_prods:
    st.subheader("📦 Base de Données des Produits")
    st.write("Importez une liste Excel ou CSV pour mettre à jour les produits disponibles dans le formulaire de litige. Les doublons seront automatiquement ignorés.")
    
    col_up, col_list = st.columns([1, 1])
    with col_up:
        file_up = st.file_uploader("Importer une nouvelle liste de produits", type=["xlsx", "xls", "csv"])
        if file_up:
            if st.button("🚀 Importer et Mettre à jour la Base", type="primary"):
                with st.spinner("Analyse et nettoyage en cours..."):
                    try:
                        if file_up.name.endswith(".csv"):
                            df_new = pd.read_csv(file_up)
                        else:
                            df_new = pd.read_excel(file_up)
                        
                        # 1. Trouver la bonne colonne de désignation
                        prod_col = None
                        for c in df_new.columns:
                            c_low = str(c).lower()
                            if "produit" in c_low or "designation" in c_low or "nom" in c_low:
                                prod_col = c
                                break
                        if not prod_col: prod_col = df_new.columns[0]
                        
                        # 2. Nettoyer et formater les nouveaux produits
                        new_prods = pd.DataFrame({
                            "Désignation": df_new[prod_col].dropna().astype(str).str.upper().str.strip()
                        })
                        
                        # 3. Fusionner avec l'ancienne base sans créer de doublons
                        df_merged = pd.concat([df_prods, new_prods]).drop_duplicates(subset=["Désignation"]).reset_index(drop=True)
                        
                        # Ne garder que ceux qui ne sont pas vides
                        df_merged = df_merged[df_merged["Désignation"] != ""]
                        
                        # 4. Sauvegarder dans la base centrale
                        save_gs_data(df_merged, "Base_Produits", "data_produits.csv")
                        
                        st.success(f"✅ Import réussi ! Vous avez maintenant {len(df_merged)} produits uniques dans la base.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur lors de l'importation : {e}")

    with col_list:
        st.metric("Total de produits uniques", len(df_prods))
        if not df_prods.empty:
            st.dataframe(df_prods.sort_values("Désignation"), use_container_width=True, hide_index=True)
        else:
            st.info("La base est actuellement vide.")
