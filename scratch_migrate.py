import sys
import pandas as pd
sys.path.append(r'c:\projects\PHARMACIEL')
from config_users import DEFAULT_USERS
from utils_gsheets import save_users_to_config

df = pd.DataFrame(DEFAULT_USERS)
if 'email' not in df.columns:
    df['email'] = ""
success, msg = save_users_to_config(df)
print("Migration:", success, msg)
