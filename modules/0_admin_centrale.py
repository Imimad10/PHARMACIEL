import streamlit as st
import pandas as pd
import os
from datetime import datetime
from utils_gsheets import load_gs_data, save_gs_data, get_gs_client, get_gs_url, USER_COLUMNS
from utils import log_action
from utils_themes import (
    load_themes_db, save_themes_db, get_active_themes,
    toggle_theme_active, set_user_theme, remove_user_theme,
    save_premium_dashboard_html
)

# --- CONFIGURATION ---
DATA_CLIENTS = "base_clients.csv"
DATA_LIVREURS = "data_expedition/livreurs.csv"
DATA_SECTEURS = "data_expedition/secteurs.csv"

COLS_CLIENTS = ["ID", "Code_Client", "Nom_Pharmacie", "Categorie", "Type_Client", "Adresse", "Wilaya", "Region", "Ville", "Conventionne", "Tx_Conv", "Echeance", "Nbr_Jour", "Telephone", "Tel_2", "Mobile", "Code_Postal", "Fax", "Email", "Web", "Filiale", "Active", "Bloque", "Agent_Recouvrement", "AI", "Compte", "RC", "NIS", "NIF", "Agence_Bancaire", "Portefeuille", "Cagnotte", "Commercial_Reserve", "Famille", "Date_Creation", "Solde_Max", "Marge", "Calcul_TVA", "Client_EDF", "Gerant", "Tel_Contact_1", "Contact_2", "Tel_Contact_2", "Commentaire", "Categorie_UG", "Tel_3", "Client_BL", "Contact_3", "Tel_Contact_3", "Latitude", "Longitude", "Demi_Marge", "Delegue", "Mode_Paiement", "Tiers_Fact_Route", "Num_Inspection", "Type_Vente", "Auxiliaire", "Code_Site", "Assurance", "Mont_Assure", "Site", "Forme_Juridique", "Motif_Blocage", "Compte_Ligne", "BP", "PharmaDrive", "Blocage_Fin", "Date_Recrut", "Date_Reprise", "Num_Modele_Imp", "LogiDrive", "Etat_Dossier", "Exclure_PSY", "Exclure_PSY_SPE", "Exclure_LogiDrive", "Date_Agrement", "Num_Ordre", "Verification", "Date_Verif", "Verif_Par", "Tx_Vente", "Cash", "Banque", "NIN", "PI", "VF", "Num_Agrement"]
COLS_LIVREURS = ["Nom", "Prénom", "Téléphone", "Secteur"]
COLS_SECTEURS = ["Client", "Ville", "Tel", "Secteur"]

def clean_client_cols(df):
    mapping = {
        'ID': ['n°', 'id'],
        'Code_Client': ['code.', 'code client'],
        'Nom_Pharmacie': ['raison sociale', 'nom', 'pharmacie', 'client'],
        'Categorie': ['catégorie', 'categorie'],
        'Type_Client': ['type client'],
        'Adresse': ['adresse'],
        'Wilaya': ['wilaya'],
        'Region': ['région', 'region'],
        'Ville': ['ville'],
        'Conventionne': ['conventionné', 'conventionne'],
        'Tx_Conv': ['tx conv.', 'tx conv'],
        'Echeance': ['echéance', 'echeance'],
        'Nbr_Jour': ['nbr jour'],
        'Telephone': ['tel prof.', 'telephone', 'téléphone', 'tel'],
        'Tel_2': ['tél 2', 'tel 2'],
        'Mobile': ['mobile'],
        'Code_Postal': ['code postal'],
        'Fax': ['fax'],
        'Email': ['email', 'e-mail'],
        'Web': ['web'],
        'Filiale': ['filiale'],
        'Active': ['active'],
        'Bloque': ['bloqué', 'bloque'],
        'Agent_Recouvrement': ['agent de recouvrement'],
        'AI': ['a.i', 'ai'],
        'Compte': ['compte'],
        'RC': ['r.c', 'rc'],
        'NIS': ['nis'],
        'NIF': ['nif'],
        'Agence_Bancaire': ['agence bancaire'],
        'Portefeuille': ['portefeuille'],
        'Cagnotte': ['cagnotte'],
        'Commercial_Reserve': ['commercial reserve', 'commercial'],
        'Famille': ['famille'],
        'Date_Creation': ['date création', 'date creation'],
        'Solde_Max': ['solde max'],
        'Marge': ['marge'],
        'Calcul_TVA': ['calcul tva'],
        'Client_EDF': ['client e.d.f', 'client edf'],
        'Gerant': ['contact 1', 'gerant', 'gérant'],
        'Tel_Contact_1': ['tél contact 1', 'tel contact 1'],
        'Contact_2': ['contact 2'],
        'Tel_Contact_2': ['tél contact 2', 'tel contact 2'],
        'Commentaire': ['observation', 'commentaire', 'remarque'],
        'Categorie_UG': ['categorie ug', 'catégorie ug'],
        'Tel_3': ['tél 3', 'tel 3'],
        'Client_BL': ['client b.l', 'client bl'],
        'Contact_3': ['contact 3'],
        'Tel_Contact_3': ['tél contact 3', 'tel contact 3'],
        'Latitude': ['latitude'],
        'Longitude': ['langitude', 'longitude'],
        'Demi_Marge': ['demi-marge'],
        'Delegue': ['delegue', 'délégué'],
        'Mode_Paiement': ['mode paiement'],
        'Tiers_Fact_Route': ['tiers fact.route', 'tiers fact route'],
        'Num_Inspection': ['n°inspection', 'n inspection'],
        'Type_Vente': ['type vente'],
        'Auxiliaire': ['auxiliare', 'auxiliaire'],
        'Code_Site': ['code site'],
        'Assurance': ['assurance'],
        'Mont_Assure': ['mont.assuré', 'mont assure'],
        'Site': ['site'],
        'Forme_Juridique': ['forme juridique'],
        'Motif_Blocage': ['motif blocage'],
        'Compte_Ligne': ['compte en ligne'],
        'BP': ['bp'],
        'PharmaDrive': ['pharmadrive'],
        'Blocage_Fin': ['bocage fin.', 'blocage fin', 'blocage financier'],
        'Date_Recrut': ['date recrut.', 'date recrut'],
        'Date_Reprise': ['date reprise'],
        'Num_Modele_Imp': ['n°moldèle imp.', 'n modele imp'],
        'LogiDrive': ['logidrive'],
        'Etat_Dossier': ['etat dossier', 'état dossier'],
        'Exclure_PSY': ['exclure psy.', 'exclure psy'],
        'Exclure_PSY_SPE': ['exclure psy.spe', 'exclure psy spe'],
        'Exclure_LogiDrive': ['exclure logidrive'],
        'Date_Agrement': ['date agrement', 'date agrément'],
        'Num_Ordre': ['n°ordre', 'n ordre'],
        'Verification': ['vérification', 'verification'],
        'Date_Verif': ['date vérif.', 'date verif'],
        'Verif_Par': ['vérif.par', 'verif par'],
        'Tx_Vente': ['tx vente%', 'tx vente'],
        'Cash': ['cash'],
        'Banque': ['banque'],
        'NIN': ['nin'],
        'PI': ['pi'],
        'VF': ['v.f', 'vf'],
        'Num_Agrement': ['n°agrement', 'n agrement']
    }
    
    new_cols = {}
    for col in df.columns:
        col_str = str(col).lower().strip()
        matched = False
        for target, alts in mapping.items():
            if col_str in alts:
                new_cols[col] = target
                matched = True
                break
        if not matched:
            for target, alts in mapping.items():
                valid_alts = [a for a in alts if len(a) > 3]
                if any(alt in col_str for alt in valid_alts):
                    new_cols[col] = target
                    break
                    
    return df.rename(columns=new_cols)

def clean_inventory_cols(df):
    mapping = {
        'depot': ['dépôt', 'depot', 'id depot'],
        'produit': ['produit', 'article', 'désignation', 'designation', 'n°produit', 'code'],
        'lot': ['n°lot', 'lot', 'batch', 'nlot'],
        'qte_logi': ['quantité dépôt', 'quantité depot', 'qte.globale', 'quantité', 'qte'],
        'colissage': ['colis', 'u/colis', 'colissage', 'nbr colis'],
        'zone': ['zone produit', 'zone', 'emplacement'],
        'ddp': ['ddp', 'peremption', 'péremption', 'exp', 'date'],
        'ppa': ['ppa', 'prix public', 'prix'],
        'shp': ['shp', 'tarif'],
        'laboratoire': ['laboratoire', 'labo'],
        'fournisseur': ['fournisseur', 'fourn'],
        'dci': ['d.c.i', 'dci'],
        'rotation': ['rotation'],
        'categorie': ['catégorie', 'categorie'],
        'vrac': ['vrac'],
        'prix_achat': ['prix d\'achat', 'prix achat', 'valeur achat'],
        'prix_vente': ['prix vente', 'valeur vente'],
        'marge': ['marge', 'marge ph.', 'marge ph', 'marge 2'],
        'tva': ['tva'],
        'remise': ['remise ug', 'remise achat', 'remise']
    }
    
    new_cols = {}
    for col in df.columns:
        col_str = str(col).lower().strip()
        matched = False
        for target, alts in mapping.items():
            if col_str in alts:
                new_cols[col] = target
                matched = True
                break
        if not matched:
            new_cols[col] = col # On garde les noms de colonnes originaux pour ne rien perdre
    return df.rename(columns=new_cols)

# Sécurité
if "current_user" not in st.session_state or st.session_state.current_user is None:
    st.warning("Veuillez vous connecter.")
    st.stop()

if st.session_state.current_user.get('role') not in ['Admin', 'Superviseur']:
    st.error("Accès réservé à l'administration.")
    st.stop()

st.set_page_config(page_title="Administration Centrale", layout="wide")

st.markdown("""
<style>
    .admin-centrale-header {
        background: linear-gradient(135deg, #0f172a, #3b82f6);
        padding: 35px;
        border-radius: 24px;
        color: white;
        box-shadow: 0 15px 35px rgba(59, 130, 246, 0.3);
        margin-bottom: 30px;
        position: relative;
        overflow: hidden;
    }
    .admin-centrale-header::after {
        content: '';
        position: absolute;
        top: -50%; right: -10%;
        width: 300px; height: 300px;
        background: rgba(255,255,255,0.1);
        border-radius: 50%;
        filter: blur(40px);
    }
    .admin-centrale-header h1 {
        margin:0; font-size: 2.4rem; font-weight: 900; color: white;
        letter-spacing: -0.5px;
    }
    .admin-centrale-header p {
        margin: 8px 0 0 0; font-size: 1.1rem; opacity: 0.85;
        font-weight: 500;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('''
<div class="admin-centrale-header">
    <div>
        <h1>🏛️ Administration Centrale (Master Data)</h1>
        <p>Centre de pilotage et gestion centralisée de la base de données DarPharm.</p>
    </div>
</div>
''', unsafe_allow_html=True)

# --- TABS ---
tabs = st.tabs(["📤 Importateur Universel", "👥 Base Clients", "🚚 Livreurs", "🗺️ Secteurs Logistique", "📦 Archivage Cloud", "🎨 Gestion des Thèmes", "⚙️ Maintenance & Hors-Ligne"])

# ONGLET 0 : IMPORTATEUR UNIVERSEL (DRAG & DROP)
with tabs[0]:
    st.subheader("🚀 Importation Centralisée")
    st.info("Déposez un fichier Excel contenant vos données. Le système détectera automatiquement s'il s'agit de clients, de livreurs ou de secteurs.")
    
    f_up = st.file_uploader("Fichier Master Data (Excel ou PDF Fournisseurs)", type=["xlsx", "pdf"])
    if f_up:
        target = None
        mapping = {}
        
        if f_up.name.endswith(".pdf"):
            import pdfplumber
            st.info("Traitement du PDF en cours... Extraction des données des établissements de fabrication.")
            try:
                extracted_data = []
                with pdfplumber.open(f_up) as pdf:
                    for page in pdf.pages:
                        table = page.extract_table()
                        if table:
                            for row in table:
                                # On cherche les lignes qui ressemblent à la table officielle (N°, Etablissement, Wilaya, Activité)
                                if row and len(row) >= 4 and str(row[0]).strip().isdigit():
                                    extracted_data.append({
                                        "Etablissement": str(row[1]).replace('\n', ' ').strip() if row[1] else "",
                                        "Wilaya": str(row[2]).replace('\n', ' ').strip() if row[2] else "",
                                        "Activité": str(row[3]).replace('\n', ' ').strip() if row[3] else ""
                                    })
                df_up = pd.DataFrame(extracted_data)
                target = "Fournisseurs"
                mapping = {"Etablissement": "Etablissement", "Wilaya": "Wilaya", "Activité": "Activité"}
            except Exception as e:
                st.error(f"Erreur lors de la lecture du PDF : {e}")
                df_up = pd.DataFrame()
        else:
            df_up = pd.read_excel(f_up)
        
        # Détection automatique du type de données (si non défini par le PDF)
        cols = [str(c).strip() for c in df_up.columns.tolist()]
        cols_lower = [c.lower() for c in cols]
        
        if not target:
            if "prenom" in cols_lower or "prénom" in cols_lower:
                target = "Livreurs"
                mapping = {c: "Prénom" for c in cols if c.lower() in ["prenom","prénom"]}
                mapping.update({c: "Nom" for c in cols if c.lower() == "nom"})
                mapping.update({c: "Secteur" for c in cols if c.lower() == "secteur"})
                mapping.update({c: "Téléphone" for c in cols if c.lower() in ["téléphone","telephone","tel"]})
            elif "ville" in cols_lower:
                target = "Secteurs"
                mapping = {c: "Client" for c in cols if c.lower() in ["client","raison sociale","raison sociale","nom client"]}
                mapping.update({c: "Ville" for c in cols if c.lower() == "ville"})
                mapping.update({c: "Secteur" for c in cols if c.lower() == "secteur"})
                mapping.update({c: "Tel" for c in cols if c.lower() in ["tel","téléphone","telephone"]})
            elif any(c.lower() in ["raison sociale","nom client","nom", "client", "pharmacie"] for c in cols):
                target = "Base_Clients"
                df_up = clean_client_cols(df_up)
                if 'Nom_Pharmacie' not in df_up.columns:
                    df_up['Nom_Pharmacie'] = df_up['ID'].astype(str) if 'ID' in df_up.columns else "Client_Inconnu"
            elif "username" in cols_lower:
                target = "Utilisateurs"
                mapping = {c: "username" for c in cols if c.lower() == "username"}
                mapping.update({c: "password" for c in cols if c.lower() in ["password", "mot de passe", "pwd"]})
                mapping.update({c: "nom" for c in cols if c.lower() == "nom"})
                mapping.update({c: "prenom" for c in cols if c.lower() in ["prenom", "prénom"]})
                mapping.update({c: "role" for c in cols if c.lower() in ["role", "rôle"]})
                mapping.update({c: "zone" for c in cols if c.lower() == "zone"})
                mapping.update({c: "pages" for c in cols if c.lower() == "pages"})
            elif any(x in cols_lower for x in ["dépôt", "depot", "quantité dépôt", "quantité depot", "qte.globale", "n°lot", "zone produit"]):
                target = "Master_Inventaire_Zone"
                df_up = clean_inventory_cols(df_up)
        
        elif not target:
            # Si le fichier était un Excel mais sans colonnes reconnues
            pass
        
        if not df_up.empty:
            st.write("**Aperçu des données :**")
        st.dataframe(df_up.head(5), use_container_width=True)
        
        if target:
            st.success(f"🎯 Type détecté : **{target}**")
            
            # Définition des paramètres de destination
            if target == "Base_Clients":
                db_path, db_cols, key = DATA_CLIENTS, COLS_CLIENTS, "Nom_Pharmacie"
            elif target == "Livreurs":
                db_path, db_cols, key = DATA_LIVREURS, COLS_LIVREURS, "Nom"
            elif target == "Utilisateurs":
                from utils_gsheets import DB_USERS_WORKSHEET, DB_USERS_FALLBACK
                db_path, db_cols, key = DB_USERS_FALLBACK, ["username", "password", "role", "pages", "nom", "prenom", "zone"], "username"
            elif target == "Master_Inventaire_Zone":
                # db_cols est laissé vide pour accepter toutes les colonnes
                db_path, db_cols, key = "data_inventaire_detail/master_detail.csv", df_up.columns.tolist(), "lot"
            elif target == "Fournisseurs":
                db_path, db_cols, key = "data/db_fournisseurs.csv", ["Etablissement", "Wilaya", "Activité", "Logo"], "Etablissement"
            else:
                db_path, db_cols, key = DATA_SECTEURS, COLS_SECTEURS, "Client"

            if target == "Fournisseurs":
                if st.button(f"📥 Fusionner avec la base {target}", type="primary", use_container_width=True):
                    df_old = load_gs_data(target, db_path, db_cols)
                    
                    df_merged = df_up.copy()
                    df_merged["Logo"] = ""
                    
                    # On concatène en gardant les nouveaux s'il y a conflit
                    df_final = pd.concat([df_old, df_merged]).drop_duplicates(subset=[key], keep='last')
                    save_gs_data(df_final, "DB_Fournisseurs", db_path)
                    st.success(f"{len(df_final)} fournisseurs sauvegardés avec succès ! ✅")
                    
            elif st.button(f"📥 Fusionner avec la base {target}", type="primary", use_container_width=True):
                # On renomme intelligemment pour éviter les colonnes en double
                new_cols = []
                mapped_targets = set()
                for c in df_up.columns:
                    target_name = mapping.get(c, c)
                    if target_name in db_cols and target_name not in mapped_targets:
                        new_cols.append(target_name)
                        mapped_targets.add(target_name)
                    else:
                        new_cols.append(f"old_{c}")
                
                df_up.columns = new_cols
                
                if target == "Base_Clients":
                    df_merged = pd.concat([df_old, df_up], ignore_index=True).drop_duplicates(subset=[key], keep='last')
                    
                    # Also keep backwards compatibility fields for other modules
                    if 'Nom Client' not in df_merged.columns: df_merged['Nom Client'] = df_merged['Nom_Pharmacie']
                    if 'Région' not in df_merged.columns: df_merged['Région'] = df_merged['Region'].combine_first(df_merged['Wilaya'])
                    if 'Secteur' not in df_merged.columns: df_merged['Secteur'] = df_merged['Region']
                    if 'Téléphone' not in df_merged.columns: df_merged['Téléphone'] = df_merged['Telephone']
                elif target == "Master_Inventaire_Zone":
                    # Remplacement COMPLET pour l'inventaire avec TOUTES les colonnes
                    df_merged = df_up
                    if 'inv_work_df' in st.session_state:
                        del st.session_state.inv_work_df
                else:
                    cols_to_keep = [c for c in db_cols if c in df_up.columns]
                    df_merged = pd.concat([df_old, df_up[cols_to_keep]], ignore_index=True).drop_duplicates(subset=[key])
                
                save_gs_data(df_merged, target, db_path)
                st.success(f"✅ Migration réussie vers **{target}** — {len(df_up)} lignes traitées.")
                log_action(st.session_state.current_user['username'], f"Import Master Data : {target}", "Admin Centrale")
                st.cache_data.clear()
                st.rerun()
        else:
            st.warning("⚠️ Type non reconnu. Vérifiez que vos colonnes sont nommées : 'Raison sociale', 'Prénom', ou 'Ville'.")

# ONGLET 1 : BASE CLIENTS
with tabs[1]:
    st.subheader("👥 Annuaire Général des Clients")
    df_clients = load_gs_data("Base_Clients", DATA_CLIENTS, COLS_CLIENTS)
    edited_clients = st.data_editor(df_clients, use_container_width=True, num_rows="dynamic", key="editor_clients")
    
    c1, c2, c3 = st.columns(3)
    if c1.button("💾 Sauvegarder", key="btn_save_clients", use_container_width=True):
        save_gs_data(edited_clients, "Base_Clients", DATA_CLIENTS)
        st.success("Base Clients mise à jour !")

    if c2.button("📥 Importer depuis Secteurs", key="btn_import_secteurs", use_container_width=True):
        df_sec = load_gs_data("Secteurs", DATA_SECTEURS, COLS_SECTEURS)
        rows = []
        for _, row in df_sec.iterrows():
            rows.append({
                "Nom_Pharmacie": str(row.get("Client", "")),
                "Nom Client": str(row.get("Client", "")),
                "Region":     str(row.get("Ville", "")),
                "Telephone":  str(row.get("Tel", "")),
                "Secteur":    str(row.get("Secteur", ""))
            })
        df_new_clients = pd.DataFrame(rows)
        df_old_clients = load_gs_data("Base_Clients", DATA_CLIENTS, COLS_CLIENTS)
        df_merged = pd.concat([df_old_clients, df_new_clients], ignore_index=True).drop_duplicates(subset=["Nom_Pharmacie"])
        save_gs_data(df_merged, "Base_Clients", DATA_CLIENTS)
        st.success(f"✅ Clients importés depuis Secteurs Logistique !")
        st.cache_data.clear()
        st.rerun()

    if c3.button("🔄 Transmettre vers Secteurs", key="btn_sync_secteurs", use_container_width=True, type="primary"):
        df_src = edited_clients.copy()
        # Construction propre du DataFrame Secteurs depuis zéro
        rows = []
        for _, row in df_src.iterrows():
            rows.append({
                "Client": str(row.get("Nom_Pharmacie", row.get("Nom Client", ""))),
                "Ville":  str(row.get("Region", row.get("Région", ""))),
                "Tel":    str(row.get("Telephone", row.get("Téléphone", ""))),
                "Secteur": str(row.get("Region", row.get("Secteur", "")))
            })
        df_new_sec = pd.DataFrame(rows, columns=COLS_SECTEURS)
        df_old_sec = load_gs_data("Secteurs", DATA_SECTEURS, COLS_SECTEURS)
        df_merged = pd.concat([df_old_sec, df_new_sec], ignore_index=True).drop_duplicates(subset=["Client"])
        save_gs_data(df_merged, "Secteurs", DATA_SECTEURS)
        st.success(f"✅ {len(df_new_sec)} clients transmis vers Secteurs Logistique !")
        st.cache_data.clear()

    # --- MINI-CRM : SUIVI DES INTERACTIONS ---
    st.divider()
    st.subheader("🤝 Mini-CRM : Suivi des Interactions")
    
    col_crm1, col_crm2 = st.columns([1, 2])
    
    # Charger les clients pour la sélection
    liste_clients_crm = sorted(df_clients["Nom Client"].dropna().unique().tolist())
    
    with col_crm1:
        st.write("📝 **Nouvelle Interaction**")
        with st.form("form_crm_note", clear_on_submit=True):
            client_sel = st.selectbox("Client", [""] + liste_clients_crm)
            type_int = st.selectbox("Type", ["Note", "Appel", "Visite", "Réclamation", "Promesse Paiement"])
            note_txt = st.text_area("Détails de l'échange")
            
            if st.form_submit_button("Enregistrer l'interaction"):
                if client_sel and note_txt:
                    df_crm = load_gs_data("CRM", "data/db_crm.csv", ["Date", "Client", "Type", "Note", "Agent"])
                    new_note = pd.DataFrame([{
                        "Date": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Client": client_sel,
                        "Type": type_int,
                        "Note": note_txt,
                        "Agent": st.session_state.current_user['username']
                    }])
                    df_crm = pd.concat([df_crm, new_note], ignore_index=True)
                    save_gs_data(df_crm, "CRM", "data/db_crm.csv")
                    st.success("Interaction enregistrée !")
                    st.rerun()
                else:
                    st.warning("Veuillez remplir tous les champs.")

    with col_crm2:
        st.write("📜 **Historique des Échanges**")
        client_hist = st.selectbox("Filtrer par Client", ["Tous"] + liste_clients_crm, key="crm_filter")
        df_crm_view = load_gs_data("CRM", "data/db_crm.csv", ["Date", "Client", "Type", "Note", "Agent"])
        
        if not df_crm_view.empty:
            if client_hist != "Tous":
                df_crm_view = df_crm_view[df_crm_view["Client"] == client_hist]
            
            st.dataframe(df_crm_view.sort_values("Date", ascending=False), use_container_width=True, hide_index=True)
        else:
            st.info("Aucun historique d'interaction pour le moment.")

# ONGLET 2 : LIVREURS
with tabs[2]:
    st.subheader("🚚 Gestion des Livreurs")
    df_liv = load_gs_data("Livreurs", DATA_LIVREURS, COLS_LIVREURS)
    
    # --- AJOUT ---
    with st.expander("➕ Ajouter un nouveau Livreur"):
        with st.form("form_add_livreur", clear_on_submit=True):
            c_a1, c_a2, c_a3, c_a4 = st.columns(4)
            n_nom = c_a1.text_input("Nom*")
            n_pre = c_a2.text_input("Prénom")
            n_tel = c_a3.text_input("Téléphone")
            n_sec = c_a4.text_input("Secteur")
            
            if st.form_submit_button("Ajouter", type="primary"):
                if n_nom:
                    new_liv = pd.DataFrame([{"Nom": n_nom.upper(), "Prénom": n_pre.capitalize(), "Téléphone": n_tel, "Secteur": n_sec.upper()}])
                    df_liv = pd.concat([df_liv, new_liv], ignore_index=True)
                    save_gs_data(df_liv, "Livreurs", DATA_LIVREURS)
                    st.success("Livreur ajouté avec succès !")
                    st.rerun()
                else:
                    st.error("Le Nom est obligatoire.")

    st.divider()

    # --- ÉTAT DE SESSION POUR L'ÉDITION ---
    if 'edit_liv_idx' not in st.session_state: st.session_state.edit_liv_idx = None
    if 'del_liv_idx' not in st.session_state: st.session_state.del_liv_idx = None

    if not df_liv.empty:
        # En-têtes
        h1, h2, h3, h4, h5 = st.columns([2, 2, 2, 2, 2])
        h1.markdown("**Nom**")
        h2.markdown("**Prénom**")
        h3.markdown("**Téléphone**")
        h4.markdown("**Secteur**")
        h5.markdown("**Actions**")
        st.write("---")

        for idx, row in df_liv.iterrows():
            with st.container():
                # MODE ÉDITION
                if st.session_state.edit_liv_idx == idx:
                    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 2])
                    e_nom = c1.text_input("Nom", value=str(row.get('Nom', '')), key=f"en_{idx}", label_visibility="collapsed")
                    e_pre = c2.text_input("Prénom", value=str(row.get('Prénom', '')), key=f"ep_{idx}", label_visibility="collapsed")
                    e_tel = c3.text_input("Téléphone", value=str(row.get('Téléphone', '')), key=f"et_{idx}", label_visibility="collapsed")
                    e_sec = c4.text_input("Secteur", value=str(row.get('Secteur', '')), key=f"es_{idx}", label_visibility="collapsed")
                    
                    ca, cb = c5.columns(2)
                    if ca.button("💾", key=f"save_{idx}", help="Enregistrer"):
                        df_liv.at[idx, 'Nom'] = e_nom.upper()
                        df_liv.at[idx, 'Prénom'] = e_pre.capitalize()
                        df_liv.at[idx, 'Téléphone'] = e_tel
                        df_liv.at[idx, 'Secteur'] = e_sec.upper()
                        save_gs_data(df_liv, "Livreurs", DATA_LIVREURS)
                        st.session_state.edit_liv_idx = None
                        st.rerun()
                    if cb.button("❌", key=f"canc_ed_{idx}", help="Annuler"):
                        st.session_state.edit_liv_idx = None
                        st.rerun()

                # MODE SUPPRESSION
                elif st.session_state.del_liv_idx == idx:
                    st.warning(f"⚠️ Voulez-vous vraiment supprimer **{row.get('Nom', '')}** ?")
                    c1, c2 = st.columns(2)
                    if c1.button("✅ Confirmer la suppression", key=f"conf_del_{idx}", type="primary"):
                        df_liv = df_liv.drop(idx)
                        save_gs_data(df_liv, "Livreurs", DATA_LIVREURS)
                        st.session_state.del_liv_idx = None
                        st.success("Supprimé !")
                        st.rerun()
                    if c2.button("🚫 Annuler", key=f"canc_del_{idx}"):
                        st.session_state.del_liv_idx = None
                        st.rerun()

                # MODE NORMAL (AFFICHAGE)
                else:
                    c1, c2, c3, c4, c5 = st.columns([2, 2, 2, 2, 2])
                    c1.write(str(row.get('Nom', '')))
                    c2.write(str(row.get('Prénom', '')))
                    c3.write(str(row.get('Téléphone', '')))
                    c4.write(str(row.get('Secteur', '')))
                    
                    ca, cb = c5.columns(2)
                    if ca.button("✏️", key=f"ed_{idx}", help="Modifier cette ligne"):
                        st.session_state.edit_liv_idx = idx
                        st.session_state.del_liv_idx = None
                        st.rerun()
                    if cb.button("🗑️", key=f"del_{idx}", help="Supprimer cette ligne"):
                        st.session_state.del_liv_idx = idx
                        st.session_state.edit_liv_idx = None
                        st.rerun()
                st.write("---")
    else:
        st.info("Aucun livreur enregistré pour le moment.")

# ONGLET 3 : SECTEURS
with tabs[3]:
    st.subheader("🗺️ Cartographie Secteurs & Clients Logistique")
    df_sec = load_gs_data("Secteurs", DATA_SECTEURS, COLS_SECTEURS)
    edited_sec = st.data_editor(df_sec, use_container_width=True, num_rows="dynamic", key="editor_sec")
    if st.button("💾 Sauvegarder Secteurs", key="btn_save_sec"):
        save_gs_data(edited_sec, "Secteurs", DATA_SECTEURS)
        st.success("Cartographie des Secteurs mise à jour !")

# ONGLET 4 : ARCHIVAGE CLOUD
with tabs[4]:
    st.subheader("📦 Archivage & Nettoyage Cloud")
    st.write("Cet outil permet de déplacer les données anciennes vers un **nouveau fichier Google Sheets** séparé pour garder la base principale légère et rapide.")
    
    col_arch1, col_arch2 = st.columns(2)
    module_to_archive = col_arch1.selectbox("Sélectionner le module à archiver", ["Logs", "Recouvrement", "Pointages", "Saisie_Inventaire"])
    
    # Paramètres par défaut selon module
    fallback_map = {
        "Logs": "data/db_logs.csv",
        "Recouvrement": "data_recouvrement.csv",
        "Pointages": "data/db_pointages.csv",
        "Saisie_Inventaire": "data_inventaire/saisie.csv"
    }
    
    archive_name = col_arch2.text_input("Nom du nouveau fichier archive", value=f"Archive_{module_to_archive}_{datetime.now().strftime('%m_%Y')}")
    
    if st.button("🚀 Créer l'archive et Vider la base actuelle", type="primary", use_container_width=True):
        from utils_gsheets import create_archive_spreadsheet
        
        # 1. Charger les données actuelles
        df_to_archive = load_gs_data(module_to_archive, fallback_map[module_to_archive], [])
        
        if not df_to_archive.empty:
            # 2. Créer le nouveau fichier
            archive_url = create_archive_spreadsheet(archive_name, df_to_archive)
            
            if archive_url:
                st.success(f"✅ Nouveau fichier Sheets créé avec succès !")
                st.markdown(f"🔗 [Cliquez ici pour ouvrir l'archive : {archive_name}]({archive_url})")
                
                # 3. Vider la base actuelle (On garde les colonnes)
                empty_df = pd.DataFrame(columns=df_to_archive.columns)
                save_gs_data(empty_df, module_to_archive, fallback_map[module_to_archive])
                
                st.warning("⚠️ La base actuelle a été vidée pour optimiser les performances.")
                log_action(st.session_state.current_user['username'], f"Archivage Cloud : {module_to_archive} -> {archive_name}", "Admin Centrale")
                st.cache_data.clear()
        else:
            st.warning("La base sélectionnée est déjà vide.")

# =============================================================================
# ONGLET 5 : GESTION DES THÈMES
# =============================================================================
with tabs[5]:
    st.subheader("🎨 Gestion des Thèmes Visuels")
    st.write("Activez ou désactivez les thèmes, affectez-les à vos utilisateurs, et importez votre dashboard premium personnalisé.")

    # Injecter le CSS de la page d'admin des thèmes
    st.markdown("""
    <style>
    .theme-card {
        background: linear-gradient(135deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02));
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 16px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
    }
    .theme-card:hover {
        border-color: rgba(79,142,247,0.5);
        box-shadow: 0 4px 20px rgba(79,142,247,0.15);
    }
    .theme-preview-dot {
        width: 48px;
        height: 48px;
        border-radius: 50%;
        display: inline-block;
        border: 3px solid rgba(255,255,255,0.2);
        flex-shrink: 0;
    }
    .badge-active {
        background: #10b981;
        color: white;
        border-radius: 20px;
        padding: 2px 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-inactive {
        background: #6b7280;
        color: white;
        border-radius: 20px;
        padding: 2px 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .drop-zone {
        border: 2px dashed rgba(79,142,247,0.5);
        border-radius: 16px;
        padding: 2rem;
        text-align: center;
        background: linear-gradient(135deg, rgba(79,142,247,0.05), rgba(139,92,246,0.05));
        transition: all 0.3s ease;
    }
    .drop-zone:hover {
        border-color: rgba(79,142,247,0.9);
        background: rgba(79,142,247,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

    themes_data = load_themes_db()
    all_themes = themes_data.get("themes", [])
    user_assignments = themes_data.get("user_theme_assignments", {})

    # --- SECTION 1 : ACTIVER / DÉSACTIVER LES THÈMES ---
    st.markdown("### 🎛️ Catalogue des Thèmes")
    st.caption("Activez les thèmes disponibles pour vos utilisateurs.")

    cols_themes = st.columns(min(3, len(all_themes)) if all_themes else 1)
    theme_changed = False

    for idx, theme in enumerate(all_themes):
        col = cols_themes[idx % 3]
        with col:
            is_active = theme.get("active", False)
            badge = "<span class='badge-active'>✅ Actif</span>" if is_active else "<span class='badge-inactive'>⏸ Inactif</span>"

            st.markdown(f"""
            <div class='theme-card'>
                <div style='display:flex; align-items:center; gap:12px; margin-bottom:8px;'>
                    <div class='theme-preview-dot' style='background:{theme.get('preview_color','#333')};'></div>
                    <div>
                        <strong style='font-size:1rem;'>{theme.get('name','Thème')}</strong><br>
                        {badge}
                    </div>
                </div>
                <p style='font-size:0.8rem; opacity:0.7; margin:0;'>{theme.get('description','')}</p>
                <div style='margin-top:8px;'>
                    <span style='display:inline-block; width:16px; height:16px; border-radius:50%; background:{theme.get('accent_color','#fff')}; border:2px solid rgba(255,255,255,0.3); vertical-align:middle;'></span>
                    <span style='font-size:0.75rem; opacity:0.6;'> Couleur accent</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            btn_label = "⏸ Désactiver" if is_active else "▶️ Activer"
            btn_type = "secondary" if is_active else "primary"
            if st.button(btn_label, key=f"toggle_theme_{theme['id']}", use_container_width=True, type=btn_type):
                themes_data = toggle_theme_active(theme["id"], themes_data)
                save_themes_db(themes_data)
                action_txt = "Désactivé" if is_active else "Activé"
                st.success(f"{action_txt} le thème **{theme['name']}**")
                log_action(st.session_state.current_user['username'], f"Thème {action_txt}: {theme['name']}", "Admin Thèmes")
                theme_changed = True

    if theme_changed:
        st.rerun()

    st.divider()

    # --- SECTION 2 : AFFECTER LES THÈMES AUX UTILISATEURS ---
    st.markdown("### 👥 Affectation des Thèmes aux Utilisateurs")
    st.caption("Choisissez un thème personnalisé pour chaque utilisateur. Sans affectation, l'utilisateur voit le thème par défaut.")

    # Charger la liste des utilisateurs
    from utils_gsheets import DB_USERS_WORKSHEET, DB_USERS_FALLBACK
    df_users = load_gs_data(DB_USERS_WORKSHEET, DB_USERS_FALLBACK, USER_COLUMNS)

    active_themes = get_active_themes(themes_data)
    theme_options = {t["id"]: t["name"] for t in active_themes}
    theme_options_list = ["— Défaut (aucun) —"] + list(theme_options.values())
    theme_ids_list = [None] + list(theme_options.keys())

    if df_users.empty:
        st.info("Aucun utilisateur trouvé. Vérifiez la connexion à la base utilisateurs.")
    elif not active_themes:
        st.warning("⚠️ Aucun thème actif. Activez au moins un thème ci-dessus pour pouvoir l'affecter.")
    else:
        assign_changed = False

        # En-têtes du tableau d'affectation
        hcols = st.columns([2, 2, 2, 3, 2])
        hcols[0].markdown("**Utilisateur**")
        hcols[1].markdown("**Nom**")
        hcols[2].markdown("**Rôle**")
        hcols[3].markdown("**Thème affecté**")
        hcols[4].markdown("**Action**")
        st.markdown("<hr style='margin:4px 0;'>", unsafe_allow_html=True)

        for _, urow in df_users.iterrows():
            username = str(urow.get("username", ""))
            if not username:
                continue
            nom_complet = f"{str(urow.get('prenom',''))} {str(urow.get('nom',''))}".strip()
            role_user = str(urow.get("role", ""))
            current_theme_id = user_assignments.get(username)
            current_theme_name = theme_options.get(current_theme_id, "— Défaut —")

            ucols = st.columns([2, 2, 2, 3, 2])
            ucols[0].write(f"👤 `{username}`")
            ucols[1].write(nom_complet or "—")
            ucols[2].write(role_user)

            # Sélecteur de thème
            default_idx = theme_ids_list.index(current_theme_id) if current_theme_id in theme_ids_list else 0
            selected_label = ucols[3].selectbox(
                "Thème",
                options=theme_options_list,
                index=default_idx,
                key=f"theme_sel_{username}",
                label_visibility="collapsed"
            )

            selected_idx = theme_options_list.index(selected_label)
            selected_theme_id = theme_ids_list[selected_idx]

            if ucols[4].button("💾 Appliquer", key=f"apply_theme_{username}", use_container_width=True):
                if selected_theme_id is None:
                    themes_data = remove_user_theme(username, themes_data)
                    msg = f"Thème par défaut restauré pour **{username}**"
                else:
                    themes_data = set_user_theme(username, selected_theme_id, themes_data)
                    msg = f"Thème **{theme_options[selected_theme_id]}** affecté à **{username}**"
                save_themes_db(themes_data)
                log_action(st.session_state.current_user['username'], msg, "Admin Thèmes")
                st.success(f"✅ {msg}")
                assign_changed = True

        if assign_changed:
            st.rerun()

        # Résumé des affectations actuelles
        st.divider()
        st.markdown("#### 📋 Résumé des Affectations")
        if user_assignments:
            rows_summary = []
            for uname, tid in user_assignments.items():
                tname = theme_options.get(tid, f"(id: {tid})")
                rows_summary.append({"Utilisateur": uname, "Thème": tname})
            st.dataframe(pd.DataFrame(rows_summary), use_container_width=True, hide_index=True)
        else:
            st.info("Aucune affectation individuelle. Tous les utilisateurs utilisent le thème par défaut.")

    st.divider()

    # --- SECTION 3 : DRAG & DROP — DASHBOARD PREMIUM HTML ---
    st.markdown("### 💎 Dashboard Premium — Import du fichier HTML")
    st.caption("Déposez le fichier HTML de votre dashboard premium. Il sera utilisé dans le module **Tableau Premium**.")

    st.markdown("""
    <div class='drop-zone'>
        <div style='font-size:2.5rem;'>📂</div>
        <div style='font-size:1.1rem; font-weight:600; margin:0.5rem 0;'>Glissez et déposez votre fichier HTML ici</div>
        <div style='font-size:0.85rem; opacity:0.6;'>Format accepté : .html · Taille max recommandée : 5 Mo</div>
    </div>
    """, unsafe_allow_html=True)

    # Vérifier si un fichier premium existe déjà
    premium_path_default = os.path.join(os.getcwd(), "assets", "dashboard_premium.html")
    premium_path_desktop = r"C:\Users\DARPHARM DEPOT 2\Desktop\DARNA_integrated.html"

    existing_path = None
    if os.path.exists(premium_path_default):
        existing_path = premium_path_default
    elif os.path.exists(premium_path_desktop):
        existing_path = premium_path_desktop

    if existing_path:
        fsize = os.path.getsize(existing_path) / 1024
        fmod = datetime.fromtimestamp(os.path.getmtime(existing_path)).strftime("%d/%m/%Y %H:%M")
        st.success(f"✅ Fichier actuel : `{os.path.basename(existing_path)}` — {fsize:.1f} Ko — Modifié le {fmod}")
    else:
        st.warning("⚠️ Aucun fichier HTML premium trouvé. Veuillez en importer un ci-dessous.")

    uploaded_html = st.file_uploader(
        "Sélectionner le fichier HTML du dashboard premium",
        type=["html"],
        key="upload_premium_html",
        help="Le fichier sera sauvegardé dans le dossier assets/ du projet et utilisé automatiquement par le module Tableau Premium."
    )

    if uploaded_html is not None:
        col_prev, col_btn = st.columns([3, 1])
        col_prev.info(f"📄 Fichier sélectionné : **{uploaded_html.name}** — {uploaded_html.size / 1024:.1f} Ko")

        if col_btn.button("📥 Importer", type="primary", use_container_width=True, key="btn_import_html"):
            file_bytes = uploaded_html.read()
            dest = save_premium_dashboard_html(file_bytes, filename="dashboard_premium.html")
            st.success(f"✅ Dashboard premium importé avec succès !")
            st.code(dest, language="text")
            log_action(
                st.session_state.current_user['username'],
                f"Import Dashboard Premium HTML : {uploaded_html.name}",
                "Admin Thèmes"
            )
            st.balloons()
            st.rerun()

    # Aperçu rapide du fichier HTML importé
    if existing_path and st.checkbox("👁️ Prévisualiser le dashboard premium", key="preview_premium_html"):
        try:
            with open(existing_path, "r", encoding="utf-8") as f:
                html_preview = f.read()
            import streamlit.components.v1 as components
            components.html(html_preview, height=600, scrolling=True)
        except Exception as e:
            st.error(f"Impossible de prévisualiser : {e}")

# =============================================================================
# ONGLET 6 : MAINTENANCE & MODE HORS-LIGNE
# =============================================================================
with tabs[6]:
    st.subheader("⚙️ Maintenance Système & Connectivité")
    st.write("Gérez le comportement de la plateforme en cas de coupure internet ou pour une utilisation sur réseau local (Intranet).")
    
    # --- MODE HORS-LIGNE ---
    col_off1, col_off2 = st.columns([1, 1])
    
    with col_off1:
        st.markdown("### 🔌 Mode Hors-Ligne (Local Only)")
        st.info("Lorsqu'activé, la plateforme ignore Google Sheets et utilise exclusivement les fichiers CSV locaux. Idéal pour les dépôts sans internet.")
        
        is_offline = st.toggle("Activer le Mode Hors-Ligne Forcé", value=st.session_state.get("offline_mode", False))
        if is_offline != st.session_state.get("offline_mode", False):
            st.session_state.offline_mode = is_offline
            st.cache_data.clear()
            st.success(f"Mode {'HORS-LIGNE' if is_offline else 'CLOUD'} activé !")
            st.rerun()

    with col_off2:
        st.markdown("### 📡 État de la Synchronisation")
        current_mode = "Hors-Ligne (Local)" if st.session_state.get("offline_mode", False) else "Connecté (Cloud)"
        status_color = "🔴" if st.session_state.get("offline_mode", False) else "🟢"
        
        st.write(f"**Statut actuel :** {status_color} {current_mode}")
        
        if st.button("🔄 Forcer la synchronisation vers le Cloud", type="primary", use_container_width=True):
            if st.session_state.get("offline_mode", False):
                st.error("Désactivez le mode hors-ligne pour synchroniser.")
            else:
                with st.spinner("Synchronisation en cours..."):
                    # On vide le cache pour forcer la lecture/écriture
                    st.cache_data.clear()
                    st.success("Synchronisation terminée ! Les données locales ont été fusionnées avec le Cloud.")
                    log_action(st.session_state.current_user['username'], "Synchronisation Cloud Manuelle", "Maintenance")

    st.divider()
    
    # --- DIAGNOSTIC ---
    st.markdown("### 🔍 Outils de Diagnostic")
    c1, c2, c3 = st.columns(3)
    
    if c1.button("🗑️ Vider le Cache Système", use_container_width=True):
        st.cache_data.clear()
        st.success("Cache vidé !")
        
    if c2.button("📊 Vérifier Fichiers Locaux", use_container_width=True):
        local_files = [f for f in os.listdir('.') if f.endswith('.csv') or f.endswith('.json')]
        st.write(f"Nombre de bases locales détectées : {len(local_files)}")
        st.json(local_files)
        
    if c3.button("📂 Ouvrir dossier images", use_container_width=True):
        st.info(f"Dossier images : {os.path.abspath('images_stock')}")
