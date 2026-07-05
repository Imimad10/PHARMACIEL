import streamlit as st
import pandas as pd
from datetime import datetime
import os
import plotly.express as px
from utils import log_action
from utils_gsheets import load_gs_data, save_gs_data

# --- CONFIGURATION ---
WORKSHEET_NAME = "Retours_Avoirs"
FALLBACK_PATH = "data/data_retours.csv"
COLUMNS = ["Date", "Client", "Produit", "Quantite", "Motif", "Etat_Boite", "Action_Stock", "Valeur_Avoir", "Statut", "N_Avoir", "Agent"]

# Charger les clients existants pour le selectbox
df_clients = load_gs_data("Clients", "base_clients.csv", ["Nom Client", "Région"])
liste_clients = sorted(df_clients["Nom Client"].dropna().unique().tolist()) if not df_clients.empty else []

# Charger les produits existants
df_prods = load_gs_data("Base_Produits", "data_produits.csv", ["Désignation"])
liste_prods = sorted(df_prods["Désignation"].dropna().unique().tolist()) if not df_prods.empty else [
    "PARACETAMOL 1G SANOFI", "DOLIPRANE 1000", "AMOXYCILLINE 500MG", "SPASFON LYOC", "BETADINE DERMIQUE",
    "SERUM SALÉ 0.9%", "VICHY EAU THERMALE", "LAROCHE-POSAY ANTHELIOS"
]

# Charger les retours
df_retours = load_gs_data(WORKSHEET_NAME, FALLBACK_PATH, COLUMNS)

st.set_page_config(page_title="Retours & Avoirs - PHARMACIEL", layout="wide")

# --- CSS PREMIUM & ANIMATIONS ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    * { font-family: 'Outfit', sans-serif; }
    
    .header-box {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        padding: 30px; border-radius: 20px; color: white;
        margin-bottom: 25px; box-shadow: 0 10px 30px rgba(0,0,0,0.15);
    }
    .kpi-card {
        background: white; border-radius: 15px; padding: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border: 1px solid #f1f5f9; text-align: center;
        transition: all 0.3s ease;
    }
    .kpi-card:hover {
        transform: translateY(-4px); box-shadow: 0 8px 25px rgba(0,0,0,0.1);
    }
    .kpi-num { font-size: 1.8rem; font-weight: 800; color: #1e293b; margin-top: 5px; }
    .kpi-lbl { font-size: 0.75rem; color: #94a3b8; font-weight: 700; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-box">
    <h1 style="margin:0; font-size:2.2rem; font-weight:800;">🔄 Retours & Avoirs Clients</h1>
    <p style="margin:5px 0 0; opacity:0.75; font-size:1rem;">Gestion de la chaîne inverse : Déclaration de retours, inspection qualitative et émission de bons d'avoirs officines.</p>
</div>
""", unsafe_allow_html=True)

# --- STATISTIQUES GLOBALES ---
col1, col2, col3, col4 = st.columns(4)
total_retours = len(df_retours)
en_attente = len(df_retours[df_retours["Statut"] == "En attente"]) if total_retours > 0 else 0
avoirs_emis = len(df_retours[df_retours["Statut"] == "Validé (Avoir Émis)"]) if total_retours > 0 else 0
total_val_avoirs = 0.0
if total_retours > 0:
    df_retours["Valeur_Avoir"] = pd.to_numeric(df_retours["Valeur_Avoir"], errors="coerce").fillna(0.0)
    total_val_avoirs = df_retours[df_retours["Statut"] == "Validé (Avoir Émis)"]["Valeur_Avoir"].sum()

col1.markdown(f'<div class="kpi-card"><div class="kpi-lbl">Total Demandes</div><div class="kpi-num">{total_retours}</div></div>', unsafe_allow_html=True)
col2.markdown(f'<div class="kpi-card"><div class="kpi-lbl">En Attente Inspection</div><div class="kpi-num" style="color:#d97706;">{en_attente}</div></div>', unsafe_allow_html=True)
col3.markdown(f'<div class="kpi-card"><div class="kpi-lbl">Avoirs Émis</div><div class="kpi-num" style="color:#059669;">{avoirs_emis}</div></div>', unsafe_allow_html=True)
col4.markdown(f'<div class="kpi-card"><div class="kpi-lbl">Montant Avoirs Émis</div><div class="kpi-num" style="color:#2563eb;">{total_val_avoirs:,.2f} DA</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

tabs = st.tabs(["➕ Déclarer un retour", "🔍 Inspection & Validation", "📋 Historique & Suivi", "📊 Analyses"])

# --- TAB 1 : DÉCLARER UN RETOUR ---
with tabs[0]:
    st.subheader("📝 Formulaire de déclaration de retour client")
    with st.form("form_nouveau_retour", clear_on_submit=True):
        c1, c2 = st.columns(2)
        
        with c1:
            client = st.selectbox("Sélectionner la Pharmacie Client", options=liste_clients if liste_clients else ["Pharmacie Centrale", "Pharmacie Pasteur"])
            produit = st.selectbox("Produit concerné", options=liste_prods)
            quantite = st.number_input("Quantité retournée", min_value=1, step=1)
            
        with c2:
            motif = st.selectbox("Motif principal du retour", [
                "Péremption / Date courte", 
                "Boite Endommagée", 
                "Erreur de commande / livraison", 
                "Rappel de lot réglementaire", 
                "Autre"
            ])
            valeur_initiale = st.number_input("Prix unitaire d'achat (Estimation DZD)", min_value=0.0, step=10.0, value=100.0)
            etat_boite = st.selectbox("État visuel de la boîte", ["Scellée / Intacte", "Abîmée mais utilisable", "Inutilisable / Déchirée"])

        st.markdown("<br>", unsafe_allow_html=True)
        if st.form_submit_button("🚀 Déclarer le retour", use_container_width=True):
            valeur_totale_est = quantite * valeur_initiale
            nouveau_retour = {
                "Date": datetime.now().strftime("%Y-%m-%d"),
                "Client": client,
                "Produit": produit,
                "Quantite": quantite,
                "Motif": motif,
                "Etat_Boite": etat_boite,
                "Action_Stock": "En attente",
                "Valeur_Avoir": valeur_totale_est,
                "Statut": "En attente",
                "N_Avoir": "Non généré",
                "Agent": st.session_state.current_user["username"] if st.session_state.get("current_user") else "System"
            }
            
            df_retours = pd.concat([df_retours, pd.DataFrame([nouveau_retour])], ignore_index=True)
            save_gs_data(df_retours, WORKSHEET_NAME, FALLBACK_PATH)
            
            log_action(nouveau_retour["Agent"], f"Retour déclaré: {client} - {produit} (x{quantite})", "Retours_Avoirs")
            st.success("✅ Retour client déclaré avec succès ! Prêt pour inspection qualitative.")
            st.rerun()

# --- TAB 2 : INSPECTION & VALIDATION ---
with tabs[1]:
    st.subheader("🔍 Contrôle Qualité & Décision Avoir")
    df_attente = df_retours[df_retours["Statut"] == "En attente"].copy()
    
    if df_attente.empty:
        st.info("Aucun retour en attente d'inspection qualitative.")
    else:
        st.write(f"Il y a **{len(df_attente)}** retours en attente d'inspection.")
        
        for idx, row in df_attente.iterrows():
            with st.expander(f"📦 {row['Client']} — {row['Produit']} (x{row['Quantite']}) - {row['Motif']}", expanded=False):
                col_i, col_d = st.columns([1, 1])
                
                with col_i:
                    st.write(f"**Date déclaration :** {row['Date']}")
                    st.write(f"**État initial déclaré :** {row['Etat_Boite']}")
                    st.write(f"**Valeur estimée initiale :** {row['Valeur_Avoir']} DA")
                    st.write(f"**Déclaré par :** {row['Agent']}")
                    
                with col_d:
                    action_stock = st.radio("Décision Stock pour cet article :", [
                        "Réintégration dans le stock (Parapharmacie / Produit scellé)",
                        "Transfert en quarantaine / Destruction (Médicament périmé / abîmé)"
                    ], key=f"act_stk_{idx}")
                    
                    pourcentage_avoir = st.slider("Pourcentage de l'avoir accordé (%)", min_value=0, max_value=100, value=80, key=f"pct_av_{idx}")
                    val_calc = (float(row['Valeur_Avoir']) * pourcentage_avoir) / 100.0
                    st.info(f"Montant final de l'avoir calculé : **{val_calc:,.2f} DA**")
                    
                    decision = st.selectbox("Action Finale", ["Valider et Émettre l'avoir", "Refuser le retour"], key=f"dec_{idx}")
                    
                    if st.button("Confirmer la décision", type="primary", key=f"btn_conf_{idx}"):
                        if decision == "Valider et Émettre l'avoir":
                            n_avoir = f"AV-{datetime.now().strftime('%Y%m%d')}-{idx:03d}"
                            df_retours.loc[idx, "Action_Stock"] = "Réintégré" if "Réintégration" in action_stock else "Mis en destruction"
                            df_retours.loc[idx, "Valeur_Avoir"] = val_calc
                            df_retours.loc[idx, "Statut"] = "Validé (Avoir Émis)"
                            df_retours.loc[idx, "N_Avoir"] = n_avoir
                            st.success(f"Avoir {n_avoir} validé !")
                        else:
                            df_retours.loc[idx, "Action_Stock"] = "Renvoyé au client"
                            df_retours.loc[idx, "Valeur_Avoir"] = 0.0
                            df_retours.loc[idx, "Statut"] = "Refusé"
                            df_retours.loc[idx, "N_Avoir"] = "Refusé"
                            st.warning("Retour refusé.")
                            
                        save_gs_data(df_retours, WORKSHEET_NAME, FALLBACK_PATH)
                        log_action(
                            st.session_state.current_user["username"] if st.session_state.get("current_user") else "System",
                            f"Décision Retour {row['Client']}: {decision} - Avoir {df_retours.loc[idx, 'N_Avoir']}",
                            "Retours_Avoirs"
                        )
                        st.rerun()

# --- TAB 3 : HISTORIQUE & SUIVI ---
with tabs[2]:
    st.subheader("📋 Historique complet des retours et avoirs")
    
    col_fil1, col_fil2 = st.columns(2)
    with col_fil1:
        f_client = st.text_input("Filtrer par Client").lower()
    with col_fil2:
        f_statut = st.selectbox("Filtrer par Statut", ["Tous", "En attente", "Validé (Avoir Émis)", "Refusé"])
        
    df_filt = df_retours.copy()
    if f_client:
        df_filt = df_filt[df_filt["Client"].str.lower().str.contains(f_client)]
    if f_statut != "Tous":
        df_filt = df_filt[df_filt["Statut"] == f_statut]
        
    st.dataframe(df_filt.sort_index(ascending=False), use_container_width=True, hide_index=True)

# --- TAB 4 : ANALYSES ---
with tabs[3]:
    st.subheader("📊 Analyses statistiques des retours")
    if df_retours.empty:
        st.info("Aucune donnée disponible pour les graphiques.")
    else:
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.markdown("### Répartition des motifs de retour")
            df_motifs = df_retours["Motif"].value_counts().reset_index()
            fig_motif = px.pie(df_motifs, values="count", names="Motif", hole=0.3,
                               color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_motif, use_container_width=True)
            
        with col_g2:
            st.markdown("### Top 5 Clients par volume de retour")
            df_top_c = df_retours["Client"].value_counts().head(5).reset_index()
            fig_client = px.bar(df_top_c, x="Client", y="count", labels={"count": "Nombre de retours"},
                                color="Client", color_discrete_sequence=px.colors.qualitative.Safe)
            st.plotly_chart(fig_client, use_container_width=True)
