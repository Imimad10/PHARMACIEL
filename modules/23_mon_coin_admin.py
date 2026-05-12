import streamlit as st
import pandas as pd
from datetime import datetime
from utils_gsheets import load_gs_data, save_gs_data
from utils_ia import ask_ai, is_ia_enabled

# --- CONFIGURATION ---
IDEAS_WORKSHEET = "DB_Admin_Ideas"
IDEAS_FALLBACK = "data/db_admin_ideas.csv"
COLS_IDEAS = ["id", "date", "titre", "idee_brute", "developpement_ia"]

st.title("🤫 Mon Coin Secret (Admin Only)")
st.markdown("### Brainstorming & Développement d'idées")

# --- 1. CHARGEMENT DONNÉES ---
df_ideas = load_gs_data(IDEAS_WORKSHEET, IDEAS_FALLBACK, COLS_IDEAS)

# --- 2. NOUVELLE IDÉE ---
with st.expander("💡 Noter une nouvelle idée", expanded=True):
    with st.form("form_idea"):
        titre = st.text_input("Titre de l'idée")
        idee = st.text_area("Décrivez votre idée en quelques mots...", height=150)
        
        col1, col2 = st.columns(2)
        help_ia = col1.checkbox("Développer avec l'IA ?", value=True)
        
        if st.form_submit_button("✨ Enregistrer & Développer"):
            if titre and idee:
                dev_ia = ""
                if help_ia and is_ia_enabled():
                    with st.spinner("L'IA développe votre concept..."):
                        prompt = f"""
                        En tant que consultant expert en stratégie et logistique, aide-moi à développer cette idée pour ma plateforme Pharmaciel :
                        Titre : {titre}
                        Idée : {idee}
                        
                        Donne-moi :
                        1. Les avantages principaux.
                        2. Un plan d'action pour la mettre en place.
                        3. Les risques potentiels.
                        """
                        dev_ia = ask_ai(prompt)
                
                new_row = {
                    "id": len(df_ideas) + 1,
                    "date": datetime.now().strftime("%d/%m/%Y"),
                    "titre": titre,
                    "idee_brute": idee,
                    "developpement_ia": dev_ia
                }
                df_ideas = pd.concat([df_ideas, pd.DataFrame([new_row])], ignore_index=True)
                save_gs_data(df_ideas, IDEAS_WORKSHEET, IDEAS_FALLBACK)
                st.success("Idée enregistrée dans votre coin secret !")
                st.rerun()

# --- 3. MES IDÉES ENREGISTRÉES ---
st.divider()
st.subheader("📚 Ma Bibliothèque d'Idées")

if not df_ideas.empty:
    for idx, row in df_ideas.sort_index(ascending=False).iterrows():
        with st.expander(f"📌 {row['titre']} ({row['date']})"):
            st.markdown("**Idée originale :**")
            st.write(row['idee_brute'])
            st.divider()
            if row['developpement_ia']:
                st.markdown("**🧠 Analyse & Développement IA :**")
                st.markdown(row['developpement_ia'])
            
            if st.button("🗑️ Supprimer", key=f"del_{row['id']}"):
                df_ideas = df_ideas.drop(idx)
                save_gs_data(df_ideas, IDEAS_WORKSHEET, IDEAS_FALLBACK)
                st.rerun()
else:
    st.info("Votre coin est vide. Notez votre première idée géniale ci-dessus !")
