import streamlit as st
import pandas as pd
from datetime import datetime
from utils_gsheets import load_gs_data, save_gs_data
import plotly.express as px

# --- CONFIGURATION ---
VEHICULES_WORKSHEET = "DB_Flotte_Vehicules"
VEHICULES_FALLBACK = "data/db_flotte_vehicules.csv"
COLS_VEHICULES = ["id", "id_vehicule", "vehicule", "immatriculation", "nom_vehicule", "capacite_reservoir", "carburant", "prix_litre", "derniere_date", "prochaine_echeance", "alerte_kms", "km_actuel", "dernier_km_vidange", "dernier_km_freins", "dernier_km_distribution"]

JOURNAL_WORKSHEET = "DB_Flotte_Journal"
JOURNAL_FALLBACK = "data/db_flotte_journal.csv"
COLS_JOURNAL = ["id", "livreur", "vehicule", "kilometrage", "date", "depense", "conso_estimee"]

MECANIQUE_WORKSHEET = "DB_Entretien_Mecanique"
MECANIQUE_FALLBACK = "data/db_entretien_mecanique.csv"
COLS_MECANIQUE = ["id", "vehicule", "type_intervention", "kilometrage", "cout", "date", "commentaires"]

CAISSE_WORKSHEET = "DB_Flotte_Caisse"
CAISSE_FALLBACK = "data/db_flotte_caisse.csv"
COLS_CAISSE = ["id", "solde_initial"]

LIVREURS_WORKSHEET = "Livreurs"
LIVREURS_FALLBACK = "data/db_livreurs.csv"
COLS_LIVREURS = ["id", "nom", "telephone", "vehicule", "statut"]

st.title("🚛 Maintenance & Flotte")
st.markdown("### Suivi Financier et Maintenance du Parc")

# --- 1. CHARGEMENT DONNÉES ---
df_vehicules = load_gs_data(VEHICULES_WORKSHEET, VEHICULES_FALLBACK, COLS_VEHICULES)
df_journal = load_gs_data(JOURNAL_WORKSHEET, JOURNAL_FALLBACK, COLS_JOURNAL)
df_mecanique = load_gs_data(MECANIQUE_WORKSHEET, MECANIQUE_FALLBACK, COLS_MECANIQUE)
df_caisse = load_gs_data(CAISSE_WORKSHEET, CAISSE_FALLBACK, COLS_CAISSE)
df_livreurs = load_gs_data(LIVREURS_WORKSHEET, LIVREURS_FALLBACK, COLS_LIVREURS)

# Initialisation de la caisse si vide
if df_caisse.empty:
    df_caisse = pd.DataFrame([{"id": 1, "solde_initial": 0.0}])
    save_gs_data(df_caisse, CAISSE_WORKSHEET, CAISSE_FALLBACK)

# Conversion des types numériques
solde_initial = float(df_caisse['solde_initial'].iloc[0]) if not df_caisse.empty else 0.0
df_journal['depense'] = pd.to_numeric(df_journal['depense'], errors='coerce').fillna(0.0)
df_journal['kilometrage'] = pd.to_numeric(df_journal['kilometrage'], errors='coerce').fillna(0.0)
df_mecanique['cout'] = pd.to_numeric(df_mecanique['cout'], errors='coerce').fillna(0.0)

total_depenses = df_journal['depense'].sum() + df_mecanique['cout'].sum()
solde_restant = solde_initial - total_depenses

# --- 2. DASHBOARD FINANCIER ---
st.markdown("#### 💰 Synthèse Financière")
col_m1, col_m2, col_m3 = st.columns(3)

with col_m1:
    st.metric("Caisse Initiale", f"{solde_initial:,.2f} DZD")
with col_m2:
    st.metric("Total Dépenses", f"{total_depenses:,.2f} DZD")
with col_m3:
    is_critical = solde_restant < (solde_initial * 0.15)
    st.markdown(f"""
    <div style="padding: 1rem; border-radius: 0.5rem; background-color: {'rgba(239, 68, 68, 0.1)' if is_critical else 'rgba(34, 197, 94, 0.1)'}; border: 1px solid {'#ef4444' if is_critical else '#22c55e'};">
        <p style="margin: 0; font-size: 0.875rem; color: {'#ef4444' if is_critical else '#22c55e'}; font-weight: 600;">Solde Restant</p>
        <h3 style="margin: 0; color: {'#ef4444' if is_critical else '#22c55e'}; font-size: 1.5rem;">{solde_restant:,.2f} DZD</h3>
    </div>
    """, unsafe_allow_html=True)

with st.expander("⚙️ Modifier le solde initial de la caisse"):
    with st.form("form_caisse"):
        new_solde = st.number_input("Nouveau Solde Initial (DZD)", min_value=0.0, value=float(solde_initial), step=1000.0)
        if st.form_submit_button("Mettre à jour"):
            df_caisse.loc[0, 'solde_initial'] = new_solde
            save_gs_data(df_caisse, CAISSE_WORKSHEET, CAISSE_FALLBACK)
            st.success("Solde de caisse mis à jour.")
            st.rerun()

st.divider()

# --- 3. ALERTES DE MAINTENANCE ---
st.subheader("⚠️ Alertes de Maintenance")
alertes_trouvees = False
today = datetime.now()

if not df_vehicules.empty:
    df_vehicules['date_dt'] = pd.to_datetime(df_vehicules['prochaine_echeance'], format="%d/%m/%Y", errors='coerce')
    
    for _, row in df_vehicules.iterrows():
        # Check by date
        alert_date = False
        if pd.notna(row['date_dt']) and row['date_dt'] <= (today + pd.Timedelta(days=7)):
            alert_date = True
            
        # Check by kms
        alert_kms = False
        v_journal = df_journal[df_journal['vehicule'] == row['nom_vehicule']]
        max_km = 0
        if not v_journal.empty:
            max_km = v_journal['kilometrage'].max()
            try:
                alerte_km_val = float(row['alerte_kms'])
                if max_km >= alerte_km_val:
                    alert_kms = True
            except:
                pass
                
        if alert_date or alert_kms:
            alertes_trouvees = True
            msg = f"🚨 **{row['nom_vehicule']}** : "
            reasons = []
            if alert_date: reasons.append(f"Échéance le {row['prochaine_echeance']}")
            if alert_kms: reasons.append(f"Kilométrage critique atteint ({max_km:,.0f} km >= {row['alerte_kms']} km)")
            st.error(msg + " | ".join(reasons))

if not alertes_trouvees:
    st.success("✅ Tout le parc matériel est à jour (Dates & Kilométrages).")

st.divider()

# --- 4. TABS: JOURNAL & VÉHICULES ---
tab1, tab2, tab3, tab4 = st.tabs(["📝 Saisie & Journal des Dépenses", "🚛 Référentiel Véhicules", "👨‍✈️ Dépenses par Livreur", "🔧 Suivi & Entretien Mécanique"])

with tab1:
    st.markdown("### Ajouter une dépense / course")
    
    # Préparation de la liste des livreurs
    liste_livreurs = []
    if not df_livreurs.empty and 'nom' in df_livreurs.columns:
        liste_livreurs = df_livreurs['nom'].dropna().unique().tolist()
    
    # Ajout des livreurs déjà existants dans le journal
    if not df_journal.empty and 'livreur' in df_journal.columns:
        existing_journal_livreurs = df_journal['livreur'].dropna().unique().tolist()
        liste_livreurs = list(set(liste_livreurs + existing_journal_livreurs))
        
    liste_livreurs = sorted([str(x) for x in liste_livreurs if str(x).strip()])
    options_livreur = liste_livreurs + ["➕ Ajouter manuellement..."]
    
    # Préparation de la liste des véhicules
    liste_vehicules = []
    if not df_vehicules.empty and 'nom_vehicule' in df_vehicules.columns:
        liste_vehicules = df_vehicules['nom_vehicule'].dropna().unique().tolist()
        
    with st.form("form_depense"):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            sel_livreur = st.selectbox("Livreur", options_livreur)
            custom_livreur = st.text_input("Nom du livreur (si 'Ajouter manuellement...' sélectionné)")
            vehicule_sel = st.selectbox("Véhicule", liste_vehicules if liste_vehicules else ["Aucun véhicule"])
            date_depense = st.date_input("Date")
        with col_f2:
            km_actuel = st.number_input("Kilométrage (Relevé Compteur)", min_value=0.0, step=1.0)
            montant = st.number_input("Montant Dépense (DZD)", min_value=0.0, step=100.0)
            
        submit_depense = st.form_submit_button("Enregistrer la dépense", type="primary")
        
        if submit_depense:
            if not liste_vehicules or vehicule_sel == "Aucun véhicule":
                st.error("Veuillez d'abord ajouter un véhicule dans le référentiel.")
            else:
                final_livreur = custom_livreur.strip().upper() if sel_livreur == "➕ Ajouter manuellement..." else sel_livreur
                if not final_livreur:
                    st.error("Veuillez spécifier le livreur.")
                elif montant <= 0:
                    st.error("Le montant de la dépense doit être supérieur à 0.")
                else:
                    # Logique de calcul de consommation
                    conso_estimee = "N/A"
                    v_history = df_journal[df_journal['vehicule'] == vehicule_sel]
                    distance = 0.0
                    if not v_history.empty:
                        last_km = v_history['kilometrage'].max()
                        if km_actuel > last_km:
                            distance = km_actuel - last_km
                            # Récupération infos véhicule
                            v_info = df_vehicules[df_vehicules['nom_vehicule'] == vehicule_sel]
                            if not v_info.empty:
                                try:
                                    prix_l = float(v_info.iloc[0]['prix_litre'])
                                    if prix_l > 0:
                                        litres = montant / prix_l
                                        conso_100 = (litres / distance) * 100
                                        conso_estimee = f"{conso_100:.2f} L/100km"
                                except:
                                    pass
                        elif km_actuel < last_km:
                            st.warning(f"Le kilométrage saisi ({km_actuel}) est inférieur au précédent ({last_km}).")
                    
                    new_id = int(df_journal['id'].max()) + 1 if not df_journal.empty and pd.notna(df_journal['id'].max()) else 1
                    new_dep = {
                        "id": new_id,
                        "livreur": final_livreur,
                        "vehicule": vehicule_sel,
                        "kilometrage": km_actuel,
                        "date": date_depense.strftime("%d/%m/%Y"),
                        "depense": montant,
                        "conso_estimee": conso_estimee
                    }
                    df_journal = pd.concat([df_journal, pd.DataFrame([new_dep])], ignore_index=True)
                    save_gs_data(df_journal, JOURNAL_WORKSHEET, JOURNAL_FALLBACK)
                    
                    # Mise à jour km_actuel
                    if not df_vehicules.empty:
                        idx = df_vehicules[df_vehicules['nom_vehicule'] == vehicule_sel].index
                        if not idx.empty:
                            current_km = pd.to_numeric(df_vehicules.loc[idx[0], 'km_actuel'], errors='coerce')
                            if pd.isna(current_km) or km_actuel > current_km:
                                df_vehicules.loc[idx[0], 'km_actuel'] = km_actuel
                                save_gs_data(df_vehicules, VEHICULES_WORKSHEET, VEHICULES_FALLBACK)
                    
                    st.success(f"Dépense ajoutée ! ({conso_estimee} estimé pour {distance} km parcourus)")
                    st.rerun()

    st.markdown("### 📖 Journal des Dépenses")
    if df_journal.empty:
        st.info("Aucune dépense enregistrée.")
    else:
        # Nettoyage et formatage du tableau pour affichage
        df_display = df_journal.copy()
        df_display = df_display.sort_values(by="id", ascending=False)
        st.dataframe(df_display, use_container_width=True, hide_index=True)

with tab2:
    st.markdown("### Gestion du Parc Matériel")
    
    with st.expander("➕ Ajouter un nouveau véhicule", expanded=False):
        with st.form("form_vehicule"):
            col_v1, col_v2 = st.columns(2)
            with col_v1:
                v_id_veh = st.selectbox("ID Véhicule", [f"{i:02d}" for i in range(1, 101)])
                v_veh = st.text_input("Véhicule (ex: DOBLO)")
                v_imm = st.text_input("Immatriculation (ex: 12345 123 16)")
                v_cap = st.number_input("Capacité Réservoir (L)", min_value=1, value=50)
                v_carb = st.selectbox("Carburant", ["MAZOUT", "ESSENCE", "GPL", "SANS PLOMB"])
                v_prix = st.number_input("Prix au litre (DZD)", min_value=0.0, value=31.0)
            with col_v2:
                v_last_d = st.date_input("Date dernière maintenance")
                v_next_d = st.date_input("Date prochaine échéance prévue")
                v_alert_km = st.number_input("Kilométrage pour prochaine alerte", min_value=0, value=10000, step=1000)
                st.markdown("**Initialisation Kilométrage**")
                v_km_actuel = st.number_input("Kilométrage Actuel", min_value=0.0, step=1.0)
                v_km_vidange = st.number_input("Dernier km Vidange", min_value=0.0, step=1.0)
                v_km_freins = st.number_input("Dernier km Freins", min_value=0.0, step=1.0)
                v_km_distrib = st.number_input("Dernier km Distribution", min_value=0.0, step=1.0)
            
            if st.form_submit_button("Ajouter le véhicule"):
                if v_veh and v_imm:
                    v_nom = f"{v_id_veh} - {v_veh} - {v_imm}"
                    new_v_id = int(df_vehicules['id'].max()) + 1 if not df_vehicules.empty and pd.notna(df_vehicules['id'].max()) else 1
                    new_vehicule = {
                        "id": new_v_id,
                        "id_vehicule": v_id_veh,
                        "vehicule": v_veh,
                        "immatriculation": v_imm,
                        "nom_vehicule": v_nom,
                        "capacite_reservoir": v_cap,
                        "carburant": v_carb,
                        "prix_litre": v_prix,
                        "derniere_date": v_last_d.strftime("%d/%m/%Y"),
                        "prochaine_echeance": v_next_d.strftime("%d/%m/%Y"),
                        "alerte_kms": v_alert_km,
                        "km_actuel": v_km_actuel,
                        "dernier_km_vidange": v_km_vidange,
                        "dernier_km_freins": v_km_freins,
                        "dernier_km_distribution": v_km_distrib
                    }
                    df_vehicules = pd.concat([df_vehicules, pd.DataFrame([new_vehicule])], ignore_index=True)
                    save_gs_data(df_vehicules, VEHICULES_WORKSHEET, VEHICULES_FALLBACK)
                    st.success(f"Véhicule {v_nom} ajouté avec succès !")
                    st.rerun()
                else:
                    st.error("Les champs Véhicule et Immatriculation sont obligatoires.")
                    
    st.markdown("### 📋 Liste des Véhicules & Alertes paramétrées")
    if df_vehicules.empty:
        st.info("Aucun véhicule dans le référentiel.")
    else:
        st.dataframe(df_vehicules.drop(columns=['date_dt'], errors='ignore'), use_container_width=True, hide_index=True)

with tab3:
    st.markdown("### 👨‍✈️ Dépenses par Livreur")
    if df_journal.empty:
        st.info("Aucune donnée disponible pour le moment.")
    else:
        df_l = df_journal.copy()
        df_l['depense'] = pd.to_numeric(df_l['depense'], errors='coerce').fillna(0)
        df_l['date'] = pd.to_datetime(df_l['date'], format='%d/%m/%Y', errors='coerce')
        
        recap_l = df_l.groupby("livreur").agg(
            Total_Depense_DZD=('depense', 'sum'),
            Nombre_Courses=('id', 'count'),
            Derniere_Course=('date', 'max')
        ).reset_index()
        
        recap_l['Derniere_Course'] = recap_l['Derniere_Course'].dt.strftime('%d/%m/%Y')
        
        col_t3_1, col_t3_2 = st.columns([1.5, 1])
        with col_t3_1:
            st.dataframe(recap_l, use_container_width=True, hide_index=True)
        with col_t3_2:
            fig = px.pie(recap_l, values='Total_Depense_DZD', names='livreur', title="Répartition du budget carburant")
            st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.markdown("### 🔧 Suivi & Entretien Mécanique")
    
    st.markdown("#### 🚨 Dashboard des Alertes Préventives")
    alertes_meca = False
    
    if not df_vehicules.empty:
        df_vehicules['km_actuel'] = pd.to_numeric(df_vehicules['km_actuel'], errors='coerce').fillna(0)
        df_vehicules['dernier_km_vidange'] = pd.to_numeric(df_vehicules['dernier_km_vidange'], errors='coerce').fillna(0)
        df_vehicules['dernier_km_freins'] = pd.to_numeric(df_vehicules['dernier_km_freins'], errors='coerce').fillna(0)
        df_vehicules['dernier_km_distribution'] = pd.to_numeric(df_vehicules['dernier_km_distribution'], errors='coerce').fillna(0)
        
        for _, row in df_vehicules.iterrows():
            km = row['km_actuel']
            alert_list = []
            if km - row['dernier_km_vidange'] >= 10000:
                alert_list.append("Vidange (>= 10 000 km)")
            if km - row['dernier_km_freins'] >= 20000:
                alert_list.append("Freins (>= 20 000 km)")
            if km - row['dernier_km_distribution'] >= 80000:
                alert_list.append("Distribution (>= 80 000 km)")
                
            if alert_list:
                alertes_meca = True
                st.error(f"**{row['nom_vehicule']}** nécessite : " + ", ".join(alert_list))
                
    if not alertes_meca:
        st.success("✅ Aucun entretien mécanique préventif en attente.")
        
    st.divider()
    
    st.markdown("#### 🛠️ Saisir une intervention mécanique")
    with st.form("form_mecanique"):
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            liste_vehicules_meca = []
            if not df_vehicules.empty and 'nom_vehicule' in df_vehicules.columns:
                liste_vehicules_meca = df_vehicules['nom_vehicule'].dropna().unique().tolist()
                
            m_vehicule = st.selectbox("Véhicule concerné", liste_vehicules_meca if liste_vehicules_meca else ["Aucun véhicule"])
            m_type = st.selectbox("Type d'intervention", ["Vidange", "Freins", "Distribution", "Autre"])
            m_date = st.date_input("Date de l'intervention")
        with col_m2:
            m_km = st.number_input("Kilométrage (Relevé lors de l'intervention)", min_value=0.0, step=1.0)
            m_cout = st.number_input("Coût (DZD)", min_value=0.0, step=100.0)
            m_com = st.text_area("Commentaires additionnels (optionnel)")
            
        if st.form_submit_button("Enregistrer l'intervention", type="primary"):
            if not liste_vehicules_meca or m_vehicule == "Aucun véhicule":
                st.error("Veuillez d'abord ajouter un véhicule dans le référentiel.")
            elif m_cout <= 0:
                st.error("Le coût doit être supérieur à 0.")
            else:
                new_m_id = int(df_mecanique['id'].max()) + 1 if not df_mecanique.empty and pd.notna(df_mecanique['id'].max()) else 1
                new_meca = {
                    "id": new_m_id,
                    "vehicule": m_vehicule,
                    "type_intervention": m_type,
                    "kilometrage": m_km,
                    "cout": m_cout,
                    "date": m_date.strftime("%d/%m/%Y"),
                    "commentaires": m_com
                }
                df_mecanique = pd.concat([df_mecanique, pd.DataFrame([new_meca])], ignore_index=True)
                save_gs_data(df_mecanique, MECANIQUE_WORKSHEET, MECANIQUE_FALLBACK)
                
                if not df_vehicules.empty:
                    idx = df_vehicules[df_vehicules['nom_vehicule'] == m_vehicule].index
                    if not idx.empty:
                        df_vehicules.loc[idx[0], 'km_actuel'] = max(m_km, pd.to_numeric(df_vehicules.loc[idx[0], 'km_actuel'], errors='coerce') or 0)
                        
                        if m_type == "Vidange":
                            df_vehicules.loc[idx[0], 'dernier_km_vidange'] = m_km
                        elif m_type == "Freins":
                            df_vehicules.loc[idx[0], 'dernier_km_freins'] = m_km
                        elif m_type == "Distribution":
                            df_vehicules.loc[idx[0], 'dernier_km_distribution'] = m_km
                            
                        save_gs_data(df_vehicules, VEHICULES_WORKSHEET, VEHICULES_FALLBACK)
                
                st.success("Intervention enregistrée et base de données mise à jour !")
                st.rerun()

    st.markdown("#### 📖 Historique des réparations")
    if df_mecanique.empty:
        st.info("Aucune intervention enregistrée.")
    else:
        st.dataframe(df_mecanique.sort_values(by="id", ascending=False), use_container_width=True, hide_index=True)
