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
        # Identification produit
        'num_produit':        ['n°produit'],
        'produit':            ['produit', 'article', 'désignation', 'designation'],
        'code':               ['code'],
        'id_med':             ['id méd.', 'id med'],
        'dci':                ['d.c.i', 'dci'],
        'dosage':             ['dosage'],
        'forme':              ['forme'],
        'categorie':          ['catégorie', 'categorie'],
        'gamme':              ['gamme'],
        'classe':             ['classe'],
        'source':             ['source'],
        'type_produit':       ['type produit'],
        'type_lot':           ['type lot'],
        'code_barre_lot':     ['code barre lot'],
        'code_cnas':          ['code cnas'],
        # Stock et localisation
        'depot':              ['dépôt', 'depot', 'id depot'],
        'lot':                ['n°lot', 'lot', 'batch', 'nlot'],
        'qte_logi':           ['quantité dépôt', 'quantité depot', 'qte.globale'],
        'qte_bloquee':        ['qte bloquée', 'qte bloquee'],
        'reserve':            ['réserve', 'reserve'],
        'quarantaine':        ['quarantaine'],
        'colissage':          ['colis', 'nbr colis'],
        'vrac':               ['vrac'],
        'zone':               ['zone produit', 'zone'],
        'emplacement':        ['emplac.', 'emplacement'],
        'emplacement_reserve':['emplacement réserve', 'emplacement reserve'],
        'emplacement_2':      ['emplacement 2'],
        'niveau_blocage':     ['niveau blocage'],
        'motif_blocage':      ['motif de blocage', 'motif blocage'],
        'age':                ['age'],
        'perime':             ['périmé', 'perime'],
        # Dates
        'ddp':                ['ddp'],
        'ddf':                ['ddf'],
        'date_creation':      ['date création', 'date creation'],
        'arrivage':           ['arrivage'],
        'annee':              ['année', 'annee'],
        # Personnel
        'cree_par':           ['créer par', 'creer par'],
        # Fournisseur / labo
        'laboratoire':        ['laboratoire', 'labo'],
        'fournisseur':        ['fournisseur', 'fourn'],
        # Prix
        'ppa':                ['ppa', 'prix public'],
        'shp':                ['shp'],
        'prix_ph':            ['prix ph'],
        'prix_gr':            ['prix gr'],
        'prix_achat':         ["prix d'achat", 'prix achat'],
        'prix_achat_remise':  ['prix achat remisé', 'prix achat remise'],
        'prix_vente_remise':  ['prix vente remisé', 'prix vente remise'],
        'valeur_achat':       ['valeur achat'],
        'valeur_vente':       ['valeur vente'],
        'cout_revient':       ['cout de revient'],
        'valeur_revient':     ['valeur de revient'],
        # Taxes et taux
        'tva':                ['tva'],
        'tx_achat':           ['tx achat'],
        'tx_vente_1':         ['tx vente 1'],
        'tx_vente_2':         ['tx vente 2'],
        'tx_vente_3':         ['tx vente3'],
        'tx_vente_4':         ['tx vente 4'],
        'tx_revient':         ['tx revient'],
        # Marges et remises
        'marge':              ['marge'],
        'marge_ph':           ['marge ph.', 'marge ph'],
        'marge_2':            ['marge 2'],
        'demi_marge':         ['demi-marge'],
        'palier':             ['palier'],
        'remise_ug':          ['remise ug'],
        'rm_sup':             ['r.m.sup.', 'rm sup'],
        'note_credit':        ['note crédit', 'note credit'],
        'ristourne_achat':    ['ristourne achat'],
        'ristourne':          ['ristourne'],
        'remise_achat':       ['remise achat'],
        'quota':              ['quota'],
        # Flags commerciaux
        'frigo':              ['frigo.', 'frigo'],
        'psycho':             ['psycho.', 'psycho'],
        'chers':              ['chers'],
        'rotation':           ['rotation'],
        'ref_facture':        ['réf facture', 'ref facture'],
        'site':               ['site'],
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
            new_cols[col] = col  # On garde les noms de colonnes originaux
    df = df.rename(columns=new_cols)

    # --- DETECTION AUTOMATIQUE DU DEPOT SECONDAIRE (Périmés, Abimés, SV...) ---
    # Dans DarPharm, le dépôt secondaire (ex: ID > 1, ou nommé "SEC", "NON CONFORME") 
    # contient les produits périmés, abimés ou sans valeur.
    if 'depot' in df.columns:
        depot_vals = df['depot'].astype(str).str.strip().str.upper()
        
        # Règles de détection du dépôt secondaire
        is_secondaire = (
            depot_vals.isin(['2', '02', 'SEC', 'SECONDAIRE', 'NON CONFORME', 'NC', 'SV']) |
            depot_vals.str.contains('SEC|PERIMES|ABIMES|NON.CONF|S\.V\.|HORS', na=False, regex=True)
        )
        
        # Créer la colonne statut_stock si elle n'existe pas
        if 'statut_stock' not in df.columns:
            df['statut_stock'] = 'Conforme'
        
        # Affiner avec les colonnes existantes
        if 'perime' in df.columns:
            df.loc[df['perime'].astype(str).str.upper().isin(['OUI', 'TRUE', 'VRAI', '1', 'X']), 'statut_stock'] = 'Périmé'
        if 'quarantaine' in df.columns:
            df.loc[df['quarantaine'].astype(str).str.upper().isin(['OUI', 'TRUE', 'VRAI', '1', 'X']), 'statut_stock'] = 'Quarantaine'
        
        # Le dépôt secondaire prend le dessus si rien d'autre n'est précisé
        df.loc[is_secondaire & (df['statut_stock'] == 'Conforme'), 'statut_stock'] = 'Non Conforme (Dépôt Sec.)'
        
        # Créer une colonne is_secondaire pour filtrage rapide
        df['is_depot_secondaire'] = is_secondaire
    
    return df

def clean_sales_cols(df):
    mapping = {
        'designation': ['designation', 'produit', 'article', 'libelle', 'désignation'],
        'quantite': ['quantite', 'qte', 'volume', 'nombre', 'quantité'],
        'prix_vente': ['h.t', 'ht', 'prix vente', 'prix_v', 'ca', 'montant', 'total ht', 't.t.c', 'ttc'],
        'marge': ['marge', 'profit', 'rentabilite', 'benefice', 'gain'],
        'date': ['date', 'jour', 'facturé le'],
        'heure': ['heure', 'time', 'moment'],
        'colis': ['colis', 'nb colis', 'colissage', 'paquets'],
        'client': ['client'],
        'reference': ['référence', 'reference', 'ref'],
        'remise': ['remise'],
        'tva': ['t.v.a', 'tva'],
        'timbre': ['timbre'],
        'montant_regle': ['montant réglé', 'montant regle'],
        'commercial': ['commercial', 'vendeur', 'rep', 'délégué'],
        'superviseur': ['superviseur'],
        'offre_lab': ['offre lab.'],
        'annuler': ['annuler'],
        'cash': ['cash'],
        'tx_qt': ['tx qt%'],
        'part': ['part'],
        'mg': ['mg'],
        'cat_client': ['cat.client'],
        'n_ordre': ['n° ordre', 'n ordre']
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
            new_cols[col] = col
    return df.rename(columns=new_cols)

def clean_reclam_cols(df):
    mapping = {
        'client': ['client', 'pharmacie', 'destinataire'],
        'reference': ['référence', 'reference', 'ref', 'bon', 'commande', 'document'],
        'type': ['type'],
        'date': ['date'],
        'code_client': ['code client'],
        'region': ['région', 'region'],
        'produit': ['produit', 'designation', 'article'],
        'qte_reclam': ['qte réclam.', 'qte reclam', 'quantité'],
        'qte_fact': ['qte fact.', 'qte fact'],
        'motif': ['motif', 'raison'],
        'statut': ['statut', 'etat'],
        'commercial': ['commercial', 'vendeur'],
        'date_retour': ['date retour'],
        'reponse': ['reponse', 'réponse'],
        'emp_produit': ['emp.produit', 'emp produit'],
        'responsable': ['responsable'],
        'avis_dt': ['avis dt'],
        'verifier_par': ['vérifier par', 'verifier par'],
        'envoyer_par': ['envoyer par'],
        'recu_par': ['reçu par', 'recu par'],
        'date_verification': ['date vérification', 'date verification'],
        'date_reception': ['date réception', 'date reception'],
        'nbr_jours': ['nbr jours'],
        'offre': ['offre'],
        'delai_reclam': ['délai réclam.', 'délai réclam', 'delai reclam']
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
            new_cols[col] = col
    return df.rename(columns=new_cols)

def clean_recouvrement_logipharm_cols(df):
    """Mappe les colonnes Logipharm vers le format attendu par 4_recouvrement.py."""
    mapping = {
        'Client':          ['client'],
        'Facture':         ['référence', 'reference', 'ref', 'b.l', 'n° ordre', 'n°ordre'],
        'Date':            ['date', 'date création', 'date creation'],
        'Montant Initial': ['h.t', 'ht', 't.t.c', 'ttc', 'montant initial'],
        'Montant Réglé':   ['montant réglé', 'montant regle'],
        'Reste à payer':   ['reste à payer', 'reste a payer'],
        'Mode Paiement':   ['mode paiement', 'cash'],
        'Région':          ['région', 'region', 'wilaya', 'zone', 'ville'],
        'Statut':          ['statut', 'clôture', 'cloture'],
        'Commentaires':    ['remarque', 'observation', 'échéance', 'echeance'],
    }
    new_cols = {}
    mapped_targets = set()
    for col in df.columns:
        col_str = str(col).lower().strip()
        matched = False
        for target_col, alts in mapping.items():
            if col_str in alts and target_col not in mapped_targets:
                new_cols[col] = target_col
                mapped_targets.add(target_col)
                matched = True
                break
        if not matched:
            new_cols[col] = f"_logi_{col}"
    return df.rename(columns=new_cols)

def clean_expedition_logipharm_cols(df):
    """Mappe les colonnes Logipharm vers le format expédition/pointage."""
    mapping = {
        'client':         ['client'],
        'reference':      ['référence', 'reference', 'ref', 'b.l', 'n° ordre'],
        'date':           ['date', 'date création'],
        'region':         ['région', 'region', 'wilaya', 'zone'],
        'statut':         ['statut', 'préparé', 'prepare'],
        'preparateur':    ['préparateur', 'preparateur'],
        'verificateur':   ['vérificateur', 'verificateur'],
        'superviseur':    ['superviseur'],
        'colis':          ['colis', 'nbr colis'],
        'annuler':        ['annuler'],
        'depot':          ['dépôt', 'depot'],
    }
    new_cols = {}
    mapped_targets = set()
    for col in df.columns:
        col_str = str(col).lower().strip()
        matched = False
        for target_col, alts in mapping.items():
            if col_str in alts and target_col not in mapped_targets:
                new_cols[col] = target_col
                mapped_targets.add(target_col)
                matched = True
                break
        if not matched:
            new_cols[col] = col
    return df.rename(columns=new_cols)

def parse_numeric_series(series):
    """Nettoie et convertit une série en valeurs numériques en éliminant les espaces insécables (alt+0160), espaces normaux et virgules."""
    if series.empty:
        return series
    
    def clean_val(val):
        if pd.isna(val):
            return "0.0"
        s = str(val).strip()
        # Supprimer séquentiellement tous les types d'espaces problématiques
        for space_char in [" ", "\xa0", "\u202f", "\u205f", "\u2007", "\t", "\n", "\r"]:
            s = s.replace(space_char, "")
        s = s.replace(",", ".")
        return s
        
    cleaned = series.apply(clean_val)
    return pd.to_numeric(cleaned, errors='coerce').fillna(0.0)

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
tabs = st.tabs(["📤 Importateur Universel", "👥 Base Clients", "🚚 Livreurs", "🗺️ Secteurs Logistique", "📦 Archivage Cloud", "🎨 Gestion des Thèmes", "⚙️ Maintenance & Hors-Ligne", "🧹 Remise à Zéro"])

# ONGLET 0 : IMPORTATEUR UNIVERSEL (DRAG & DROP)
with tabs[0]:
    st.subheader("🚀 Importation Centralisée")
    st.info("Déposez un fichier Excel Logipharm. Le système détecte automatiquement le type : **Recouvrement**, **Ventes**, **Réclamations**, **Inventaire**, **Expédition**, **Clients**, etc.")
    
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
            # ── PRIORITÉ STRICTE : EXPÉDITION QUOTIDIENNE ──
            # Règle stricte : On ignore les 'Unnamed' et on vérifie la présence de colonnes clés
            cols_lower_valid = [c for c in cols_lower if not c.startswith("unnamed:")]
            if all(x in cols_lower_valid for x in ["n°bon", "livreur", "matricule", "total ttc"]):
                target = "Expedition_Logipharm"
                # Nettoyage automatique : suppression des colonnes non nommées faussant la structure
                df_up = df_up.loc[:, ~df_up.columns.str.lower().str.startswith("unnamed:")]
                df_up = clean_expedition_logipharm_cols(df_up)

            # ── PRIORITÉ STRICTE 2 : COMMANDES ET VENTES GLOBALES ──
            req_cmd = ["client", "nbr ligne", "colis", "date", "région"]
            if not target and all(any(k in c for c in cols_lower_valid) for k in req_cmd) and any(x in cols_lower_valid for x in ["référence", "reference", "ref", "b.l"]):
                target = "Commandes & Recouvrement"
                # Nettoyage automatique
                df_up = df_up.loc[:, ~df_up.columns.str.lower().str.startswith("unnamed:")]
                
                # Préparation aux autres modules
                date_col = next((c for c in df_up.columns if str(c).strip().lower() == "date"), None)
                if date_col:
                    try:
                        temp_dt = pd.to_datetime(df_up[date_col], errors='coerce')
                        df_up['Heure_Rotation'] = temp_dt.dt.strftime('%H:%M:%S')
                        df_up['Rotation'] = temp_dt.apply(lambda x: 1 if pd.notna(x) and x.time() > pd.to_datetime('12:15:00').time() else 2)
                    except Exception:
                        pass
                
                colis_col = next((c for c in df_up.columns if str(c).strip().lower() == "colis"), None)
                ligne_col = next((c for c in df_up.columns if str(c).strip().lower() == "nbr ligne"), None)
                if colis_col and ligne_col:
                    df_up['Volume_Préparation'] = pd.to_numeric(df_up[colis_col], errors='coerce').fillna(0) + pd.to_numeric(df_up[ligne_col], errors='coerce').fillna(0)
                
                reg_col = next((c for c in df_up.columns if str(c).strip().lower() in ["région", "region", "wilaya"]), None)
                if reg_col:
                    df_up['Secteur'] = df_up[reg_col]

                # ── MOTEUR DE RECONNAISSANCE AUTOMATIQUE DES LIVREURS ──
                try:
                    df_exp = load_gs_data("Expedition_Logipharm", "data/db_expedition_logipharm.csv", None)
                    if not df_exp.empty:
                        col_liv = next((c for c in df_exp.columns if str(c).strip().lower() in ['livreur', 'preparateur']), None)
                        col_ref_exp = next((c for c in df_exp.columns if str(c).strip().lower() in ['référence', 'reference', 'ref', 'b.l', "n°bon", "bon"]), None)
                        col_reg_exp = next((c for c in df_exp.columns if str(c).strip().lower() in ['région', 'region', 'wilaya']), None)
                        
                        ref_col_cmd = next((c for c in df_up.columns if str(c).strip().lower() in ["référence", "reference", "ref", "b.l"]), None)
                        
                        if col_liv and col_ref_exp and ref_col_cmd:
                            # 1. Extraction de la flotte (Mapping exact)
                            df_exp['_join_ref'] = df_exp[col_ref_exp].astype(str).str.strip().str.upper()
                            df_up['_join_ref'] = df_up[ref_col_cmd].astype(str).str.strip().str.upper()
                            
                            mapping_livreurs = df_exp.set_index('_join_ref')[col_liv].to_dict()
                            
                            # 2. Injection Automatique
                            df_up['_logi_Livreur_Attribue'] = df_up['_join_ref'].map(mapping_livreurs)
                            
                            # 3. Logique Géographique (Régions vs Livreurs)
                            if reg_col and col_reg_exp:
                                df_exp['_join_reg'] = df_exp[col_reg_exp].astype(str).str.strip().str.upper()
                                df_up['_join_reg'] = df_up[reg_col].astype(str).str.strip().str.upper()
                                
                                # Le livreur le plus fréquent par région
                                freq_liv_by_reg = df_exp.groupby('_join_reg')[col_liv].agg(lambda x: x.mode()[0] if not x.mode().empty else None).to_dict()
                                
                                def suggest_driver(row):
                                    val = row.get('_logi_Livreur_Attribue')
                                    if pd.isna(val) or str(val).strip() == "":
                                        r = row.get('_join_reg')
                                        if r in freq_liv_by_reg and freq_liv_by_reg[r]:
                                            return f"Livreur habituel détecté : {freq_liv_by_reg[r]}"
                                    return val
                                    
                                df_up['_logi_Livreur_Attribue'] = df_up.apply(suggest_driver, axis=1)
                                df_up = df_up.drop(columns=['_join_reg'])
                                
                            df_up = df_up.drop(columns=['_join_ref'])
                except Exception as e:
                    pass

            # ── PRIORITÉ 0 : RÉCLAMATIONS LOGIPHARM (préfixe RC dans la colonne Référence) ──
            # Les fichiers de réclamations Logipharm ont une colonne 'Référence' dont les valeurs
            # commencent par 'RC' (ex: 26/RC0000000144). Cette règle est prioritaire sur tout.
            if not target:
                _ref_col = None
                for c in df_up.columns:
                    if str(c).strip().lower() in ["référence", "reference", "réf.", "ref.", "ref"]:
                        _ref_col = c
                        break
                if _ref_col is not None:
                    _ref_sample = df_up[_ref_col].dropna().astype(str).str.upper().str.strip()
                    _rc_count = _ref_sample.str.contains(r'/RC\d|^RC\d', regex=True, na=False).sum()
                    if _rc_count > 0:
                        target = "Analyse_Reclamations"
                        # Renommer les colonnes Unnamed en noms sémantiques selon la structure Logipharm
                        logi_reclam_rename = {}
                        unnamed_cols = [c for c in df_up.columns if str(c).startswith("Unnamed:")]
                        semantic_names = ["Valide", "Imprime", "Expedie", "Cloture"]
                        for i, uc in enumerate(unnamed_cols[:4]):
                            logi_reclam_rename[uc] = semantic_names[i]
                        if logi_reclam_rename:
                            df_up = df_up.rename(columns=logi_reclam_rename)
                        df_up = clean_reclam_cols(df_up)

            # ── PRIORITÉ 1 : RECOUVREMENT (champs financiers client) ──
            _rec_keys = ["reste à payer", "reste a payer", "montant réglé", "montant regle"]
            if not target and any(x in cols_lower for x in _rec_keys) and "client" in cols_lower:
                target = "Recouvrement_Logipharm"
                df_up = clean_recouvrement_logipharm_cols(df_up)

            # ── PRIORITÉ 2 : RÉCLAMATIONS (colonnes nominatives classiques) ──
            elif not target and any(x in cols_lower for x in ["réclam.", "reclam.", "imprime réclam", "qte réclam.", "qte reclam."]):
                target = "Analyse_Reclamations"
                df_up = clean_reclam_cols(df_up)

            # ── PRIORITÉ 3 : ANALYSE VENTES (h.t/marge sans reste à payer) ──
            elif not target and any(x in cols_lower for x in ["h.t", "prix_vente", "total ht", "marge ph.", "tx qt%", "offre lab."]):
                target = "Analyse_Ventes_Perf"
                df_up = clean_sales_cols(df_up)

            # ── PRIORITÉ 4 : INVENTAIRE (dépôt/lots) ──
            elif not target and any(x in cols_lower for x in ["dépôt", "depot", "quantité dépôt", "quantité depot", "qte.globale", "n°lot", "zone produit"]):
                target = "Master_Inventaire_Zone"
                df_up = clean_inventory_cols(df_up)

            # ── PRIORITÉ 5 : EXPÉDITION / POINTAGE ──
            elif not target and any(x in cols_lower for x in ["préparateur", "preparateur", "vérificateur", "verificateur"]) and "client" in cols_lower:
                target = "Expedition_Logipharm"
                df_up = clean_expedition_logipharm_cols(df_up)

            # ── PRIORITÉ 6 : UTILISATEURS ──
            elif not target and "username" in cols_lower:
                target = "Utilisateurs"
                mapping = {c: "username" for c in cols if c.lower() == "username"}
                mapping.update({c: "password" for c in cols if c.lower() in ["password", "mot de passe", "pwd"]})
                mapping.update({c: "nom" for c in cols if c.lower() == "nom"})
                mapping.update({c: "prenom" for c in cols if c.lower() in ["prenom", "prénom"]})
                mapping.update({c: "role" for c in cols if c.lower() in ["role", "rôle"]})
                mapping.update({c: "zone" for c in cols if c.lower() == "zone"})
                mapping.update({c: "pages" for c in cols if c.lower() == "pages"})

            # ── PRIORITÉ 7 : LIVREURS ──
            elif not target and ("prenom" in cols_lower or "prénom" in cols_lower):
                target = "Livreurs"
                mapping = {c: "Prénom" for c in cols if c.lower() in ["prenom","prénom"]}
                mapping.update({c: "Nom" for c in cols if c.lower() == "nom"})
                mapping.update({c: "Secteur" for c in cols if c.lower() == "secteur"})
                mapping.update({c: "Téléphone" for c in cols if c.lower() in ["téléphone","telephone","tel"]})

            # ── PRIORITÉ 8 : SECTEURS ──
            elif not target and "ville" in cols_lower:
                target = "Secteurs"
                mapping = {c: "Client" for c in cols if c.lower() in ["client","raison sociale","nom client"]}
                mapping.update({c: "Ville" for c in cols if c.lower() == "ville"})
                mapping.update({c: "Secteur" for c in cols if c.lower() == "secteur"})
                mapping.update({c: "Tel" for c in cols if c.lower() in ["tel","téléphone","telephone"]})

            # ── PRIORITÉ 9 : BASE CLIENTS ──
            elif not target and any(c.lower() in ["raison sociale","nom client","nom", "client", "pharmacie"] for c in cols):
                target = "Base_Clients"
                df_up = clean_client_cols(df_up)
                if 'Nom_Pharmacie' not in df_up.columns:
                    df_up['Nom_Pharmacie'] = df_up['ID'].astype(str) if 'ID' in df_up.columns else "Client_Inconnu"
        
        elif not target:
            # Si le fichier était un Excel mais sans colonnes reconnues
            pass
        
        if not df_up.empty:
            # Sécurité contre les colonnes dupliquées (ex: 2 colonnes qui pointent vers "marge")
            cols = pd.Series(df_up.columns)
            for dup in cols[cols.duplicated()].unique():
                cols[cols[cols == dup].index.values.tolist()] = [f"{dup}_{i}" if i != 0 else dup for i in range(sum(cols == dup))]
            df_up.columns = cols
            
            st.write("**Aperçu des données :**")
            
            # 4. VISUEL DANS L'ADMIN CENTRALE
            if target == "Commandes & Recouvrement" and '_logi_Livreur_Attribue' in df_up.columns:
                st.success("🤖 **Moteur IA : Affectation automatique des livreurs réussie !**")
                colis_c = next((c for c in df_up.columns if str(c).strip().lower() == "colis"), None)
                reg_c = next((c for c in df_up.columns if str(c).strip().lower() in ["région", "region", "wilaya"]), None)
                
                df_up['_temp_colis'] = pd.to_numeric(df_up[colis_c], errors='coerce').fillna(0) if colis_c else 1
                    
                recap_df = df_up.groupby('_logi_Livreur_Attribue').agg(
                    Colis_Total=('_temp_colis', 'sum'),
                    Régions_Couvertes=(reg_c, 'nunique') if reg_c else ('_logi_Livreur_Attribue', 'count')
                ).reset_index()
                
                recap_df.rename(columns={
                    '_logi_Livreur_Attribue': 'Nom du Livreur', 
                    'Colis_Total': 'Nombre de Colis Total'
                }, inplace=True)
                
                st.dataframe(recap_df, use_container_width=True, hide_index=True)
                df_up = df_up.drop(columns=['_temp_colis'], errors='ignore')
                st.markdown("---")

            try:
                st.dataframe(df_up.head(5).astype(str), use_container_width=True)
            except Exception:
                st.table(df_up.head(5).astype(str))
        
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
            elif target == "Commandes & Recouvrement":
                db_path, db_cols = "data/db_commandes_globales.csv", df_up.columns.tolist()
                key = next((c for c in df_up.columns if str(c).strip().lower() in ["référence", "reference", "ref"]), df_up.columns[0])
            elif target == "Analyse_Ventes_Perf":
                db_path, db_cols, key = "data/db_ventes_performance.csv", df_up.columns.tolist(), "reference"
            elif target == "Analyse_Reclamations":
                db_path, db_cols, key = "data/db_reclamations_analyse.csv", df_up.columns.tolist(), "reference"
            elif target == "Recouvrement_Logipharm":
                COLS_REC = ["Client", "Facture", "Date", "Montant Initial", "Montant Réglé", "Reste à payer", "Mode Paiement", "Livreur", "Région", "Statut", "Commentaires"]
                db_path, db_cols, key = "data_recouvrement.csv", COLS_REC, "Facture"
            elif target == "Expedition_Logipharm":
                db_path, db_cols, key = "data/db_expedition_logipharm.csv", df_up.columns.tolist(), "reference"
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
                # Correction: load df_old for the target worksheet
                worksheet_name = target if target not in ["Recouvrement_Logipharm", "Expedition_Logipharm", "Commandes & Recouvrement"] else target.replace("_Logipharm", "").replace(" & ", "_")
                load_cols = None if target in ["Analyse_Reclamations", "Master_Inventaire_Zone", "Analyse_Ventes_Perf", "Expedition_Logipharm", "Commandes & Recouvrement"] else db_cols
                df_old = load_gs_data(worksheet_name, db_path, load_cols)
                
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
                
                if target == "Recouvrement_Logipharm":
                    # Compléter les colonnes manquantes
                    if "Facture" not in df_up.columns:
                        df_up["Facture"] = [f"LOGI_{i}" for i in range(len(df_up))]
                    if "Statut" not in df_up.columns:
                        df_up["Statut"] = "En attente"
                    if "Livreur" not in df_up.columns:
                        df_up["Livreur"] = "NON ASSIGNÉ"
                    if "Montant Initial" in df_up.columns:
                        df_up["Montant Initial"] = parse_numeric_series(df_up["Montant Initial"])
                    else:
                        df_up["Montant Initial"] = 0.0
                        
                    if "Montant Réglé" not in df_up.columns:
                        df_up["Montant Réglé"] = 0.0
                    else:
                        df_up["Montant Réglé"] = parse_numeric_series(df_up["Montant Réglé"])
                        
                    if "Reste à payer" not in df_up.columns:
                        df_up["Reste à payer"] = df_up["Montant Initial"] - df_up["Montant Réglé"]
                    else:
                        df_up["Reste à payer"] = parse_numeric_series(df_up["Reste à payer"])
                    if "Date" not in df_up.columns:
                        df_up["Date"] = str(datetime.now().date())
                    df_merged = pd.concat([df_old, df_up], ignore_index=True).drop_duplicates(subset=[key], keep='last')
                    st.session_state.pop("pending_rec", None)

                elif target == "Base_Clients":
                    df_merged = pd.concat([df_old, df_up], ignore_index=True).drop_duplicates(subset=[key], keep='last')
                    if 'Nom Client' not in df_merged.columns: df_merged['Nom Client'] = df_merged['Nom_Pharmacie']
                    if 'Région' not in df_merged.columns: df_merged['Région'] = df_merged['Region'].combine_first(df_merged['Wilaya'])
                    if 'Secteur' not in df_merged.columns: df_merged['Secteur'] = df_merged['Region']
                    if 'Téléphone' not in df_merged.columns: df_merged['Téléphone'] = df_merged['Telephone']

                elif target in ["Master_Inventaire_Zone", "Analyse_Ventes_Perf", "Analyse_Reclamations", "Expedition_Logipharm"]:
                    if target == "Analyse_Reclamations":
                        if not df_old.empty:
                            df_old = df_old.drop_duplicates(subset=["reference"])
                            df_up = df_up.drop_duplicates(subset=["reference"])
                            
                            # Assurer l'existence de motif et decision
                            if 'decision' not in df_old.columns:
                                df_old['decision'] = ""
                            if 'decision' not in df_up.columns:
                                df_up['decision'] = ""
                            if 'motif' not in df_old.columns:
                                df_old['motif'] = ""
                            if 'motif' not in df_up.columns:
                                df_up['motif'] = ""
                            
                            # Fusionner sur 'reference'
                            df_old_indexed = df_old.set_index("reference", drop=False)
                            df_up_indexed = df_up.set_index("reference", drop=False)
                            
                            common_refs = df_old_indexed.index.intersection(df_up_indexed.index)
                            for ref in common_refs:
                                old_row = df_old_indexed.loc[ref]
                                new_row = df_up_indexed.loc[ref]
                                
                                # Conserver la décision existante
                                dec_val = old_row.get("decision", "")
                                if pd.isna(dec_val) or str(dec_val).strip() == "":
                                    dec_val = new_row.get("decision", "")
                                
                                # Conserver le motif si le nouveau est vide
                                motif_val = new_row.get("motif", "")
                                if pd.isna(motif_val) or str(motif_val).strip() == "":
                                    motif_val = old_row.get("motif", "")
                                    if pd.isna(motif_val):
                                        motif_val = ""
                                        
                                df_up_indexed.loc[ref, "decision"] = dec_val
                                df_up_indexed.loc[ref, "motif"] = motif_val
                                
                            df_old_indexed = df_old_indexed.drop(common_refs)
                            df_old_indexed = pd.concat([df_old_indexed, df_up_indexed], ignore_index=False)
                                
                            df_merged = df_old_indexed.reset_index(drop=True)
                        else:
                            df_merged = df_up
                            if 'decision' not in df_merged.columns:
                                df_merged['decision'] = ""
                            if 'motif' not in df_merged.columns:
                                df_merged['motif'] = ""
                    else:
                        df_merged = df_up
                        
                    if target == "Master_Inventaire_Zone" and 'inv_work_df' in st.session_state:
                        del st.session_state.inv_work_df
                    if target == "Analyse_Ventes_Perf" and 'df_ventes_perf' in st.session_state:
                        del st.session_state.df_ventes_perf
                    if target == "Analyse_Reclamations" and 'df_reclam_analysed' in st.session_state:
                        del st.session_state.df_reclam_analysed
                else:
                    cols_to_keep = [c for c in db_cols if c in df_up.columns]
                    df_merged = pd.concat([df_old, df_up[cols_to_keep]], ignore_index=True).drop_duplicates(subset=[key])
                
                save_gs_data(df_merged, worksheet_name, db_path)
                st.success(f"✅ Migration réussie vers **{worksheet_name}** — {len(df_up)} lignes traitées.")
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
    col_name = 'Nom_Pharmacie' if 'Nom_Pharmacie' in df_clients.columns else 'Nom Client'
    if col_name in df_clients.columns:
        liste_clients_crm = sorted(df_clients[col_name].dropna().unique().tolist())
    else:
        liste_clients_crm = []
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
                        for c in ['Nom', 'Prénom', 'Téléphone', 'Secteur']:
                            if c not in df_liv.columns: df_liv[c] = ""
                            df_liv[c] = df_liv[c].astype(object)
                            
                        df_liv.loc[idx, 'Nom'] = str(e_nom).upper()
                        df_liv.loc[idx, 'Prénom'] = str(e_pre).capitalize()
                        df_liv.loc[idx, 'Téléphone'] = str(e_tel)
                        df_liv.loc[idx, 'Secteur'] = str(e_sec).upper()
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

# --- ONGLET 7 : REMISE À ZÉRO / SAUVEGARDE ---
with tabs[7]:
    st.subheader("🧹 Remise à Zéro & Sauvegarde de Sécurité")
    st.warning("⚠️ **ATTENTION** : Cet onglet permet d'archiver sur le Cloud et/ou de supprimer les données locales des modules. Utilisez cet outil avec extrême précaution !")

    # Définition des bases de données
    MODULES_DB = {
        "👥 Base Clients": {
            "worksheet": "Base_Clients",
            "path": DATA_CLIENTS,
            "columns": COLS_CLIENTS,
            "type": "csv"
        },
        "🚚 Livreurs": {
            "worksheet": "Livreurs",
            "path": DATA_LIVREURS,
            "columns": COLS_LIVREURS,
            "type": "csv"
        },
        "🗺️ Secteurs Logistique": {
            "worksheet": "Secteurs",
            "path": DATA_SECTEURS,
            "columns": COLS_SECTEURS,
            "type": "csv"
        },
        "📦 Master Inventaire (Lots)": {
            "worksheet": "Master_Inventaire_Zone",
            "path": "data_inventaire_detail/master_detail.csv",
            "columns": [],
            "type": "csv"
        },
        "📈 Performance Ventes": {
            "worksheet": "Analyse_Ventes_Perf",
            "path": "data/db_ventes_performance.csv",
            "columns": [],
            "type": "csv"
        },
        "📋 Réclamations Clients": {
            "worksheet": "Analyse_Reclamations",
            "path": "data/db_reclamations_analyse.csv",
            "columns": [],
            "type": "csv"
        },
        "💳 Suivi Recouvrement": {
            "worksheet": "Recouvrement",
            "path": "data_recouvrement.csv",
            "columns": ["Client", "Facture", "Date", "Montant Initial", "Montant Réglé", "Reste à payer", "Mode Paiement", "Livreur", "Région", "Statut", "Commentaires", "Société"],
            "type": "csv"
        },
        "🚚 Suivi Expédition": {
            "worksheet": "Expedition",
            "path": "data/db_expedition_logipharm.csv",
            "columns": [],
            "type": "csv"
        },
        "🏢 Fournisseurs": {
            "worksheet": "DB_Fournisseurs",
            "path": "data/db_fournisseurs.csv",
            "columns": ["Etablissement", "Wilaya", "Activité", "Logo"],
            "type": "csv"
        },
        "🤝 Mini-CRM Interactions": {
            "worksheet": "CRM",
            "path": "data/db_crm.csv",
            "columns": ["Date", "Client", "Type", "Note", "Agent"],
            "type": "csv"
        },
        "📦 Litiges & Anomalies Fournisseurs": {
            "worksheet": "Litiges",
            "path": "data/data_litiges.csv",
            "columns": ["Date", "Heure", "Facture", "Fournisseur", "Agent", "Produit", "Lot", "Quantite", "Type", "Priorite", "Statut", "Commentaire", "Photo_Path", "Date_Resolution", "IA_Analyse"],
            "type": "csv"
        },
        "📦 Base Produits (Réclamations)": {
            "worksheet": "Base_Produits",
            "path": "data_produits.csv",
            "columns": ["Désignation"],
            "type": "csv"
        },
        "👥 Utilisateurs & Accès": {
            "worksheet": "Utilisateurs",
            "path": "data/db_users.json",
            "columns": [],
            "type": "json"
        }
    }

    # Liste des modules sous forme de cases à cocher dans 3 colonnes
    st.markdown("### 🗄️ Sélectionner les Modules / Bases de Données")
    selected_modules = []
    
    col_sel_all1, col_sel_all2 = st.columns([1, 4])
    select_all = col_sel_all1.checkbox("Tout cocher", value=False)
    
    cols_select = st.columns(3)
    for idx, (mod_name, mod_info) in enumerate(MODULES_DB.items()):
        col_item = cols_select[idx % 3]
        if col_item.checkbox(mod_name, value=select_all, key=f"wipe_chk_{idx}"):
            selected_modules.append(mod_name)
            
    st.divider()
    
    # Choix de l'action
    st.markdown("### ⚙️ Sélectionner l'Action à Exécuter")
    action_type = st.radio(
        "Action à appliquer sur les éléments cochés :",
        [
            "☁️ Sauvegarder dans le Cloud (Backup Google Sheets uniquement)",
            "🗑️ Remise à Zéro (Suppression des données locales uniquement)",
            "🔄 Backup Cloud ET Remise à Zéro (Sauvegarder puis Vider localement - Recommandé)"
        ],
        index=2
    )
    
    st.divider()
    
    # Sécurité
    st.markdown("### 🔒 Sécurité & Confirmation de l'Opération")
    check_safety = st.checkbox("⚠️ Je confirme avoir sélectionné uniquement les modules à traiter et je comprends que la suppression locale est définitive.")
    confirm_txt = st.text_input("Veuillez saisir 'CONFIRMER' en majuscules pour valider l'action :", key="wipe_confirm_input")
    
    if st.button("🚨 Lancer l'opération sur les éléments cochés", type="primary", use_container_width=True):
        if not selected_modules:
            st.error("❌ Veuillez sélectionner au moins un module.")
        elif not check_safety:
            st.error("❌ Veuillez cocher la case de confirmation de sécurité.")
        elif confirm_txt != "CONFIRMER":
            st.error("❌ Veuillez saisir exactement le mot 'CONFIRMER'.")
        else:
            progress_bar = st.progress(0.0)
            success_logs = []
            error_logs = []
            
            for idx_m, mod_name in enumerate(selected_modules):
                db_info = MODULES_DB[mod_name]
                worksheet = db_info["worksheet"]
                path = db_info["path"]
                cols = db_info["columns"]
                db_type = db_info["type"]
                
                do_backup = "Cloud" in action_type or "Backup" in action_type
                do_delete = "Suppression" in action_type or "Remise" in action_type or "Backup Cloud ET Remise à Zéro" in action_type
                
                step_success = True
                
                # 1. SAUVEGARDE CLOUD
                if do_backup:
                    try:
                        if os.path.exists(path):
                            if db_type == "csv":
                                df_to_backup = pd.read_csv(path)
                                save_gs_data(df_to_backup, worksheet, path)
                            elif db_type == "json":
                                import json
                                with open(path, 'r', encoding='utf-8') as f:
                                    data_json = json.load(f)
                                df_to_backup = pd.DataFrame(data_json)
                                save_gs_data(df_to_backup, worksheet, path)
                            success_logs.append(f"☁️ Cloud Backup : **{mod_name}** sauvegardé avec succès.")
                        else:
                            success_logs.append(f"ℹ️ Cloud Backup : **{mod_name}** ignoré (le fichier local n'existait pas).")
                    except Exception as e_backup:
                        step_success = False
                        error_logs.append(f"❌ Erreur Backup **{mod_name}** : {e_backup}")
                
                # 2. REMISE A ZERO LOCALE
                if do_delete and step_success:
                    try:
                        # Assurer le répertoire parent
                        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
                        if db_type == "csv":
                            df_empty = pd.DataFrame(columns=cols)
                            df_empty.to_csv(path, index=False, sep=',', encoding='utf-8-sig')
                        elif db_type == "json":
                            import json
                            # Sécurité lockout Utilisateurs
                            if worksheet == "Utilisateurs":
                                default_users = [{"username": "admin", "password": "admin", "role": "Admin", "pages": "All", "nom": "Admin", "prenom": "Systeme", "zone": "Toutes"}]
                                with open(path, 'w', encoding='utf-8') as f:
                                    json.dump(default_users, f, indent=4, ensure_ascii=False)
                            else:
                                with open(path, 'w', encoding='utf-8') as f:
                                    json.dump([], f, indent=4, ensure_ascii=False)
                        
                        success_logs.append(f"🗑️ Remise à Zéro : **{mod_name}** réinitialisé à vide.")
                    except Exception as e_del:
                        error_logs.append(f"❌ Erreur Suppression **{mod_name}** : {e_del}")
                
                progress_bar.progress((idx_m + 1) / len(selected_modules))
            
            st.cache_data.clear()
            
            if success_logs:
                st.success("### 🎉 Opérations Réussies :\n" + "\n".join([f"- {log}" for log in success_logs]))
            if error_logs:
                st.error("### ⚠️ Erreurs Rencontrées :\n" + "\n".join([f"- {log}" for log in error_logs]))
                
            st.balloons()
