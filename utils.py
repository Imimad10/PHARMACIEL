from utils_gsheets import load_gs_data, save_gs_data
import pandas as pd

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
