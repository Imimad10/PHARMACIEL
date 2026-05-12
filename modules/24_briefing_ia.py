import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils_gsheets import load_gs_data
from utils_ia import ask_ai, is_ia_enabled

st.title("🎤 Briefing Matinal IA")
st.markdown("### Votre stratégie pour une journée productive")

if not is_ia_enabled():
    st.warning("L'IA n'est pas activée.")
    st.stop()

# --- 1. COLLECTE DES DONNÉES ---
TASKS_WORKSHEET = "DB_Tasks_Team"
TASKS_FALLBACK = "data/db_tasks.csv"
COLS_TASKS = ["id", "creation_date", "task", "assigned_to", "priority", "status"]

df_tasks = load_gs_data(TASKS_WORKSHEET, TASKS_FALLBACK, COLS_TASKS)

if st.button("🚀 Générer le Briefing du Jour", use_container_width=True, type="primary"):
    with st.spinner("L'IA prépare votre briefing..."):
        # Stats d'hier (approximatif pour la démo)
        hier = (datetime.now() - timedelta(days=1)).strftime("%d/%m/%Y")
        tasks_hier = df_tasks[df_tasks['creation_date'] == hier]
        fini_hier = len(tasks_hier[tasks_hier['status'] == "Terminé"])
        total_hier = len(tasks_hier)
        
        # Tasks à faire aujourd'hui
        todo_today = df_tasks[df_tasks['status'] == "À faire"]
        todo_list = todo_today['task'].tolist()[:5]
        
        prompt = f"""
        Tu es un chef d'entrepôt charismatique et motivant.
        Fais un briefing court (150 mots max) pour l'équipe (Ayoub, Islem, Imad, Seif).
        
        Bilan d'hier : {fini_hier} tâches terminées sur {total_hier}.
        Objectifs du jour : {todo_list}.
        
        Donne un conseil de sécurité, une phrase de motivation et une priorité claire.
        Format : Discours direct.
        """
        
        briefing = ask_ai(prompt)
        
        st.chat_message("assistant", avatar="🤖").markdown(f"### 📢 Briefing du {datetime.now().strftime('%d/%m/%Y')}")
        st.chat_message("assistant", avatar="🤖").write(briefing)
        
        st.divider()
        st.info("💡 Partagez ce message sur le groupe WhatsApp de l'équipe pour bien démarrer !")

st.divider()
with st.expander("📊 Aperçu de la charge de travail actuelle"):
    if not df_tasks.empty:
        st.bar_chart(df_tasks['status'].value_counts())
    else:
        st.write("Aucune donnée disponible.")
