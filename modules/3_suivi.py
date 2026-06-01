import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import plotly.express as px
import plotly.graph_objects as go
from fpdf import FPDF

# Forcer le rechargement de utils_pdf pour éviter le cache Streamlit lors du déploiement
import importlib
import utils_pdf
importlib.reload(utils_pdf)
from utils_pdf import generate_fiche_temperature_pdf

from utils import log_action
from utils_ia import ask_ai, is_ia_enabled
from utils_gsheets import load_gs_data, save_gs_data
import time

# --- CONFIGURATION ---
WORKSHEET_SUIVI = "Suivi_Frigo"
FALLBACK_SUIVI = "suivi_data.csv"
CHAMBRES = ["Chambre Froide 1", "Chambre Froide 2"]
COLS_SUIVI = ["Date", "Heure", "Température", "Agent", "Statut", "Commentaire", "Type", "Chambre"]

if "tz_offset" not in st.session_state:
    st.session_state.tz_offset = 1

if "current_user" not in st.session_state or st.session_state.current_user is None:
    st.warning("Veuillez vous connecter depuis la page principale.")
    st.stop()

def get_now():
    return datetime.utcnow() + timedelta(hours=st.session_state.tz_offset)

# --- STYLING PREMIUM ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    
    .thermostat-card {
        background: #ffffff;
        border-radius: 30px;
        padding: 40px;
        text-align: center;
        box-shadow: 0 20px 50px rgba(0,0,0,0.05);
        border: 1px solid #f0f2f5;
        transition: all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    }
    
    .temp-display {
        font-family: 'Outfit', sans-serif;
        font-size: 80px;
        font-weight: 800;
        margin: 20px 0;
        transition: color 0.3s ease;
    }
    
    .status-badge-pulse {
        display: inline-block;
        width: 12px;
        height: 12px;
        border-radius: 50%;
        margin-right: 8px;
        animation: pulse-green 2s infinite;
    }
    @keyframes pulse-green {
        0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(16, 185, 129, 0); }
        100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
    }
    
    .kpi-tile {
        background: white;
        padding: 20px;
        border-radius: 20px;
        text-align: center;
        border: 1px solid #e2e8f0;
        transition: transform 0.3s ease;
    }
    .kpi-tile:hover {
        transform: translateY(-5px);
        border-color: #5b6cf9;
    }
    
    .quick-btn {
        background: linear-gradient(135deg, #5b6cf9 0%, #364fc7 100%);
        color: white !important;
        border-radius: 15px;
        padding: 15px;
        font-weight: bold;
        text-align: center;
        cursor: pointer;
        transition: all 0.3s ease;
        margin-bottom: 20px;
    }
    .quick-btn:hover {
        transform: scale(1.02);
        box-shadow: 0 10px 20px rgba(91, 108, 249, 0.3);
    }
</style>
""", unsafe_allow_html=True)

# --- LOGIQUE ---
def clean_frigo_data(df):
    if 'Température' in df.columns:
        df['Température'] = pd.to_numeric(df['Température'], errors='coerce')
        df.loc[(df['Température'] >= 2.0) & (df['Température'] <= 8.0), 'Statut'] = 'OK'
        df.loc[(df['Température'] < 2.0) | (df['Température'] > 8.0), 'Statut'] = 'ALERTE'
    if 'Type' in df.columns:
        df['Type'] = df['Type'].replace('Relevé Standard', 'Plage idéale :+2°C+8°C')
    if 'Chambre' not in df.columns: df['Chambre'] = CHAMBRES[0]
    return df

def get_data():
    df = load_gs_data(WORKSHEET_SUIVI, FALLBACK_SUIVI, COLS_SUIVI)
    return clean_frigo_data(df) if not df.empty else df

def save_entry(data):
    df_old = load_gs_data(WORKSHEET_SUIVI, FALLBACK_SUIVI, COLS_SUIVI)
    df_new = pd.concat([df_old, pd.DataFrame([data])], ignore_index=True)
    save_gs_data(df_new, WORKSHEET_SUIVI, FALLBACK_SUIVI)
    log_action(data['Agent'], f"T° {data['Chambre']}: {data['Température']}°C", "Suivi Frigo")
    if data['Statut'] == "ALERTE":
        st.toast(f"🚨 ALERTE {data['Chambre']} !", icon="❌")
    else:
        st.toast(f"✅ {data['Chambre']} Enregistrée", icon="✔")

# --- UI ---
df_all = get_data()

c_h1, c_h2 = st.columns([2.5, 1])
with c_h1:
    st.title("🌡️ Suivi Thermique")
    st.markdown(f"**Agent :** `{st.session_state.current_user['username']}` | {get_now().strftime('%d/%m/%Y %H:%M')}")
with c_h2:
    st.markdown("""
        <div style="background: rgba(16, 185, 129, 0.1); padding: 10px 20px; border-radius: 15px; border: 1px solid rgba(16, 185, 129, 0.2); text-align: right;">
            <span class="status-badge-pulse" style="background: #10b981;"></span>
            <span style="color: #065f46; font-weight: 700; font-size: 0.8rem;">GSheets Online</span>
        </div>
    """, unsafe_allow_html=True)

tabs = st.tabs(["🎮 Pilotage & Saisie", "📈 Dashboards", "📑 Rapports & Admin"])

# --- TAB 1 : PILOTAGE ---
with tabs[0]:
    col_sel1, col_sel2 = st.columns([1, 1])
    room = col_sel1.radio("Choisir l'unité", CHAMBRES, horizontal=True, label_visibility="collapsed")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    col_input, col_info = st.columns([1.5, 1])
    
    with col_input:
        # Thermostat visuel interactif
        val_temp = st.slider("Ajuster la température", -10.0, 20.0, 4.0, 0.1, label_visibility="collapsed")
        
        # Logique de couleur dynamique
        t_color = "#10b981" # Green
        if val_temp < 2.0: t_color = "#5b6cf9" # Blue
        elif val_temp > 8.0: t_color = "#ef4444" # Red
        
        st.markdown(f"""
            <div class="thermostat-card">
                <div style="color: #64748b; font-weight: 600; text-transform: uppercase; letter-spacing: 1px;">{room}</div>
                <div class="temp-display" style="color: {t_color};">{val_temp}°C</div>
                <div style="background: {t_color}1a; color: {t_color}; padding: 8px 20px; border-radius: 20px; display: inline-block; font-weight: bold;">
                    {"CONFORME ✅" if 2.0 <= val_temp <= 8.0 else "HORS PLAGE ⚠️"}
                </div>
            </div>
        """, unsafe_allow_html=True)

    with col_info:
        st.markdown(f"""<div class="quick-btn" onclick="">🚀 ENREGISTREMENT RAPIDE ({val_temp:.1f}°C)</div>""", unsafe_allow_html=True)
        if st.button(f"Confirmer {val_temp:.1f}°C", use_container_width=True):
            now = get_now()
            status = "OK" if 2.0 <= val_temp <= 8.0 else "ALERTE"
            save_entry({"Date": now.strftime("%d/%m/%Y"), "Heure": now.strftime("%H:%M"), "Température": val_temp, "Agent": st.session_state.current_user['username'], "Statut": status, "Commentaire": "Rapide", "Type": "Plage idéale :+2°C+8°C", "Chambre": room})
            st.rerun()
            
        with st.form("full_entry", clear_on_submit=True):
            motif = st.selectbox("Type de relevé", ["Standard", "Arrivage", "Maintenance", "Nettoyage"])
            comm = st.text_input("Note (Optionnel)")
            if st.form_submit_button("VALIDER LE RELEVÉ", use_container_width=True):
                now = get_now()
                save_entry({"Date": now.strftime("%d/%m/%Y"), "Heure": now.strftime("%H:%M"), "Température": val_temp, "Agent": st.session_state.current_user['username'], "Statut": "OK" if 2.0 <= val_temp <= 8.0 else "ALERTE", "Commentaire": comm, "Type": motif, "Chambre": room})
                st.rerun()

# --- TAB 2 : DASHBOARD ---
with tabs[1]:
    if df_all.empty:
        st.info("Aucune donnée disponible.")
    else:
        room_dash = st.selectbox("Unité de visualisation", CHAMBRES)
        df = df_all[df_all['Chambre'] == room_dash].copy()
        
        if not df.empty:
            df['Timestamp'] = pd.to_datetime(df['Date'] + ' ' + df['Heure'], format="%d/%m/%Y %H:%M", errors='coerce')
            last = df.iloc[-1]
            
            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f"""<div class="kpi-tile"><div style="font-size: 0.8rem; color: #64748b;">ACTUELLE</div><div style="font-size: 1.5rem; font-weight: 800; color: #1e293b;">{last['Température']}°C</div></div>""", unsafe_allow_html=True)
            c2.markdown(f"""<div class="kpi-tile"><div style="font-size: 0.8rem; color: #64748b;">MOYENNE</div><div style="font-size: 1.5rem; font-weight: 800; color: #1e293b;">{df['Température'].mean():.1f}°C</div></div>""", unsafe_allow_html=True)
            conf = (len(df[df['Statut']=='OK'])/len(df))*100
            c3.markdown(f"""<div class="kpi-tile"><div style="font-size: 0.8rem; color: #64748b;">CONFORMITÉ</div><div style="font-size: 1.5rem; font-weight: 800; color: #10b981;">{conf:.0f}%</div></div>""", unsafe_allow_html=True)
            c4.markdown(f"""<div class="kpi-tile"><div style="font-size: 0.8rem; color: #64748b;">ALERTES</div><div style="font-size: 1.5rem; font-weight: 800; color: #ef4444;">{len(df[df['Statut']=='ALERTE'])}</div></div>""", unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            fig = px.line(df.tail(48), x="Timestamp", y="Température", markers=True, 
                         template="plotly_white", color_discrete_sequence=["#5b6cf9"])
            fig.add_hline(y=8, line_dash="dot", line_color="red", annotation_text="Max 8°C")
            fig.add_hline(y=2, line_dash="dot", line_color="blue", annotation_text="Min 2°C")
            fig.update_layout(hovermode="x unified", margin=dict(l=0, r=0, t=20, b=0))
            st.plotly_chart(fig, use_container_width=True)
            
            with st.expander("📝 Voir l'historique complet"):
                st.dataframe(df.sort_index(ascending=False), use_container_width=True)
        else:
            st.warning(f"Pas de relevés pour {room_dash}")

# --- TAB 3 : ADMIN & RAPPORTS ---
with tabs[2]:
    st.subheader("🛠️ Outils Administratifs")
    
    col_a1, col_a2 = st.columns(2)
    with col_a1:
        st.info("Configurez et générez votre fiche de relevés vierge.")
        
        french_months_list = [
            "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
            "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
        ]
        
        c_sel1, c_sel2 = st.columns(2)
        with c_sel1:
            sel_month_name = st.selectbox(
                "Mois de la fiche", 
                options=french_months_list,
                index=get_now().month - 1
            )
            sel_month = french_months_list.index(sel_month_name) + 1
        with c_sel2:
            sel_year = st.selectbox(
                "Année", 
                options=[2026, 2027],
                index=0 if get_now().year == 2026 else 1
            )
            
        sel_chambre = st.selectbox(
            "Unité / Chambre Froide",
            options=["Chambre Froide 1", "Chambre Froide 2", "Toutes les unités (2 pages)"],
            index=0
        )
        
        heures_saisie = st.text_input(
            "Heures de pointage (séparées par des virgules)",
            value="08:00, 17:00",
            help="Saisissez les heures séparées par des virgules, par exemple: 08:00, 17:00, 20:00"
        )
        
        # Nettoyer et séparer
        sel_hours = [h.strip() for h in heures_saisie.split(",") if h.strip()]
        
        if not sel_hours:
            st.warning("Veuillez saisir au moins une heure de relevé.")
        else:
            chambres_to_gen = CHAMBRES
            suffixe = "Toutes"
            if "Chambre Froide 1" in sel_chambre:
                chambres_to_gen = ["Chambre Froide 1"]
                suffixe = "CF1"
            elif "Chambre Froide 2" in sel_chambre:
                chambres_to_gen = ["Chambre Froide 2"]
                suffixe = "CF2"
                
            nom_fichier = f"Fiche_Temp_{suffixe}_{sel_year}_{sel_month:02d}.pdf"
            try:
                pdf_bytes = generate_fiche_temperature_pdf(
                    year=sel_year,
                    month=sel_month,
                    hours=sel_hours,
                    chambres=chambres_to_gen
                )
                st.download_button(
                    label="📄 Télécharger Fiche Manuelle",
                    data=pdf_bytes,
                    file_name=nom_fichier,
                    mime="application/pdf",
                    use_container_width=True,
                )
                st.caption(f"ℹ️ Fiche pré-remplie pour **{sel_chambre}** ({sel_month_name} {sel_year}) à **{', '.join(sel_hours)}**.")
            except Exception as e:
                st.error(f"Erreur lors de la génération : {e}")
            
    with col_a2:
        if is_ia_enabled():
            st.info("L'IA analyse les tendances de température pour détecter des anomalies.")
            if st.button("🤖 Analyse Stratégique IA", use_container_width=True):
                st.write(ask_ai("Analyse les tendances de froid et suggère des optimisations."))

    st.divider()
    if st.session_state.current_user.get('role') == 'Admin':
        st.write("### 📂 Édition de la Base de Données (Admin uniquement)")
        
        # 1. Formulaire d'ajout rapide rétroactif
        with st.expander("➕ Ajouter un relevé manuel rétroactif (Date et Heure passées)", expanded=False):
            with st.form("retro_form", clear_on_submit=True):
                col_r1, col_r2, col_r3 = st.columns(3)
                with col_r1:
                    retro_date = st.date_input("Date", value=get_now().date())
                    retro_heure = st.text_input("Heure (ex: 17:00)", value="17:00")
                with col_r2:
                    retro_temp = st.number_input("Température (°C)", value=4.0, min_value=-20.0, max_value=40.0, step=0.1)
                    retro_chambre = st.selectbox("Chambre / Unité", CHAMBRES)
                with col_r3:
                    retro_agent = st.text_input("Agent", value=st.session_state.current_user['username'])
                    retro_type = st.selectbox("Type de relevé", ["Plage idéale :+2°C+8°C", "Arrivage", "Maintenance", "Nettoyage"])
                
                retro_comment = st.text_input("Commentaire (Optionnel)", value="Saisie rétroactive")
                
                if st.form_submit_button("💾 ENREGISTRER LE RELEVÉ RETROACTIF", use_container_width=True):
                    now_str = retro_date.strftime("%d/%m/%Y")
                    status_calc = "OK" if 2.0 <= retro_temp <= 8.0 else "ALERTE"
                    
                    new_entry = {
                        "Date": now_str,
                        "Heure": retro_heure,
                        "Température": retro_temp,
                        "Agent": retro_agent,
                        "Statut": status_calc,
                        "Commentaire": retro_comment,
                        "Type": retro_type,
                        "Chambre": retro_chambre
                    }
                    
                    df_old = load_gs_data(WORKSHEET_SUIVI, FALLBACK_SUIVI, COLS_SUIVI)
                    df_new = pd.concat([df_old, pd.DataFrame([new_entry])], ignore_index=True)
                    save_gs_data(df_new, WORKSHEET_SUIVI, FALLBACK_SUIVI)
                    
                    st.toast("✅ Relevé rétroactif ajouté avec succès !", icon="💾")
                    time.sleep(1)
                    st.rerun()

        # 2. Guide d'édition directe
        st.info("💡 **Guide de modification / suppression :**\n"
                "- **Modifier** : Double-cliquez sur n'importe quelle cellule du tableau pour corriger une valeur (Date, Heure, Température, Agent, etc.).\n"
                "- **Supprimer** : Cochez la case tout à gauche d'une ou plusieurs lignes dans le tableau, puis appuyez sur la touche **Suppr** (Delete) de votre clavier.\n"
                "- **Sauvegarder** : Cliquez sur le bouton bleu **💾 Sauvegarder les modifications** ci-dessous pour enregistrer le tout.")

        edited_df = st.data_editor(df_all, use_container_width=True, num_rows="dynamic")
        if st.button("💾 Sauvegarder les modifications", use_container_width=True):
            save_gs_data(edited_df, WORKSHEET_SUIVI, FALLBACK_SUIVI)
            st.success("Données synchronisées !")
    else:
        st.caption("Accès restreint aux administrateurs pour la modification des données.")

st.markdown('<div style="text-align: center; color: #94a3b8; font-size: 0.8rem; margin-top: 30px;">DarPharm Solution | Supervision Thermique Automatisée</div>', unsafe_allow_html=True)
