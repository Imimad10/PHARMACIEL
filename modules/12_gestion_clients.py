import streamlit as st
import pandas as pd
import os
from utils_gsheets import load_gs_data, save_gs_data, show_sync_ui
from utils_ia import ask_ai
import json
import re

# --- CONFIGURATION ---
WORKSHEET_NAME = "DB_Clients_CRM"
FALLBACK_PATH = "data/db_clients.csv"
COLUMNS = ["ID", "Nom_Pharmacie", "Gerant", "Ville", "Adresse", "Telephone", "Coordonnees", "Email", "Statut", "Commentaire"]

st.title("🤝 Gestion de la Clientèle (CRM)")
st.markdown("### Suivez et développez votre réseau de pharmacies")

show_sync_ui(WORKSHEET_NAME, FALLBACK_PATH, COLUMNS)
df_clients = load_gs_data(WORKSHEET_NAME, FALLBACK_PATH, COLUMNS)

# --- STYLE CSS CARTE DE VISITE PREMIUM ---
st.markdown("""
<style>
    .client-card {
        background: white;
        border-radius: 20px;
        padding: 25px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.05);
        border: 1px solid rgba(0,0,0,0.05);
        margin-top: 20px;
        position: relative;
        overflow: hidden;
    }
    .client-card::after {
        content: "";
        position: absolute;
        top: 0; right: 0; width: 100px; height: 100px;
        background: linear-gradient(135deg, #5b6cf9 0%, #3a47d5 100%);
        opacity: 0.1;
        border-radius: 0 0 0 100%;
    }
    .client-name {
        font-size: 1.8rem;
        font-weight: 800;
        color: #1a1f3c;
        margin-bottom: 5px;
    }
    .client-sub {
        font-size: 1rem;
        color: #5b6cf9;
        font-weight: 700;
        margin-bottom: 20px;
    }
    .info-item {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 10px;
        color: #4a5568;
    }
</style>
""", unsafe_allow_html=True)

tab_list, tab_add, tab_ia, tab_admin = st.tabs(["📋 Liste des Clients", "➕ Ajouter un Client", "🤖 Assistant IA CRM", "⚙️ Configuration"])

# --- TAB 0 : ADMIN / SYNC ---
with tab_admin:
    st.subheader("⚙️ Synchronisation & Maintenance")
    
    if st.session_state.current_user.get('role') != 'Admin':
        st.warning("Accès réservé aux administrateurs.")
    else:
        # --- BOUTON SYNC RECOUVREMENT ---
        st.markdown("#### 🔄 Intégration avec le Recouvrement")
        st.write("Importer les clients depuis la base de recouvrement pour éviter les saisies multiples.")
        
        if st.button("📥 Synchroniser avec la base Recouvrement", use_container_width=True):
            with st.spinner("Fusion des bases de données..."):
                # On définit les constantes du module recouvrement directement (évite l'import invalide '4_recouvrement')
                DATA_RECOUV_CLIENTS = "base_clients.csv"
                COLS_RECOUV_CLIENTS = ["Nom Client", "Secteur"]
                
                # Charger la base recouvrement
                df_recouv = load_gs_data("Base_Clients", DATA_RECOUV_CLIENTS, COLS_RECOUV_CLIENTS)
                
                if not df_recouv.empty:
                    count_added = 0
                    current_names = [str(n).upper().strip() for n in df_clients['Nom_Pharmacie'].tolist()]
                    
                    new_rows = []
                    for _, row in df_recouv.iterrows():
                        name = str(row.get('Nom Client', row.get('Nom_Client', ''))).upper().strip()
                        if name and name not in current_names:
                            new_rows.append({
                                "ID": len(df_clients) + len(new_rows) + 1,
                                "Nom_Pharmacie": name,
                                "Gerant": "A compléter",
                                "Ville": row.get('Secteur', ''),
                                "Adresse": "",
                                "Telephone": "",
                                "Coordonnees": "",
                                "Email": "",
                                "Statut": "A prospecter",
                                "Commentaire": "Importé depuis Recouvrement"
                            })
                            count_added += 1
                    
                    if new_rows:
                        df_clients = pd.concat([df_clients, pd.DataFrame(new_rows)], ignore_index=True)
                        save_gs_data(df_clients, WORKSHEET_NAME, FALLBACK_PATH)
                        st.success(f"✨ {count_added} nouveaux clients importés depuis le recouvrement !")
                        st.rerun()
                    else:
                        st.info("Tout est déjà à jour. Aucun nouveau client trouvé.")
                else:
                    st.error("Impossible de charger la base de recouvrement (Worksheet 'Base_Clients' introuvable).")

        st.divider()
        
        # --- BOUTON NETTOYAGE DOUBLONS ---
        st.markdown("#### 🧹 Nettoyage des Doublons")
        if st.button("Supprimer les doublons (par nom de pharmacie)", use_container_width=True):
            old_len = len(df_clients)
            df_clients['Nom_Pharmacie'] = df_clients['Nom_Pharmacie'].str.upper().str.strip()
            df_clients = df_clients.drop_duplicates(subset=['Nom_Pharmacie'], keep='first')
            new_len = len(df_clients)
            
            if old_len > new_len:
                save_gs_data(df_clients, WORKSHEET_NAME, FALLBACK_PATH)
                st.success(f"✅ {old_len - new_len} doublons supprimés !")
                st.rerun()
            else:
                st.info("Aucun doublon détecté.")

        st.divider()
        
        # --- IMPORT FICHIER EXTERNE ---
        st.markdown("#### 📤 Importation de fichier externe")
        uploaded_file = st.file_uploader("Téléverser la base client (XLSX, XLS, CSV)", type=['xlsx', 'xls', 'csv'], key="crm_up")

with tab_list:
    col_s1, col_s2 = st.columns([2, 1])
    search = col_s1.text_input("🔍 Rechercher une pharmacie :", placeholder="Nom, ville, gérant...")
    
    df_filtered = df_clients.copy()
    if search:
        df_filtered = df_filtered[
            df_filtered['Nom_Pharmacie'].str.contains(search, case=False, na=False) |
            df_filtered['Gerant'].str.contains(search, case=False, na=False) |
            df_filtered['Ville'].str.contains(search, case=False, na=False)
        ]
    
    if df_filtered.empty:
        st.info("Aucun client trouvé.")
    else:
        # Liste de sélection pour la carte de visite
        client_selected_name = st.selectbox("Sélectionner un client pour voir sa fiche :", df_filtered['Nom_Pharmacie'].tolist())
        
        if client_selected_name:
            client = df_filtered[df_filtered['Nom_Pharmacie'] == client_selected_name].iloc[0]
            
            # --- CARTE DE VISITE ---
            st.markdown(f"""
            <div class="client-card">
                <div class="client-name">{client['Nom_Pharmacie']}</div>
                <div class="client-sub">👤 {client['Gerant']}</div>
                <div class="info-item">📍 <b>Ville:</b> {client['Ville']}</div>
                <div class="info-item">🏠 <b>Adresse:</b> {client['Adresse']}</div>
                <div class="info-item">📞 <b>Tél:</b> {client['Telephone']}</div>
                <div class="info-item">✉️ <b>Email:</b> {client['Email']}</div>
                <div class="info-item">🏷️ <b>Statut:</b> {client['Statut']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # --- CARTE MAPS ---
            st.markdown("#### 📍 Localisation")
            coords = str(client['Coordonnees'])
            if coords and "," in coords:
                try:
                    lat, lon = map(float, coords.split(","))
                    map_data = pd.DataFrame({'lat': [lat], 'lon': [lon]})
                    st.map(map_data, zoom=14)
                except:
                    st.warning("Coordonnées invalides.")
            else:
                st.info("Aucun point GPS enregistré pour ce client.")
                if st.button("🗺️ Rechercher Coordonnées avec l'IA"):
                    with st.spinner("Recherche des coordonnées..."):
                        prompt = f"Donne les coordonnées GPS (latitude, longitude) approximatives pour la pharmacie {client['Nom_Pharmacie']} à {client['Ville']}, {client['Adresse']}. Réponds UNIQUEMENT sous la forme: lat, lon"
                        res_coords = ask_ai(prompt)
                        st.write(f"Suggéré : {res_coords}")
                        if st.button("Appliquer ces coordonnées"):
                            df_clients.loc[df_clients['ID'] == client['ID'], 'Coordonnees'] = res_coords
                            save_gs_data(df_clients, WORKSHEET_NAME, FALLBACK_PATH)
                            st.rerun()

with tab_add:
    st.subheader("💊 Nouvelle fiche Professionnelle")
    with st.form("form_add_client"):
        c1, c2 = st.columns(2)
        nom = c1.text_input("Nom de l'Établissement", placeholder="Ex: Pharmacie Centrale")
        gerant = c2.text_input("Pharmacien Directeur / Gérant")
        
        ville = c1.selectbox("Wilaya / Ville", ["Alger", "Oran", "Constantine", "Sétif", "Annaba", "Blida", "Tizi Ouzou", "Batna", "Autre..."])
        adresse = c2.text_input("Adresse (Rue, Quartier)")
        
        tel = c1.text_input("Téléphone (Fixe/Mobile)")
        email = c2.text_input("Email Professionnel")
        
        # Mise à jour des types selon la demande utilisateur
        status = st.selectbox("Type d'Établissement", ["Officine (Pharmacie)", "Grossiste Répartiteur", "Parapharmacie", "Laboratoire", "Autre"])
        
        if st.form_submit_button("✅ Enregistrer dans le Réseau", use_container_width=True, type="primary"):
            if nom and gerant:
                new_row = {
                    "ID": len(df_clients) + 1,
                    "Nom_Pharmacie": nom.upper(),
                    "Gerant": gerant,
                    "Ville": ville,
                    "Adresse": adresse,
                    "Telephone": tel,
                    "Coordonnees": "",
                    "Email": email,
                    "Statut": status,
                    "Commentaire": ""
                }
                df_clients = pd.concat([df_clients, pd.DataFrame([new_row])], ignore_index=True)
                save_gs_data(df_clients, WORKSHEET_NAME, FALLBACK_PATH)
                st.success(f"✅ {status} ajouté avec succès !")
                st.rerun()
            else:
                st.error("Le Nom et le Gérant sont obligatoires.")

with tab_ia:
    st.subheader("🧠 Intelligence Artificielle Pharmaceutique")
    st.info("L'IA DarPharm analyse le secteur pour compléter les fiches techniques de vos clients.")
    
    target_client = st.selectbox("Sélectionner l'établissement à enrichir :", df_clients['Nom_Pharmacie'].tolist(), key="ia_crm_select")
    
    if st.button("🔍 Lancer l'analyse sectorielle", use_container_width=True, type="primary"):
        client_data = df_clients[df_clients['Nom_Pharmacie'] == target_client].iloc[0]
        with st.spinner("Recherche dans les bases pharmaceutiques..."):
            prompt = f"""Tu es un expert du marché pharmaceutique algérien. 
            Je veux compléter les informations pour l'établissement suivant : 
            Nom: {client_data['Nom_Pharmacie']}
            Type: {client_data['Statut']}
            Localisation: {client_data['Ville']}, {client_data['Adresse']}
            
            Recherche spécifiquement :
            1. Le numéro de téléphone professionnel.
            2. Les coordonnées GPS précises pour la logistique (lat, lon).
            3. L'email de contact.
            
            Réponds uniquement sous format JSON strict : 
            {{
              "Telephone": "...",
              "Coordonnees": "lat, lon",
              "Email": "..."
            }}"""

            {{
              "Telephone": "...",
              "Coordonnees": "lat, lon",
              "Email": "..."
            }}"""
            
            res_ia = ask_ai(prompt)
            try:
                # Extraction du JSON
                json_match = re.search(r'\{.*\}', res_ia, re.DOTALL)
                if json_match:
                    new_data = json.loads(json_match.group())
                    st.write("### ✨ Informations trouvées :")
                    st.json(new_data)
                    
                    if st.button("💾 Appliquer les modifications"):
                        for key, value in new_data.items():
                            if value and value != "...":
                                df_clients.loc[df_clients['Nom_Pharmacie'] == target_client, key] = value
                        save_gs_data(df_clients, WORKSHEET_NAME, FALLBACK_PATH)
                        st.success("Fiche client mise à jour !")
                        st.rerun()
                else:
                    st.warning("L'IA n'a pas pu structurer les données. Voici sa réponse :")
                    st.write(res_ia)
            except Exception as e:
                st.error(f"Erreur lors du traitement IA : {e}")

st.divider()
st.caption("Pharmaciel CRM v1.0 — Intelligence Client Intégrée.")
