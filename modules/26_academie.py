import streamlit as st
import pandas as pd
from utils_gsheets import load_gs_data, save_gs_data
from utils_ia import ask_ai, is_ia_enabled

# --- CONFIGURATION ---
KNOWLEDGE_WORKSHEET = "DB_Knowledge_Base"
KNOWLEDGE_FALLBACK = "data/db_knowledge.csv"
COLS_KB = ["id", "categorie", "titre", "contenu", "date_maj"]

etab_nom = "Pharmaciel" if st.session_state.get('etablissement') == 'pharmaciel' else "DarPharm"
st.title(f"🎓 Académie {etab_nom}")
st.markdown("### Centre de formation & Procédures standards")

# --- 1. CHARGEMENT DONNÉES ---
df_kb = load_gs_data(KNOWLEDGE_WORKSHEET, KNOWLEDGE_FALLBACK, COLS_KB)

# --- 2. ASSISTANT IA FORMATEUR ---
with st.sidebar.expander("🤖 Demander à l'IA Formateur", expanded=True):
    query = st.text_input("Comment puis-je t'aider ?")
    if st.button("Chercher la procédure"):
        if query and is_ia_enabled():
            context = "\n".join(df_kb['contenu'].tolist()) if not df_kb.empty else "Pas de procédures encore."
            prompt = f"""
            Tu es le formateur de {etab_nom}. En te basant UNIQUEMENT sur ces procédures : {{context}}.
            Réponds à cette question de l'agent : {query}.
            Si l'info n'est pas dans le contexte, dis-lui de demander au chef d'équipe.
            """
            st.info(ask_ai(prompt))

# --- 3. CONSULTATION ---
categories = ["Logistique", "Hygiène & Sécurité", "Inventaire", "RH & Primes", "Maintenance"]
sel_cat = st.selectbox("Filtrer par catégorie", ["Toutes"] + categories)

df_disp = df_kb if sel_cat == "Toutes" else df_kb[df_kb['categorie'] == sel_cat]

if not df_disp.empty:
    for idx, row in df_disp.iterrows():
        with st.expander(f"📄 {row['titre']} ({row['categorie']})"):
            st.markdown(row['contenu'])
            st.caption(f"Dernière mise à jour : {row['date_maj']}")
else:
    st.info("Aucune procédure enregistrée dans cette catégorie.")

# --- 4. AJOUT (ADMIN SEULEMENT) ---
is_admin = st.session_state.get('current_user', {}).get('role') == 'Admin'
if is_admin:
    st.divider()
    with st.expander("📝 Ajouter/Modifier une procédure (Admin)"):
        with st.form("form_kb"):
            cat = st.selectbox("Catégorie", categories)
            titre = st.text_input("Titre de la procédure")
            contenu = st.text_area("Contenu (Markdown supporté)", height=200)
            if st.form_submit_button("Publier dans l'Académie"):
                if titre and contenu:
                    new_row = {
                        "id": len(df_kb) + 1,
                        "categorie": cat,
                        "titre": titre,
                        "contenu": contenu,
                        "date_maj": pd.Timestamp.now().strftime("%d/%m/%Y")
                    }
                    df_kb = pd.concat([df_kb, pd.DataFrame([new_row])], ignore_index=True)
                    save_gs_data(df_kb, KNOWLEDGE_WORKSHEET, KNOWLEDGE_FALLBACK)
                    st.success("Procédure publiée !")
                    st.rerun()
