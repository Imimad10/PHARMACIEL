import streamlit as st
import pandas as pd
from datetime import datetime
import os
import plotly.express as px
from fpdf import FPDF
from utils import log_action
from streamlit_gsheets import GSheetsConnection
from utils_ia import ask_ai, is_ia_enabled

# --- CONFIGURATION ---
# st.set_page_config(page_title="Darpharm Solution - Suivi Frigo", layout="wide")
DATA_FILE = "suivi_data.csv"

if "current_user" not in st.session_state or st.session_state.current_user is None:
    st.warning("Veuillez vous connecter depuis la page principale.")
    st.stop()


# --- FONCTIONS ---
def clean_frigo_data(df):
    if 'Température' in df.columns:
        df.loc[(df['Température'] >= 2.0) & (df['Température'] <= 8.0), 'Statut'] = 'OK'
        df.loc[(df['Température'] < 2.0) | (df['Température'] > 8.0), 'Statut'] = 'ALERTE'
    if 'Type' in df.columns:
        df['Type'] = df['Type'].replace('Relevé Standard', 'Plage idéale :+2°C+8°C')
    return df

def generer_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    
    # 1. Logo
    if os.path.exists("logo.png"):
        try:
            pdf.image("logo.png", x=10, y=8, w=30)
        except:
            pass
            
    # 2. En-tête
    pdf.set_font("Arial", 'B', 15)
    pdf.cell(0, 10, "DARPHARM SOLUTION", 0, 1, 'C')
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, "RAPPORT DE SUIVI FRIGO (+2 C a +8 C)", 0, 1, 'C')
    
    pdf.set_font("Arial", 'I', 9)
    extraction_date = datetime.now().strftime("%d/%m/%Y a %H:%M")
    pdf.cell(0, 6, f"Date d'extraction : {extraction_date}", 0, 1, 'C')
    pdf.ln(8)
    
    # 3. KPIs
    nb_releves = len(df)
    moyenne = df['Température'].mean() if nb_releves > 0 else 0
    alertes = len(df[df['Statut'] == 'ALERTE'])
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 6, "Resume des donnees :", 0, 1)
    pdf.set_font("Arial", '', 9)
    pdf.cell(0, 5, f"- Total des releves : {nb_releves}", 0, 1)
    pdf.cell(0, 5, f"- Temperature moyenne : {moyenne:.1f} C", 0, 1)
    pdf.cell(0, 5, f"- Nombre d'alertes : {alertes}", 0, 1)
    pdf.ln(6)
    
    # 4. En-tête du tableau
    pdf.set_fill_color(200, 220, 255)
    pdf.set_font("Arial", 'B', 8)
    w = [20, 15, 20, 20, 65, 50] # Largeurs de colonnes (Total 190)
    
    pdf.cell(w[0], 7, "Date", border=1, fill=True, align='C')
    pdf.cell(w[1], 7, "Heure", border=1, fill=True, align='C')
    pdf.cell(w[2], 7, "Temp (C)", border=1, fill=True, align='C')
    pdf.cell(w[3], 7, "Statut", border=1, fill=True, align='C')
    pdf.cell(w[4], 7, "Motif", border=1, fill=True, align='C')
    pdf.cell(w[5], 7, "Agent", border=1, fill=True, align='C', ln=1)
    
    # 5. Lignes du tableau
    pdf.set_font("Arial", '', 8)
    for _, row in df.iterrows():
        temp_val = f"{row['Température']} C"
        statut = str(row['Statut'])
        
        if statut == "ALERTE":
            pdf.set_text_color(200, 0, 0)
        else:
            pdf.set_text_color(0, 100, 0)
            
        pdf.cell(w[0], 6, str(row['Date']), border=1, align='C')
        pdf.cell(w[1], 6, str(row['Heure']), border=1, align='C')
        pdf.cell(w[2], 6, temp_val, border=1, align='C')
        pdf.cell(w[3], 6, statut, border=1, align='C')
        
        pdf.set_text_color(0, 0, 0)
        motif = str(row['Type'])[:40].encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(w[4], 6, motif, border=1)
        agent = str(row['Agent'])[:30].encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(w[5], 6, agent, border=1, ln=1)
        
    return pdf.output(dest='S').encode('latin-1', 'replace')

def get_data():
    error_msg = None
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="Suivi_Frigo", ttl=0)
        df = df.dropna(how="all")
        if not df.empty and 'Température' in df.columns:
            return clean_frigo_data(df), True, None
        else:
            return df, True, None # Connecté mais vide
    except Exception as e:
        error_msg = str(e)
        
    # Fallback local
    if os.path.isfile(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        return clean_frigo_data(df), False, error_msg
    return pd.DataFrame(), False, error_msg

def save_data(data):
    df_new = pd.DataFrame([data])
    
    # 1. Sauvegarde Google Sheets
    gsheets_ok = False
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        try:
            existing_df = conn.read(worksheet="Suivi_Frigo", ttl=0).dropna(how="all")
            if existing_df.empty or 'Température' not in existing_df.columns:
                updated_df = df_new
            else:
                updated_df = pd.concat([existing_df, df_new], ignore_index=True)
        except:
            updated_df = df_new
        conn.update(worksheet="Suivi_Frigo", data=updated_df)
        gsheets_ok = True
    except Exception as e:
        st.warning(f"⚠️ Erreur Google Sheets (sauvegarde locale uniquement). Erreur: {e}")

    # 2. Sauvegarde Locale (Secours)
    file_exists = os.path.isfile(DATA_FILE)
    df_new.to_csv(DATA_FILE, mode='a', header=not file_exists, index=False)
    
    # Historisation et Alerte
    log_action(data['Agent'], f"Saisie température: {data['Température']}°C ({data['Statut']})", "Suivi Frigo")
    if data['Statut'] == "ALERTE":
        st.error(f"⚠️ ALERTE : La température ({data['Température']}°C) est en dehors de la plage idéale (+2°C à +8°C) !")
    else:
        if gsheets_ok:
            st.success("✅ Donnée synchronisée sur Google Sheets et en local !")
        else:
            st.success("✅ Donnée enregistrée localement.")

# --- INTERFACE ---
st.title(f"🌡️ Darpharm Solution - {st.session_state.current_user['username']}")

tab_names = ["📝 Saisie terrain", "📊 Tableau de bord"]
is_admin = st.session_state.current_user.get('role') == 'Admin'
if is_admin:
    tab_names.append("⚙️ Administration")

tabs = st.tabs(tab_names)
tab_saisie = tabs[0]
tab_data = tabs[1]

with tab_saisie:
    st.subheader("Nouvelle saisie")
    if st.button("🚀 Saisie Rapide (OK - Plage idéale :+2°C+8°C)", use_container_width=True):
        save_data({
            "Date": datetime.now().strftime("%d/%m/%Y"), "Heure": datetime.now().strftime("%H:%M"),
            "Température": 4.0, "Agent": st.session_state.current_user['username'],
            "Statut": "OK", "Commentaire": "Rapide", "Type": "Plage idéale :+2°C+8°C"
        })
        st.rerun()

    with st.form("form_saisie", clear_on_submit=True):
        t = st.number_input("Température (°C)", min_value=-20.0, max_value=30.0, value=4.0, step=0.1)
        type_releve = st.selectbox("Motif", ["Plage idéale :+2°C+8°C", "Remplissage / Arrivage", "Nettoyage", "Autre"])
        comm = st.text_input("Commentaire")
        if st.form_submit_button("Enregistrer", use_container_width=True):
            save_data({
                "Date": datetime.now().strftime("%d/%m/%Y"), "Heure": datetime.now().strftime("%H:%M"),
                "Température": t, "Agent": st.session_state.current_user['username'],
                "Statut": "OK" if 2.0 <= t <= 8.0 else "ALERTE", "Commentaire": comm, "Type": type_releve
            })
            st.rerun()

with tab_data:
    df, is_gsheets, error_msg = get_data()
    
    if is_gsheets:
        st.caption("🟢 Synchronisé avec Google Sheets")
    else:
        st.caption("🟠 Mode hors-ligne (Fichier Local)")
        if error_msg:
            st.error(f"Détail de l'erreur de connexion : {error_msg}")
            
    if not df.empty and 'Température' in df.columns:
        # Création d'une colonne Timestamp pour le graphe
        df['Timestamp'] = pd.to_datetime(df['Date'] + ' ' + df['Heure'], format="%d/%m/%Y %H:%M", errors='coerce')
        
        # KPIs
        c1, c2, c3 = st.columns(3)
        c1.metric("Dernière T°", f"{df.iloc[-1]['Température']} °C")
        c2.metric("Moyenne", f"{df['Température'].mean():.1f} °C")
        c3.metric("Alertes", len(df[df['Statut'] == 'ALERTE']))
        
        # Graphique chronologique
        st.plotly_chart(px.line(df.tail(50), x="Timestamp", y="Température", markers=True, title="Tendance T°"), use_container_width=True)
        
        # Export PDF
        pdf_data = generer_pdf(df)
        st.download_button("📥 Télécharger Rapport PDF", data=pdf_data, file_name="Rapport_Frigo.pdf", mime="application/pdf")
        
        # --- ASSISTANT IA MAINTENANCE PREDICTIVE ---
        if is_ia_enabled():
            st.divider()
            st.subheader("🤖 IA - Maintenance Prédictive")
            st.info("L'IA analyse vos derniers relevés pour détecter des signes d'usure ou d'anomalies du frigo.")
            if st.button("✨ Analyser la santé du Frigo", use_container_width=True):
                with st.spinner("L'IA examine les variations de température..."):
                    last_temps = df.tail(30)['Température'].tolist()
                    prompt = f"""
                    Tu es l'expert technique IA de Darpharm Solution, spécialisé dans les chambres froides de pharmacie (plage cible: 2°C à 8°C).
                    Voici les 30 derniers relevés de température (en °C) : {last_temps}.
                    Analyse la tendance.
                    - Y a-t-il un risque de panne (tendance à la hausse) ?
                    - Les variations sont-elles saines ?
                    Fais un rapport très court (3 lignes max) et donne une recommandation immédiate au pharmacien.
                    """
                    st.warning(ask_ai(prompt))
                
        st.dataframe(df.sort_index(ascending=False), use_container_width=True)
    else:
        st.info("Aucune donnée disponible.")

if is_admin:
    tab_admin = tabs[2]
    with tab_admin:
        st.subheader("☁️ Migration vers Google Sheets")
        st.write("Si votre fichier Google Sheets est vide, utilisez ce bouton pour y envoyer tout l'historique local.")
        if st.button("🚀 Migrer l'historique local vers Google Sheets", use_container_width=True):
            if os.path.isfile(DATA_FILE):
                try:
                    df_local = pd.read_csv(DATA_FILE)
                    df_local = clean_frigo_data(df_local)
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    conn.update(worksheet="Suivi_Frigo", data=df_local)
                    st.success("Migration réussie ! Toutes les anciennes données ont été transférées vers Google Sheets.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur de migration : {e}")
            else:
                st.info("Aucun historique local à migrer.")
                
        st.divider()
        st.subheader("🛠️ Édition manuelle des relevés")
        df_admin, is_gsheets, _ = get_data()
        if not df_admin.empty and 'Température' in df_admin.columns:
            df_admin = clean_frigo_data(df_admin)
            edited_df = st.data_editor(df_admin, use_container_width=True, num_rows="dynamic")
            if st.button("💾 Sauvegarder les modifications"):
                try:
                    if is_gsheets:
                        conn = st.connection("gsheets", type=GSheetsConnection)
                        conn.update(worksheet="Suivi_Frigo", data=edited_df)
                    # Sauvegarde locale aussi
                    edited_df.to_csv(DATA_FILE, index=False)
                    st.success("Modifications enregistrées !")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur lors de la sauvegarde : {e}")
        else:
            st.info("Aucun historique à éditer.")
            
        st.divider()
        st.subheader("📥 Importer un historique Excel")
        st.write("Format attendu : **Date, Heure, Température, Agent, Statut, Commentaire, Type**")
        f_up = st.file_uploader("Fichier Excel (.xlsx)", type=["xlsx"])
        if f_up:
            try:
                df_up = pd.read_excel(f_up)
                st.write("Aperçu de l'import :")
                st.dataframe(df_up.head())
                if st.button("Fusionner avec l'historique existant"):
                    df_current, is_gs, _ = get_data()
                    if not df_current.empty:
                        df_final = pd.concat([df_current, df_up], ignore_index=True)
                    else:
                        df_final = df_up
                    df_final = clean_frigo_data(df_final)
                    
                    try:
                        if is_gs:
                            conn = st.connection("gsheets", type=GSheetsConnection)
                            conn.update(worksheet="Suivi_Frigo", data=df_final)
                        df_final.to_csv(DATA_FILE, index=False)
                        st.success("Données importées avec succès !")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur lors de l'importation : {e}")
            except Exception as e:
                st.error(f"Erreur de lecture du fichier : {e}")
