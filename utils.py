from utils_gsheets import load_gs_data, save_gs_data
import pandas as pd
from datetime import datetime

def log_action(user, action, module="Système"):
    """Enregistre une action dans la base de données des logs sur GSheets."""
    WORKSHEET = "Logs"
    FALLBACK = "data/db_logs.csv"
    COLS = ["timestamp", "user", "module", "action"]
    
    new_log = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user": user,
        "module": module,
        "action": action
    }
    
    df_logs = load_gs_data(WORKSHEET, FALLBACK, COLS)
    df_logs = pd.concat([df_logs, pd.DataFrame([new_log])], ignore_index=True)
    save_gs_data(df_logs, WORKSHEET, FALLBACK)

def trigger_vibration():
    """Injecte un script JS pour faire vibrer le téléphone (PWA)."""
    import streamlit.components.v1 as components
    components.html("<script>window.navigator.vibrate([100, 50, 100]);</script>", height=0)

def trigger_success_sound():
    """Joue un son de succès court."""
    import streamlit.components.v1 as components
    components.html("""
        <audio autoplay>
            <source src="https://assets.mixkit.co/active_storage/sfx/2436/2436-preview.mp3" type="audio/mpeg">
        </audio>
    """, height=0)

def trigger_error_sound():
    """Joue un son d'erreur court."""
    import streamlit.components.v1 as components
    components.html("""
        <audio autoplay>
            <source src="https://assets.mixkit.co/active_storage/sfx/2437/2437-preview.mp3" type="audio/mpeg">
        </audio>
    """, height=0)
