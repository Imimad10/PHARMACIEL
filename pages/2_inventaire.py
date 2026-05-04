# --- TROUVEZ LA SECTION ADMIN ET ASSUREZ-VOUS QU'ELLE EST INDÉPENDANTE ---

with tabs[3]: # L'onglet Admin
    st.header("⚙️ Configuration & Import Logipharm")
    
    # Cette zone doit être visible même si le reste plante
    file = st.file_uploader("Glissez votre fichier Excel Logipharm ici", type=["xlsx"])
    
    if file:
        with open(MASTER_PATH, "wb") as f:
            f.write(file.getbuffer())
        st.success("✅ Fichier Master mis à jour avec succès !")
        st.rerun()

    st.divider()
    st.write("### 🛠️ Zone de secours")
    if st.button("🔴 Réinitialiser TOUTES les données (Master + Saisie)"):
        if os.path.exists(MASTER_PATH): os.remove(MASTER_PATH)
        if os.path.exists(SAISIE_PATH): os.remove(SAISIE_PATH)
        st.warning("Système remis à zéro. Rechargez un fichier Excel.")
        st.rerun()
