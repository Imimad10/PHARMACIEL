import streamlit as st
import pandas as pd
from datetime import datetime
import os
import io
from PIL import Image
from utils import log_action
from utils_gsheets import load_gs_data, save_gs_data, show_sync_ui
from generator_pdf import generate_reclam_pdf, generate_multi_reclam_pdf, generate_bon_retour_pdf
from utils_ia import ask_ai, ask_ai_vision, is_ia_enabled
import base64
import plotly.express as px

# --- CONFIGURATION ---
WORKSHEET_NAME = "Litiges"
FALLBACK_PATH = 'data/data_litiges.csv'
PHOTO_DIR = 'data/photos_litiges/'
os.makedirs(PHOTO_DIR, exist_ok=True)

COLUMNS = ["Date", "Heure", "Facture", "Fournisseur", "Agent", "Produit", "Lot", "Quantite", "Type", "Priorite", "Statut", "Commentaire", "Photo_Path", "Date_Resolution", "IA_Analyse"]

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

etab_nom = "Pharmaciel" if st.session_state.get('etablissement') == 'pharmaciel' else "DarPharm"
st.title(f"📦 {etab_nom.upper()} - Gestion des Litiges & Réclamations")
st.write("Système synchronisé pour le suivi des anomalies de réception et litiges fournisseurs.")

def render_litiges_accordion(df, mode="active"):
    """
    Affiche les litiges sous forme d'accordéon (expander).
    mode: "active" → boutons Résoudre/Supprimer
          "solved"  → lecture seule avec date de résolution
    """
    if df.empty:
        st.info("Aucune réclamation à afficher.")
        return

    PRIORITY_COLORS = {"Critique": "🔴", "Important": "🟡", "Normal": "🟢"}

    for idx, row in df.iterrows():
        prio_icon = PRIORITY_COLORS.get(str(row.get("Priorite", "Normal")), "⚪")
        label = (
            f"{prio_icon} [{row.get('Date', '')}] "
            f"{row.get('Fournisseur', '')} — "
            f"{row.get('Produit', '')} "
            f"(x{row.get('Quantite', '')}) — {row.get('Type', '')}"
        )

        with st.expander(label, expanded=False):
            col_info, col_photo = st.columns([2, 1])

            with col_info:
                st.markdown(f"**N° Facture :** {row.get('Facture', '-')}")
                st.markdown(f"**Agent :** {row.get('Agent', '-')}")
                st.markdown(f"**Lot :** {row.get('Lot', '-')}")
                st.markdown(f"**Priorité :** {row.get('Priorite', '-')}")
                st.markdown(f"**Statut :** {row.get('Statut', '-')}")
                if str(row.get("Date_Resolution", "")) not in ("", "None", "nan"):
                    st.markdown(f"**Date Résolution :** {row.get('Date_Resolution', '')}")
                commentaire = str(row.get("Commentaire", "")).strip()
                if commentaire and commentaire != "nan":
                    st.markdown(f"**Observations :** {commentaire}")
                ia = str(row.get("IA_Analyse", "")).strip()
                if ia and ia not in ("nan", "Analyse en attente..."):
                    with st.expander("🤖 Analyse IA"):
                        st.info(ia)

            with col_photo:
                photo_path = str(row.get("Photo_Path", "")).strip()
                if photo_path and photo_path != "nan" and os.path.exists(photo_path):
                    try:
                        st.image(photo_path, caption="Photo de preuve", use_container_width=True)
                    except Exception:
                        st.caption("(Photo non lisible)")

            # --- Actions ---
            if mode == "active":
                col_btn1, col_btn2, col_btn3 = st.columns(3)
                
                # Bouton de génération PDF
                if col_btn1.button("🖨️ Bon de Retour", key=f"print_{mode}_{idx}", type="primary"):
                    pdf_data = {
                        "date": str(row.get('Date', '')),
                        "fournisseur": str(row.get('Fournisseur', '')),
                        "agent": str(row.get('Agent', '')),
                        "produit": str(row.get('Produit', '')),
                        "lot": str(row.get('Lot', '')),
                        "quantite": str(row.get('Quantite', '')),
                        "type": str(row.get('Type', '')),
                        "facture": str(row.get('Facture', '')),
                        "commentaire": str(row.get('Commentaire', ''))
                    }
                    pdf_bytes = generate_bon_retour_pdf(pdf_data)
                    log_action(
                        st.session_state.current_user["username"],
                        f"Impression Bon Retour Fournisseur: {row.get('Produit', '')}",
                        "Litiges"
                    )
                    st.session_state[f"pdf_dl_litige_{idx}"] = pdf_bytes
                    st.rerun()
                    
                if col_btn2.button("✅ Réglée", key=f"resolve_{mode}_{idx}"):
                    df_litiges.loc[idx, "Statut"] = "Réglée"
                    df_litiges.loc[idx, "Date_Resolution"] = datetime.now().strftime("%Y-%m-%d")
                    save_gs_data(df_litiges, WORKSHEET_NAME, FALLBACK_PATH)
                    log_action(
                        st.session_state.current_user["username"],
                        f"Résolution litige: {row.get('Produit', '')} — {row.get('Fournisseur', '')}",
                        "Litiges"
                    )
                    st.success("Réclamation marquée comme réglée.")
                    st.rerun()

                if col_btn3.button("🗑️ Supprimer", key=f"delete_{mode}_{idx}"):
                    df_litiges.drop(index=idx, inplace=True)
                    df_litiges.reset_index(drop=True, inplace=True)
                    save_gs_data(df_litiges, WORKSHEET_NAME, FALLBACK_PATH)
                    log_action(
                        st.session_state.current_user["username"],
                        f"Suppression litige: {row.get('Produit', '')} — {row.get('Fournisseur', '')}",
                        "Litiges"
                    )
                    st.warning("Réclamation supprimée.")
                    st.rerun()

                # Zone de téléchargement du PDF si généré
                if st.session_state.get(f"pdf_dl_litige_{idx}"):
                    st.download_button(
                        label="📥 TÉLÉCHARGER LE BON DE RETOUR PDF",
                        data=st.session_state[f"pdf_dl_litige_{idx}"],
                        file_name=f"Bon_Retour_{row.get('Fournisseur', 'Fournisseur')}_{row.get('Lot', '00')}.pdf",
                        mime="application/pdf",
                        type="primary"
                    )


tab_new, tab_list, tab_regl, tab_arch, tab_stats, tab_prods = st.tabs(["➕ Nouveau Rapport", "📋 Suivi Actif", "✅ Réclamations réglées", "🗄️ Archives", "📊 Dashboard Performance", "📦 Base Produits"])

# --- CHARGEMENT DYNAMIQUE DES DONNÉES ---
df_prods = load_gs_data("Base_Produits", "data_produits.csv", ["Désignation"])
liste_prods = sorted([str(p).upper().strip() for p in df_prods["Désignation"].unique() if pd.notna(p) and str(p).strip() != ""])

df_fournisseurs = load_gs_data("DB_Fournisseurs", "data/db_fournisseurs.csv", ["Etablissement"])
liste_fournisseurs = sorted([str(f).upper().strip() for f in df_fournisseurs["Etablissement"].unique() if pd.notna(f) and str(f).strip() != ""])

if "temp_litiges" not in st.session_state:
    st.session_state.temp_litiges = []

# --- ONGLET 1 : NOUVELLE RÉCLAMATION ---
with tab_new:
    # 1. En-tête commune
    st.subheader("📝 Informations Générales")
    c_h1, c_h2 = st.columns(2)
    
    choix_f = c_h1.selectbox("Fournisseur / Laboratoire", ["-- Saisie Manuelle --"] + liste_fournisseurs, help="Sélectionnez un fournisseur de la base ou saisissez-en un nouveau.")
    if choix_f == "-- Saisie Manuelle --":
        fournisseur = c_h1.text_input("Nom du Fournisseur (Manuel)", placeholder="Ex: Sanofi, Biopharm...")
    else:
        fournisseur = choix_f
        
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
                    "Date_Resolution": "",
                    "IA_Analyse": "Analyse en attente..."
                })
            
            df_litiges = pd.concat([df_litiges, pd.DataFrame(new_rows)], ignore_index=True)
            save_gs_data(df_litiges, WORKSHEET_NAME, FALLBACK_PATH)
            
            st.session_state.temp_litiges = []
            st.success("✅ Tous les litiges ont été enregistrés et synchronisés !")
            log_action(st.session_state.current_user['username'], f"Multi-Litiges: {fournisseur} - {len(new_rows)} articles", "Litiges")
            st.rerun()

# --- ONGLET 2 : LISTE ET PDF (ACTIFS) ---
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
                    formatted_items = []
                    for it in items_list:
                        formatted_items.append({
                            'date': it['Date'], 'fournisseur': it['Fournisseur'], 'facture': it['Facture'],
                            'agent': it['Agent'], 'produit': it['Produit'], 'lot': it['Lot'],
                            'quantite': it['Quantite'], 'type': it['Type'], 'commentaire': it['Commentaire'],
                            'Photo_Path': it['Photo_Path']
                        })
                    pdf_bytes = generate_multi_reclam_pdf(formatted_items)
                    st.download_button(label="📥 Télécharger PDF Groupé", data=pdf_bytes, file_name=f"Rapport_Litiges_{selected_inv}.pdf", mime="application/pdf")

        st.divider()
        f_search = st.text_input("🔍 Rechercher par Fournisseur ou Produit (EN COURS)").upper()
        df_active = df_litiges[df_litiges['Statut'] == "En cours"].copy()
        if f_search:
            df_active = df_active[df_active['Fournisseur'].str.contains(f_search) | df_active['Produit'].str.contains(f_search)]
        
        st.write(f"**{len(df_active)}** réclamations en cours.")
        render_litiges_accordion(df_active, "active")

# --- ONGLET 3 : RÉCLAMATIONS RÉGLÉES ---
with tab_regl:
    st.subheader("✅ Historique des Réclamations Réglées")
    f_search_r = st.text_input("🔍 Rechercher par Fournisseur ou Produit (RÉGLÉES)").upper()
    df_solved = df_litiges[df_litiges['Statut'] == "Réglée"].copy()
    if f_search_r:
        df_solved = df_solved[df_solved['Fournisseur'].str.contains(f_search_r) | df_solved['Produit'].str.contains(f_search_r)]
    
    st.write(f"**{len(df_solved)}** réclamations réglées.")
    render_litiges_accordion(df_solved, "solved")

# --- ONGLET 4 : ARCHIVES (VUE TABULAIRE) ---
with tab_arch:
    st.subheader("🗄️ Archives Complètes (Base de données)")
    st.dataframe(df_litiges.sort_values("Date", ascending=False), use_container_width=True, hide_index=True)

# --- ONGLET 5 : STATS ---
with tab_stats:
    if not df_litiges.empty:
        df_active = df_litiges[df_litiges['Statut'] == "En cours"].copy()
        df_closed = df_litiges[df_litiges['Statut'] == "Réglée"].copy()

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Historique", len(df_litiges))
        c2.metric("En cours (Actifs)", len(df_active))
        c3.metric("Résolus", len(df_closed))
        
        # Calcul du temps moyen de résolution
        if not df_closed.empty:
            df_closed['delai'] = df_closed.apply(lambda r: get_delay(r['Date'], r['Date_Resolution']), axis=1)
            avg_time = df_closed['delai'].mean()
            c4.metric("Délai Moyen Résolution", f"{avg_time:.1f} Jours")
        
        st.divider()
        col_st1, col_st2 = st.columns(2)
        
        with col_st1:
            st.subheader("⏳ Âge des Litiges Actifs")
            if not df_active.empty:
                df_active['age'] = df_active.apply(lambda r: get_delay(r['Date'], datetime.now().strftime("%Y-%m-%d")), axis=1)
                fig_age = px.histogram(df_active, x="age", nbins=10, title="Répartition par ancienneté (Jours)", 
                                       labels={'age': 'Jours'}, color_discrete_sequence=['#ff4b4b'])
                st.plotly_chart(fig_age, use_container_width=True)
            else:
                st.write("Aucun litige en cours.")

        with col_st2:
            st.subheader("📦 Top Produits Problématiques")
            df_prod_count = df_litiges['Produit'].value_counts().head(10).reset_index()
            fig_prod = px.bar(df_prod_count, x='Produit', y='count', title="Top 10 Produits en litige")
            st.plotly_chart(fig_prod, use_container_width=True)

        st.subheader("📊 Répartition par Motif")
        df_motif = df_litiges['Type'].value_counts().reset_index()
        fig_motif = px.pie(df_motif, values='count', names='Type', hole=0.4)
        st.plotly_chart(fig_motif, use_container_width=True)

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
