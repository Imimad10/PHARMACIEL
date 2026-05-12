import streamlit as st
import pandas as pd
from utils_gsheets import load_gs_data
from datetime import datetime

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
    
    # 1. Check Temperature
    try:
        df_suivi = load_gs_data("Suivi_Frigo", "suivi_data.csv", ["Date", "Heure", "Température", "Statut", "Chambre"])
        if not df_suivi.empty:
            last_entries = df_suivi.groupby('Chambre').tail(1)
            for _, row in last_entries.iterrows():
                if row['Statut'] == 'ALERTE':
                    notifications.append({
                        "type": "error",
                        "icon": "❄️",
                        "title": f"Alerte Température : {row['Chambre']}",
                        "message": f"Dernier relevé : {row['Température']}°C."
                    })
    except: pass

    # 2. Check Expiries
    try:
        df_inv = load_gs_data("Saisie_Inventaire", "data_inventaire/saisie.csv", ["designation", "ddp_saisi"])
        if not df_inv.empty:
            df_inv['expiry_date'] = df_inv['ddp_saisi'].apply(parse_ddp_local)
            df_valid = df_inv.dropna(subset=['expiry_date']).copy()
            if not df_valid.empty:
                df_valid['mois'] = df_valid['expiry_date'].apply(lambda d: (d.year - now.year) * 12 + d.month - now.month)
                critiques = df_valid[df_valid['mois'] <= 3]
                if not critiques.empty:
                    notifications.append({
                        "type": "warning",
                        "icon": "⏳",
                        "title": f"{len(critiques)} Produits Critiques",
                        "message": "Péremption dans moins de 3 mois."
                    })
    except: pass

    # 3. Check Large Payments
    try:
        df_rec = load_gs_data("Recouvrement", "data_recouvrement.csv", ["Reste à payer", "Client", "Statut"])
        if not df_rec.empty:
            df_rec['Reste à payer'] = pd.to_numeric(df_rec['Reste à payer'].astype(str).str.replace(',', '.'), errors='coerce').fillna(0)
            large_debts = df_rec[df_rec['Reste à payer'] > 500000]
            if not large_debts.empty:
                notifications.append({
                    "type": "info",
                    "icon": "💰",
                    "title": "Gros Impayés",
                    "message": f"{len(large_debts)} dossiers > 500k DA."
                })
    except: pass

    return notifications

def show_notification_center():
    with st.sidebar.expander("🔔 Notifications & Alertes", expanded=False):
        notifs = check_notifications()
        if not notifs:
            st.success("Système stable ✅")
        else:
            for n in notifs:
                if n['type'] == "error":
                    st.error(f"{n['icon']} **{n['title']}**\n{n['message']}")
                elif n['type'] == "warning":
                    st.warning(f"{n['icon']} **{n['title']}**\n{n['message']}")
                else:
                    st.info(f"{n['icon']} **{n['title']}**\n{n['message']}")
