import toml
from google.oauth2.service_account import Credentials

try:
    with open("c:/projects/PHARMACIEL/.streamlit/secrets.toml", "r") as f:
        secrets = toml.load(f)
    
    creds_dict = secrets["connections"]["gsheets"]
    
    creds = Credentials.from_service_account_info(creds_dict)
    print("Success!")
except Exception as e:
    print(f"Error: {e}")
