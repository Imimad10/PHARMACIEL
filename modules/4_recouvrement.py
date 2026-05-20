import streamlit as st
import pandas as pd
import os
import io
import qrcode
from PIL import Image
from datetime import datetime
from fpdf import FPDF
import plotly.express as px
from utils_ia import ask_ai, is_ia_enabled
import gspread
from google.oauth2.service_account import Credentials

from utils_gsheets import (
    load_gs_data, save_gs_data, show_sync_ui, 
    get_gs_client, get_gs_url, GS_CREDS_PATH, GS_CONFIG_PATH
)

# --- CONFIGURATION ET CHEMINS ---
DATA_RECOUV = "data_recouvrement.csv"
DATA_CLIENTS = "base_clients.csv"
COLS_RECOUV = ["Client", "Facture", "Date", "Montant Initial", "Montant Réglé", "Reste à payer", "Mode Paiement", "Livreur", "Région", "Statut", "Commentaires", "Société"]
COLS_CLIENTS = ["Nom Client", "Région", "Secteur"]
STATUS_OPTIONS = ["En attente", "Partiel", "Réglé", "Clôturé", "Annulé", "Litige"]
RECOUV_MAPPING_PATH = "data_recouvrement_mapping.csv"
RECOUV_MAPPING_WORKSHEET = "Recouv_Mapping"

st.set_page_config(page_title="Recouvrement Pharmaciel", layout="wide")
show_sync_ui("Recouvrement", DATA_RECOUV, COLS_RECOUV)

def is_sums_authorized():
    """Vérifie si l'utilisateur connecté est autorisé à voir les sommes d'argent."""
    if "current_user" not in st.session_state or st.session_state.current_user is None:
        return False
    user_info = st.session_state.current_user
    username = str(user_info.get("username", "")).strip().lower()
    role = str(user_info.get("role", "")).strip()
    
    # Autorisé pour Karim (chef de parc), les Administrateurs, les Superviseurs et les Livreurs
    if username == "karim" or role in ["Admin", "Superviseur", "Livreur"]:
        return True
    return False

def is_admin_or_karim():
    """Vérifie si l'utilisateur connecté est Karim (chef de parc) ou un Administrateur."""
    if "current_user" not in st.session_state or st.session_state.current_user is None:
        return False
    user_info = st.session_state.current_user
    username = str(user_info.get("username", "")).strip().lower()
    role = str(user_info.get("role", "")).strip()
    if username == "karim" or role == "Admin":
        return True
    return False

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

# --- FONCTIONS DE GESTION DES DONNÉES (WRAPPERS) ---
def load_data(path, columns):
    worksheet_name = "Recouvrement" if path == DATA_RECOUV else "Base_Clients"
    df = load_gs_data(worksheet_name, path, columns)
    # Nettoyage spécifique aux montants avec notre parseur robuste
    for col in ["Montant Initial", "Montant Réglé", "Reste à payer"]:
        if col in df.columns:
            df[col] = parse_numeric_series(df[col])
    
    # Assurer que les colonnes de texte sont bien de type string (pour éviter les erreurs st.data_editor avec des NaNs)
    text_cols = ["Statut", "Commentaires", "Client", "Facture", "Date", "Mode Paiement", "Livreur", "Région", "Nom Client", "Téléphone", "Secteur", "Société"]
    for col in text_cols:
        if col in df.columns:
            df[col] = df[col].fillna("").astype(str)
            
    return df

def save_data(df, path):
    worksheet_name = "Recouvrement" if path == DATA_RECOUV else "Base_Clients"
    save_gs_data(df, worksheet_name, path)
    return df

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
        'Société':         ['societe', 'société', 'entreprise', 'company', 'filiale'],
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

def get_livreur(region_val):
    reg = str(region_val).strip().upper() if pd.notna(region_val) else ""
    if not reg: return "NON ASSIGNÉ"
    
    try:
        # 1. Priorité au mapping spécifique Recouvrement
        df_map = load_gs_data(RECOUV_MAPPING_WORKSHEET, RECOUV_MAPPING_PATH, ["Région", "Livreur"])
        if not df_map.empty:
            match_map = df_map[df_map["Région"].astype(str).str.strip().str.upper() == reg]
            if not match_map.empty:
                return str(match_map.iloc[0]["Livreur"]).strip().upper()

        # 2. Fallback sur la base Livreurs générale
        df_livreurs = load_gs_data("Livreurs", "data_expedition/livreurs.csv", ["Nom", "Prénom", "Téléphone", "Secteur"])
        if not df_livreurs.empty:
            match = df_livreurs[df_livreurs["Secteur"].astype(str).str.strip().str.upper() == reg]
            if not match.empty:
                return str(match.iloc[0]["Nom"]).strip().upper()
            
            for _, row in df_livreurs.iterrows():
                secteur = str(row["Secteur"]).strip().upper()
                if secteur and secteur in reg:
                    return str(row["Nom"]).strip().upper()
    except Exception as e:
        pass 
    
    return "NON ASSIGNÉ"

def generate_pdf(df, livreur_name, societe_name=""):
    mission_id = f"REC-{int(datetime.now().timestamp())}"
    total_du = df["Reste à payer"].sum() if "Reste à payer" in df.columns else 0
    
    # Génération du QR Code
    qr_data = f"ID:{mission_id}|Livreur:{livreur_name}|Societe:{societe_name}|Date:{datetime.now().strftime('%d/%m/%Y')}|Clients:{len(df)}|Total:{total_du:.2f} DA"
    qr_img = qrcode.make(qr_data)
    qr_path = f"temp_qr_recouv_{mission_id}.png"
    qr_img.save(qr_path)

    pdf = FPDF()
    pdf.add_page()
    
    # En-tête avec QR Code à droite
    pdf.set_font("Arial", "B", 16)
    title = "FEUILLE DE RECOUVREMENT"
    if societe_name and societe_name != "TOUTES":
        title += f" - {societe_name}"
    pdf.cell(150, 10, title, ln=False, align='L')
    pdf.image(qr_path, x=165, y=8, w=35)  # QR en haut à droite
    pdf.ln(12)
    pdf.set_font("Arial", "B", 13)
    pdf.cell(190, 8, f"Livreur : {livreur_name}", ln=True, align='L')
    pdf.set_font("Arial", "", 11)
    pdf.cell(190, 8, f"Date : {datetime.now().strftime('%d/%m/%Y')}   |   Ref. Mission : {mission_id}", ln=True)
    pdf.cell(190, 8, f"Nb Clients : {len(df)}   |   Total à recouvrer : {total_du:,.2f} DA", ln=True)
    pdf.ln(8)
    
    # Entête du tableau PDF
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(60, 10, "Client", 1, 0, 'C', True)
    pdf.cell(35, 10, "Region", 1, 0, 'C', True)
    pdf.cell(35, 10, "Montant", 1, 0, 'C', True)
    pdf.cell(25, 10, "Mode", 1, 0, 'C', True)
    pdf.cell(35, 10, "Pointage", 1, 1, 'C', True)
    
    pdf.set_font("Arial", "", 9)
    for _, row in df.iterrows():
        pdf.cell(60, 10, str(row['Client'])[:30].encode('latin-1', 'replace').decode('latin-1'), 1)
        pdf.cell(35, 10, str(row['Région']), 1)
        pdf.cell(35, 10, f"{row['Reste à payer']:,.2f} DA", 1, 0, 'R')
        pdf.cell(25, 10, str(row['Mode Paiement']), 1, 0, 'C')
        pdf.cell(35, 10, "", 1, 1)
    
    raw = pdf.output(dest='S')
    if isinstance(raw, (bytes, bytearray)):
        result = bytes(raw)
    else:
        result = raw.encode('latin-1', 'replace')
    
    if os.path.exists(qr_path): os.remove(qr_path)
    return result

def generate_relance_pdf(client_name, df_client, total_du):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "DARPHARM SOLUTION - MISE EN DEMEURE / RELANCE", 0, 1, 'C')
    pdf.ln(10)
    
    pdf.set_font("Arial", '', 12)
    pdf.cell(0, 8, f"Date : {datetime.now().strftime('%d/%m/%Y')}", 0, 1, 'R')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, f"A l'attention de : {client_name}", 0, 1, 'L')
    pdf.ln(5)
    
    pdf.set_font("Arial", '', 11)
    texte = (
        "Cher client,\n\n"
        "Sauf erreur ou omission de notre part, nous constatons que votre compte client presente "
        f"actuellement un solde debiteur de {total_du:,.2f} DA.\n\n"
        "Voici le detail des factures / montants en attente :\n"
    )
    pdf.multi_cell(0, 8, texte.encode('latin-1', 'replace').decode('latin-1'))
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(60, 8, "Facture / Ref", 1)
    pdf.cell(40, 8, "Date", 1)
    pdf.cell(40, 8, "Montant Du (DA)", 1)
    pdf.ln()
    
    pdf.set_font("Arial", '', 10)
    for _, row in df_client.iterrows():
        fac = str(row.get('Facture', 'N/A'))
        d = str(row.get('Date', ''))
        mnt = f"{row.get('Reste à payer', 0.0):,.2f}"
        
        pdf.cell(60, 8, fac[:25].encode('latin-1', 'replace').decode('latin-1'), 1)
        pdf.cell(40, 8, d.encode('latin-1', 'replace').decode('latin-1'), 1)
        pdf.cell(40, 8, mnt.encode('latin-1', 'replace').decode('latin-1'), 1)
        pdf.ln()
        
    pdf.ln(10)
    footer = "Nous vous remercions de bien vouloir regulariser cette situation dans les plus brefs delais.\n\nCordialement,\nLe Service Recouvrement"
    pdf.multi_cell(0, 8, footer.encode('latin-1', 'replace').decode('latin-1'))
    
    raw = pdf.output(dest='S')
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    return raw.encode('latin-1', 'replace')

# --- INTERFACE UTILISATEUR ---
st.title("💰 Système de Recouvrement")

tabs = st.tabs(["🆕 Créer / Importer", "📄 Feuilles de Recouvrement", "📊 Suivi Global", "🗄️ Archives", "📈 Analyse Financière", "⚙️ Administration"])

# ONGLET 1 : SAISIE ET IMPORT
with tabs[0]:
    col1, col2 = st.columns([1, 2])
    df_clients = load_data(DATA_CLIENTS, COLS_CLIENTS)
    
    with col1:
        st.subheader("Saisie Manuelle")
        with st.form("form_rec", clear_on_submit=True):
            if not df_clients.empty:
                noms_valides = sorted([n for n in df_clients["Nom Client"].unique() if str(n).lower() != 'nan'])
                nom_sel = st.selectbox("Client", noms_valides, index=None, placeholder="Rechercher ou sélectionner un client...")
                
                if nom_sel:
                    # Recherche du secteur
                    match_rows = df_clients[df_clients["Nom Client"] == nom_sel]
                    if not match_rows.empty:
                        reg_auto = match_rows["Secteur"].values[0]
                        # Fallback sur Région si Secteur est vide
                        if not reg_auto or str(reg_auto).strip().lower() in ('nan', ''):
                            reg_auto = match_rows["Région"].values[0] if "Région" in match_rows.columns else ""
                    else:
                        reg_auto = ""
                    
                    reg_auto = str(reg_auto).strip().upper()
                else:
                    reg_auto = ""
            else:
                nom_sel = st.text_input("Nom Client")
                reg_auto = st.text_input("Région")
                
            col_m1, col_m2 = st.columns(2)
            montant_ini = col_m1.number_input("Montant Initial", min_value=0.0)
            montant_reg = col_m2.number_input("Montant Réglé", min_value=0.0)
            
            col_f3, col_f4 = st.columns(2)
            mode = col_f3.selectbox("Mode de Paiement", ["CASH", "CHÈQUE", "VERSEMENT", "TRAITE"])
            societe = col_f4.selectbox("Société", ["DARPHARM", "PHARMACIEL"])
            statut = st.selectbox("Statut Initial", STATUS_OPTIONS)
            comm = st.text_area("Commentaires / Notes", placeholder="Ex: Promesse de paiement pour lundi...")
            
            if st.form_submit_button("➕ Ajouter à la liste (Instantané)"):
                if not nom_sel:
                    st.error("Veuillez sélectionner un client.")
                else:
                    reste = max(0.0, montant_ini - montant_reg)
                    new_entry = {
                        "Client": nom_sel, 
                        "Facture": f"MAN_FAST_{datetime.now().strftime('%d%m%H%M%S')}",
                        "Date": str(datetime.now().date()),
                        "Montant Initial": montant_ini,
                        "Montant Réglé": montant_reg,
                        "Reste à payer": reste,
                        "Mode Paiement": mode, 
                        "Livreur": get_livreur(reg_auto), 
                        "Région": reg_auto, 
                        "Statut": statut,
                        "Commentaires": comm,
                        "Société": societe
                    }
                    
                    # --- OPTIMISATION : AJOUT INSTANTANÉ EN SESSION ---
                    if "pending_rec" not in st.session_state: st.session_state.pending_rec = []
                    st.session_state.pending_rec.append(new_entry)
                    st.toast(f"✅ {nom_sel} ajouté au tampon local !", icon="⚡")
                    st.rerun()

    # --- ZONE DE SYNCHRONISATION RAPIDE ---
    if "pending_rec" in st.session_state and st.session_state.pending_rec:
        with st.container(border=True):
            st.markdown(f"⚡ **{len(st.session_state.pending_rec)} dossiers en attente de synchronisation Cloud**")
            c_s1, c_s2 = st.columns([1, 1])
            if c_s1.button("🚀 Tout envoyer sur le Cloud (GSheets)", type="primary", use_container_width=True):
                with st.spinner("Synchronisation groupée en cours..."):
                    db = load_data(DATA_RECOUV, COLS_RECOUV)
                    df_pending = pd.DataFrame(st.session_state.pending_rec)
                    save_data(pd.concat([db, df_pending], ignore_index=True), DATA_RECOUV)
                    st.session_state.pending_rec = []
                    st.success("✅ Tout est synchronisé !")
                    st.rerun()
            if c_s2.button("🗑️ Annuler les ajouts locaux", use_container_width=True):
                st.session_state.pending_rec = []
                st.rerun()
            
            pending_df = pd.DataFrame(st.session_state.pending_rec)
            cols_all = ["Client", "Région", "Montant Initial", "Montant Réglé", "Mode Paiement", "Société", "Statut", "Commentaires"] if is_sums_authorized() else ["Client", "Région", "Mode Paiement", "Société", "Statut", "Commentaires"]
            cols_all = [c for c in cols_all if c in pending_df.columns]
            
            edited_df = st.data_editor(
                pending_df,
                column_order=cols_all,
                num_rows="dynamic",
                use_container_width=True,
                key="pending_rec_editor"
            )
            
            if not edited_df.equals(pending_df):
                new_pending = []
                for _, r in edited_df.iterrows():
                    item = r.to_dict()
                    # Recalculer les champs automatiques en toute sécurité
                    try:
                        item["Montant Initial"] = float(item.get("Montant Initial", 0.0))
                        item["Montant Réglé"] = float(item.get("Montant Réglé", 0.0))
                        item["Reste à payer"] = max(0.0, item["Montant Initial"] - item["Montant Réglé"])
                        item["Livreur"] = get_livreur(item.get("Région", ""))
                    except:
                        pass
                    new_pending.append(item)
                st.session_state.pending_rec = new_pending
                st.rerun()

    with col2:
        # ── BLOC : IMPORT DEPUIS L'ADMIN CENTRALE ──────────────────────────────
        with st.container(border=True):
            st.markdown("### 🏛️ Synchronisation — Base Clients Admin Centrale")
            st.info(
                "Importe automatiquement la liste de tous les clients "
                "enregistrés dans l'**Administration Centrale** vers ce module. "
                "Aucun doublon ne sera créé."
            )

            # Chemin de la base master (partagée avec l'admin centrale)
            ADMIN_CLIENTS_PATH = "base_clients.csv"
            ADMIN_CLIENTS_COLS_MASTER = [
                "Nom_Pharmacie", "Region", "Wilaya", "Ville",
                "Telephone", "Secteur", "Nom Client", "Région", "Téléphone"
            ]

            col_imp1, col_imp2 = st.columns([2, 1])

            # Aperçu du nombre de clients disponibles dans la base master
            try:
                df_master_preview = load_gs_data("Base_Clients", ADMIN_CLIENTS_PATH, [])
                nb_master = len(df_master_preview) if not df_master_preview.empty else 0
                col_imp2.metric("Clients dans l'Admin Centrale", nb_master)
            except Exception:
                nb_master = 0
                col_imp2.metric("Clients dans l'Admin Centrale", "—")

            if col_imp1.button(
                "🔄 Importer / Synchroniser la base clients",
                use_container_width=True,
                type="primary",
                key="btn_import_admin_centrale"
            ):
                with st.spinner("Synchronisation en cours depuis l'Admin Centrale…"):
                    try:
                        # 1. Charger la base master complète
                        df_master = load_gs_data("Base_Clients", ADMIN_CLIENTS_PATH, [])

                        if df_master.empty:
                            st.warning("⚠️ La base clients de l'Admin Centrale est vide.")
                        else:
                            # 2. Normalisation — créer les colonnes standard du recouvrement
                            rows_import = []
                            for _, r in df_master.iterrows():
                                # Nom client : priorité Nom_Pharmacie, sinon "Nom Client"
                                nom = str(r.get("Nom_Pharmacie", r.get("Nom Client", ""))).strip()
                                if not nom or nom.lower() in ("nan", ""):
                                    continue

                                # Secteur / Région
                                secteur = str(
                                    r.get("Secteur", r.get("Region", r.get("Région", r.get("Wilaya", ""))))
                                ).strip()

                                # Téléphone
                                tel = str(
                                    r.get("Telephone", r.get("Téléphone", r.get("Mobile", "")))
                                ).strip()
                                if tel.lower() == "nan":
                                    tel = ""

                                rows_import.append({
                                    "Nom Client": nom,
                                    "Région": secteur,
                                    "Téléphone": tel,
                                    "Secteur": secteur,
                                })

                            df_import = pd.DataFrame(rows_import)

                            # 3. Fusionner avec la base locale (sans doublons sur Nom Client)
                            df_local = load_data(DATA_CLIENTS, COLS_CLIENTS)
                            df_merged = pd.concat([df_local, df_import], ignore_index=True)
                            df_merged = df_merged.drop_duplicates(
                                subset=["Nom Client"], keep="last"
                            )

                            # 4. Sauvegarder
                            save_data(df_merged, DATA_CLIENTS)
                            st.cache_data.clear()

                            nb_new = len(df_import)
                            nb_total = len(df_merged)
                            st.success(
                                f"✅ Synchronisation réussie ! "
                                f"**{nb_new}** clients traités · "
                                f"**{nb_total}** clients disponibles dans le recouvrement."
                            )
                            st.rerun()

                    except Exception as e:
                        st.error(f"❌ Erreur lors de l'import : {e}")

        st.divider()

        st.subheader("Import Excel")
        f_rec = st.file_uploader("Déposer rec.xlsx", type=["xlsx"])
        if f_rec:
            df_ex = pd.read_excel(f_rec)
            df_ex = clean_recouvrement_logipharm_cols(df_ex)
            
            # Afficher un aperçu des colonnes détectées pour rassurer l'utilisateur
            detected_cols = [c for c in COLS_RECOUV if c in df_ex.columns]
            st.success(f"🔍 Colonnes détectées automatiquement : {', '.join(detected_cols)}")
            
            # Si Société n'est pas détectée, on propose une sélection par défaut
            default_soc = "DARPHARM"
            if "Société" not in df_ex.columns:
                default_soc = st.selectbox("Société par défaut pour les lignes importées", ["DARPHARM", "PHARMACIEL"])
            
            if st.button("🚀 Valider l'importation"):
                if "Client" not in df_ex.columns:
                    st.error("❌ La colonne 'Client' n'a pas pu être détectée. Assurez-vous que le fichier contient une colonne nommée 'Client' ou 'Raison Sociale'.")
                else:
                    # Nettoyage et complétion des colonnes pour le format standard
                    if "Région" not in df_ex.columns: 
                        df_ex["Région"] = "INCONNU"
                    if "Montant Initial" not in df_ex.columns and "Reste à payer" in df_ex.columns:
                        df_ex["Montant Initial"] = df_ex["Reste à payer"]
                    if "Montant Initial" not in df_ex.columns:
                        df_ex["Montant Initial"] = 0.0
                    if "Montant Réglé" not in df_ex.columns:
                        df_ex["Montant Réglé"] = 0.0
                    
                    # Convertir en types numériques avec parseur robuste
                    df_ex["Montant Initial"] = parse_numeric_series(df_ex["Montant Initial"])
                    df_ex["Montant Réglé"] = parse_numeric_series(df_ex["Montant Réglé"])
                    
                    if "Reste à payer" not in df_ex.columns:
                        df_ex["Reste à payer"] = df_ex["Montant Initial"] - df_ex["Montant Réglé"]
                    else:
                        df_ex["Reste à payer"] = parse_numeric_series(df_ex["Reste à payer"])
                        
                    if "Facture" not in df_ex.columns:
                        df_ex["Facture"] = [f"LOGI_{datetime.now().strftime('%d%m')}_{i}" for i in range(len(df_ex))]
                    if "Date" not in df_ex.columns:
                        df_ex["Date"] = str(datetime.now().date())
                    if "Statut" not in df_ex.columns:
                        df_ex["Statut"] = "En attente"
                    if "Livreur" not in df_ex.columns:
                        df_ex["Livreur"] = df_ex["Région"].apply(get_livreur)
                    if "Mode Paiement" not in df_ex.columns:
                        df_ex["Mode Paiement"] = "CASH"
                    if "Commentaires" not in df_ex.columns:
                        df_ex["Commentaires"] = ""
                    if "Société" not in df_ex.columns:
                        df_ex["Société"] = default_soc
                    else:
                        df_ex["Société"] = df_ex["Société"].fillna(default_soc).astype(str).str.strip().str.upper()
                        # Normaliser les valeurs "DARPHARM" ou "PHARMACIEL"
                        df_ex["Société"] = df_ex["Société"].apply(lambda x: "PHARMACIEL" if "PHARM" in str(x).upper() else "DARPHARM")
                    
                    # Filtrer pour ne garder que le schéma standard
                    df_to_save = df_ex[COLS_RECOUV].copy()
                    
                    db_old = load_data(DATA_RECOUV, COLS_RECOUV)
                    save_data(pd.concat([db_old, df_to_save], ignore_index=True), DATA_RECOUV)
                    st.success("🎉 Importation et nettoyage terminés avec succès !")
                    st.rerun()

# ONGLET 2 : FEUILLES DE ROUTE (AVEC SUPPRESSION DOUBLONS ET RÉINITIALISATION)
with tabs[1]:
    df_main = load_data(DATA_RECOUV, COLS_RECOUV)
    
    # 1. Chargement des bases centrales
    from utils_gsheets import load_gs_data
    df_livreurs_db = load_gs_data("Livreurs", "data_expedition/livreurs.csv", ["Nom", "Prénom", "Téléphone", "Secteur"])
    df_clients_db = load_gs_data("Base_Clients", DATA_CLIENTS, COLS_CLIENTS)
    
    if not df_main.empty:
        # 2. Mise à jour dynamique des Régions et Livreurs selon la base centrale
        if not df_clients_db.empty:
            # Construction intelligente du mapping Client -> Région (avec fallback Secteur -> Région)
            client_to_region = {}
            for _, crow in df_clients_db.iterrows():
                c_name = str(crow.get("Nom Client", "")).strip().upper()
                c_sec = str(crow.get("Secteur", "")).strip().upper()
                c_reg = str(crow.get("Région", "")).strip().upper()
                
                final_reg = c_sec
                if not final_reg or final_reg in ('NAN', ''):
                    final_reg = c_reg
                if final_reg and final_reg not in ('NAN', ''):
                    client_to_region[c_name] = final_reg
            
            for idx, row in df_main.iterrows():
                c_name = str(row["Client"]).strip().upper()
                if c_name in client_to_region and pd.notna(client_to_region[c_name]) and client_to_region[c_name] != "":
                    df_main.at[idx, "Région"] = client_to_region[c_name]
                    
        if not df_livreurs_db.empty:
            # On charge le mapping spécifique pour l'affectation automatique
            df_mapping_rec = load_gs_data(RECOUV_MAPPING_WORKSHEET, RECOUV_MAPPING_PATH, ["Région", "Livreur"])
            mapping_dict = dict(zip(df_mapping_rec["Région"].astype(str).str.upper(), df_mapping_rec["Livreur"].astype(str).str.upper())) if not df_mapping_rec.empty else {}

            for idx, row in df_main.iterrows():
                reg = str(row["Région"]).strip().upper()
                
                # Priorité au mapping spécifique
                if reg in mapping_dict:
                    df_main.at[idx, "Livreur"] = mapping_dict[reg]
                else:
                    # Fallback sur la base logistique
                    assigned = "NON ASSIGNÉ"
                    for _, lrow in df_livreurs_db.iterrows():
                        sec = str(lrow["Secteur"]).strip().upper()
                        if sec and (sec in reg or reg == sec):
                            assigned = str(lrow["Nom"]).strip().upper()
                            break
                    df_main.at[idx, "Livreur"] = assigned

        # 3. Listes déroulantes de filtrage
        livs_actifs = sorted([str(l).upper() for l in df_main["Livreur"].unique() if str(l).strip() != "" and str(l).upper() != "NAN"])
        if "NON ASSIGNÉ" not in livs_actifs: livs_actifs.append("NON ASSIGNÉ")
            
        col_fil1, col_fil2 = st.columns(2)
        with col_fil1:
            sel_liv = st.selectbox("Sélectionner Livreur", livs_actifs)
        with col_fil2:
            sel_soc = st.selectbox("Sélectionner Société", ["DARPHARM", "PHARMACIEL", "TOUTES"])
        
        # 4. Identifier le secteur du livreur sélectionné
        sel_secteur = ""
        if sel_liv != "NON ASSIGNÉ" and not df_livreurs_db.empty:
            match_liv = df_livreurs_db[df_livreurs_db["Nom"].str.upper() == sel_liv]
            if not match_liv.empty:
                sel_secteur = str(match_liv.iloc[0]["Secteur"]).upper().strip()
                st.caption(f"📍 Secteur centralisé : **{sel_secteur}**")
            
        # 5. Filtrage automatique
        mask = df_main["Livreur"].astype(str).str.upper() == sel_liv
        
        if sel_soc != "TOUTES":
            if sel_soc == "DARPHARM":
                # Pour DARPHARM, on inclut aussi les enregistrements sans société pour la rétrocompatibilité
                mask = mask & ((df_main["Société"].astype(str).str.upper() == "DARPHARM") | (df_main["Société"].astype(str).str.strip() == ""))
            else:
                mask = mask & (df_main["Société"].astype(str).str.upper() == sel_soc.upper())
                
        df_display = df_main[mask].drop_duplicates(subset=["Client", "Reste à payer", "Société"], keep='first').copy()
        
        # Insérer une colonne de sélection pour le PDF
        if "Inclure dans PDF" not in df_display.columns:
            df_display.insert(0, "Inclure dans PDF", True)
            
        # Liste des livreurs pour l'édition
        liv_options = sorted(df_livreurs_db["Nom"].astype(str).str.upper().unique().tolist()) if not df_livreurs_db.empty else []
        if "NON ASSIGNÉ" not in liv_options: liv_options.append("NON ASSIGNÉ")

        # Configuration des colonnes
        col_config_display = {
            "Inclure dans PDF": st.column_config.CheckboxColumn("Inclure", help="Cochez pour inclure dans la feuille de recouvrement PDF", default=True),
            "Livreur": st.column_config.SelectboxColumn("Livreur (Modifier)", options=liv_options, required=True),
            "Mode Paiement": st.column_config.SelectboxColumn("Mode Paiement", options=["CASH", "CHÈQUE", "VERSEMENT", "VIREMENT", "TRAITE"]),
            "Reste à payer": st.column_config.NumberColumn("Reste à payer", min_value=0.0, format="%.2f"),
            "Statut": st.column_config.SelectboxColumn("Statut", options=STATUS_OPTIONS),
            "Société": st.column_config.SelectboxColumn("Société", options=["DARPHARM", "PHARMACIEL"], required=True)
        }
        # Masquage de sécurité des montants d'argent
        if not is_sums_authorized():
            col_config_display["Montant Initial"] = st.column_config.Column(visible=False)
            col_config_display["Montant Réglé"] = st.column_config.Column(visible=False)
            col_config_display["Reste à payer"] = st.column_config.Column(visible=False)

        # Éditeur interactif
        edited = st.data_editor(
            df_display, 
            use_container_width=True, 
            hide_index=True,
            column_config=col_config_display
        )
        
        # Bouton de téléchargement dynamique (uniquement les clients sélectionnés/cochés)
        df_pdf = edited[edited["Inclure dans PDF"] == True].copy()
        df_pdf_clean = df_pdf.drop(columns=["Inclure dans PDF"], errors="ignore")
        
        col_btns = st.columns([1, 1, 2])
        with col_btns[0]:
            pdf_filename = f"Recouvrement_{sel_liv}_{sel_soc}.pdf"
            st.download_button(
                "📥 Télécharger la Feuille de Recouvrement PDF", 
                generate_pdf(df_pdf_clean, sel_liv, sel_soc), 
                pdf_filename,
                use_container_width=True
            )
        
        with col_btns[1]:
            if is_admin_or_karim():
                with st.popover("🗑️ Vider ce tableau", use_container_width=True):
                    st.warning(f"⚠️ Supprimer définitivement tous les dossiers affichés pour {sel_liv} - {sel_soc} ?")
                    confirm_clear = st.checkbox("Confirmer la suppression définitive", key="confirm_clear_tab2")
                    if st.button("🔴 Confirmer", disabled=not confirm_clear, use_container_width=True, key="btn_clear_tab2"):
                        df_all_rec = load_data(DATA_RECOUV, COLS_RECOUV)
                        delete_mask = df_all_rec["Livreur"].astype(str).str.upper() == sel_liv
                        if sel_soc != "TOUTES":
                            if sel_soc == "DARPHARM":
                                delete_mask = delete_mask & ((df_all_rec["Société"].astype(str).str.upper() == "DARPHARM") | (df_all_rec["Société"].astype(str).str.strip() == ""))
                            else:
                                delete_mask = delete_mask & (df_all_rec["Société"].astype(str).str.upper() == sel_soc.upper())
                        
                        df_remaining = df_all_rec[~delete_mask]
                        save_data(df_remaining, DATA_RECOUV)
                        st.success("✅ Tableau vidé avec succès !")
                        st.rerun() 

        if st.button("💾 Sauvegarder Statuts, Montants & Affectations", use_container_width=True):
            # Supprimer la colonne temporaire 'Inclure dans PDF' avant la sauvegarde définitive
            df_to_save = edited.drop(columns=["Inclure dans PDF"], errors="ignore")
            
            # On remplace les anciennes lignes par les éditées dans la base globale
            df_final = pd.concat([df_main[~df_main.index.isin(df_display.index)], df_to_save], ignore_index=True)
            save_data(df_final, DATA_RECOUV)
            st.success("🎉 Données de recouvrement mises à jour avec succès !")
            st.rerun()
    else:
        st.info("Aucune donnée disponible.")

# ONGLET 3 : SUIVI GLOBAL (FILTRÉ)
with tabs[2]:
    st.subheader("État Global des Recouvrements Actifs")
    df_all = load_data(DATA_RECOUV, COLS_RECOUV)
    
    # Séparation Actifs / Archivés
    status_archived = ["Clôturé", "Annulé", "Réglé"]
    df_global = df_all[~df_all["Statut"].isin(status_archived)].copy()
    
    if not df_global.empty:
        # Filtre par statut
        col_f1, col_f2 = st.columns([1, 2])
        filter_status = col_f1.selectbox("Filtrer par statut", ["Tous les actifs"] + [s for s in STATUS_OPTIONS if s not in status_archived])
        
        if filter_status != "Tous les actifs":
            df_view = df_global[df_global["Statut"] == filter_status]
        else:
            df_view = df_global

        c1, c2, c3 = st.columns(3)
        if is_sums_authorized():
            c1.metric("Total Actif à recouvrer", f"{df_view['Reste à payer'].sum():,.2f} DA")
        else:
            c1.metric("Total Actif à recouvrer", "🔒 Accès restreint")
        c2.metric("Dossiers en vue", len(df_view))
        c3.metric("En attente critique", len(df_view[df_view["Statut"] == "En attente"]))
        
        # Action si "En attente" est sélectionné ou présent
        if "En attente" in df_view["Statut"].values:
            st.info("💡 **Conseil :** Vous avez des dossiers 'En attente'. Pensez à générer une relance ou à envoyer un message WhatsApp ci-dessous.")

        # Configuration des colonnes
        col_config_global = {
            "Statut": st.column_config.SelectboxColumn("Statut", options=STATUS_OPTIONS, required=True, width="medium"),
            "Commentaires": st.column_config.TextColumn("Commentaires", width="large"),
            "Société": st.column_config.SelectboxColumn("Société", options=["DARPHARM", "PHARMACIEL"], required=True)
        }
        # Masquage de sécurité des montants d'argent
        if not is_sums_authorized():
            col_config_global["Montant Initial"] = st.column_config.Column(visible=False)
            col_config_global["Montant Réglé"] = st.column_config.Column(visible=False)
            col_config_global["Reste à payer"] = st.column_config.Column(visible=False)

        # Tableau éditable
        edited_global = st.data_editor(
            df_view.sort_values("Date", ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config=col_config_global,
            key="editor_suivi_global"
        )

        col_glob_btns = st.columns([2, 1])
        with col_glob_btns[0]:
            if st.button("💾 Sauvegarder & Archiver les clôturés", type="primary", use_container_width=True):
                # Séparation : à archiver vs à garder actifs
                to_archive = edited_global[edited_global["Statut"].isin(status_archived)].copy()
                to_keep    = edited_global[~edited_global["Statut"].isin(status_archived)].copy()

                if not to_archive.empty:
                    st.success(f"✅ {len(to_archive)} dossier(s) archivé(s) avec succès dans la base de données principale !")

                # Reconstruire la base complète (actifs non touchés + édités actifs + les dossiers nouvellement archivés)
                df_untouched = df_all[df_all["Statut"].isin(status_archived)]  # archives déjà existantes
                df_final = pd.concat([df_untouched, df_global[~df_global.index.isin(df_view.index)], to_keep, to_archive], ignore_index=True)
                save_data(df_final, DATA_RECOUV)
                st.rerun()

        with col_glob_btns[1]:
            if is_admin_or_karim():
                with st.popover("🗑️ Vider ce tableau", use_container_width=True):
                    st.warning(f"⚠️ Supprimer définitivement tous les dossiers affichés pour le filtre actuel : {filter_status} ?")
                    confirm_clear_glob = st.checkbox("Confirmer la suppression définitive", key="confirm_clear_tab3")
                    if st.button("🔴 Confirmer", disabled=not confirm_clear_glob, use_container_width=True, key="btn_clear_tab3"):
                        df_all_rec = load_data(DATA_RECOUV, COLS_RECOUV)
                        status_archived = ["Clôturé", "Annulé", "Réglé"]
                        if filter_status != "Tous les actifs":
                            delete_mask = (~df_all_rec["Statut"].isin(status_archived)) & (df_all_rec["Statut"] == filter_status)
                        else:
                            delete_mask = ~df_all_rec["Statut"].isin(status_archived)
                        
                        df_remaining = df_all_rec[~delete_mask]
                        save_data(df_remaining, DATA_RECOUV)
                        st.success("✅ Tableau vidé avec succès !")
                        st.rerun()
        
        st.divider()
        st.subheader("✉️ Génération de Lettres de Relance")
        clients_impayes = df_global[df_global['Reste à payer'] > 0]['Client'].dropna().unique().tolist()
        
        if clients_impayes:
            client_relance = st.selectbox("Sélectionner un client pour la relance", clients_impayes, index=None, placeholder="Choisir un client pour la relance...")
            
            if client_relance:
                df_client_impayes = df_global[(df_global['Client'] == client_relance) & (df_global['Reste à payer'] > 0)]
                total_client = df_client_impayes['Reste à payer'].sum()
                
                st.write(f"Total dû par **{client_relance}** : {total_client:,.2f} DA")
                
                pdf_relance_bytes = generate_relance_pdf(client_relance, df_client_impayes, total_client)
                
                st.download_button(
                    label="📥 Télécharger Lettre de Relance (PDF)",
                    data=pdf_relance_bytes,
                    file_name=f"Relance_{client_relance.replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    type="primary"
                )
            else:
                st.info("Veuillez sélectionner un client pour voir les options de relance.")
            
            # --- PHASE 5: WHATSAPP LINK ---
            st.write("---")
            st.subheader("📲 Relance Rapide via WhatsApp")
            
            # Recherche sécurisée du téléphone
            client_phone = ""
            if not df_clients.empty and "Téléphone" in df_clients.columns:
                match_phone = df_clients[df_clients["Nom Client"] == client_relance]["Téléphone"]
                client_phone = match_phone.values[0] if not match_phone.empty else ""
            
            if pd.notna(client_phone) and str(client_phone) != "":
                # Nettoyage du numéro (garder uniquement les chiffres)
                phone_clean = "".join(filter(str.isdigit, str(client_phone)))
                if not phone_clean.startswith("213"): phone_clean = "213" + phone_clean.lstrip("0")
                
                msg = f"Bonjour {client_relance}, nous vous relançons concernant un solde débiteur de {total_client:,.2f} DA. Merci de régulariser la situation. Cordialement, Service Recouvrement Darpharm Solution."
                wa_link = f"https://wa.me/{phone_clean}?text={msg.replace(' ', '%20')}"
                
                st.link_button(f"💬 Envoyer Relance Standard (WhatsApp)", wa_link)
                
                # --- ASSISTANT IA POUR LA RELANCE ---
                if is_ia_enabled():
                    st.write("---")
                    st.markdown("### 🤖 Assistant IA de Relance")
                    st.info("L'IA va rédiger un message de recouvrement personnalisé en analysant la situation du client.")
                    
                    tone = st.selectbox("Ton du message", ["Professionnel et courtois", "Amical (Bon client)", "Ferme et urgent (Retard important)"])
                    
                    if st.button("✨ Générer un message sur mesure avec l'IA"):
                        with st.spinner("L'IA rédige le message..."):
                            factures_str = "\n".join([f"- Facture {row.get('Facture', 'N/A')} du {row.get('Date', '')}: {row.get('Reste à payer', 0.0)} DA" for _, row in df_client_impayes.iterrows()])
                            
                            prompt = f"""
                            Rédige un message WhatsApp de relance de paiement pour le client {client_relance}.
                            Le ton doit être : {tone}.
                            Le total dû est de {total_client:,.2f} DA.
                            Détail des factures :
                            {factures_str}
                            
                            Le message doit être poli, professionnel, inclure des émojis adaptés et être prêt à être envoyé par le Service Recouvrement de Darpharm Solution. Ne mets pas d'objet de mail, commence directement par Bonjour.
                            """
                            ai_message = ask_ai(prompt)
                            st.session_state[f"ai_msg_{client_relance}"] = ai_message
                    
                    if f"ai_msg_{client_relance}" in st.session_state:
                        ai_text = st.text_area("Message IA (vous pouvez le modifier)", st.session_state[f"ai_msg_{client_relance}"], height=200)
                        wa_link_ai = f"https://wa.me/{phone_clean}?text={ai_text.replace(' ', '%20').replace(chr(10), '%0A')}"
                        st.link_button(f"🚀 Envoyer ce message IA via WhatsApp", wa_link_ai, type="primary")

            else:
                st.warning("Numéro de téléphone manquant pour ce client dans la base.")
        else:
            st.success("Aucun client n'a de reste à payer. Tout est en règle !")
# ONGLET 4 : ARCHIVES
with tabs[3]:
    st.subheader("🗄️ Archives des dossiers terminés")
    
    # --- HOTFIX : Récupération des archives locales perdues ---
    archive_path = "data_archive_recouvrement.csv"
    if os.path.exists(archive_path):
        try:
            df_arch_local = pd.read_csv(archive_path, sep=',', encoding='utf-8-sig')
            if not df_arch_local.empty:
                if "Date Archivage" in df_arch_local.columns:
                    df_arch_local = df_arch_local.drop(columns=["Date Archivage"])
                df_current = load_data(DATA_RECOUV, COLS_RECOUV)
                df_merged = pd.concat([df_current, df_arch_local], ignore_index=True)
                save_data(df_merged, DATA_RECOUV)
                st.success(f"🔄 {len(df_arch_local)} dossier(s) récupéré(s) et réintégré(s) dans la base centrale !")
            os.remove(archive_path)
            st.rerun()
        except Exception as e:
            st.error(f"Erreur de récupération locale : {e}")

    df_all_arch = load_data(DATA_RECOUV, COLS_RECOUV)
    status_archived = ["Clôturé", "Annulé", "Réglé"]
    df_arch = df_all_arch[df_all_arch["Statut"].isin(status_archived)].copy()
    
    if not df_arch.empty:
        st.write(f"Il y a **{len(df_arch)}** dossiers archivés.")
        
        # Masquage de sécurité des montants d'argent
        col_config_arch = {}
        if not is_sums_authorized():
            col_config_arch["Montant Initial"] = st.column_config.Column(visible=False)
            col_config_arch["Montant Réglé"] = st.column_config.Column(visible=False)
            col_config_arch["Reste à payer"] = st.column_config.Column(visible=False)
            
        st.dataframe(
            df_arch.sort_values("Date", ascending=False), 
            use_container_width=True, 
            hide_index=True,
            column_config=col_config_arch
        )
        
        if is_sums_authorized():
            if st.button("📥 Exporter les archives en Excel"):
                import io
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_arch.to_excel(writer, index=False, sheet_name='Archives')
                st.download_button(
                    label="📁 Télécharger le fichier Excel",
                    data=output.getvalue(),
                    file_name=f"Archives_Recouvrement_{datetime.now().strftime('%Y%m%d')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
    else:
        st.info("Aucune archive pour le moment.")

# ONGLET 5 : ANALYSE FINANCIÈRE (BALANCE ÂGÉE)
with tabs[4]:
    st.header("📈 Dashboard Financier & Balance Âgée")
    if not is_sums_authorized():
        st.warning("🔒 Accès restreint. Seuls les Administrateurs, Livreurs et le Chef de Parc (Karim) sont autorisés à visualiser les analyses financières.")
    else:
        df_global = load_data(DATA_RECOUV, COLS_RECOUV)
        
        if not df_global.empty:
            # Analyse de l'âge de la balance
            df_global['Date_dt'] = pd.to_datetime(df_global['Date'], errors='coerce')
            now = pd.Timestamp(datetime.now().date())
            
            df_global['Ancienneté'] = (now - df_global['Date_dt']).dt.days.fillna(0)
            
            # S'assurer que le reste à payer est numérique
            df_global['Reste à payer'] = pd.to_numeric(df_global['Reste à payer'], errors='coerce').fillna(0)
            
            def age_bucket(days):
                if days <= 15: return "0-15 Jours"
                if days <= 30: return "16-30 Jours"
                if days <= 60: return "31-60 Jours"
                return "+60 Jours"
            
            df_global['Tranche'] = df_global['Ancienneté'].apply(age_bucket)
            
            # Graphiques
            col_g1, col_g2 = st.columns(2)
            
            with col_g1:
                st.subheader("📁 Balance Âgée")
                df_age = df_global.groupby('Tranche')['Reste à payer'].sum().reindex(["0-15 Jours", "16-30 Jours", "31-60 Jours", "+60 Jours"]).reset_index()
                fig_age = px.bar(df_age, x='Tranche', y='Reste à payer', color='Tranche', 
                                 color_discrete_sequence=px.colors.sequential.Reds_r, template="plotly_dark")
                st.plotly_chart(fig_age, use_container_width=True)
                
            with col_g2:
                st.subheader("🚚 Dette par Livreur")
                df_liv_debt = df_global.groupby('Livreur')['Reste à payer'].sum().reset_index()
                fig_pie = px.pie(df_liv_debt, values='Reste à payer', names='Livreur', hole=0.4, template="plotly_dark")
                st.plotly_chart(fig_pie, use_container_width=True)
                
            st.divider()
            st.subheader("🚨 Risques Clients (+60 Jours)")
            df_risques = df_global[df_global['Tranche'] == "+60 Jours"].sort_values('Ancienneté', ascending=False)
            if not df_risques.empty:
                st.warning(f"Il y a {len(df_risques)} factures impayées depuis plus de 60 jours !")
                st.dataframe(df_risques, use_container_width=True)
            else:
                st.success("Aucun client n'a de dettes de plus de 60 jours.")
                
        else:
            st.info("Aucune donnée pour l'analyse financière.")

# ONGLET 6 : ADMINISTRATION
with tabs[5]:
    st.header("⚙️ Administration & Affectations")
    
    # --- NOUVELLE ZONE D'AFFECTATION ---
    st.subheader("🎯 Affectation Régionale des Livreurs (Recouvrement)")
    
    # Chargement des bases centrales et locales
    df_map = load_gs_data(RECOUV_MAPPING_WORKSHEET, RECOUV_MAPPING_PATH, ["Région", "Livreur"])
    df_clients_db = load_gs_data("Base_Clients", DATA_CLIENTS, ["Nom Client", "Région", "Secteur"])
    df_liv_db = load_gs_data("Livreurs", "data_expedition/livreurs.csv", ["Nom", "Secteur"])
    df_secteurs_db = load_gs_data("Secteurs", "data_expedition/secteurs.csv", ["Secteur"])
    
    # Construction de la liste globale des secteurs/régions uniques
    regions_set = set()
    if not df_secteurs_db.empty:
        regions_set.update(df_secteurs_db["Secteur"].dropna().astype(str).str.strip().str.upper().tolist())
    if not df_clients_db.empty:
        if "Région" in df_clients_db.columns:
            regions_set.update(df_clients_db["Région"].dropna().astype(str).str.strip().str.upper().tolist())
        if "Secteur" in df_clients_db.columns:
            regions_set.update(df_clients_db["Secteur"].dropna().astype(str).str.strip().str.upper().tolist())
    if not df_liv_db.empty and "Secteur" in df_liv_db.columns:
        regions_set.update(df_liv_db["Secteur"].dropna().astype(str).str.strip().str.upper().tolist())
        
    regions_list = sorted([r for r in regions_set if r and r.lower() not in ("nan", "inconnu", "libre", "")])
    livreurs_list = sorted(df_liv_db["Nom"].dropna().astype(str).str.strip().str.upper().unique().tolist()) if not df_liv_db.empty else []
    
    col_aff1, col_aff2 = st.columns(2)
    with col_aff1:
        st.markdown("##### ➕ Créer une nouvelle affectation")
        reg_to_map = st.selectbox("Choisir une Région / Secteur", regions_list, index=None, placeholder="Secteur à affecter...")
        
        # Sélection du livreur avec option de saisie manuelle
        col_ls1, col_ls2 = st.columns([3, 1])
        with col_ls1:
            liv_to_map_sel = st.selectbox("Choisir le Livreur (Liste)", ["Autre / Saisir..."] + livreurs_list, index=0)
        
        if liv_to_map_sel == "Autre / Saisir...":
            liv_to_map = st.text_input("Nom du Livreur (Manuel)", placeholder="Saisissez le nom ici...")
        else:
            liv_to_map = liv_to_map_sel
        
        if st.button("💾 Enregistrer l'affectation", use_container_width=True):
            if reg_to_map and liv_to_map:
                new_map = pd.DataFrame([{"Région": reg_to_map, "Livreur": liv_to_map}])
                # Supprimer l'ancien si existe
                if not df_map.empty:
                    df_map = df_map[df_map["Région"] != reg_to_map]
                df_map = pd.concat([df_map, new_map], ignore_index=True)
                save_gs_data(df_map, RECOUV_MAPPING_WORKSHEET, RECOUV_MAPPING_PATH)
                st.success(f"✅ {liv_to_map} affecté à {reg_to_map}")
                st.rerun()
            else:
                st.error("Sélectionnez une région et un livreur.")

    with col_aff2:
        st.markdown("##### 📍 Affectations Actuelles")
        if not df_map.empty:
            for idx, row in df_map.iterrows():
                c1, c2, c3 = st.columns([2, 2, 0.5])
                c1.write(f"🌍 **{row['Région']}**")
                c2.write(f"👤 {row['Livreur']}")
                if c3.button("🗑️", key=f"del_map_{idx}"):
                    df_map = df_map.drop(idx)
                    save_gs_data(df_map, RECOUV_MAPPING_WORKSHEET, RECOUV_MAPPING_PATH)
                    st.rerun()
        else:
            st.info("Aucune affectation spécifique définie.")

    st.divider()
    st.subheader("🌐 Connexion Google Sheets (Cloud)")
    st.info("Cette section permet de synchroniser le module Recouvrement avec un Google Sheet pour un accès collaboratif.")
    
    with st.expander("🛠️ Configuration GSheets"):
        c_gs1, c_gs2 = st.columns(2)
        
        # 1. Upload des credentials
        uploaded_json = c_gs1.file_uploader("1. Upload 'service_account.json'", type="json")
        if uploaded_json:
            with open(GS_CREDS_PATH, "wb") as f:
                f.write(uploaded_json.getbuffer())
            st.success("Fichier credentials enregistré !")
            
        # 2. Saisie de l'URL
        current_url = get_gs_url() or ""
        new_url = c_gs2.text_input("2. URL du Google Sheet", value=current_url)
        if c_gs2.button("Enregistrer l'URL"):
            with open(GS_CONFIG_PATH, "w") as f:
                f.write(new_url)
            st.success("URL enregistrée !")
            st.rerun()

        st.write("---")
        st.markdown("### 🚀 Migration groupée vers le Cloud")
        c_mig1, c_mig2 = st.columns(2)
        
        if c_mig1.button("📊 Migrer Recouvrement", use_container_width=True):
            with st.spinner("Migration..."):
                df = load_data(DATA_RECOUV, COLS_RECOUV)
                save_data(df, DATA_RECOUV)
                st.success("Recouvrement migré !")

        if c_mig2.button("👥 Migrer Base Clients", use_container_width=True):
            with st.spinner("Migration..."):
                df = load_data(DATA_CLIENTS, COLS_CLIENTS)
                save_data(df, DATA_CLIENTS)
                st.success("Base Clients migrée !")

        c_mig3, c_mig4 = st.columns(2)
        if c_mig3.button("🚚 Migrer Livreurs", use_container_width=True):
            import importlib.util
            spec = importlib.util.spec_from_file_location("expedition", "modules/1_expedition.py")
            exp_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(exp_mod)
            with st.spinner("Migration..."):
                df = exp_mod.load_livreurs()
                exp_mod.save_livreurs(df)
                st.success("Livreurs migrés !")

        if c_mig4.button("🗺️ Migrer Secteurs/Clients Logistique", use_container_width=True):
            import importlib.util
            spec = importlib.util.spec_from_file_location("expedition", "modules/1_expedition.py")
            exp_mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(exp_mod)
            with st.spinner("Migration..."):
                df = exp_mod.load_clients()
                exp_mod.save_clients(df)
                st.success("Secteurs migrés !")

    st.divider()
    st.subheader("👥 Synchronisation Centralisée")
    st.info("La gestion des clients et l'affectation régionale des livreurs sont centralisées. Vous pouvez forcer la mise à jour immédiate depuis le Cloud ici.")
    
    col_sync1, col_sync2 = st.columns(2)
    with col_sync1:
        if st.button("🔄 Synchroniser Clients & Livreurs", use_container_width=True, help="Force le rechargement des bases clients et livreurs depuis Google Sheets"):
            with st.spinner("Synchronisation..."):
                st.cache_data.clear() # Vider le cache pour forcer le reload global
                df_sync = load_data(DATA_CLIENTS, COLS_CLIENTS)
                from utils_gsheets import load_gs_data
                df_liv = load_gs_data("Livreurs", "data_expedition/livreurs.csv", ["Nom", "Prénom", "Téléphone", "Secteur"])
                st.success(f"✅ Synchronisation réussie : {len(df_sync)} clients et {len(df_liv)} livreurs à jour !")
                st.rerun()
    
    with col_sync2:
        if st.session_state.current_user.get('role') == 'Admin':
            if st.button("🚀 Aller à l'Administration Centrale", use_container_width=True):
                st.switch_page("modules/0_admin_centrale.py")
        else:
            st.warning("Accès Admin Centrale restreint.")

    st.divider()
    # ── SAUVEGARDE & RESTAURATION DE LA BASE ESSENTIELLE ──────────────────
    st.subheader("📥 Sauvegarde & Restauration de la Base Essentielle")
    st.info("Cette section permet de sauvegarder et de restaurer la configuration de base essentielle de votre système de recouvrement (les affectations actuelles des livreurs, les régions et les noms des clients). Aucune donnée de montant ou historique de paiement en cours n'est sauvegardé ici.")
    
    try:
        df_clients_backup = load_data(DATA_CLIENTS, COLS_CLIENTS)
        df_map_backup = load_gs_data(RECOUV_MAPPING_WORKSHEET, RECOUV_MAPPING_PATH, ["Région", "Livreur"])
        
        # Préparation du fichier excel en mémoire
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
            df_clients_backup.to_excel(writer, sheet_name='Base_Clients', index=False)
            df_map_backup.to_excel(writer, sheet_name='Affectations_Livreurs', index=False)
            
        backup_bytes = excel_buffer.getvalue()
        
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            st.download_button(
                label="📥 Télécharger Backup Essentiel (Excel)",
                data=backup_bytes,
                file_name=f"Backup_Essentiel_Recouvrement_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            
            if st.button("💾 Enregistrer une copie locale de sécurité", use_container_width=True):
                os.makedirs("backups_recouvrement", exist_ok=True)
                local_file_path = f"backups_recouvrement/Backup_Essentiel_Recouvrement_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
                with open(local_file_path, "wb") as f:
                    f.write(backup_bytes)
                st.success(f"🎉 Sauvegarde locale enregistrée avec succès dans le dossier `backups_recouvrement` !")
                
        with col_b2:
            uploaded_backup = st.file_uploader("Restaurer la Base Essentielle (.xlsx)", type=["xlsx"])
            if uploaded_backup:
                if st.button("⚠️ Confirmer la Restauration (Écrase les clients et affectations actuels)", type="primary", use_container_width=True):
                    try:
                        xl = pd.ExcelFile(uploaded_backup)
                        restored_any = False
                        
                        if "Base_Clients" in xl.sheet_names:
                            df_restored_clients = xl.parse("Base_Clients")
                            save_data(df_restored_clients, DATA_CLIENTS)
                            restored_any = True
                            
                        if "Affectations_Livreurs" in xl.sheet_names:
                            df_restored_map = xl.parse("Affectations_Livreurs")
                            save_gs_data(df_restored_map, RECOUV_MAPPING_WORKSHEET, RECOUV_MAPPING_PATH)
                            restored_any = True
                            
                        if restored_any:
                            st.success("🎉 Base essentielle restaurée avec succès ! Clients, Régions et Affectations remis à jour.")
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error("❌ Format de fichier invalide (feuilles 'Base_Clients' ou 'Affectations_Livreurs' introuvables).")
                    except Exception as e_restore:
                        st.error(f"❌ Erreur lors de la restauration : {e_restore}")
    except Exception as e_backup:
        st.warning(f"⚠️ Impossible de préparer l'outil de sauvegarde : {e_backup}")

    st.divider()
    if st.session_state.current_user.get('role') == 'Admin':
        st.subheader("🗑️ Nettoyage des Données (Admin uniquement)")
        st.error("⚠️ Attention : Cette action supprimera définitivement toutes les données de recouvrement enregistrées.")
        
        # Double validation par checkbox pour éviter les erreurs
        confirm = st.checkbox("Je confirme vouloir tout effacer")
        if st.button("🔴 Réinitialiser le système de recouvrement", disabled=not confirm):
            with st.spinner("Réinitialisation complète..."):
                # 1. Vider le fichier local (CSV) avec les en-têtes corrects
                try:
                    df_empty = pd.DataFrame(columns=COLS_RECOUV)
                    df_empty.to_csv(DATA_RECOUV, index=False, sep=',', encoding='utf-8-sig')
                except Exception as e_local:
                    st.error(f"❌ Erreur lors du nettoyage local : {e_local}")
                
                # 2. Vider le Cloud (Google Sheets) de manière forcée
                try:
                    client = get_gs_client()
                    url = get_gs_url("Recouvrement")
                    if client and url:
                        sh = client.open_by_url(url)
                        try:
                            worksheet = sh.worksheet("Recouvrement")
                            worksheet.clear()
                            # Écrire uniquement la ligne d'en-tête
                            worksheet.update([COLS_RECOUV])
                        except Exception as e_sheet:
                            st.warning(f"⚠️ Impossible de vider la feuille Google Sheets 'Recouvrement' (mais le fichier local a été vidé) : {e_sheet}")
                except Exception as e_cloud:
                    st.warning(f"⚠️ Service Cloud Google Sheets indisponible : {e_cloud}")
                
                # 3. Vider le cache de Streamlit et le session_state
                st.session_state.pop("pending_rec", None)
                st.cache_data.clear()
                
                st.success("🎉 Le système de recouvrement et la feuille de programme ont été réinitialisés avec succès !")
                st.rerun()
    else:
        st.info("Les fonctions de nettoyage sont réservées à l'administrateur système.")
