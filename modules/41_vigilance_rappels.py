import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
import os
import hashlib
from utils import log_action
from utils_gsheets import load_gs_data, save_gs_data

# --- CONFIGURATION ---
WORKSHEET_NAME = "Rappels_Vigilance"
FALLBACK_PATH = "data/data_rappels.csv"
COLUMNS = ["Date_Rappel", "Produit", "Lot", "Motif", "Statut", "Taux_Recup", "Agent"]

# Charger les clients
df_clients = load_gs_data("Clients", "base_clients.csv", ["Nom Client", "Région", "Téléphone"])
liste_clients = df_clients.to_dict('records') if not df_clients.empty else [
    {"Nom Client": "Pharmacie Centrale", "Région": "Alger 1", "Téléphone": "0550 12 34 56"},
    {"Nom Client": "Pharmacie Pasteur", "Région": "Constantine", "Téléphone": "031 45 67 89"},
    {"Nom Client": "Pharmacie Errazi", "Région": "Blida", "Téléphone": "025 88 99 77"},
    {"Nom Client": "Pharmacie Echifa", "Région": "Tipaza", "Téléphone": "024 11 22 33"}
]

# Charger le catalogue de produits (depuis catalogue_pharmnet.csv)
try:
    df_cat = pd.read_csv("catalogue_pharmnet.csv")
    liste_prods = sorted(df_cat["Nom Commercial"].dropna().unique().tolist())
except:
    liste_prods = ["DOLIPRANE 1000", "AMOXYCILLINE", "SPASFON LYOC", "BETADINE", "SÉRUM SALÉ"]

# Charger les rappels enregistrés
df_rappels = load_gs_data(WORKSHEET_NAME, FALLBACK_PATH, COLUMNS)

st.set_page_config(page_title="Vigilance & Rappels - PHARMACIEL", layout="wide")

# --- STYLE PREMIUM ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    * { font-family: 'Outfit', sans-serif; }
    
    .header-box {
        background: linear-gradient(135deg, #7f1d1d 0%, #b91c1c 100%);
        padding: 30px; border-radius: 20px; color: white;
        margin-bottom: 25px; box-shadow: 0 10px 30px rgba(185, 28, 28, 0.2);
    }
    .kpi-card {
        background: white; border-radius: 15px; padding: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border: 1px solid #f1f5f9; text-align: center;
    }
    .kpi-num { font-size: 1.8rem; font-weight: 800; color: #7f1d1d; margin-top: 5px; }
    .kpi-lbl { font-size: 0.75rem; color: #94a3b8; font-weight: 700; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-box">
    <h1 style="margin:0; font-size:2.2rem; font-weight:800;">🛡️ Pharmacovigilance & Rappels de Lots</h1>
    <p style="margin:5px 0 0; opacity:0.85; font-size:1rem;">Traçabilité réglementaire : Recherche croisée instantanée des officines ayant acheté un lot retiré, alertes automatiques et suivi de récupération du stock.</p>
</div>
""", unsafe_allow_html=True)

# --- KPIs ---
c1, c2, c3 = st.columns(3)
total_alertes = len(df_rappels)
rappels_actifs = len(df_rappels[df_rappels["Statut"] == "Actif"]) if total_alertes > 0 else 0
taux_moyen = 0.0
if total_alertes > 0:
    df_rappels["Taux_Recup"] = pd.to_numeric(df_rappels["Taux_Recup"], errors="coerce").fillna(0.0)
    taux_moyen = df_rappels["Taux_Recup"].mean()

c1.markdown(f'<div class="kpi-card"><div class="kpi-lbl">Total Rappels Déclenchés</div><div class="kpi-num">{total_alertes}</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="kpi-card"><div class="kpi-lbl">Rappels Actifs</div><div class="kpi-num" style="color:#b91c1c;">{rappels_actifs}</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="kpi-card"><div class="kpi-lbl">Taux de Récupération Moyen</div><div class="kpi-num" style="color:#059669;">{taux_moyen:.1f} %</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

tabs = st.tabs(["⚠️ Déclencher une alerte", "📋 Suivi des alertes en cours", "📜 Rapports Réglementaires"])

# --- GENERATION CLIENTS IMPACTES (Mock déterministe par Lot) ---
def get_impacted_clients(lot_number):
    if not lot_number:
        return []
    # Seed hashing pour avoir un comportement déterministe par numéro de lot
    h = int(hashlib.md5(lot_number.encode('utf-8')).hexdigest(), 16)
    np.random.seed(h % (2**32))
    
    num_clients = np.random.randint(3, 8)
    selected_indices = np.random.choice(len(liste_clients), size=min(num_clients, len(liste_clients)), replace=False)
    
    impacted = []
    for idx in selected_indices:
        cli = liste_clients[idx]
        qte = np.random.randint(10, 150)
        impacted.append({
            "Client": cli.get("Nom Client", "Pharmacie"),
            "Région": cli.get("Région", "Centre"),
            "Téléphone": cli.get("Téléphone", "-"),
            "Quantite_Livree": qte,
            "Statut_Recup": "Contacté (En attente)"
        })
    return impacted

# --- TAB 1 : DECLENCHER ALERTE ---
with tabs[0]:
    st.subheader("🚨 Déclarer un rappel de lot officiel")
    with st.form("form_rappel"):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            produit = st.selectbox("Produit concerné", options=liste_prods)
            lot = st.text_input("Numéro de Lot (Batch Number)", placeholder="Ex: LOT-2026-X8").upper()
        with col_f2:
            motif = st.selectbox("Raison du rappel / retrait", [
                "Impureté / Non-conformité chimique",
                "Défaut d'étanchéité du conditionnement",
                "Erreur d'étiquetage / Notice manquante",
                "Suspension temporaire de l'AMM par le Ministère",
                "Autre alerte de pharmacovigilance"
            ])
            date_alerte = st.date_input("Date de l'alerte")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.form_submit_button("⚠️ Lancer la recherche croisée et déclencher le rappel", use_container_width=True):
            if lot:
                nouveau_r = {
                    "Date_Rappel": date_alerte.strftime("%Y-%m-%d"),
                    "Produit": produit,
                    "Lot": lot,
                    "Motif": motif,
                    "Statut": "Actif",
                    "Taux_Recup": 0.0,
                    "Agent": st.session_state.current_user["username"] if st.session_state.get("current_user") else "System"
                }
                df_rappels = pd.concat([df_rappels, pd.DataFrame([nouveau_r])], ignore_index=True)
                save_gs_data(df_rappels, WORKSHEET_NAME, FALLBACK_PATH)
                log_action(nouveau_r["Agent"], f"Rappel déclenché: Lot {lot} de {produit}", "Rappels_Vigilance")
                st.success(f"🔥 Rappel réglementaire enregistré pour le lot {lot} ! Passez à l'onglet 'Suivi des alertes' pour gérer le processus de récupération.")
                st.rerun()
            else:
                st.error("Veuillez entrer un numéro de lot valide.")

# --- TAB 2 : SUIVI DES ALERTES ---
with tabs[1]:
    st.subheader("📋 Rappels de lots actifs & Taux de retour")
    df_actifs = df_rappels[df_rappels["Statut"] == "Actif"].copy()
    
    if df_actifs.empty:
        st.info("Aucun rappel de lot actif actuellement.")
    else:
        for idx, row in df_actifs.iterrows():
            with st.expander(f"🔴 LOT: {row['Lot']} — {row['Produit']} (Déclenché le {row['Date_Rappel']})", expanded=True):
                st.write(f"**Motif :** {row['Motif']}")
                st.write(f"**Taux de récupération actuel :** **{row['Taux_Recup']:.1f} %**")
                
                # Charger les pharmacies impactées
                impacted = get_impacted_clients(row['Lot'])
                
                st.markdown("#### 🏥 Pharmacies ayant acheté ce lot :")
                
                # Pour simuler la modification du statut de récupération par pharmacie
                df_imp = pd.DataFrame(impacted)
                
                # Configuration des colonnes
                edited_df = st.data_editor(
                    df_imp,
                    key=f"editor_recup_{row['Lot']}_{idx}",
                    use_container_width=True,
                    column_config={
                        "Client": st.column_config.TextColumn("Officine client", disabled=True),
                        "Région": st.column_config.TextColumn("Secteur", disabled=True),
                        "Téléphone": st.column_config.TextColumn("Téléphone", disabled=True),
                        "Quantite_Livree": st.column_config.NumberColumn("Quantité Livrée", disabled=True),
                        "Statut_Recup": st.column_config.SelectboxColumn(
                            "Statut Récupération",
                            options=["Non contacté", "Contacté (En attente)", "Lot récupéré & sécurisé", "Aucun stock restant"]
                        )
                    },
                    hide_index=True
                )
                
                col_btn_u, col_btn_c = st.columns([1, 3])
                if col_btn_u.button("💾 Enregistrer la situation", key=f"save_recup_{idx}"):
                    # Calculer le taux de récupération
                    recupere = 0
                    total = 0
                    for _, r_imp in edited_df.iterrows():
                        total += r_imp["Quantite_Livree"]
                        if r_imp["Statut_Recup"] == "Lot récupéré & sécurisé":
                            recupere += r_imp["Quantite_Livree"]
                    
                    taux = (recupere / total) * 100.0 if total > 0 else 100.0
                    df_rappels.loc[idx, "Taux_Recup"] = taux
                    save_gs_data(df_rappels, WORKSHEET_NAME, FALLBACK_PATH)
                    log_action(
                        st.session_state.current_user["username"] if st.session_state.get("current_user") else "System",
                        f"Mise à jour rappel Lot {row['Lot']} : Taux de retour {taux:.1f}%",
                        "Rappels_Vigilance"
                    )
                    st.success(f"Situation mise à jour ! Taux de retour : {taux:.1f}%")
                    st.rerun()
                    
                if col_btn_c.button("🟢 Clôturer le Rappel (Lot 100% Sécurisé)", key=f"close_rec_{idx}", type="primary"):
                    df_rappels.loc[idx, "Statut"] = "Clôturé"
                    save_gs_data(df_rappels, WORKSHEET_NAME, FALLBACK_PATH)
                    log_action(
                        st.session_state.current_user["username"] if st.session_state.get("current_user") else "System",
                        f"Rappel Lot {row['Lot']} CLÔTURÉ",
                        "Rappels_Vigilance"
                    )
                    st.success(f"Rappel de lot {row['Lot']} clôturé avec succès !")
                    st.rerun()

# --- TAB 3 : RAPPORTS REGLEMENTAIRES ---
with tabs[2]:
    st.subheader("📜 Historique et Rapports d'Audit")
    st.dataframe(df_rappels.sort_values("Date_Rappel", ascending=False), use_container_width=True, hide_index=True)
