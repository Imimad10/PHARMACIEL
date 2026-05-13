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

    return notifications

def get_ai_briefing(notifs):
    """Génère un petit message d'encouragement/alerte via l'IA."""
    if not notifs:
        return "✨ Tout est sous contrôle. Vos stocks sont sains et la chaîne du froid est respectée."
    
    try:
        from utils_ia import ask_ai
        # On simplifie les notifs pour le prompt
        summary = ", ".join([n['title'] for n in notifs])
        prompt = f"Voici les alertes actuelles de la pharmacie : {summary}. Fais un briefing ultra-court (2 phrases max) de ton rôle d'assistant expert DarPharm pour motiver l'équipe."
        return ask_ai(prompt)
    except:
        return "⚠️ L'assistant IA est temporairement indisponible pour le briefing."

def show_notification_center():
    with st.sidebar.expander("🔔 Centre de Notifications IA", expanded=False):
        notifs = check_notifications()
        
        # --- SON INTELLIGENT basé sur la sévérité ---
        # On utilise session_state pour ne jouer le son qu'une seule fois par changement d'état
        notif_key = str(sorted([n['title'] for n in notifs]))
        prev_key = st.session_state.get("_last_notif_key", "")
        
        if notif_key != prev_key and notifs:
            st.session_state["_last_notif_key"] = notif_key
            has_error = any(n['type'] == 'error' for n in notifs)
            if has_error:
                play_sound("warning")   # Son grave pour les alertes critiques (périmés)
            else:
                play_sound("notification")  # Ding pour les avertissements
        
        # Briefing IA
        st.markdown("### 🤖 Briefing Assistant")
        briefing = get_ai_briefing(notifs)
        
        # Son doux lors de la réception de la réponse IA
        if briefing and briefing != st.session_state.get("_last_briefing", ""):
            st.session_state["_last_briefing"] = briefing
            play_sound("ai")
        
        st.markdown(f"""
            <div style="font-style: italic; font-size: 0.85rem; color: #5b6cf9; background: rgba(91,108,249,0.05); padding: 12px; border-radius: 12px; border-left: 3px solid #5b6cf9; margin-bottom: 15px;">
                "{briefing}"
            </div>
        """, unsafe_allow_html=True)

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

