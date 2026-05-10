import streamlit as st
import pandas as pd
from datetime import datetime
import os
import plotly.express as px
from fpdf import FPDF
from utils import log_action
from utils_ia import ask_ai, is_ia_enabled
from utils_gsheets import load_gs_data, save_gs_data
# --- CONFIGURATION ---
WORKSHEET_SUIVI = "Suivi_Frigo"
FALLBACK_SUIVI = "suivi_data.csv"
CHAMBRES = ["Chambre Froide 1", "Chambre Froide 2"]
COLS_SUIVI = ["Date", "Heure", "Température", "Agent", "Statut", "Commentaire", "Type", "Chambre"]

# Initialisation du fuseau horaire dans le session_state
if "tz_offset" not in st.session_state:
    st.session_state.tz_offset = 1 # Défaut GMT+1

if "current_user" not in st.session_state or st.session_state.current_user is None:
    st.warning("Veuillez vous connecter depuis la page principale.")
    st.stop()

# --- FONCTIONS TEMPORELLES ---
from datetime import timedelta
def get_now():
    return datetime.utcnow() + timedelta(hours=st.session_state.tz_offset)

# --- FONCTIONS ---
def clean_frigo_data(df):
    if 'Température' in df.columns:
        df['Température'] = pd.to_numeric(df['Température'], errors='coerce')
        df.loc[(df['Température'] >= 2.0) & (df['Température'] <= 8.0), 'Statut'] = 'OK'
        df.loc[(df['Température'] < 2.0) | (df['Température'] > 8.0), 'Statut'] = 'ALERTE'
    if 'Type' in df.columns:
        df['Type'] = df['Type'].replace('Relevé Standard', 'Plage idéale :+2°C+8°C')
    if 'Chambre' not in df.columns:
        df['Chambre'] = CHAMBRES[0]
    else:
        # Gérer les valeurs vides ou NaN issues de l'ancien format
        df['Chambre'] = df['Chambre'].astype(str).str.strip().replace(["nan", "None", ""], CHAMBRES[0])
        df['Chambre'] = df['Chambre'].fillna(CHAMBRES[0])
    return df


def generer_pdf(df, chambre_name):
    pdf = FPDF()
    pdf.add_page()
    if os.path.exists("logo.png"):
        try: pdf.image("logo.png", x=10, y=8, w=30)
        except: pass
    pdf.set_font("Arial", 'B', 15)
    pdf.cell(0, 10, "DARPHARM SOLUTION", 0, 1, 'C')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, f"RAPPORT DE SUIVI : {chambre_name.upper()}", 0, 1, 'C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 6, "(Plage cible : +2 C a +8 C)", 0, 1, 'C')
    pdf.set_font("Arial", 'I', 9)
    pdf.cell(0, 6, f"Extrait le : {get_now().strftime('%d/%m/%Y a %H:%M')}", 0, 1, 'C')
    pdf.ln(8)
    
    nb_releves = len(df)
    moyenne = df['Température'].mean() if nb_releves > 0 else 0
    alertes = len(df[df['Statut'] == 'ALERTE'])
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 6, "Resume des releves :", 0, 1)
    pdf.set_font("Arial", '', 9)
    pdf.cell(0, 5, f"- Total des releves : {nb_releves}", 0, 1)
    pdf.cell(0, 5, f"- Temperature moyenne : {moyenne:.1f} C", 0, 1)
    pdf.cell(0, 5, f"- Nombre d'alertes : {alertes}", 0, 1)
    pdf.ln(6)
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font("Arial", 'B', 8)
    w = [25, 15, 20, 20, 60, 50]
    cols = ["Date", "Heure", "Temp (C)", "Statut", "Motif", "Agent"]
    for i, head in enumerate(cols): pdf.cell(w[i], 7, head, border=1, fill=True, align='C')
    pdf.ln()
    pdf.set_font("Arial", '', 8)
    for _, row in df.iterrows():
        if str(row['Statut']) == "ALERTE": pdf.set_text_color(200, 0, 0)
        else: pdf.set_text_color(0, 100, 0)
        pdf.cell(w[0], 6, str(row['Date']), border=1, align='C')
        pdf.cell(w[1], 6, str(row['Heure']), border=1, align='C')
        pdf.cell(w[2], 6, f"{row['Température']} C", border=1, align='C')
        pdf.cell(w[3], 6, str(row['Statut']), border=1, align='C')
        pdf.set_text_color(0, 0, 0)
        pdf.cell(w[4], 6, str(row['Type'])[:35], border=1)
        pdf.cell(w[5], 6, str(row['Agent'])[:25], border=1, ln=1)
    raw = pdf.output()
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    return raw.encode('latin-1', 'replace')

def get_data():
    df = load_gs_data(WORKSHEET_SUIVI, FALLBACK_SUIVI, COLS_SUIVI)
    if not df.empty:
        df = clean_frigo_data(df)
        conn_status = "green"
    else:
        conn_status = "orange"
    return df, conn_status, None

def save_data(data):
    df_old = load_gs_data(WORKSHEET_SUIVI, FALLBACK_SUIVI, COLS_SUIVI)
    df_new = pd.concat([df_old, pd.DataFrame([data])], ignore_index=True)
    save_gs_data(df_new, WORKSHEET_SUIVI, FALLBACK_SUIVI)
    
    log_action(data['Agent'], f"T° {data['Chambre']}: {data['Température']}°C", "Suivi Frigo")
    if data['Statut'] == "ALERTE":
        st.error(f"🚨 ALERTE {data['Chambre']} : {data['Température']}°C !")
    else:
        st.success(f"✅ Enregistré pour {data['Chambre']}")

# --- UI INTERFACE ---
col_head1, col_head2 = st.columns([3, 1])
with col_head1:
    st.title(f"🌡️ Suivi T° - {st.session_state.current_user['username']}")
with col_head2:
    df_all, conn_status, error_msg = get_data()
    if conn_status == "green": st.success("📡 GSheets Online")
    elif conn_status == "orange": st.warning("💾 Mode Local")
    else: st.error("❌ Connexion Échouée")
    st.caption(f"Maj: {get_now().strftime('%H:%M')}")

tabs = st.tabs(["📝 Saisie CF1", "📝 Saisie CF2", "📊 Dashboard CF1", "📊 Dashboard CF2", "📋 Fiche Manuelle", "⚙️ Admin"])

# --- SAISIE ---
def render_saisie(chambre_name):
    st.subheader(f"Saisie : {chambre_name}")
    now = get_now()
    if st.button(f"🚀 Rapide (OK 4°C) - {chambre_name}", use_container_width=True):
        save_data({
            "Date": now.strftime("%d/%m/%Y"), "Heure": now.strftime("%H:%M"),
            "Température": 4.0, "Agent": st.session_state.current_user['username'],
            "Statut": "OK", "Commentaire": "Rapide", "Type": "Plage idéale :+2°C+8°C",
            "Chambre": chambre_name
        })
        st.rerun()

    with st.form(f"form_{chambre_name.replace(' ','_')}", clear_on_submit=True):
        t = st.number_input("Température (°C)", min_value=-20.0, max_value=30.0, value=4.0, step=0.1)
        motif = st.selectbox("Motif", ["Plage idéale :+2°C+8°C", "Arrivage", "Nettoyage", "Alerte technique"])
        comm = st.text_input("Commentaire")
        if st.form_submit_button("Enregistrer", use_container_width=True):
            save_data({
                "Date": now.strftime("%d/%m/%Y"), "Heure": now.strftime("%H:%M"),
                "Température": t, "Agent": st.session_state.current_user['username'],
                "Statut": "OK" if 2.0 <= t <= 8.0 else "ALERTE", "Commentaire": comm, "Type": motif,
                "Chambre": chambre_name
            })
            st.rerun()

with tabs[0]: render_saisie(CHAMBRES[0])
with tabs[1]: render_saisie(CHAMBRES[1])

# --- DASHBOARD ---
def render_dashboard(chambre_name, df_all):
    if df_all.empty:
        st.info(f"Aucune donnée globale disponible.")
        return

    # Nettoyage préventif pour le filtrage
    df_all['Chambre'] = df_all['Chambre'].astype(str).str.strip()
    df = df_all[df_all['Chambre'] == chambre_name.strip()].copy()
    
    if not df.empty:
        df['Timestamp'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Heure'].astype(str), format="%d/%m/%Y %H:%M", errors='coerce')
        # Gérer les formats modifiés par GSheets (ex: YYYY-MM-DD)
        mask = df['Timestamp'].isna()
        if mask.any():
            df.loc[mask, 'Timestamp'] = pd.to_datetime(df.loc[mask, 'Date'].astype(str) + ' ' + df.loc[mask, 'Heure'].astype(str), errors='coerce')
            
        last_entry = df.iloc[-1]
        if last_entry['Statut'] == "ALERTE":
            st.error(f"🚨 ATTENTION : La dernière température de la {chambre_name} ({last_entry['Température']}°C) est HORS PLAGE !")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Dernier Relevé", f"{last_entry['Température']} °C")
        c2.metric("Moyenne", f"{df['Température'].mean():.1f} °C")
        conformite = (len(df[df['Statut'] == 'OK']) / len(df)) * 100 if len(df) > 0 else 0
        c3.metric("Conformité", f"{conformite:.1f} %")
        c4.metric("Alertes", len(df[df['Statut'] == 'ALERTE']))
        st.plotly_chart(px.line(df.tail(50), x="Timestamp", y="Température", markers=True, title=f"Historique {chambre_name}"), use_container_width=True)
        col_exp1, col_exp2 = st.columns(2)
        with col_exp1:
            pdf = generer_pdf(df, chambre_name)
            st.download_button(f"📥 Rapport PDF {chambre_name}", data=pdf, file_name=f"Rapport_{chambre_name}.pdf", use_container_width=True)
        with col_exp2:
            if is_ia_enabled():
                if st.button(f"🤖 IA Analyse : {chambre_name}", use_container_width=True):
                    last_30 = df.tail(30)['Température'].tolist()
                    st.info(ask_ai(f"Analyse ces relevés pour {chambre_name} : {last_30}"))
        st.dataframe(df.sort_index(ascending=False), use_container_width=True)
    else:
        st.info(f"Aucune donnée pour {chambre_name}")

with tabs[2]: render_dashboard(CHAMBRES[0], df_all)
with tabs[3]: render_dashboard(CHAMBRES[1], df_all)

# --- ONGLET 4 : FICHE MANUELLE ---
with tabs[4]:
    st.subheader("📋 Génération de Fiche de Relevés Manuels")
    st.write("Générez un tableau vierge à imprimer pour vos relevés au stylo.")
    col_f1, col_f2 = st.columns(2)
    mois_noms = ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"]
    mois_sel = col_f1.selectbox("Mois", range(1, 13), format_func=lambda x: mois_noms[x-1], index=get_now().month - 1)
    annee_sel = col_f2.number_input("Année", value=get_now().year, step=1)
    room_fiche = st.selectbox("Chambre Froide concernée", CHAMBRES)
    if st.button("📄 Générer la fiche PDF", use_container_width=True):
        import calendar
        num_days = calendar.monthrange(annee_sel, mois_sel)[1]
        jours_valides = [datetime(annee_sel, mois_sel, d) for d in range(1, num_days + 1)]
        jours_valides = [d.strftime("%d/%m/%Y") for d in jours_valides if d.weekday() not in [4, 5]]
        pdf_f = FPDF()
        pdf_f.add_page()
        pdf_f.set_font("Arial", 'B', 14)
        pdf_f.cell(0, 10, f"FICHE DE SUIVI DES TEMPERATURES ET HUMIDITE", 0, 1, 'C')
        pdf_f.set_font("Arial", 'B', 11)
        pdf_f.cell(0, 8, f"{room_fiche.upper()} - {mois_noms[mois_sel-1]} {annee_sel}", 0, 1, 'C')
        pdf_f.ln(5)
        # Tableau
        pdf_f.set_font("Arial", 'B', 8)
        pdf_f.set_fill_color(230, 230, 230)
        h_cell = 7
        w_date, w_sub, w_rem = 25, 15, 75
        
        # Ligne 1 : En-têtes groupés
        pdf_f.cell(w_date, h_cell, " ", border=1)
        pdf_f.cell(w_sub*3, h_cell, "MATIN", border=1, fill=True, align='C')
        pdf_f.cell(w_sub*3, h_cell, "SOIR", border=1, fill=True, align='C')
        pdf_f.cell(w_rem, h_cell, " ", border=1, ln=1)
        
        # Ligne 2 : Sous-titres
        headers = ["Date", "Heure", "T (C)", "H (%)", "Heure", "T (C)", "H (%)", "Remarques"]
        widths = [w_date, w_sub, w_sub, w_sub, w_sub, w_sub, w_sub, w_rem]
        for i, head in enumerate(headers):
            pdf_f.cell(widths[i], h_cell, head, border=1, fill=True, align='C')
        pdf_f.ln()
        
        pdf_f.set_font("Arial", '', 8)
        for d_str in jours_valides:
            pdf_f.cell(w_date, h_cell, d_str, border=1, align='C')
            for _ in range(6): pdf_f.cell(w_sub, h_cell, "", border=1) # Matin + Soir
            pdf_f.cell(w_rem, h_cell, "", border=1, ln=1)
        _raw_f = pdf_f.output()
        _pdf_bytes_f = bytes(_raw_f) if isinstance(_raw_f, (bytes, bytearray)) else _raw_f.encode('latin-1')
        st.download_button("📥 Télécharger la fiche PDF", data=_pdf_bytes_f, file_name=f"Fiche_{mois_noms[mois_sel-1]}.pdf", type="primary")

# --- ADMIN ---
with tabs[5]:
    if st.session_state.current_user.get('role') == 'Admin':
        st.subheader("⚙️ Paramètres Système")
        st.session_state.tz_offset = st.number_input("Fuseau Horaire (GMT Offset)", value=st.session_state.tz_offset, step=1)
        st.caption(f"Heure actuelle : {get_now().strftime('%H:%M:%S')}")
        st.divider()
        st.subheader("🛠️ Gestion Administrative")
        df_edit = st.data_editor(df_all, use_container_width=True, num_rows="dynamic")
        if st.button("💾 Sauvegarder"):
            try:
                save_gs_data(df_edit, WORKSHEET_SUIVI, FALLBACK_SUIVI)
                st.success("Base de données mise à jour sur GSheets !")
                st.rerun()
            except Exception as e: st.error(f"Erreur: {e}")
        if st.button("🚀 Migrer vers GSheets"):
            try:
                if os.path.exists(FALLBACK_SUIVI):
                    df_local = pd.read_csv(FALLBACK_SUIVI)
                    save_gs_data(df_local, WORKSHEET_SUIVI, FALLBACK_SUIVI)
                    st.success("✅ Données locales migrées avec succès vers GSheets !")
                    st.rerun()
                else:
                    st.warning("Aucun fichier local trouvé.")
            except Exception as e: st.error(f"Erreur: {e}")
            
        st.divider()
        st.subheader("🗑️ Nettoyage des Données (Admin)")
        st.error("⚠️ Cette action supprimera définitivement tout l'historique des relevés de température.")
        confirm_suivi = st.checkbox("Confirmer la suppression du Suivi Global")
        if st.button("🔴 Réinitialiser le Suivi Global (GSheets)", disabled=not confirm_suivi, use_container_width=True):
            save_gs_data(pd.DataFrame(columns=COLS_SUIVI), WORKSHEET_SUIVI, FALLBACK_SUIVI)
            st.success("Historique des températures supprimé sur GSheets.")
            st.rerun()
    else:
        st.warning("Accès restreint.")
