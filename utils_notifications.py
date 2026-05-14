import streamlit as st
import pandas as pd
from utils_gsheets import load_gs_data
from datetime import datetime
from utils_sound import play_sound

def parse_ddp_local(ddp_str):
    if pd.isna(ddp_str) or ddp_str == "": return None
    ddp_str = str(ddp_str).strip()
    try:
        if '/' in ddp_str:
            parts = ddp_str.split('/')
            if len(parts) == 2:
                m, y = int(parts[0]), int(parts[1])
                if y < 100: y += 2000
                return datetime(y, m, 1)
        return pd.to_datetime(ddp_str)
    except: return None

@st.cache_data(ttl=120)
def check_notifications():
    notifications = []
    now = datetime.now()
    
    # 1. Check Temperature (Suivi Frigo)
    try:
        df_suivi = load_gs_data("Suivi_Frigo", "suivi_data.csv", ["Date", "Heure", "Température", "Statut", "Chambre"])
        if not df_suivi.empty:
            last_entries = df_suivi.groupby('Chambre').tail(1)
            for _, row in last_entries.iterrows():
                if row['Statut'] == 'ALERTE':
                    notifications.append({
                        "type": "error", "icon": "❄️", "title": f"Alerte Température : {row['Chambre']}",
                        "message": f"Niveau critique : {row['Température']}°C."
                    })
    except: pass

    # 2. Check Expiries (Multi-Source)
    try:
        # On check la Liste Officielle
        df_lots = load_gs_data("Master_Inventaire_Zone", "data_inventaire_detail/master_detail.csv", ["produit", "ddp"])
        if not df_lots.empty:
            df_lots['expiry_date'] = df_lots['ddp'].apply(parse_ddp_local)
            df_v = df_lots.dropna(subset=['expiry_date']).copy()
            if not df_v.empty:
                df_v['mois'] = df_v['expiry_date'].apply(lambda d: (d.year - now.year) * 12 + d.month - now.month)
                
                perimes = df_v[df_v['mois'] < 0]
                critiques = df_v[(df_v['mois'] >= 0) & (df_v['mois'] <= 3)]
                
                if not perimes.empty:
                    notifications.append({
                        "type": "error", "icon": "❌", "title": "Produits Périmés !",
                        "message": f"{len(perimes)} produits à retirer immédiatement."
                    })
                if not critiques.empty:
                    notifications.append({
                        "type": "warning", "icon": "⏳", "title": "Alertes Péremptions",
                        "message": f"{len(critiques)} produits expirent dans < 3 mois."
                    })
    except: pass
    
    # 3. Check SAV (Réclamations > 48h)
    if st.session_state.get("enable_sav_notifs", True):
        try:
            df_sav = load_gs_data("Litiges_SAV", "data/db_sav.csv", ["date_crea", "statut", "ref"])
            if not df_sav.empty:
                df_sav['date_crea'] = pd.to_datetime(df_sav['date_crea'], errors='coerce')
                df_sav = df_sav.dropna(subset=['date_crea'])
                
                # Réclamations en cours de plus de 48h
                mask = (df_sav['statut'] == 'En cours') & ((datetime.now() - df_sav['date_crea']).dt.total_seconds() / 3600 > 48)
                retards = df_sav[mask]
                
                if not retards.empty:
                    notifications.append({
                        "type": "error", "icon": "🚛", "title": "SAV en Retard (>48h)",
                        "message": f"{len(retards)} réclamations dépassent le délai de 48h."
                    })
        except: pass

    return notifications

@st.cache_data(ttl=3600)
def get_ai_briefing(notifs_summary):
    """Génère un petit message d'encouragement/alerte via l'IA."""
    if not notifs_summary:
        return "✨ Tout est sous contrôle. Vos stocks sont sains et la chaîne du froid est respectée."
    
    try:
        from utils_ia import ask_ai
        prompt = f"Voici les alertes actuelles de la pharmacie : {notifs_summary}. Fais un briefing ultra-court (2 phrases max) de ton rôle d'assistant expert DarPharm pour motiver l'équipe."
        return ask_ai(prompt)
    except:
        return "⚠️ L'assistant IA est temporairement indisponible pour le briefing."

def show_notification_center():
    with st.sidebar.expander("🔔 Centre de Notifications IA", expanded=False):
        notifs = check_notifications()
        # On passe un résumé textuel pour le cache
        notifs_summary = ", ".join([n['title'] for n in notifs])
        briefing = get_ai_briefing(notifs_summary)
        
        # Son doux lors de la réception de la réponse IA
        if briefing and briefing != st.session_state.get("_last_briefing", ""):
            st.session_state["_last_briefing"] = briefing
            play_sound("ai")
        
        st.markdown(f"""
            <div style="font-style: italic; font-size: 0.85rem; color: #5b6cf9; background: rgba(91,108,249,0.05); padding: 12px; border-radius: 12px; border-left: 3px solid #5b6cf9; margin-bottom: 15px;">
                "{briefing}"
            </div>
        """, unsafe_allow_html=True)

        # Réglages des notifications
        st.write("---")
        st.session_state.enable_sav_notifs = st.toggle("🔔 Alertes SAV (>48h)", value=st.session_state.get("enable_sav_notifs", True))

        st.divider()

        if not notifs:
            st.success("Aucune alerte critique.")
        else:
            for n in notifs:
                icon_name = "error" if n['type'] == "error" else "warning" if n['type'] == "warning" else "info"
                color = "#f06585" if n['type'] == "error" else "#e8a020" if n['type'] == "warning" else "#5b6cf9"
                bg = "rgba(240,101,133,0.1)" if n['type'] == "error" else "rgba(232,160,32,0.1)" if n['type'] == "warning" else "rgba(91,108,249,0.1)"
                
                st.markdown(f"""
                    <div style="padding: 12px; border-radius: 12px; background: {bg}; color: {color}; margin-bottom: 10px; border: 1px solid {color}33;">
                        <div style="font-weight: 800; font-size: 0.9rem; display: flex; align-items: center; gap: 8px;">
                            <span class="material-symbols-outlined" style="font-size: 18px;">{icon_name}</span> {n['title']}
                        </div>
                        <div style="font-size: 0.8rem; opacity: 0.9; margin-top: 4px; padding-left: 26px;">{n['message']}</div>
                    </div>
                """, unsafe_allow_html=True)

