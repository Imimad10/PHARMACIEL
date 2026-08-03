import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta, date
import uuid

try:
    from utils import log_action
except ImportError:
    def log_action(*args, **kwargs):
        """Fallback silencieux si log_action n'existe pas dans utils.py de ce projet."""
        pass

import sys
import importlib

# Resolve Streamlit Cloud module caching issues
import utils_gsheets
import utils_pdf
import utils_excel

if not hasattr(utils_pdf, 'generate_cheques_report_pdf'):
    importlib.reload(utils_pdf)
if not hasattr(utils_excel, 'generate_cheques_excel'):
    importlib.reload(utils_excel)

from utils_gsheets import load_gs_data, save_gs_data
from utils_pdf import generate_cheques_report_pdf
from utils_excel import generate_cheques_excel

# --- CONFIGURATION GOOGLE SHEETS ---
WORKSHEET_CHEQUES = "Suivi_Cheques"
FALLBACK_CHEQUES = "cheques_data.csv"
COLS_CHEQUES = ["N", "Chauffeur", "Client", "Montant", "N_Cheque", "Date_Sortie", "Date_Retour", "Statut"]

WORKSHEET_LIVREURS = "Livreurs"
FALLBACK_LIVREURS = "livreurs_data.csv"

WORKSHEET_CLIENTS = "Clients_Cheques"
FALLBACK_CLIENTS = "clients_cheques_data.csv"

COLS_PERSONNE = ["ID", "Nom", "Prenom", "Tel"]

STATUTS = ["En attente", "Réglé", "Refusée"]
STATUT_COLORS = {
    "Réglé": "#10b981",
    "En attente": "#f59e0b",
    "Refusée": "#ef4444",
}
STATUT_BG = {
    "Réglé": "#d1fae5",
    "En attente": "#fef3c7",
    "Refusée": "#fee2e2",
}
STATUT_ICON = {
    "Réglé": "✅",
    "En attente": "⏳",
    "Refusée": "❌",
}

if "tz_offset" not in st.session_state:
    st.session_state.tz_offset = 1

if "current_user" not in st.session_state or st.session_state.current_user is None:
    st.warning("Veuillez vous connecter depuis la page principale.")
    st.stop()

def get_now():
    return datetime.utcnow() + timedelta(hours=st.session_state.tz_offset)

# --- STYLING PREMIUM (cohérent avec le reste de l'application) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');

    .kpi-tile {
        background: white;
        padding: 22px 16px;
        border-radius: 20px;
        text-align: center;
        border: 1px solid #e2e8f0;
        transition: transform 0.3s ease;
        box-shadow: 0 6px 18px rgba(0,0,0,0.03);
    }
    .kpi-tile:hover {
        transform: translateY(-5px);
        border-color: #5b6cf9;
    }
    .kpi-value {
        font-family: 'Outfit', sans-serif;
        font-size: 1.7rem;
        font-weight: 800;
        color: #1e293b;
    }
    .kpi-label {
        font-size: 0.75rem;
        color: #64748b;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    .statut-pill {
        display: inline-block;
        padding: 5px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.78rem;
        color: white;
        white-space: nowrap;
    }

    .cheque-card {
        background: white;
        border-radius: 16px;
        padding: 16px 20px;
        margin-bottom: 10px;
        border-left: 6px solid #94a3b8;
        box-shadow: 0 4px 14px rgba(0,0,0,0.04);
        display: flex;
        justify-content: space-between;
        align-items: center;
        flex-wrap: wrap;
        gap: 10px;
        transition: all 0.25s ease;
    }
    .cheque-card:hover {
        box-shadow: 0 8px 22px rgba(0,0,0,0.08);
        transform: translateX(2px);
    }
    .cheque-main {
        display: flex;
        flex-direction: column;
        gap: 2px;
    }
    .cheque-num {
        font-family: 'Outfit', sans-serif;
        font-weight: 800;
        color: #364fc7;
        font-size: 1.05rem;
    }
    .cheque-sub {
        color: #64748b;
        font-size: 0.82rem;
    }
    .cheque-montant {
        font-family: 'Outfit', sans-serif;
        font-weight: 800;
        font-size: 1.3rem;
        color: #1e293b;
    }

    .form-panel {
        background: linear-gradient(160deg, #f8f9ff 0%, #eef1ff 100%);
        border: 2px solid #dfe4ff;
        border-radius: 24px;
        padding: 26px;
    }
    .form-panel h4 {
        color: #364fc7;
        margin-top: 0;
        font-family: 'Outfit', sans-serif;
    }

    .person-card {
        background: white;
        border-radius: 16px;
        padding: 14px 18px;
        margin-bottom: 8px;
        border: 1px solid #e2e8f0;
        display: flex;
        justify-content: space-between;
        align-items: center;
        transition: all 0.2s ease;
    }
    .person-card:hover {
        border-color: #5b6cf9;
        box-shadow: 0 6px 16px rgba(91,108,249,0.1);
    }
    .person-name {
        font-weight: 700;
        color: #1e293b;
        font-family: 'Outfit', sans-serif;
        font-size: 1.05rem;
    }
    .person-tel {
        color: #64748b;
        font-size: 0.85rem;
    }

    .mode-toggle .stButton>button {
        border-radius: 14px;
        font-weight: 700;
        padding: 10px 0;
        width: 100%;
    }

    .alert-banner {
        background: linear-gradient(135deg, #fef2f2 0%, #fee2e2 100%);
        border: 1px solid #fecaca;
        border-left: 6px solid #ef4444;
        border-radius: 16px;
        padding: 16px 22px;
        margin-bottom: 18px;
    }
    .alert-title {
        color: #b91c1c;
        font-weight: 800;
        font-family: 'Outfit', sans-serif;
        font-size: 1rem;
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 6px;
    }
    .alert-dot {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: #ef4444;
        animation: pulse-red 1.6s infinite;
    }
    @keyframes pulse-red {
        0% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.6); }
        70% { box-shadow: 0 0 0 9px rgba(239, 68, 68, 0); }
        100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
    }
    .alert-item {
        color: #7f1d1d;
        font-size: 0.85rem;
        padding: 2px 0;
    }
</style>
""", unsafe_allow_html=True)


# =========================================================
# --- FONCTIONS DE DONNEES ---
# =========================================================
def get_cheques():
    df = load_gs_data(WORKSHEET_CHEQUES, FALLBACK_CHEQUES, COLS_CHEQUES)
    if not df.empty:
        df["Montant"] = pd.to_numeric(df["Montant"], errors="coerce").fillna(0)
        if "N" in df.columns:
            df["N"] = pd.to_numeric(df["N"], errors="coerce")
    return df

def save_cheques(df):
    save_gs_data(df, WORKSHEET_CHEQUES, FALLBACK_CHEQUES)

def get_personnes(worksheet, fallback):
    df = load_gs_data(worksheet, fallback, COLS_PERSONNE)
    # Force text columns to object dtype to prevent dtype coercion errors on assignment
    for col in ["Nom", "Prenom", "Tel"]:
        if col in df.columns:
            df[col] = df[col].astype(object).fillna("")
    return ensure_unique_ids(df, worksheet, fallback)

def ensure_unique_ids(df, worksheet, fallback):
    """
    Garantit que la colonne 'ID' existe et contient des valeurs uniques et non vides.
    Répare et sauvegarde automatiquement les données existantes si besoin
    (ex : lignes ajoutées manuellement dans Google Sheets sans ID).
    """
    if df.empty:
        return df

    if "ID" not in df.columns:
        df["ID"] = ""
    # Forcer le type "objet" (texte) : si la colonne était vide, pandas l'infère
    # parfois en float64, ce qui empêche d'y écrire des identifiants texte.
    df["ID"] = df["ID"].astype(object)

    seen = set()
    needs_save = False
    for idx in df.index:
        raw_id = df.at[idx, "ID"]
        current_id = "" if pd.isna(raw_id) else str(raw_id).strip()
        if not current_id or current_id in seen:
            current_id = str(uuid.uuid4())[:8]
            df.at[idx, "ID"] = current_id
            needs_save = True
        seen.add(current_id)

    if needs_save:
        save_personnes(df, worksheet, fallback)

    return df

def save_personnes(df, worksheet, fallback):
    save_gs_data(df, worksheet, fallback)

def personne_display_list(df):
    """Retourne une liste de libellés 'Nom Prenom' pour les menus déroulants."""
    if df.empty:
        return []
    return [f"{r['Nom']} {r['Prenom']}".strip() for _, r in df.iterrows()]

def get_overdue_cheques(df):
    """Chèques 'En attente' dont la date de retour prévue est dépassée."""
    if df.empty:
        return df
    d = df.copy()
    d["_date_retour_dt"] = pd.to_datetime(d["Date_Retour"], format="%d/%m/%Y", errors="coerce")
    today = pd.Timestamp(get_now().date())
    mask = (d["Statut"] == "En attente") & d["_date_retour_dt"].notna() & (d["_date_retour_dt"] < today)
    return d[mask].drop(columns=["_date_retour_dt"])


# =========================================================
# --- EN-TETE ---
# =========================================================
c_h1, c_h2 = st.columns([2.5, 1])
with c_h1:
    st.title("🧾 Suivi des Chèques")
    st.markdown(f"**Agent :** `{st.session_state.current_user['username']}` | {get_now().strftime('%d/%m/%Y %H:%M')}")
with c_h2:
    st.markdown("""
        <div style="background: rgba(16, 185, 129, 0.1); padding: 10px 20px; border-radius: 15px; border: 1px solid rgba(16, 185, 129, 0.2); text-align: right;">
            <span style="color: #065f46; font-weight: 700; font-size: 0.8rem;">GSheets Online</span>
        </div>
    """, unsafe_allow_html=True)

df_cheques = get_cheques()
df_livreurs = get_personnes(WORKSHEET_LIVREURS, FALLBACK_LIVREURS)
df_clients = get_personnes(WORKSHEET_CLIENTS, FALLBACK_CLIENTS)

tabs = st.tabs(["📊 Tableau de Bord", "🚚 Livreurs", "👥 Clients", "📈 Statistiques"])

# =========================================================
# --- TAB 1 : TABLEAU DE BORD ---
# =========================================================
with tabs[0]:
    # --- KPI ---
    if not df_cheques.empty:
        total_montant = df_cheques["Montant"].sum()
        montant_attente = df_cheques.loc[df_cheques["Statut"] == "En attente", "Montant"].sum()
        n_regle = len(df_cheques[df_cheques["Statut"] == "Réglé"])
        n_attente = len(df_cheques[df_cheques["Statut"] == "En attente"])
        n_refuse = len(df_cheques[df_cheques["Statut"] == "Refusée"])
    else:
        total_montant = montant_attente = 0
        n_regle = n_attente = n_refuse = 0

    k1, k2, k3, k4, k5 = st.columns(5)
    k1.markdown(f"""<div class="kpi-tile"><div class="kpi-label">Total Chèques</div><div class="kpi-value">{len(df_cheques)}</div></div>""", unsafe_allow_html=True)
    k2.markdown(f"""<div class="kpi-tile"><div class="kpi-label">Montant Total</div><div class="kpi-value">{total_montant:,.0f}</div></div>""", unsafe_allow_html=True)
    k3.markdown(f"""<div class="kpi-tile"><div class="kpi-label">Réglés</div><div class="kpi-value" style="color:#10b981;">{n_regle}</div></div>""", unsafe_allow_html=True)
    k4.markdown(f"""<div class="kpi-tile"><div class="kpi-label">En Attente</div><div class="kpi-value" style="color:#f59e0b;">{n_attente}</div></div>""", unsafe_allow_html=True)
    k5.markdown(f"""<div class="kpi-tile"><div class="kpi-label">Refusés</div><div class="kpi-value" style="color:#ef4444;">{n_refuse}</div></div>""", unsafe_allow_html=True)

    # --- ALERTE CHEQUES EN RETARD ---
    df_overdue = get_overdue_cheques(df_cheques)
    if not df_overdue.empty:
        items_html = "".join([
            f"<div class='alert-item'>• N°{int(r['N']) if pd.notna(r['N']) else '-'} — {r['Chauffeur']} / {r['Client']} — {r['Montant']:,.0f} DA — retour prévu le {r['Date_Retour']}</div>"
            for _, r in df_overdue.sort_values("Date_Retour").iterrows()
        ])
        st.markdown(f"""
            <div class="alert-banner">
                <div class="alert-title"><span class="alert-dot"></span>⚠️ {len(df_overdue)} chèque(s) en retard de retour</div>
                {items_html}
            </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_list, col_form = st.columns([2, 1])

    # --- LISTE / FILTRES (colonne gauche) ---
    with col_list:
        f1, f2, f3 = st.columns(3)
        filtre_statut = f1.selectbox("Filtrer par statut", ["Tous"] + STATUTS)
        filtre_chauffeur = f2.selectbox("Filtrer par chauffeur", ["Tous"] + sorted(df_cheques["Chauffeur"].dropna().unique().tolist()) if not df_cheques.empty else ["Tous"])
        filtre_client = f3.selectbox("Filtrer par client", ["Tous"] + sorted(df_cheques["Client"].dropna().unique().tolist()) if not df_cheques.empty else ["Tous"])

        df_view = df_cheques.copy()
        if not df_view.empty:
            if filtre_statut != "Tous":
                df_view = df_view[df_view["Statut"] == filtre_statut]
            if filtre_chauffeur != "Tous":
                df_view = df_view[df_view["Chauffeur"] == filtre_chauffeur]
            if filtre_client != "Tous":
                df_view = df_view[df_view["Client"] == filtre_client]

        exp1, exp2, _ = st.columns([1, 1, 2])
        subtitle_export = f"Export du {get_now().strftime('%d/%m/%Y %H:%M')}"
        with exp1:
            if not df_view.empty:
                pdf_bytes = generate_cheques_report_pdf(df_view, subtitle=subtitle_export)
                st.download_button(
                    "📄 Export PDF",
                    data=pdf_bytes,
                    file_name=f"Cheques_{get_now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            else:
                st.button("📄 Export PDF", disabled=True, use_container_width=True)
        with exp2:
            if not df_view.empty:
                xlsx_bytes = generate_cheques_excel(df_view, subtitle=subtitle_export)
                st.download_button(
                    "📊 Export Excel",
                    data=xlsx_bytes,
                    file_name=f"Cheques_{get_now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            else:
                st.button("📊 Export Excel", disabled=True, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if df_view.empty:
            st.info("Aucun chèque enregistré pour ces filtres.")
        else:
            for _, row in df_view.sort_values("N", ascending=False).iterrows():
                color = STATUT_COLORS.get(row["Statut"], "#94a3b8")
                bg = STATUT_BG.get(row["Statut"], "#f1f5f9")
                icon = STATUT_ICON.get(row["Statut"], "•")
                st.markdown(f"""
                    <div class="cheque-card" style="border-left-color: {color};">
                        <div class="cheque-main">
                            <div class="cheque-num">N° {int(row['N']) if pd.notna(row['N']) else '-'} — Chèque {row['N_Cheque']}</div>
                            <div class="cheque-sub">🚚 {row['Chauffeur']} → 👤 {row['Client']}</div>
                            <div class="cheque-sub">📅 Sortie : {row['Date_Sortie']}  |  Retour : {row['Date_Retour'] if row['Date_Retour'] else '—'}</div>
                        </div>
                        <div style="text-align:right;">
                            <div class="cheque-montant">{row['Montant']:,.0f} DA</div>
                            <span class="statut-pill" style="background:{color};">{icon} {row['Statut']}</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

    # --- FORMULAIRE D'AJOUT (colonne droite) ---
    with col_form:
        st.markdown('<div class="form-panel">', unsafe_allow_html=True)
        st.markdown("#### ➕ Nouveau Chèque")

        chauffeurs_list = personne_display_list(df_livreurs)
        clients_list = personne_display_list(df_clients)

        if not chauffeurs_list:
            st.warning("⚠️ Aucun livreur enregistré. Ajoutez-en un dans l'onglet **Livreurs**.")
        if not clients_list:
            st.warning("⚠️ Aucun client enregistré. Ajoutez-en un dans l'onglet **Clients**.")

        with st.form("new_cheque_form", clear_on_submit=True):
            sel_chauffeur = st.selectbox("Chauffeur", chauffeurs_list) if chauffeurs_list else st.text_input("Chauffeur (aucun livreur enregistré)")
            sel_client = st.selectbox("Client", clients_list) if clients_list else st.text_input("Client (aucun client enregistré)")
            montant = st.number_input("Montant (DA)", min_value=0.0, step=100.0)
            n_cheque = st.text_input("N° de chèque")
            date_sortie = st.date_input("Date de sortie", value=get_now().date())
            date_retour = st.date_input("Date de retour prévue", value=get_now().date())
            statut = st.selectbox("Statut", STATUTS, index=0)

            if st.form_submit_button("💾 Enregistrer le chèque", use_container_width=True):
                if not n_cheque.strip():
                    st.error("Veuillez saisir un numéro de chèque.")
                else:
                    next_n = int(df_cheques["N"].max()) + 1 if not df_cheques.empty and df_cheques["N"].notna().any() else 1
                    new_row = {
                        "N": next_n,
                        "Chauffeur": sel_chauffeur,
                        "Client": sel_client,
                        "Montant": montant,
                        "N_Cheque": n_cheque.strip(),
                        "Date_Sortie": date_sortie.strftime("%d/%m/%Y"),
                        "Date_Retour": date_retour.strftime("%d/%m/%Y"),
                        "Statut": statut,
                    }
                    df_updated = pd.concat([df_cheques, pd.DataFrame([new_row])], ignore_index=True)
                    save_cheques(df_updated)
                    log_action(st.session_state.current_user['username'], f"Chèque {n_cheque} ({montant} DA) - {sel_chauffeur}/{sel_client}", "Suivi Chèques")
                    st.toast(f"✅ Chèque N°{next_n} enregistré", icon="💾")
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # --- GESTION AVANCEE (admin) ---
    if st.session_state.current_user.get('role') == 'Admin':
        st.divider()
        with st.expander("🛠️ Gestion avancée (modifier le statut, supprimer un chèque)"):
            st.caption("Double-cliquez pour modifier une cellule. Cochez une ligne puis Suppr pour supprimer. N'oubliez pas de sauvegarder.")
            edited_cheques = st.data_editor(
                df_cheques,
                use_container_width=True,
                num_rows="dynamic",
                column_config={
                    "Statut": st.column_config.SelectboxColumn("Statut", options=STATUTS),
                },
                key="editor_cheques",
            )
            if st.button("💾 Sauvegarder les modifications (chèques)", use_container_width=True):
                save_cheques(edited_cheques)
                st.success("Données synchronisées !")
                st.rerun()


# =========================================================
# --- FONCTION GENERIQUE : GESTION D'UNE LISTE DE PERSONNES ---
# (utilisée pour l'onglet Livreurs et l'onglet Clients)
# =========================================================
def render_personnes_tab(worksheet, fallback, df, label_singulier, icon, show_sync=False):
    key_prefix = worksheet.lower()
    mode_key = f"mode_{key_prefix}"
    selected_key = f"selected_{key_prefix}"

    if mode_key not in st.session_state:
        st.session_state[mode_key] = "ajouter"
    if selected_key not in st.session_state:
        st.session_state[selected_key] = None

    col_list, col_panel = st.columns([1.4, 1])

    # --- LISTE (colonne gauche) ---
    with col_list:
        recherche = st.text_input(f"🔍 Rechercher un {label_singulier}", key=f"search_{key_prefix}")
        df_show = df.copy()
        if recherche and not df_show.empty:
            mask = (df_show["Nom"].str.contains(recherche, case=False, na=False) |
                    df_show["Prenom"].str.contains(recherche, case=False, na=False) |
                    df_show["Tel"].astype(str).str.contains(recherche, case=False, na=False))
            df_show = df_show[mask]

        st.markdown("<br>", unsafe_allow_html=True)

        if df_show.empty:
            st.info(f"Aucun {label_singulier} enregistré pour le moment.")
        else:
            for pos, (_, row) in enumerate(df_show.iterrows()):
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"""
                        <div class="person-card">
                            <div>
                                <div class="person-name">{icon} {row['Nom']} {row['Prenom']}</div>
                                <div class="person-tel">📞 {row['Tel']}</div>
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                with c2:
                    if st.button("✏️ Éditer", key=f"edit_{key_prefix}_{pos}_{row['ID']}", use_container_width=True):
                        st.session_state[mode_key] = "modifier"
                        st.session_state[selected_key] = row['ID']
                        st.rerun()

    # --- PANNEAU AJOUTER / MODIFIER (colonne droite, reprend la maquette) ---
    with col_panel:
        if show_sync:
            b1, b2, b3 = st.columns([1, 1, 1.2])
            with b1:
                if st.button("➕ Ajouter", key=f"btn_add_{key_prefix}", use_container_width=True, type="primary" if st.session_state[mode_key] == "ajouter" else "secondary"):
                    st.session_state[mode_key] = "ajouter"
                    st.session_state[selected_key] = None
                    st.rerun()
            with b2:
                if st.button("✏️ Mod/Sup", key=f"btn_edit_{key_prefix}", use_container_width=True, type="primary" if st.session_state[mode_key] == "modifier" else "secondary"):
                    st.session_state[mode_key] = "modifier"
                    st.rerun()
            with b3:
                if st.button("🔄 Sync Plat", key=f"btn_sync_{key_prefix}", use_container_width=True, help="Synchroniser depuis la base plate-forme"):
                    with st.spinner("Synchronisation des clients..."):
                        df_platform = load_gs_data("Base_Clients", "base_clients.csv")
                        if not df_platform.empty:
                            name_col = None
                            for c in ["Nom Client", "Nom_Client", "Nom_Pharmacie", "Nom"]:
                                if c in df_platform.columns:
                                    name_col = c
                                    break
                            tel_col = None
                            for c in ["Téléphone", "Telephone", "Tel", "tel"]:
                                if c in df_platform.columns:
                                    tel_col = c
                                    break
                            
                            if name_col:
                                existing_names = set()
                                for _, r in df.iterrows():
                                    full_name = f"{r.get('Nom', '')} {r.get('Prenom', '')}".strip().upper()
                                    existing_names.add(full_name)
                                
                                new_rows = []
                                for _, row in df_platform.iterrows():
                                    raw_name = row.get(name_col)
                                    if pd.isna(raw_name):
                                        continue
                                    plat_name = str(raw_name).strip()
                                    plat_tel = str(row.get(tel_col, "")).strip() if tel_col and not pd.isna(row.get(tel_col)) else ""
                                    
                                    if plat_name.upper() not in existing_names:
                                        new_rows.append({
                                            "ID": str(uuid.uuid4())[:8],
                                            "Nom": plat_name,
                                            "Prenom": "",
                                            "Tel": plat_tel
                                        })
                                        existing_names.add(plat_name.upper())
                                
                                if new_rows:
                                    df_updated = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
                                    save_personnes(df_updated, worksheet, fallback)
                                    log_action(st.session_state.current_user['username'], f"Synchro {len(new_rows)} clients depuis plateforme", "Suivi Chèques")
                                    st.toast(f"✅ {len(new_rows)} clients synchronisés avec succès !", icon="🔄")
                                    import time
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.toast("ℹ️ Tous les clients sont déjà synchronisés.", icon="ℹ️")
                            else:
                                st.error("Colonne de nom de client introuvable dans la base plateforme.")
                        else:
                            st.warning("La base plateforme des clients est vide.")
        else:
            b1, b2 = st.columns(2)
            with b1:
                if st.button("➕ Ajouter", key=f"btn_add_{key_prefix}", use_container_width=True, type="primary" if st.session_state[mode_key] == "ajouter" else "secondary"):
                    st.session_state[mode_key] = "ajouter"
                    st.session_state[selected_key] = None
                    st.rerun()
            with b2:
                if st.button("✏️ Modifier / Supprimer", key=f"btn_edit_{key_prefix}", use_container_width=True, type="primary" if st.session_state[mode_key] == "modifier" else "secondary"):
                    st.session_state[mode_key] = "modifier"
                    st.rerun()

        st.markdown('<div class="form-panel">', unsafe_allow_html=True)

        if st.session_state[mode_key] == "ajouter":
            st.markdown(f"#### ➕ Nouveau {label_singulier}")
            with st.form(f"form_add_{key_prefix}", clear_on_submit=True):
                nom = st.text_input("NOM")
                prenom = st.text_input("PRENOM")
                tel = st.text_input("TEL")
                if st.form_submit_button("Ajouter", use_container_width=True):
                    if not nom.strip():
                        st.error("Le nom est obligatoire.")
                    else:
                        new_row = {"ID": str(uuid.uuid4())[:8], "Nom": nom.strip(), "Prenom": prenom.strip(), "Tel": tel.strip()}
                        df_new = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                        save_personnes(df_new, worksheet, fallback)
                        log_action(st.session_state.current_user['username'], f"Ajout {label_singulier} : {nom} {prenom}", f"Gestion {label_singulier}s")
                        st.toast(f"✅ {label_singulier.capitalize()} ajouté", icon="💾")
                        st.rerun()

        else:  # mode "modifier"
            st.markdown(f"#### ✏️ Modifier / Supprimer un {label_singulier}")
            if df.empty:
                st.info(f"Aucun {label_singulier} à modifier.")
            else:
                options = df['ID'].tolist()
                labels = {r['ID']: f"{r['Nom']} {r['Prenom']}" for _, r in df.iterrows()}
                default_idx = options.index(st.session_state[selected_key]) if st.session_state[selected_key] in options else 0
                sel_id = st.selectbox(f"Choisir un {label_singulier}", options, index=default_idx, format_func=lambda x: labels.get(x, x), key=f"select_{key_prefix}")
                st.session_state[selected_key] = sel_id

                row_sel = df[df['ID'] == sel_id].iloc[0]
                nom = st.text_input("NOM", value=row_sel['Nom'], key=f"nom_{key_prefix}")
                prenom = st.text_input("PRENOM", value=row_sel['Prenom'], key=f"prenom_{key_prefix}")
                tel = st.text_input("TEL", value=row_sel['Tel'], key=f"tel_{key_prefix}")

                col_sup, col_save = st.columns(2)
                with col_sup:
                    if st.button("🗑️ SUP", key=f"sup_{key_prefix}", use_container_width=True):
                        df_new = df[df['ID'] != sel_id].reset_index(drop=True)
                        save_personnes(df_new, worksheet, fallback)
                        log_action(st.session_state.current_user['username'], f"Suppression {label_singulier} : {labels.get(sel_id, sel_id)}", f"Gestion {label_singulier}s")
                        st.toast(f"🗑️ {label_singulier.capitalize()} supprimé", icon="🗑️")
                        st.session_state[selected_key] = None
                        st.rerun()
                with col_save:
                    if st.button("💾 Enregistrer", key=f"save_{key_prefix}", use_container_width=True, type="primary"):
                        # Safe update: rebuild df to avoid pandas dtype coercion errors
                        df_updated = df.copy()
                        for col in ["Nom", "Prenom", "Tel"]:
                            df_updated[col] = df_updated[col].astype(object)
                        mask = df_updated['ID'] == sel_id
                        df_updated.loc[mask, "Nom"] = nom.strip()
                        df_updated.loc[mask, "Prenom"] = prenom.strip()
                        df_updated.loc[mask, "Tel"] = tel.strip()
                        save_personnes(df_updated, worksheet, fallback)
                        log_action(st.session_state.current_user['username'], f"Modification {label_singulier} : {nom} {prenom}", f"Gestion {label_singulier}s")
                        st.toast(f"✅ {label_singulier.capitalize()} mis à jour", icon="💾")
                        st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)


# =========================================================
# --- TAB 2 : LIVREURS ---
# =========================================================
with tabs[1]:
    render_personnes_tab(WORKSHEET_LIVREURS, FALLBACK_LIVREURS, df_livreurs, "livreur", "🚚")

# =========================================================
# --- TAB 3 : CLIENTS ---
# =========================================================
with tabs[2]:
    render_personnes_tab(WORKSHEET_CLIENTS, FALLBACK_CLIENTS, df_clients, "client", "👤", show_sync=True)

# =========================================================
# --- TAB 4 : STATISTIQUES ---
# =========================================================
with tabs[3]:
    if df_cheques.empty:
        st.info("Aucune donnée disponible pour générer des statistiques.")
    else:
        df_stats = df_cheques.copy()
        df_stats["Date_Sortie_dt"] = pd.to_datetime(df_stats["Date_Sortie"], format="%d/%m/%Y", errors="coerce")
        df_stats["Mois"] = df_stats["Date_Sortie_dt"].dt.to_period("M").astype(str)

        c1, c2 = st.columns(2)

        with c1:
            st.markdown("##### Répartition des chèques par statut")
            fig_pie = px.pie(
                df_stats, names="Statut", values="Montant", hole=0.55,
                color="Statut",
                color_discrete_map=STATUT_COLORS,
            )
            fig_pie.update_layout(margin=dict(l=0, r=0, t=10, b=0), legend=dict(orientation="h", y=-0.1))
            st.plotly_chart(fig_pie, use_container_width=True)

        with c2:
            st.markdown("##### Évolution du montant des chèques par mois")
            df_month = df_stats.dropna(subset=["Mois"]).groupby("Mois", as_index=False)["Montant"].sum().sort_values("Mois")
            fig_line = px.area(
                df_month, x="Mois", y="Montant",
                template="plotly_white", color_discrete_sequence=["#5b6cf9"],
            )
            fig_line.update_layout(margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig_line, use_container_width=True)

        c3, c4 = st.columns(2)

        with c3:
            st.markdown("##### Montant total par chauffeur")
            df_chauffeur = df_stats.groupby("Chauffeur", as_index=False)["Montant"].sum().sort_values("Montant", ascending=True)
            fig_bar1 = px.bar(
                df_chauffeur, x="Montant", y="Chauffeur", orientation="h",
                template="plotly_white", color_discrete_sequence=["#364fc7"],
            )
            fig_bar1.update_layout(margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig_bar1, use_container_width=True)

        with c4:
            st.markdown("##### Montant total par client")
            df_client = df_stats.groupby("Client", as_index=False)["Montant"].sum().sort_values("Montant", ascending=True)
            fig_bar2 = px.bar(
                df_client, x="Montant", y="Client", orientation="h",
                template="plotly_white", color_discrete_sequence=["#10b981"],
            )
            fig_bar2.update_layout(margin=dict(l=0, r=0, t=10, b=0))
            st.plotly_chart(fig_bar2, use_container_width=True)

        st.divider()
        st.markdown("##### Taux de conformité des retours (chèques réglés à temps)")
        df_resolved = df_stats[df_stats["Statut"].isin(["Réglé", "Refusée"])]
        if not df_resolved.empty:
            taux_regle = (len(df_stats[df_stats["Statut"] == "Réglé"]) / len(df_stats)) * 100
            st.progress(min(int(taux_regle), 100), text=f"{taux_regle:.0f}% des chèques sont réglés")
        else:
            st.caption("Pas encore assez de données pour calculer ce taux.")

st.markdown('<div style="text-align: center; color: #94a3b8; font-size: 0.8rem; margin-top: 30px;">DarPharm Solution | Suivi des Chèques</div>', unsafe_allow_html=True)
