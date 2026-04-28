import os
from datetime import datetime
from tinydb import TinyDB

def log_action(user, action, module="Système"):
    """Enregistre une action dans la base de données des logs."""
    os.makedirs("data", exist_ok=True)
    db_logs = TinyDB('data/db_logs.json')
    db_logs.insert({
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user": user,
        "module": module,
        "action": action
    })
