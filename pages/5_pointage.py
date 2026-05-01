import streamlit as st
import pandas as pd
from tinydb import TinyDB, Query
from datetime import datetime
import os
from utils import log_action

# --- CONFIGURATION ET BASE DE DONNÉES ---
# st.set_page_config(page_title="Pharmaciel Pro - Pointage", layout="wide", page_icon="🚚")

# Initialisation de la base de données locale
db = TinyDB('db_pharmaciel.json')
table_livreurs = db.table('livreurs')
table_pointage = db.table('pointages')

# --- FONCTIONS DE GESTION ---
def ajouter_livreur(nom):
    if not table_livreurs.search(Query().nom == nom):
        table_livreurs.insert({'nom': nom})
        return True
    return False

def get_livreurs():
    return [item['nom'] for item in table_livreurs.all()]

def archive_pointages_mensuel():
    """Archive les pointages des mois précédents vers un dossier archive."""
    now = datetime.now()
    all_data = table_pointage.all()
    if not all_data: return
    
    archive_dir = "data_archive"
    os.makedirs(archive_dir, exist_ok=True)
    
    data_to_archive = {}
    data_to_keep = []
    
    for item in all_data:
        try:
            dt = datetime.strptime(item['date_pointage'], "%d/%m/%Y %H:%M")
            if dt.month != now.month or dt.year != now.year:
                key = dt.strftime("%Y_%m")
                if key not in data_to_archive: data_to_archive[key] = []
                data_to_archive[key].append(item)
            else:
                data_to_keep.append(item)
        except:
            data_to_keep.append(item)
            
    if data_to_archive:
        import json
        for key, data in data_to_archive.items():
            archive_file = os.path.join(archive_dir, f"pointage_archive_{key}.json")
            with open(archive_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        
        table_pointage.truncate()
        if data_to_keep:
            table_pointage.insert_multiple(data_to_keep)
        return True
    return False

# Exécution de l'archivage automatique au chargement
archive_pointages_mensuel()

st.header("📝 Pointage des Factures", divider="red")

tab_pointage, tab_admin, tab_historique = st.tabs([
    "📋 Pointage Factures", "⚙️ Gestion des Livreurs", "📊 Historique"
])

# --- ONGLET ADMINISTRATION ---
with tab_admin:
    st.header("⚙️ Gestion des Livreurs")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Ajouter un agent")
        nouveau_nom = st.text_input("Nom du livreur (ex: Fares, Ayoub...)")
        if st.button("Enregistrer le livreur"):
            if nouveau_nom:
                if ajouter_livreur(nouveau_nom.strip().upper()):
                    st.success(f"Livreur {nouveau_nom} ajouté !")
                    st.rerun()
                else:
                    st.warning("Ce livreur existe déjà.")
    
    with col2:
        st.subheader("Équipe actuelle")
        livreurs = get_livreurs()
        if livreurs:
            for l in livreurs:
                st.text(f"• {l}")
            
            st.divider()
            if st.button("🗑️ Vider tout l'historique de pointage", type="primary"):
                table_pointage.truncate()
                st.success("Historique vidé !")
                st.rerun()
        else:
            st.info("Aucun livreur enregistré.")

# --- ONGLET POINTAGE ---
with tab_pointage:

    # 1. Importation du fichier Excel
    uploaded_file = st.file_uploader("Importer l'export LogiPharm (Excel)", type=['xlsx'])

    if uploaded_file:
        try:
            df = pd.read_excel(uploaded_file)
            
            # Normalisation robuste des colonnes (gestion des accents, espaces et casses)
            import unicodedata
            def clean_col(c):
                c = str(c).strip().lower()
                return ''.join(ch for ch in unicodedata.normalize('NFD', c) if unicodedata.category(ch) != 'Mn')
            
            df.columns = [clean_col(c) for c in df.columns]
            
            cols_attendues = ['client', 'reference', 'region', 'date creation']
            
            if all(c in df.columns for c in cols_attendues):
                df_clean = df[cols_attendues].copy()
                
                # --- FILTRES ---
                col_a, col_b, col_c = st.columns(3)
                
                with col_a:
                    liste_regions = sorted(df_clean['region'].dropna().unique())
                    region_sel = st.selectbox("📍 Sélectionner la Région (Secteur)", liste_regions)
                
                with col_b:
                    reg_str = str(region_sel).lower()
                    opts_rotation = ["1ère Rotation (Matin)", "2ème Rotation (Après-midi)"]
                    
                    if "blida" in reg_str:
                        opts_rotation = ["2ème Rotation (Après-midi)"]
                    elif any(r in reg_str for r in ["alger est", "tipaza", "medea", "chlef", "djelfa", "oran", "tizi ouzou", "tissemssilt", "relizane"]):
                        opts_rotation = ["1ère Rotation (Matin)"]
                        
                    rotation_sel = st.selectbox("🔄 Rotation", opts_rotation)
                    
                    # Filtre de date et heure pour la rotation
                    st.write("📅 Période de préparation :")
                    
                    # Date de préparation (par défaut aujourd'hui)
                    default_date = datetime.now().date()
                    d_sel = st.date_input("Date", value=default_date)
                    
                    time_filter_active = False
                    if "1ère Rotation" in rotation_sel:
                        tc1, tc2 = st.columns(2)
                        with tc1:
                            t_start = st.time_input("Début", value=datetime.strptime("00:00", "%H:%M").time(), key="t1")
                        with tc2:
                            t_end = st.time_input("Fin", value=datetime.strptime("23:59", "%H:%M").time(), key="t2")
                        time_filter_active = True
                    else:
                        t_start, t_end = None, None

                with col_c:
                    liste_livreurs = get_livreurs()
                    if not liste_livreurs:
                        st.error("⚠️ Allez dans 'Administration' pour ajouter des livreurs d'abord.")
                        livreur_sel = None
                    else:
                        idx_livreur = 0
                        if "alger 1" in reg_str:
                            match = [i for i, l in enumerate(liste_livreurs) if "fethi" in l.lower()]
                            if match: idx_livreur = match[0]
                        elif "alger 2" in reg_str:
                            match = [i for i, l in enumerate(liste_livreurs) if "fares" in l.lower()]
                            if match: idx_livreur = match[0]
                            
                        livreur_sel = st.selectbox("🚚 Affecter au Livreur", liste_livreurs, index=idx_livreur)

                if livreur_sel:
                    # --- LOGIQUE DE FILTRAGE ---
                    df_filtre = df_clean[df_clean['region'] == region_sel].copy()
                    
                    # Conversion en datetime
                    df_filtre['dt_creation'] = pd.to_datetime(df_filtre['date creation'], dayfirst=True)
                    
                    # Filtre de Date obligatoire
                    df_filtre = df_filtre[df_filtre['dt_creation'].dt.date == d_sel]
                    
                    # Filtre d'Heure (si applicable)
                    if time_filter_active:
                        df_filtre = df_filtre[
                            (df_filtre['dt_creation'].dt.time >= t_start) & 
                            (df_filtre['dt_creation'].dt.time <= t_end)
                        ]
                    
                    # --- DETECTION DES DOUBLONS (Factures déjà pointées) ---
                    existing_refs = {item['reference'] for item in table_pointage.all()}
                    df_filtre['deja_pointe'] = df_filtre['reference'].isin(existing_refs)

                    # --- ACTIONS DE MASSE ET PDF ---
                    st.divider()
                    
                    # Gestion de la sélection globale
                    if 'sel_all' not in st.session_state: st.session_state.sel_all = False
                    
                    c_act1, c_act2, c_act3 = st.columns([1, 1, 1])
                    with c_act1:
                        if st.button("✅ Tout Sélectionner" if not st.session_state.sel_all else "⬜ Tout Désélectionner"):
                            st.session_state.sel_all = not st.session_state.sel_all
                            st.rerun()
                    
                    with c_act2:
                        # Fonction PDF (Simplifiée pour fpdf standard)
                        def create_pdf_bytes(livreur, region, rotation, date, df_rows):
                            from fpdf import FPDF
                            pdf = FPDF()
                            pdf.add_page()
                            pdf.set_font("Arial", 'B', 16)
                            pdf.cell(0, 10, f"FEUILLE DE POINTAGE - {date}", ln=True, align='C')
                            pdf.ln(5)
                            pdf.set_font("Arial", 'B', 12)
                            pdf.cell(0, 10, f"Livreur : {livreur}", ln=True)
                            pdf.cell(0, 10, f"Secteur : {region} ({rotation})", ln=True)
                            pdf.ln(5)
                            # Header
                            pdf.set_font("Arial", 'B', 10)
                            pdf.cell(15, 10, "OK", 1, 0, 'C')
                            pdf.cell(50, 10, "Facture", 1, 0, 'C')
                            pdf.cell(125, 10, "Client", 1, 1, 'C')
                            # Rows
                            pdf.set_font("Arial", '', 9)
                            for _, r in df_rows.iterrows():
                                if r.get('deja_pointe'): continue # Ne pas imprimer les déjà pointées
                                pdf.cell(15, 8, "[  ]", 1, 0, 'C')
                                pdf.cell(50, 8, str(r['reference']), 1)
                                pdf.cell(125, 8, str(r['client'])[:55], 1, 1)
                            return pdf.output(dest='S').encode('latin-1', 'ignore')

                        if not df_filtre.empty:
                            pdf_bytes = create_pdf_bytes(livreur_sel, region_sel, rotation_sel, d_sel, df_filtre)
                            st.download_button("📥 Télécharger PDF (Impression)", pdf_bytes, f"Pointage_{livreur_sel}_{d_sel}.pdf", "application/pdf")
                    
                    with c_act3:
                        if st.button("🖨️ Préparer Impression"):
                            st.info("Utilisez Ctrl+P pour imprimer la page web si vous préférez le format direct.")

                    # --- AFFICHAGE POUR IMPRESSION ---
                    st.markdown(f"""
                    <div style="background-color: #ffffff; padding: 20px; border-radius: 10px; border: 2px solid #ff4b4b; margin-bottom: 20px; color: black;">
                        <h1 style="margin: 0; font-size: 40px;">Livreur : {livreur_sel}</h1>
                        <h2 style="margin: 5px 0 0 0; font-size: 24px;">Secteur : {region_sel} | {rotation_sel} | Date : {d_sel}</h2>
                    </div>
                    """, unsafe_allow_html=True)

                    st.subheader(f"📊 Factures à vérifier ({len(df_filtre)})")
                    
                    df_view = df_filtre.copy()
                    df_view.insert(0, "OK", "[  ]")
                    
                    # On ne sélectionne par défaut que celles qui ne sont pas déjà pointées
                    df_view.insert(1, "Validé", st.session_state.sel_all & ~df_view['deja_pointe'])
                    
                    # Formatter pour le statut
                    df_view['Statut System'] = df_view['deja_pointe'].apply(lambda x: "✅ Déjà Pointé" if x else "🆕 Nouveau")
                    
                    edited_df = st.data_editor(
                        df_view,
                        column_config={
                            "OK": st.column_config.TextColumn("Pointage Papier", width="small", disabled=True),
                            "Validé": st.column_config.CheckboxColumn("Saisi Karim", default=False),
                            "Statut System": st.column_config.TextColumn("État", disabled=True),
                            "reference": st.column_config.TextColumn("N° Facture", disabled=True),
                            "client": st.column_config.TextColumn("Nom du Client", disabled=True),
                            "date creation": st.column_config.TextColumn("Heure Prep", disabled=True),
                            "region": None,
                            "dt_creation": None,
                            "deja_pointe": None
                        },
                        hide_index=True,
                        use_container_width=True,
                        key=f"editor_{livreur_sel}_{d_sel}_{st.session_state.sel_all}" # Force update on toggle
                    )

                    # 3. Bouton d'enregistrement / Archivage
                    if st.button("📁 Archiver & Confirmer le pointage"):
                        factures_ok = edited_df[edited_df['Validé'] == True]
                        
                        if not factures_ok.empty:
                            new_recouv_rows = []
                            for _, row in factures_ok.iterrows():
                                table_pointage.insert({
                                    'date_pointage': datetime.now().strftime("%d/%m/%Y %H:%M"),
                                    'date_feuille': str(d_sel),
                                    'livreur': livreur_sel,
                                    'rotation': rotation_sel,
                                    'reference': row['reference'],
                                    'client': row['client'],
                                    'region': row['region'],
                                    'statut_karim': "Archivé"
                                })
                                
                                # Préparation des données pour le module Recouvrement
                                new_recouv_rows.append({
                                    "Client": row['client'],
                                    "Facture": row['reference'],
                                    "Mode Paiement": "À Définir",
                                    "Région": row['region'],
                                    "Reste à payer": 0.0,
                                    "Livreur": livreur_sel,
                                    "Date": datetime.now().strftime("%d/%m/%Y"),
                                    "Statut": "Non Payé"
                                })
                            
                            # Insertion dans Recouvrement (CSV)
                            recouv_file = "data_recouvrement.csv"
                            if os.path.exists(recouv_file):
                                df_recouv = pd.read_csv(recouv_file)
                                if "Facture" not in df_recouv.columns: df_recouv["Facture"] = ""
                            else:
                                df_recouv = pd.DataFrame(columns=["Client", "Facture", "Mode Paiement", "Région", "Reste à payer", "Livreur", "Date", "Statut"])
                                
                            df_new_recouv = pd.DataFrame(new_recouv_rows)
                            df_recouv = pd.concat([df_recouv, df_new_recouv], ignore_index=True)
                            df_recouv.to_csv(recouv_file, index=False)
                            
                            log_action(st.session_state.current_user['username'], f"Archivage pointage {len(factures_ok)} factures ({livreur_sel})", "Pointage")
                            st.success(f"✅ {len(factures_ok)} factures archivées avec succès !")
                            st.balloons()
                        else:
                            st.warning("Veuillez cocher les factures reçues avant d'archiver.")
            else:
                st.error(f"Erreur de colonnes. Votre fichier contient : {list(df.columns)}")
                st.info("Le fichier doit contenir exactement : Client, Référence, Région")
                
        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier : {e}")

# --- ONGLET HISTORIQUE ---
with tab_historique:
    st.subheader("📊 Historique des derniers pointages")
    data_hist = table_pointage.all()
    if data_hist:
        df_hist = pd.DataFrame(data_hist)
        st.dataframe(df_hist.sort_values('date_pointage', ascending=False).head(50), use_container_width=True)
    else:
        st.write("Aucun historique pour le moment.")

