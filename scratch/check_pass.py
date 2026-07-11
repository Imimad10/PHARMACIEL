import streamlit as st
import pandas as pd
from utils_gsheets import load_gs_data

# The worksheet name is "Utilisateurs"
df = load_gs_data("Utilisateurs", None, ["username", "password", "role", "metier", "depot", "zone", "nom", "prenom", "pages"])
if df is not None and not df.empty:
    user = df[df['username'].astype(str).str.lower() == 'imad']
    if not user.empty:
        print("Imad password is:", user['password'].values[0])
    else:
        print("User Imad not found in Pharmaciel Google Sheet")
else:
    print("Failed to load Google Sheet")
