import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import os
import streamlit as st

GS_CREDS_PATH = "google_creds.json"
GS_CONFIG_PATH = "gs_config.txt"

def get_gs_client():
    if os.path.exists(GS_CREDS_PATH):
        try:
            scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            creds = Credentials.from_service_account_file(GS_CREDS_PATH, scopes=scopes)
            return gspread.authorize(creds)
        except Exception as e:
            return None
    return None

def get_gs_url():
    if os.path.exists(GS_CONFIG_PATH):
        with open(GS_CONFIG_PATH, "r") as f:
            return f.read().strip()
    return None

@st.cache_data(ttl=300) # Cache de 5 minutes pour éviter les quotas Google
def load_gs_data(worksheet_name, fallback_path, columns):
    client = get_gs_client()
    url = get_gs_url()
    
    if client and url:
        try:
            sh = client.open_by_url(url)
            try:
                worksheet = sh.worksheet(worksheet_name)
            except gspread.WorksheetNotFound:
                # Création automatique de l'onglet s'il n'existe pas
                worksheet = sh.add_worksheet(title=worksheet_name, rows="100", cols="20")
                worksheet.append_row(columns)
                return pd.DataFrame(columns=columns)
            
            data = worksheet.get_all_records()
            df = pd.DataFrame(data)
            if df.empty: return pd.DataFrame(columns=columns)
            return df.reindex(columns=columns)
        except Exception as e:
            st.warning(f"Erreur GSheets ({worksheet_name}), repli local : {e}")
            
    if os.path.exists(fallback_path):
        try:
            df = pd.read_csv(fallback_path, sep=',', encoding='utf-8-sig')
            return df.reindex(columns=columns)
        except:
            return pd.DataFrame(columns=columns)
    return pd.DataFrame(columns=columns)

def save_gs_data(df, worksheet_name, fallback_path):
    df = df.dropna(how='all')
    client = get_gs_client()
    url = get_gs_url()
    
    if client and url:
        try:
            sh = client.open_by_url(url)
            try:
                worksheet = sh.worksheet(worksheet_name)
            except gspread.WorksheetNotFound:
                worksheet = sh.add_worksheet(title=worksheet_name, rows="100", cols="20")
            
            worksheet.clear()
            df_gs = df.copy()
            # Nettoyage types pour Sheets
            for col in df_gs.columns:
                if pd.api.types.is_datetime64_any_dtype(df_gs[col]):
                    df_gs[col] = df_gs[col].dt.strftime('%Y-%m-%d')
            
            worksheet.update([df_gs.columns.values.tolist()] + df_gs.values.tolist())
            st.cache_data.clear() # On vide le cache après une sauvegarde pour forcer la lecture
        except Exception as e:
            st.error(f"Erreur sauvegarde GSheets ({worksheet_name}) : {e}")
            
    df.to_csv(fallback_path, index=False, sep=',', encoding='utf-8-sig')
