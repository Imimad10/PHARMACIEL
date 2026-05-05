import streamlit as st
import pandas as pd
import os
from datetime import datetime
from fpdf import FPDF
import qrcode
import plotly.express as px
from utils import log_action
from tinydb import TinyDB, Query
from utils_ia import ask_ai, is_ia_enabled
from utils_gsheets import load_gs_data, save_gs_data

# --- CONFIGURATION ---
# st.set_page_config(page_title="Gestion des Expéditions", layout="wide")
DATA_DIR = "data_expedition"
os.makedirs(DATA_DIR, exist_ok=True)
SECTEURS_PATH = os.path.join(DATA_DIR, "secteurs.csv")
LIVREURS_PATH = os.path.join(DATA_DIR, "livreurs.csv")
MOTIFS_PATH = os.path.join(DATA_DIR, "motifs.csv")
COLS_CLIENTS = ["Client", "Ville", "Tel", "Secteur"]
COLS_LIVREURS = ["Nom", "Secteur"]
db_global = TinyDB('db_pharmaciel.json')
table_reclam = db_global.table('reclamations')

# --- FONCTIONS DE CHARGEMENT ---
def load_clients():
    df = load_gs_data("Secteurs", SECTEURS_PATH, COLS_CLIENTS)
    mapping = {'nom client': 'Client', 'VILLE': 'Ville', 'tel': 'Tel', 'SECTEUR': 'Secteur'}
    df = df.rename(columns=mapping)
    return df.loc[:, ~df.columns.duplicated()]

def save_clients(df):
    save_gs_data(df, "Secteurs", SECTEURS_PATH)

def load_livreurs():
    return load_gs_data("Livreurs", LIVREURS_PATH, ["Nom", "Prénom", "Téléphone", "Secteur"])

def save_livreurs(df):
    save_gs_data(df, "Livreurs", LIVREURS_PATH)

def load_motifs():
    if not os.path.exists(MOTIFS_PATH):
        # Motifs par défaut
        return ["RETOUR", "DEPOSER COLI", "ECHANGE"]
    try:
        return pd.read_csv(MOTIFS_PATH)['Motif'].tolist()
    except:
        return ["RETOUR", "DEPOSER COLI", "ECHANGE"]

def save_motifs(motifs):
    pd.DataFrame({"Motif": motifs}).to_csv(MOTIFS_PATH, index=False)

# --- INITIALISATION ÉTAT ---
if "rows" not in st.session_state:
    st.session_state.rows = pd.DataFrame(columns=["Client", "Ville", "Secteur", "N° Doc", "Info", "Statut", "Signature"])

def add_or_merge_row(client, ville, ref, info, statut, signature, mode, secteur=""):
    """Ajoute une ligne pour chaque réclamation/commande (évite les doublons par référence)."""
    client = str(client).strip()
    ref = str(ref).strip()
    
    # Vérification si la référence existe déjà dans le tableau actuel (session)
    if not st.session_state.rows.empty:
        if ref in st.session_state.rows['N° Doc'].astype(str).values:
            return False # Indique que la ligne n'a pas été ajoutée car doublon

    # Pour les réclamations, on enregistre en base persistante si pas déjà présent
    if mode == "Réclamation":
        Existing = Query()
        if not table_reclam.search(Existing.ref == ref):
            table_reclam.insert({
                "client": client,
                "ville": ville,
                "ref": ref,
                "motif": info,
                "date_crea": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "statut": "En cours",
                "signature": signature
            })

    # Ajout à l'état de session
    new_row = pd.DataFrame([{
        "Client": client, 
        "Ville": ville, 
        "Secteur": secteur,
        "N° Doc": ref, 
        "Info": info, 
        "Statut": statut, 
        "Signature": signature
    }])
    st.session_state.rows = pd.concat([st.session_state.rows, new_row], ignore_index=True)
    return True

# --- INTERFACE ---
st.title("🚛 Gestion des Expéditions")

tab_exp, tab_suivi_sav, tab_livreurs, tab_secteurs, tab_admin = st.tabs([
    "📋 Programme d'Expédition", "📊 Suivi des Litiges", "👤 Gestion des Livreurs", "📍 Gestion des Secteurs", "⚙️ Administration"
])

# 1. PROGRAMME D'EXPÉDITION
with tab_exp:
    mode = st.radio("Mode d'expédition", ["Commande", "Réclamation"], horizontal=True)
    
    # Sécurisation des données clients pour le Selectbox
    df_clients = load_clients()
    client_list = df_clients["Client"].dropna().astype(str).unique().tolist() if "Client" in df_clients.columns else []
    client_map = dict(zip(df_clients['Client'].astype(str), df_clients['Ville'])) if "Client" in df_clients.columns else {}

    col_g1, col_d1 = st.columns(2)
    df_livreurs = load_livreurs()
    liste_livreurs = df_livreurs["Nom"].tolist() if not df_livreurs.empty else []
    
    # Liste de tous les secteurs pour le filtrage libre
    all_sectors = sorted([str(s).strip().lower() for s in df_clients['Secteur'].dropna().unique() if str(s).lower() != 'nan'])

    with col_g1:
        livreur_choisi = st.selectbox("Choisir le livreur", liste_livreurs)
        # Déterminer le secteur par défaut du livreur
        secteur_par_defaut = ""
        if livreur_choisi:
            row_l = df_livreurs[df_livreurs['Nom'].str.upper() == str(livreur_choisi).upper()]
            if not row_l.empty:
                secteur_par_defaut = str(row_l.iloc[0]['Secteur']).strip().lower()
        
        # Sélecteur de secteur libre (choix de la région)
        default_idx = (all_sectors.index(secteur_par_defaut) + 1) if secteur_par_defaut in all_sectors else 0
        secteur_affichage = st.selectbox("🌍 Région / Secteur à traiter", ["Tous"] + all_sectors, index=default_idx)
        
        if secteur_affichage != "Tous":
            st.success(f"📍 Filtre actif : **{secteur_affichage.upper()}**")
        else:
            st.info("🔓 Affichage de toutes les régions")

    with col_d1:
        date_exp = st.date_input("Date d'expédition")

    # Préparation de la liste des clients selon le secteur choisi
    if secteur_affichage == "Tous":
        client_list_filtered = df_clients["Client"].dropna().astype(str).unique().tolist()
    else:
        df_c_filtre = df_clients[df_clients['Secteur'].astype(str).str.strip().str.lower() == secteur_affichage]
        client_list_filtered = df_c_filtre["Client"].dropna().astype(str).unique().tolist()

    st.divider()
    
    if mode == "Réclamation":
        with st.expander("📥 Importation groupée des Réclamations (Excel)", expanded=False):
            st.write(f"Importation pour le secteur : **{secteur_affichage.upper()}**")
            file_complaints = st.file_uploader("Glisser le fichier Excel ici", type=['xlsx', 'xls'], key="uploader_reclamations")
            
            if file_complaints:
                try:
                    df_reclam = pd.read_excel(file_complaints)
                    
                    import unicodedata
                    def clean_col(c):
                        c = str(c).strip().lower()
                        return ''.join(ch for ch in unicodedata.normalize('NFD', c) if unicodedata.category(ch) != 'Mn')
                    
                    df_reclam.columns = [clean_col(c) for c in df_reclam.columns]
                    
                    if 'client' in df_reclam.columns:
                        if 'statut' in df_reclam.columns:
                            df_reclam['statut_clean'] = df_reclam['statut'].astype(str).str.strip().str.lower()
                            df_to_add = df_reclam[df_reclam['statut_clean'].str.contains("en cours", na=False)].copy()
                        else:
                            df_to_add = df_reclam.dropna(subset=['client']).copy()
                        
                        if not df_to_add.empty:
                            df_clients_base = load_clients()
                            ville_map = dict(zip(df_clients_base['Client'].astype(str), df_clients_base['Ville']))
                            tel_map = dict(zip(df_clients_base['Client'].astype(str), df_clients_base['Tel']))
                            sect_map = dict(zip(df_clients_base['Client'].astype(str), df_clients_base['Secteur'].astype(str).str.strip().str.lower()))
                            
                            added_count = 0
                            skipped_count = 0
                            for _, row in df_to_add.iterrows():
                                client_name = str(row['client']).strip()
                                
                                # Détermination du secteur : Priorité au fichier Excel, puis à la base locale
                                file_secteur = ""
                                if 'region' in row: file_secteur = str(row['region']).strip().lower()
                                elif 'secteur' in row: file_secteur = str(row['secteur']).strip().lower()
                                
                                client_secteur = file_secteur if file_secteur else sect_map.get(client_name, "")
                                
                                # Filtrage selon le secteur d'affichage (si pas "Tous")
                                if secteur_affichage != "Tous" and client_secteur != secteur_affichage:
                                    skipped_count += 1
                                    continue
                                
                                ref_val = str(row['reference']).strip() if 'reference' in df_reclam.columns and pd.notna(row['reference']) else "Réclamation non validée"
                                ville = str(row['ville']).strip() if 'ville' in row else ville_map.get(client_name, "")
                                telephone = str(row['tel']).strip() if 'tel' in row else tel_map.get(client_name, "")
                                info_str = f"Tel: {telephone}" if telephone else ""
                                
                                add_or_merge_row(client_name, ville, ref_val, "RÉCLAMATION IMPORTÉE", "En cours", info_str, mode="Réclamation", secteur=client_secteur)
                                added_count += 1
                            
                            if added_count > 0:
                                st.success(f"✅ {added_count} réclamations ajoutées !")
                                if skipped_count > 0:
                                    st.info(f"ℹ️ {skipped_count} lignes ignorées (hors secteur {secteur_affichage.upper()}).")
                                log_action(st.session_state.current_user['username'], f"Importation réclamations ({secteur_affichage})", "Expédition")
                            else:
                                st.error(f"❌ Aucune donnée correspondant au secteur **{secteur_affichage.upper()}**.")
                        else:
                            st.info("Aucune réclamation valide trouvée.")
                    else:
                        st.error(f"Colonne 'client' manquante. Trouvé: {list(df_reclam.columns)}")
                except Exception as e:
                    st.error(f"Erreur : {e}")

    # Formulaire d'ajout manuel
    c1, c2, c3, c4 = st.columns([2, 1.5, 1.5, 1])
    with c1:
        new_client = st.selectbox("Client", client_list_filtered, index=None, placeholder="Rechercher ou sélectionner un client...")
    with c2:
        ref_bon = st.text_input("Réf. Bon")
    with c3:
        if mode == "Commande":
            val_info = st.text_input("Colissage")
        else:
            liste_motifs = load_motifs()
            val_motif = st.selectbox("Motif", liste_motifs)
            if val_motif == "MANQUE":
                extra_colis = st.text_input("📦 Colissage (Manque)")
                val_info = f"MANQUE: {extra_colis}" if extra_colis else "MANQUE"
            else:
                val_info = val_motif
    with c4:
        st.write("###")
        btn_ajouter = st.button("➕ Ajouter")

    if btn_ajouter:
        if new_client and ref_bon:
            annee = datetime.now().strftime('%y')
            prefixe = "RC" if mode == "Réclamation" else "BL"
            full_ref = f"{annee}/{prefixe}/{ref_bon}"
            # Récupération de la ville et du secteur du client depuis la base complète
            client_data = df_clients[df_clients['Client'] == new_client]
            ville = client_data['Ville'].values[0] if not client_data.empty else ""
            secteur_client = str(client_data['Secteur'].values[0]).strip().lower() if not client_data.empty else ""
            
            add_or_merge_row(new_client, ville, full_ref, val_info, "En cours", "", mode=mode, secteur=secteur_client)
            st.rerun()
        elif not new_client:
            st.error("Veuillez sélectionner un client.")
        elif not ref_bon:
            st.error("Veuillez saisir la référence du bon.")

    # --- OPTIMISATION IA ---
    if is_ia_enabled() and not st.session_state.rows.empty:
        st.divider()
        with st.expander("🤖 Assistant IA Logistique"):
            c_ia1, c_ia2 = st.columns(2)
            with c_ia1:
                if st.button("🗺️ Optimiser l'ordre de livraison", use_container_width=True):
                    with st.spinner("L'IA calcule l'itinéraire optimal..."):
                        villes = st.session_state.rows['Ville'].tolist()
                        prompt = f"Tu es un expert en logistique en Algérie. Voici une liste de villes pour une tournée de livraison : {villes}. Donne l'ordre le plus logique pour minimiser les kilomètres. Réponds par une liste simple."
                        st.info(ask_ai(prompt))
            with c_ia2:
                if mode == "Réclamation" and st.button("🧠 Analyser la gravité des litiges", use_container_width=True):
                    with st.spinner("Analyse IA en cours..."):
                        motifs = st.session_state.rows['Info'].tolist()
                        prompt = f"Voici des motifs de réclamations clients : {motifs}. Lesquels sont les plus critiques pour un grossiste pharma ? Donne une priorité."
                        st.warning(ask_ai(prompt))

    # --- FILTRAGE DYNAMIQUE DU TABLEAU ---
    # On filtre le tableau selon le secteur d'affichage choisi (Région)
    if secteur_affichage == "Tous":
        df_visible = st.session_state.rows
    else:
        df_visible = st.session_state.rows[st.session_state.rows['Secteur'].astype(str).str.strip().str.lower() == secteur_affichage.lower()]

    st.subheader(f"Détails des {mode}s ({secteur_affichage.upper()})")
    
    # Configuration dynamique de la colonne Info selon le mode
    col_label = "Colissage" if mode == "Commande" else "Motif"
    if mode == "Réclamation":
        info_config = st.column_config.SelectboxColumn("Motif", options=load_motifs())
    else:
        info_config = st.column_config.TextColumn("Colissage")

    # Édition du tableau filtré
    edited_df = st.data_editor(
        df_visible, 
        num_rows="dynamic", 
        use_container_width=True, 
        column_config={
            "Info": info_config,
            "Statut": st.column_config.SelectboxColumn("Statut", options=["En cours", "Livré", "Reporté", "Annulé"]),
            "Signature": None,
            "Secteur": st.column_config.TextColumn("Secteur", disabled=True)
        }
    )
    
    # Synchronisation : On met à jour les lignes modifiées dans la session globale
    if not edited_df.equals(df_visible):
        if secteur_affichage == "Tous":
            st.session_state.rows = edited_df
        else:
            other_sectors = st.session_state.rows[st.session_state.rows['Secteur'].astype(str).str.strip().str.lower() != secteur_affichage.lower()]
            st.session_state.rows = pd.concat([other_sectors, edited_df], ignore_index=True)
    
    if st.button("🗑️ Vider le secteur/filtre actuel"):
        if secteur_affichage == "Tous":
            st.session_state.rows = pd.DataFrame(columns=st.session_state.rows.columns)
        else:
            st.session_state.rows = st.session_state.rows[st.session_state.rows['Secteur'].astype(str).str.strip().str.lower() != secteur_affichage.lower()]
        st.rerun()
        
    if st.button("🖨️ Générer la Feuille de Route (PDF)"):
        if not df_visible.empty:
            try:
                # Génération du QR Code
                mission_id = f"M-{int(datetime.now().timestamp())}"
                qr_data = f"ID:{mission_id}|Livreur:{livreur_choisi}|Secteur:{secteur_affichage}|Date:{datetime.now().strftime('%d/%m/%Y')}|Nb:{len(df_visible)}"
                qr = qrcode.make(qr_data)
                qr_path = "temp_qr.png"
                qr.save(qr_path)
                
                pdf = FPDF()
                pdf.add_page()
                pdf.set_font("Arial", 'B', 16)
                pdf.cell(0, 10, f"FEUILLE DE ROUTE - {livreur_choisi}", 0, 1, 'C')
                pdf.set_font("Arial", 'B', 12)
                pdf.cell(0, 8, f"SECTEUR : {secteur_affichage.upper()}", 0, 1, 'C')
                pdf.set_font("Arial", '', 11)
                pdf.cell(0, 10, f"Date: {date_exp}   |   Total Clients: {len(df_visible)}", 0, 1, 'C')
                
                pdf.image(qr_path, x=170, y=10, w=30)
                pdf.ln(10)
                
                pdf.set_font("Arial", 'B', 10)
                pdf.cell(45, 8, "Client", 1)
                pdf.cell(30, 8, "Ville", 1)
                pdf.cell(40, 8, "N Doc", 1)
                pdf.cell(25, 8, col_label, 1)
                pdf.cell(20, 8, "Statut", 1)
                pdf.cell(30, 8, "Signature", 1)
                pdf.ln()
                
                pdf.set_font("Arial", '', 9)
                for _, row in df_visible.iterrows():
                    c = str(row.get('Client', '')).encode('latin-1', 'replace').decode('latin-1')
                    v = str(row.get('Ville', '')).encode('latin-1', 'replace').decode('latin-1')
                    d = str(row.get('N° Doc', '')).encode('latin-1', 'replace').decode('latin-1')
                    i = str(row.get('Info', '')).encode('latin-1', 'replace').decode('latin-1')
                    s = str(row.get('Statut', '')).encode('latin-1', 'replace').decode('latin-1')
                    
                    pdf.cell(45, 8, c[:22], 1)
                    pdf.cell(30, 8, v[:13], 1)
                    pdf.cell(40, 8, d[:20], 1)
                    pdf.cell(25, 8, i[:12], 1)
                    pdf.cell(20, 8, s[:10], 1)
                    pdf.cell(30, 8, "", 1)
                    pdf.ln()
                    
                pdf_bytes = pdf.output(dest='S').encode('latin-1', 'replace')
                if os.path.exists(qr_path):
                    os.remove(qr_path)
                    
                log_action(st.session_state.current_user['username'], f"Génération PDF Expédition pour {livreur_choisi}", "Expédition")
                
                st.download_button(
                    label="📥 Télécharger le PDF",
                    data=pdf_bytes,
                    file_name=f"Feuille_Route_{livreur_choisi}_{date_exp}.pdf",
                    mime="application/pdf",
                    type="primary"
                )
                
                st.success("✅ PDF prêt ! Une fois téléchargé, cliquez ci-dessous pour archiver et passer au livreur suivant.")
                if st.button("🏁 Valider l'envoi & Vider le tableau", type="secondary"):
                    log_action(st.session_state.current_user['username'], f"Validation finale tournée {livreur_choisi}", "Expédition")
                    st.session_state.rows = pd.DataFrame(columns=["Client", "Ville", "Secteur", "N° Doc", "Info", "Statut", "Signature"])
                    st.success("Tableau vidé ! Vous pouvez sélectionner un autre livreur.")
                    st.rerun()
            except Exception as e:
                st.error(f"Erreur PDF : {e}")
        else:
            st.warning("Le tableau est vide.")

# 1.1 SUIVI DES LITIGES (SAV)
with tab_suivi_sav:
    st.header("📊 Historique et Suivi des Réclamations")
    
    reclams_all = table_reclam.all()
    if not reclams_all:
        st.info("Aucun litige enregistré dans l'historique.")
    else:
        df_sav = pd.DataFrame(reclams_all)
        df_sav['date_crea'] = pd.to_datetime(df_sav['date_crea'])
        
        # Alerte retard (> 48h)
        now = datetime.now()
        df_sav['retard'] = (now - df_sav['date_crea']).dt.total_seconds() / 3600 > 48
        retards_count = df_sav[(df_sav['retard']) & (df_sav['statut'] == 'En cours')].shape[0]
        
        if retards_count > 0:
            st.error(f"🚨 {retards_count} réclamation(s) en attente depuis plus de 48 heures !")
        
        # Filtres
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            filtre_statut = st.selectbox("Filtrer par statut", ["Tous", "En cours", "Livré", "Annulé"])
        
        if filtre_statut != "Tous":
            df_sav = df_sav[df_sav['statut'] == filtre_statut]
            
        # Stats motifs
        st.subheader("📈 Analyse des Motifs")
        df_motif_stats = df_sav['motif'].value_counts().reset_index()
        df_motif_stats.columns = ['Motif', 'Nombre']
        import plotly.express as px
        fig_motifs = px.bar(df_motif_stats, x='Motif', y='Nombre', color='Nombre', template="plotly_dark")
        st.plotly_chart(fig_motifs, use_container_width=True)
        
        # Liste éditable pour clore les litiges
        st.subheader("📝 Liste détaillée")
        edited_sav = st.data_editor(
            df_sav.sort_values('date_crea', ascending=False),
            use_container_width=True,
            column_config={
                "statut": st.column_config.SelectboxColumn("Statut", options=["En cours", "Livré", "Annulé"]),
                "retard": None # On cache la colonne technique
            }
        )
        
        if st.button("💾 Mettre à jour l'historique"):
            # Pour chaque ligne modifiée, mettre à jour la TinyDB
            # (Note: une implémentation plus complexe utiliserait l'ID TinyDB, 
            # ici on écrase tout le tableau pour faire simple dans ce contexte)
            table_reclam.truncate()
            # On retire la colonne technique 'retard' avant sauvegarde
            df_to_save = edited_sav.drop(columns=['retard'])
            # Conversion date en string pour JSON
            df_to_save['date_crea'] = df_to_save['date_crea'].dt.strftime("%Y-%m-%d %H:%M")
            table_reclam.insert_multiple(df_to_save.to_dict('records'))
            st.success("Historique mis à jour !")
            st.rerun()

# 2. GESTION DES LIVREURS
with tab_livreurs:
    st.header("👤 Gestion des Livreurs")
    st.info("La gestion des livreurs est désormais centralisée. Veuillez utiliser le module **Admin Centrale** pour modifier, ajouter ou affecter des livreurs.")
    if st.button("🚀 Aller à l'Administration Centrale", use_container_width=True, key="go_admin_liv"):
        st.switch_page("pages/0_admin_centrale.py")

# 3. GESTION DES SECTEURS (Clients)
with tab_secteurs:
    st.header("📍 Gestion des Clients & Secteurs")
    st.info("La cartographie des secteurs et la base clients logistique sont désormais centralisées.")
    if st.button("🚀 Aller à l'Administration Centrale", use_container_width=True, key="go_admin_sec"):
        st.switch_page("pages/0_admin_centrale.py")

# 4. ADMINISTRATION
with tab_admin:
    st.header("⚙️ Paramètres du module")
    
    st.subheader("📋 Gestion des Motifs (Réclamations)")
    current_motifs = load_motifs()
    
    col_m1, col_m2 = st.columns([2, 1])
    with col_m1:
        new_motif = st.text_input("Nouveau motif")
    with col_m2:
        st.write("###")
        if st.button("➕ Ajouter Motif"):
            if new_motif and new_motif not in current_motifs:
                current_motifs.append(new_motif)
                save_motifs(current_motifs)
                st.rerun()
    
    # Liste des motifs avec bouton supprimer
    st.write("Motifs actuels :")
    for i, m in enumerate(current_motifs):
        c_m1, c_m2 = st.columns([3, 1])
        c_m1.text(f"• {m}")
        if c_m2.button("🗑️", key=f"del_m_{i}"):
            current_motifs.pop(i)
            save_motifs(current_motifs)
            st.rerun()

    st.divider()
    if st.session_state.current_user.get('role') == 'Admin':
        st.subheader("🗑️ Nettoyage des Données (Admin)")
        st.error("⚠️ Cette action videra toutes les expéditions en cours pour tous les secteurs.")
        confirm_route = st.checkbox("Confirmer la réinitialisation des feuilles de route")
        if st.button("🔴 Réinitialiser toutes les Feuilles de Route", use_container_width=True, disabled=not confirm_route):
            st.session_state.rows = pd.DataFrame(columns=["Client", "Ville", "Secteur", "N° Doc", "Info", "Statut", "Signature"])
            st.success("Toutes les feuilles de route ont été réinitialisées.")
            st.rerun()
    else:
        st.info("Les fonctions de nettoyage sont réservées à l'administrateur.")
