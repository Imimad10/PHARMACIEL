import streamlit as st
import pandas as pd
from datetime import datetime
from utils_gsheets import load_gs_data, save_gs_data

# --- CONFIGURATION ---
VEHICULES_WORKSHEET = "DB_Flotte_Vehicules"
VEHICULES_FALLBACK = "data/db_flotte_vehicules.csv"
COLS_VEHICULES = ["id", "nom_vehicule", "capacite_reservoir", "carburant", "prix_litre", "derniere_date", "prochaine_echeance", "alerte_kms"]

JOURNAL_WORKSHEET = "DB_Flotte_Journal"
JOURNAL_FALLBACK = "data/db_flotte_journal.csv"
COLS_JOURNAL = ["id", "livreur", "vehicule", "kilometrage", "date", "depense", "conso_estimee"]

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

total_depenses = df_journal['depense'].sum()
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
tab1, tab2 = st.tabs(["📝 Saisie & Journal des Dépenses", "🚛 Référentiel Véhicules"])

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
    options_livreur = liste_livreurs + ["➕ Autre / Saisie manuelle"]
    
    # Préparation de la liste des véhicules
    liste_vehicules = []
    if not df_vehicules.empty and 'nom_vehicule' in df_vehicules.columns:
        liste_vehicules = df_vehicules['nom_vehicule'].dropna().unique().tolist()
        
    with st.form("form_depense"):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            sel_livreur = st.selectbox("Livreur", options_livreur)
            custom_livreur = st.text_input("Nom du livreur (si 'Autre' sélectionné)")
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
                final_livreur = custom_livreur.strip().upper() if sel_livreur == "➕ Autre / Saisie manuelle" else sel_livreur
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
                v_nom = st.text_input("Nom / Immatriculation (ex: DOBLO - 12345)")
                v_cap = st.number_input("Capacité Réservoir (L)", min_value=1, value=50)
                v_carb = st.selectbox("Carburant", ["MAZOUT", "ESSENCE", "GPL", "SANS PLOMB"])
                v_prix = st.number_input("Prix au litre (DZD)", min_value=0.0, value=31.0)
            with col_v2:
                v_last_d = st.date_input("Date dernière maintenance")
                v_next_d = st.date_input("Date prochaine échéance prévue")
                v_alert_km = st.number_input("Kilométrage pour prochaine alerte", min_value=0, value=10000, step=1000)
            
            if st.form_submit_button("Ajouter le véhicule"):
                if v_nom:
                    new_v_id = int(df_vehicules['id'].max()) + 1 if not df_vehicules.empty and pd.notna(df_vehicules['id'].max()) else 1
                    new_vehicule = {
                        "id": new_v_id,
                        "nom_vehicule": v_nom,
                        "capacite_reservoir": v_cap,
                        "carburant": v_carb,
                        "prix_litre": v_prix,
                        "derniere_date": v_last_d.strftime("%d/%m/%Y"),
                        "prochaine_echeance": v_next_d.strftime("%d/%m/%Y"),
                        "alerte_kms": v_alert_km
                    }
                    df_vehicules = pd.concat([df_vehicules, pd.DataFrame([new_vehicule])], ignore_index=True)
                    save_gs_data(df_vehicules, VEHICULES_WORKSHEET, VEHICULES_FALLBACK)
                    st.success(f"Véhicule {v_nom} ajouté avec succès !")
                    st.rerun()
                else:
                    st.error("Le nom du véhicule est obligatoire.")
                    
    st.markdown("### 📋 Liste des Véhicules & Alertes paramétrées")
    if df_vehicules.empty:
        st.info("Aucun véhicule dans le référentiel.")
    else:
        st.dataframe(df_vehicules.drop(columns=['date_dt'], errors='ignore'), use_container_width=True, hide_index=True)
