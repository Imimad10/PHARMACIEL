import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import os
import streamlit as st
from datetime import datetime

GS_CREDS_PATH = "google_creds.json"
GS_CONFIG_PATH = "gs_config.txt"

# Configuration Centralisée
DB_USERS_WORKSHEET = "Utilisateurs"
DB_USERS_FALLBACK = "data/db_users.json"

# Liste des modules qui DOIVENT rester sur le Cloud en permanence (Admin, Config, Suivi critique)
ALWAYS_CLOUD = [DB_USERS_WORKSHEET, "Base_Clients", "Secteurs", "Livreurs", "Suivi_Frigo", "Logs"]

def get_storage_mode():
    """Récupère le mode de stockage actuel (Cloud ou Local)."""
    if st.session_state.get("offline_mode", False):
        return "Local"
    return st.session_state.get("storage_mode", "Cloud")

@st.cache_resource
def get_gs_client():
    creds_dict = None
    if "gsheets" in st.secrets:
        creds_dict = st.secrets["gsheets"]
    elif "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
        creds_dict = st.secrets["connections"]["gsheets"]

    if creds_dict:
        try:
            scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
            return gspread.authorize(creds)
        except Exception as e:
            st.error(f"Erreur Auth GSheets : {e}")

    if os.path.exists(GS_CREDS_PATH):
        try:
            scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            creds = Credentials.from_service_account_file(GS_CREDS_PATH, scopes=scopes)
            return gspread.authorize(creds)
        except: return None
    return None

def get_gs_url(worksheet_name=None):
    # 1. Priorité absolue aux Secrets Streamlit (Cloud)
    if "GS_URL" in st.secrets: 
        return st.secrets["GS_URL"]
    
    if "connections" in st.secrets and "gsheets" in st.secrets["connections"]:
        if "spreadsheet" in st.secrets["connections"]["gsheets"]:
            return st.secrets["connections"]["gsheets"]["spreadsheet"]

    # 2. Base dédiée pour les Utilisateurs (Fallback)
    if worksheet_name == DB_USERS_WORKSHEET:
        return "https://docs.google.com/spreadsheets/d/1tJDJCtk7cCNSBIfQLKS9J2oH95VcaNMoCVPX8V_cDc/edit"
        
    # 3. Config locale
    if os.path.exists(GS_CONFIG_PATH):
        with open(GS_CONFIG_PATH, "r") as f: return f.read().strip()
    return None

def _load_local_data(fallback_path, columns):
    """Logique interne de chargement local."""
    if os.path.exists(fallback_path):
        try:
            if fallback_path.endswith('.json'):
                import json
                with open(fallback_path, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                df = pd.DataFrame(list(raw_data["_default"].values())) if "_default" in raw_data else pd.DataFrame(raw_data)
            else:
                try:
                    df = pd.read_csv(fallback_path, sep=',', encoding='utf-8-sig')
                    if len(df.columns) <= 1: # Si mal découpé
                        df = pd.read_csv(fallback_path, sep=';', encoding='utf-8-sig')
                except:
                    df = pd.read_csv(fallback_path, sep=';', encoding='utf-8-sig')
            
            for col in df.columns:
                try: df[col] = pd.to_numeric(df[col])
                except: pass
            return df.reindex(columns=columns)
        except: pass
    return pd.DataFrame(columns=columns)

@st.cache_data(ttl=600)
def load_gs_data(worksheet_name, fallback_path, columns=None, force_cloud=False):
    """
    Charge les données depuis GSheets ou se replie sur le fichier local si hors-ligne.
    """
    # 0. Mode Hors-Ligne Forcé
    if st.session_state.get("offline_mode", False) and not force_cloud:
        return _load_local_data(fallback_path, columns)

    # 1. Tenter le Cloud si mode Cloud, ou si protégé, ou si forcé
    mode = get_storage_mode()
    is_protected = worksheet_name in ALWAYS_CLOUD

    if force_cloud or is_protected or mode == "Cloud":
        client = get_gs_client()
        url = get_gs_url(worksheet_name)
        if client and url:
            try:
                sh = client.open_by_url(url)
                worksheet = sh.worksheet(worksheet_name)
                all_vals = worksheet.get_all_values()
                if all_vals and len(all_vals) > 0:
                    headers = all_vals[0]
                    rows = all_vals[1:]
                    # Sanitize headers
                    sanitized_h = []
                    h_count = {}
                    for h in headers:
                        if h in h_count:
                            h_count[h] += 1
                            sanitized_h.append(f"{h}_{h_count[h]}")
                        else:
                            h_count[h] = 1
                            sanitized_h.append(h)
                    
                    df = pd.DataFrame(rows, columns=sanitized_h)
                    if columns:
                        df = df.reindex(columns=columns)
                    
                    # Types et Parsing
                    for col in df.columns:
                        try: df[col] = pd.to_numeric(df[col])
                        except: pass
                    import ast
                    def safe_parse(v):
                        if isinstance(v, str) and v.startswith("[") and v.endswith("]"):
                            try: return ast.literal_eval(v)
                            except: return v
                        return v
                    for col in df.columns: df[col] = df[col].apply(safe_parse)
                    return df
            except Exception as e:
                err_str = str(e)
                if "404" in err_str:
                    try:
                        email = client.auth.signer_email if hasattr(client.auth, 'signer_email') else "darpharm-bot@..."
                    except:
                        email = "l'email du robot Google"
                    st.error(f"🚨 ERREUR 404: {email} n'a pas accès au fichier. Ajoutez-le en Éditeur sur Google Drive !")
                elif "429" in err_str or "Quota exceeded" in err_str:
                    # Message plus discret pour le Rate Limit de Google
                    if "rate_limit_warned" not in st.session_state:
                        st.warning(f"⚠️ Google Sheets est très sollicité. Utilisation du cache local pour accélérer.")
                        st.session_state.rate_limit_warned = True
                else:
                    if is_protected: st.warning(f"⚠️ Connexion Cloud impossible ({worksheet_name}) : {err_str[:100]}...")
    # 2. Repli Local
    if os.path.exists(fallback_path):
        try:
            if fallback_path.endswith('.json'):
                import json
                with open(fallback_path, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                df = pd.DataFrame(list(raw_data["_default"].values())) if "_default" in raw_data else pd.DataFrame(raw_data)
            else:
                try:
                    df = pd.read_csv(fallback_path, sep=',', encoding='utf-8-sig')
                    if len(df.columns) <= 1: # Si mal découpé
                        df = pd.read_csv(fallback_path, sep=';', encoding='utf-8-sig')
                except:
                    df = pd.read_csv(fallback_path, sep=';', encoding='utf-8-sig')
            
            for col in df.columns:
                try: df[col] = pd.to_numeric(df[col])
                except: pass
            return df.reindex(columns=columns)
        except: pass
    
    # 3. Restauration de sécurité pour les Utilisateurs
    if worksheet_name == DB_USERS_WORKSHEET:
        try:
            from config_users import DEFAULT_USERS
            st.info("⚠️ Base utilisateurs vide détectée. Restauration automatique depuis la sauvegarde de sécurité...")
            df = pd.DataFrame(DEFAULT_USERS)
            # On ne sauvegarde pas forcément ici pour éviter les boucles, mais on retourne les données par défaut
            return df.reindex(columns=columns)
        except: pass

    return pd.DataFrame(columns=columns)

def save_gs_data(df, worksheet_name, fallback_path, force_cloud=False):
    """
    Sauvegarde selon le mode.
    Mode Cloud -> GSheets + Local
    Mode Local -> Local uniquement (sauf si protégé ou forcé)
    """
    df = df.dropna(how='all')
    mode = get_storage_mode()
    is_protected = worksheet_name in ALWAYS_CLOUD

    # 1. Cloud
    if force_cloud or is_protected or mode == "Cloud":
        client = get_gs_client()
        url = get_gs_url(worksheet_name)
        if client and url:
            try:
                sh = client.open_by_url(url)
                try: worksheet = sh.worksheet(worksheet_name)
                except: worksheet = sh.add_worksheet(title=worksheet_name, rows="100", cols="20")
                
                worksheet.clear()
                df_gs = df.copy().fillna("")
                for col in df_gs.columns:
                    if pd.api.types.is_datetime64_any_dtype(df_gs[col]):
                        df_gs[col] = df_gs[col].dt.strftime('%Y-%m-%d %H:%M:%S')
                    else:
                        df_gs[col] = df_gs[col].apply(lambda x: x.strftime('%Y-%m-%d %H:%M:%S') if hasattr(x, 'strftime') else x)
                    df_gs[col] = df_gs[col].apply(lambda x: str(x) if isinstance(x, (list, dict)) else x)
                
                # Unique headers
                new_cols, c_count = [], {}
                for c in df_gs.columns:
                    if c in c_count:
                        c_count[c] += 1
                        new_cols.append(f"{c}_{c_count[c]}")
                    else:
                        c_count[c] = 1
                        new_cols.append(c)
                df_gs.columns = new_cols

                worksheet.update([df_gs.columns.values.tolist()] + df_gs.values.tolist())
                st.cache_data.clear()
                if force_cloud: st.success(f"✅ Synchronisation Cloud réussie ({worksheet_name})")
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "Quota exceeded" in err_str:
                    # Message silencieux car on sauvegarde en local de toute façon
                    pass 
                else:
                    st.error(f"❌ Erreur Cloud ({worksheet_name}) : {err_str[:100]}...")

    # 2. Local
    try:
        os.makedirs(os.path.dirname(fallback_path), exist_ok=True) if os.path.dirname(fallback_path) else None
        df.to_csv(fallback_path, index=False, sep=',', encoding='utf-8-sig')
        if mode == "Local" and not is_protected and not force_cloud:
            st.info(f"💾 Sauvegarde locale effectuée ({worksheet_name})")
    except Exception as e:
        st.error(f"Erreur sauvegarde locale : {str(e)[:100]}")

def show_sync_ui(worksheet_name, fallback_path, columns):
    """Affiche les boutons de synchronisation si on est en mode Local."""
    if get_storage_mode() == "Local":
        with st.expander("🔄 Synchronisation Cloud/Local", expanded=False):
            col1, col2 = st.columns(2)
            if col1.button(f"📥 Importer {worksheet_name} (depuis Cloud)", use_container_width=True, key=f"sync_in_{worksheet_name}"):
                df_cloud = load_gs_data(worksheet_name, fallback_path, columns, force_cloud=True)
                if not df_cloud.empty:
                    df_cloud.to_csv(fallback_path, index=False, sep=',', encoding='utf-8-sig')
                    st.success("✅ Données Cloud importées sur ce PC !")
                    st.rerun()
                else:
                    st.warning("Le Cloud ne contient pas de données pour ce module.")
            
            if col2.button(f"📤 Exporter {worksheet_name} (vers Cloud)", use_container_width=True, key=f"sync_out_{worksheet_name}"):
                if os.path.exists(fallback_path):
                    df_local = pd.read_csv(fallback_path)
                    save_gs_data(df_local, worksheet_name, fallback_path, force_cloud=True)
                    st.success("✅ Données locales envoyées sur le Cloud !")
                else:
                    st.warning("Aucune donnée locale trouvée à exporter.")

def create_archive_spreadsheet(name, df):
    client = get_gs_client()
    if not client: return None
    try:
        sh = client.create(name)
        worksheet = sh.get_worksheet(0)
        df_gs = df.copy().fillna("")
        for col in df_gs.columns:
            if pd.api.types.is_datetime64_any_dtype(df_gs[col]):
                df_gs[col] = df_gs[col].dt.strftime('%Y-%m-%d %H:%M:%S')
        worksheet.update([df_gs.columns.values.tolist()] + df_gs.values.tolist())
        return sh.url
    except Exception as e:
        st.error(f"Erreur archive : {e}")
        return None

def restore_users_from_config():
    """Force la restauration de la base utilisateurs depuis le fichier config_users.py."""
    try:
        from config_users import DEFAULT_USERS
        df_new = pd.DataFrame(DEFAULT_USERS)
        save_gs_data(df_new, DB_USERS_WORKSHEET, DB_USERS_FALLBACK, force_cloud=True)
        return True, f"✅ {len(df_new)} utilisateurs restaurés avec succès !"
    except Exception as e:
        return False, f"❌ Erreur de restauration : {str(e)}"

def save_users_to_config(df):
    """Enregistre le DataFrame actuel des utilisateurs dans config_users.py pour une sauvegarde statique."""
    try:
        import pprint
        # On s'assure que les pages sont bien au format string pour la sauvegarde
        df_save = df.copy()
        if 'pages' in df_save.columns:
            df_save['pages'] = df_save['pages'].apply(lambda x: str(x) if isinstance(x, list) else x)
            
        users_list = df_save.to_dict('records')
        content = "# Configuration Statique des Utilisateurs (Sauvegarde de Sécurité)\n\n"
        content += "DEFAULT_USERS = " + pprint.pformat(users_list, indent=4, width=120) + "\n"
        
        with open("config_users.py", "w", encoding="utf-8") as f:
            f.write(content)
        return True, "✅ État actuel sauvegardé comme nouvelle référence de sécurité !"
    except Exception as e:
        return False, f"❌ Erreur lors de la sauvegarde statique : {str(e)}"
