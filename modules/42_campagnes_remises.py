import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
from utils import log_action
from utils_gsheets import load_gs_data, save_gs_data

# --- CONFIGURATION ---
WORKSHEET_NAME = "Campagnes_Remises"
FALLBACK_PATH = "data/data_campagnes.csv"
COLUMNS = ["Nom_Campagne", "Produit", "Type_Offre", "Seuil_Min", "Avantage", "Date_Debut", "Date_Fin", "Statut"]

# Charger les produits existants
df_prods = load_gs_data("Base_Produits", "data_produits.csv", ["Désignation"])
liste_prods = sorted(df_prods["Désignation"].dropna().unique().tolist()) if not df_prods.empty else [
    "PARACETAMOL 1G SANOFI", "DOLIPRANE 1000", "AMOXYCILLINE 500MG", "SPASFON LYOC", "BETADINE DERMIQUE",
    "SERUM SALÉ 0.9%", "VICHY EAU THERMALE", "LAROCHE-POSAY ANTHELIOS"
]

# Charger ou initialiser les campagnes
df_campagnes = load_gs_data(WORKSHEET_NAME, FALLBACK_PATH, COLUMNS)

# Initialiser avec des exemples si vide
if df_campagnes.empty:
    default_campagnes = [
        {
            "Nom_Campagne": "OFFRE GROUPAGE DOLIPRANE",
            "Produit": "DOLIPRANE 1000",
            "Type_Offre": "Gratuité (X+Y Offerts)",
            "Seuil_Min": 10,
            "Avantage": "10+2 gratuits",
            "Date_Debut": "2026-07-01",
            "Date_Fin": "2026-08-31",
            "Statut": "Active"
        },
        {
            "Nom_Campagne": "PROMO PARAPHARMACIE VICHY",
            "Produit": "VICHY EAU THERMALE",
            "Type_Offre": "Remise en pourcentage (%)",
            "Seuil_Min": 5,
            "Avantage": "15.0",
            "Date_Debut": "2026-07-05",
            "Date_Fin": "2026-07-20",
            "Statut": "Active"
        }
    ]
    df_campagnes = pd.DataFrame(default_campagnes)
    save_gs_data(df_campagnes, WORKSHEET_NAME, FALLBACK_PATH)

st.set_page_config(page_title="Offres & Remises - PHARMACIEL", layout="wide")

# --- STYLE PREMIUM ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');
    * { font-family: 'Outfit', sans-serif; }
    
    .header-box {
        background: linear-gradient(135deg, #0f766e 0%, #115e59 100%);
        padding: 30px; border-radius: 20px; color: white;
        margin-bottom: 25px; box-shadow: 0 10px 30px rgba(17, 94, 89, 0.2);
    }
    .kpi-card {
        background: white; border-radius: 15px; padding: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        border: 1px solid #f1f5f9; text-align: center;
    }
    .kpi-num { font-size: 1.8rem; font-weight: 800; color: #0f766e; margin-top: 5px; }
    .kpi-lbl { font-size: 0.75rem; color: #94a3b8; font-weight: 700; text-transform: uppercase; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="header-box">
    <h1 style="margin:0; font-size:2.2rem; font-weight:800;">🏷️ Gestion des Offres Commerciales & Remises</h1>
    <p style="margin:5px 0 0; opacity:0.85; font-size:1rem;">Outil commercial : Configuration des conditions d'achat avantageuses pour les officines, offres de gratuité (10+2) et remises par paliers.</p>
</div>
""", unsafe_allow_html=True)

# --- KPIs ---
c1, c2, c3 = st.columns(3)
total_campagnes = len(df_campagnes)
actives = len(df_campagnes[df_campagnes["Statut"] == "Active"])
produits_promus = df_campagnes[df_campagnes["Statut"] == "Active"]["Produit"].nunique()

c1.markdown(f'<div class="kpi-card"><div class="kpi-lbl">Total Offres Créées</div><div class="kpi-num">{total_campagnes}</div></div>', unsafe_allow_html=True)
c2.markdown(f'<div class="kpi-card"><div class="kpi-lbl">Offres Actives</div><div class="kpi-num" style="color:#0f766e;">{actives}</div></div>', unsafe_allow_html=True)
c3.markdown(f'<div class="kpi-card"><div class="kpi-lbl">Produits en Promotion</div><div class="kpi-num" style="color:#0ea5e9;">{produits_promus}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

tabs = st.tabs(["📋 Campagnes Actives", "➕ Créer une offre", "🧮 Simulateur de Facturation"])

# --- TAB 1 : LISTE DES CAMPAGNES ---
with tabs[0]:
    st.subheader("📋 Liste des campagnes promotionnelles en cours")
    if df_campagnes.empty:
        st.info("Aucune campagne configurée pour le moment.")
    else:
        for idx, row in df_campagnes.iterrows():
            stat_color = "🟢" if row["Statut"] == "Active" else "🔴"
            with st.expander(f"{stat_color} {row['Nom_Campagne']} — {row['Produit']}", expanded=True):
                col_i, col_a = st.columns(2)
                with col_i:
                    st.write(f"**Produit :** {row['Produit']}")
                    st.write(f"**Type d'avantage :** {row['Type_Offre']}")
                    st.write(f"**Condition / Seuil Minimum :** A partir de {row['Seuil_Min']} unités")
                with col_a:
                    st.write(f"**Avantage accordé :** {row['Avantage']}")
                    st.write(f"**Période :** Du {row['Date_Debut']} au {row['Date_Fin']}")
                    
                    if row["Statut"] == "Active":
                        if st.button("Désactiver l'offre", key=f"deact_{idx}"):
                            df_campagnes.loc[idx, "Statut"] = "Désactivée"
                            save_gs_data(df_campagnes, WORKSHEET_NAME, FALLBACK_PATH)
                            log_action(
                                st.session_state.current_user["username"] if st.session_state.get("current_user") else "System",
                                f"Désactivation offre: {row['Nom_Campagne']}",
                                "Campagnes_Remises"
                            )
                            st.success("Offre désactivée.")
                            st.rerun()
                    else:
                        if st.button("Réactiver l'offre", key=f"react_{idx}"):
                            df_campagnes.loc[idx, "Statut"] = "Active"
                            save_gs_data(df_campagnes, WORKSHEET_NAME, FALLBACK_PATH)
                            log_action(
                                st.session_state.current_user["username"] if st.session_state.get("current_user") else "System",
                                f"Réactivation offre: {row['Nom_Campagne']}",
                                "Campagnes_Remises"
                            )
                            st.success("Offre réactivée.")
                            st.rerun()

# --- TAB 2 : CREER UNE OFFRE ---
with tabs[1]:
    st.subheader("➕ Configurer une nouvelle promotion")
    with st.form("form_nouvelle_promo"):
        nom_c = st.text_input("Nom de la Campagne", placeholder="Ex: OFFRE EXCLUSIVE PARACETAMOL")
        prod = st.selectbox("Produit visé", options=liste_prods)
        
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            type_offre = st.selectbox("Type d'offre / Avantage", [
                "Gratuité (X+Y Offerts)",
                "Remise en pourcentage (%)",
                "Remise fixe (DZD par unité)"
            ])
            seuil = st.number_input("Seuil minimum de commande (unités)", min_value=1, value=10)
            
        with col_c2:
            avantage_val = st.text_input("Avantage (Ex: '10+2 gratuits' ou '15.0' pour 15% ou '50' pour 50 DA)")
            date_d = st.date_input("Date de début de l'offre")
            date_f = st.date_input("Date de fin de l'offre")
            
        st.markdown("<br>", unsafe_allow_html=True)
        if st.form_submit_button("🚀 Enregistrer et publier la campagne", use_container_width=True):
            if nom_c and avantage_val:
                nouvelle_camp = {
                    "Nom_Campagne": nom_c.upper(),
                    "Produit": prod,
                    "Type_Offre": type_offre,
                    "Seuil_Min": seuil,
                    "Avantage": avantage_val,
                    "Date_Debut": date_d.strftime("%Y-%m-%d"),
                    "Date_Fin": date_f.strftime("%Y-%m-%d"),
                    "Statut": "Active"
                }
                df_campagnes = pd.concat([df_campagnes, pd.DataFrame([nouvelle_camp])], ignore_index=True)
                save_gs_data(df_campagnes, WORKSHEET_NAME, FALLBACK_PATH)
                log_action(
                    st.session_state.current_user["username"] if st.session_state.get("current_user") else "System",
                    f"Nouvelle offre publiée: {nom_c} sur {prod}",
                    "Campagnes_Remises"
                )
                st.success("✅ Campagne promotionnelle publiée avec succès !")
                st.rerun()
            else:
                st.error("Veuillez remplir tous les champs.")

# --- TAB 3 : SIMULATEUR DE FACTURATION ---
with tabs[2]:
    st.subheader("🧮 Simulateur de tarifs et gratuités pour officine")
    
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        prod_sel = st.selectbox("Produit sélectionné par la pharmacie", options=liste_prods, key="sim_prod")
        qte_sel = st.number_input("Quantité d'achat envisagée", min_value=1, value=12, key="sim_qte")
        prix_public = st.number_input("Prix Brut de gros Unitaire (DZD)", min_value=10.0, value=250.0, key="sim_prix")
        
    with col_s2:
        st.markdown("#### ⚡ Offre active trouvée :")
        # Rechercher une offre active pour ce produit
        offre = df_campagnes[(df_campagnes["Produit"] == prod_sel) & (df_campagnes["Statut"] == "Active")]
        
        if offre.empty:
            st.info("Aucune offre active pour ce produit. Tarif de gros standard appliqué.")
            remise_pct = 0.0
            gratuit = 0
            prix_final_u = prix_public
            total_net = qte_sel * prix_public
        else:
            row_o = offre.iloc[0]
            st.success(f"**Campagne active :** {row_o['Nom_Campagne']}")
            st.write(f"**Avantage :** {row_o['Avantage']}")
            st.write(f"**Condition :** Minimum {row_o['Seuil_Min']} boîtes.")
            
            remise_pct = 0.0
            gratuit = 0
            remise_fixe = 0.0
            
            if qte_sel >= row_o["Seuil_Min"]:
                st.markdown("<span style='color:#059669; font-weight:800;'>✅ SEUIL MINIMUM ATTEINT ! L'offre s'applique.</span>", unsafe_allow_html=True)
                
                if row_o["Type_Offre"] == "Gratuité (X+Y Offerts)":
                    # Ex: "10+2 gratuits" -> On calcule le nombre de gratuits
                    # Si c'est 10+2, pour qte_sel on divise par 10 et multiplie par 2
                    try:
                        import re
                        match = re.search(r"(\d+)\+(\d+)", str(row_o["Avantage"]))
                        if match:
                            base_achat = int(match.group(1))
                            bonus = int(match.group(2))
                            multiplicateurs = qte_sel // base_achat
                            gratuit = multiplicateurs * bonus
                    except:
                        gratuit = 0
                elif row_o["Type_Offre"] == "Remise en pourcentage (%)":
                    try:
                        remise_pct = float(row_o["Avantage"])
                    except:
                        remise_pct = 0.0
                elif row_o["Type_Offre"] == "Remise fixe (DZD par unité)":
                    try:
                        remise_fixe = float(row_o["Avantage"])
                    except:
                        remise_fixe = 0.0
            else:
                st.warning(f"⚠️ Seuil minimum non atteint ({qte_sel} commandés / {row_o['Seuil_Min']} requis).")
                
            prix_final_u = prix_public * (1 - (remise_pct / 100.0)) - remise_fixe
            total_net = qte_sel * prix_final_u

        st.divider()
        st.write("#### 🧾 Détails du calcul :")
        st.write(f"Montant Brut : **{qte_sel * prix_public:,.2f} DA**")
        if remise_pct > 0:
            st.write(f"Remise ({remise_pct}%) : **-{(qte_sel * prix_public * remise_pct / 100.0):,.2f} DA**")
        if gratuit > 0:
            st.write(f"Boîtes offertes gratuitement : **+{gratuit} boîtes**")
        st.markdown(f"### Montant Net à Facturer : <span style='color:#0f766e;'>{total_net:,.2f} DA</span>", unsafe_allow_html=True)
