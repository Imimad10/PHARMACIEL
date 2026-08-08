import streamlit as st
import pandas as pd
import io
import plotly.express as px
from datetime import datetime, timedelta
import uuid

try:
    from utils import log_action
except ImportError:
    def log_action(*args, **kwargs):
        pass

import importlib
import utils_gsheets
import utils_pdf

if not hasattr(utils_pdf, 'generate_factures_report_pdf'):
    importlib.reload(utils_pdf)

from utils_gsheets import load_gs_data, save_gs_data
from utils_pdf import generate_factures_report_pdf

# --- CONFIGURATION GOOGLE SHEETS ---
WORKSHEET_FACTURES = "Suivi_Factures"
FALLBACK_FACTURES = "factures_data.csv"
COLS_FACTURES = ["N", "Livreur", "Region", "Client", "Reference", "Date_Creation", "Date_Pointage", "Statut"]

WORKSHEET_LIVREURS = "Livreurs"
FALLBACK_LIVREURS = "livreurs_data.csv"

COLS_PERSONNE = ["ID", "Nom", "Prenom", "Tel"]

STATUTS = ["En attente", "Réglé", "Refusée"]
IS_ADMIN = lambda: st.session_state.get("current_user", {}).get("role", "") in ["Admin", "Superviseur"]
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

# --- STYLING PREMIUM ---
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
</style>
""", unsafe_allow_html=True)


# =========================================================
# --- FONCTIONS DE DONNEES ---
# =========================================================
def get_factures():
    df = load_gs_data(WORKSHEET_FACTURES, FALLBACK_FACTURES, COLS_FACTURES)
    if not df.empty:
        if "N" in df.columns:
            df["N"] = pd.to_numeric(df["N"], errors="coerce")
    return df

def save_factures(df):
    save_gs_data(df, WORKSHEET_FACTURES, FALLBACK_FACTURES)

def get_personnes(worksheet, fallback):
    df = load_gs_data(worksheet, fallback, COLS_PERSONNE)
    for col in ["Nom", "Prenom", "Tel"]:
        if col in df.columns:
            df[col] = df[col].astype(object).fillna("")
    return ensure_unique_ids(df, worksheet, fallback)

def ensure_unique_ids(df, worksheet, fallback):
    if df.empty:
        return df
    if "ID" not in df.columns:
        df["ID"] = ""
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
        save_gs_data(df, worksheet, fallback)
    return df

def save_personnes(df, worksheet, fallback):
    save_gs_data(df, worksheet, fallback)

def personne_display_list(df):
    if df.empty:
        return []
    return [f"{r['Nom']} {r['Prenom']}".strip() for _, r in df.iterrows()]

# =========================================================
# --- EN-TETE ---
# =========================================================
c_h1, c_h2 = st.columns([2.5, 1])
with c_h1:
    st.title("📝 Pointage des Factures")
    st.markdown(f"**Agent :** `{st.session_state.current_user['username']}` | {get_now().strftime('%d/%m/%Y %H:%M')}")
with c_h2:
    st.markdown("""
        <div style="background: rgba(16, 185, 129, 0.1); padding: 10px 20px; border-radius: 15px; border: 1px solid rgba(16, 185, 129, 0.2); text-align: right;">
            <span style="color: #065f46; font-weight: 700; font-size: 0.8rem;">GSheets Online</span>
        </div>
    """, unsafe_allow_html=True)

df_factures = get_factures()
# Ensure date/status columns are object dtype to prevent pandas TypeError on .loc assignment
for _col in ["Date_Pointage", "Date_Creation", "Statut"]:
    if _col in df_factures.columns:
        df_factures[_col] = df_factures[_col].astype(object).fillna("")
df_livreurs = get_personnes(WORKSHEET_LIVREURS, FALLBACK_LIVREURS)

tabs = st.tabs(["📊 Tableau de Bord", "📥 Importation", "🚚 Livreurs", "📈 Statistiques", "🖨️ Impression PDF / Excel", "🗑️ Admin DB"])

# =========================================================
# --- TAB 1 : TABLEAU DE BORD ---
# =========================================================
with tabs[0]:
    # --- KPI ---
    if not df_factures.empty:
        total_factures = len(df_factures)
        n_regle = len(df_factures[df_factures["Statut"] == "Réglé"])
        n_attente = len(df_factures[df_factures["Statut"] == "En attente"])
        n_refuse = len(df_factures[df_factures["Statut"] == "Refusée"])
    else:
        total_factures = n_regle = n_attente = n_refuse = 0

    k1, k2, k3, k4 = st.columns(4)
    k1.markdown(f"""<div class="kpi-tile"><div class="kpi-label">Total Factures</div><div class="kpi-value">{total_factures}</div></div>""", unsafe_allow_html=True)
    k2.markdown(f"""<div class="kpi-tile"><div class="kpi-label">Pointées / OK</div><div class="kpi-value" style="color:#10b981;">{n_regle}</div></div>""", unsafe_allow_html=True)
    k3.markdown(f"""<div class="kpi-tile"><div class="kpi-label">En Attente</div><div class="kpi-value" style="color:#f59e0b;">{n_attente}</div></div>""", unsafe_allow_html=True)
    k4.markdown(f"""<div class="kpi-tile"><div class="kpi-label">Anomalies / Refusées</div><div class="kpi-value" style="color:#ef4444;">{n_refuse}</div></div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col_list, col_form = st.columns([2, 1])

    # --- LISTE / FILTRES (colonne gauche) ---
    with col_list:
        f0, f1, f2, f3 = st.columns([1.5, 1, 1, 1])
        recherche_text = f0.text_input("🔍 Rechercher Client / Réf.", key="f_search", placeholder="Nom ou Référence…")
        filtre_statut = f1.selectbox("Filtrer par statut", ["Tous"] + STATUTS, key="f_statut")
        filtre_region = f2.selectbox("Filtrer par région", ["Toutes"] + sorted(df_factures["Region"].dropna().unique().tolist()) if not df_factures.empty else ["Toutes"])
        filtre_livreur = f3.selectbox("Filtrer par livreur", ["Tous"] + sorted(df_factures["Livreur"].dropna().unique().tolist()) if not df_factures.empty else ["Tous"])

        df_view = df_factures.copy()
        if not df_view.empty:
            if recherche_text.strip():
                query = recherche_text.strip().lower()
                mask_search = (
                    df_view["Client"].astype(str).str.lower().str.contains(query, na=False) |
                    df_view["Reference"].astype(str).str.lower().str.contains(query, na=False)
                )
                df_view = df_view[mask_search]
            if filtre_statut != "Tous":
                df_view = df_view[df_view["Statut"] == filtre_statut]
            if filtre_region != "Toutes":
                df_view = df_view[df_view["Region"] == filtre_region]
            if filtre_livreur != "Tous":
                df_view = df_view[df_view["Livreur"] == filtre_livreur]

        exp1, exp2 = st.columns(2)
        with exp1:
            if not df_view.empty:
                pdf_bytes = generate_factures_report_pdf(
                    df_view, 
                    livreur_nom=filtre_livreur if filtre_livreur != "Tous" else "Non specifie",
                    region=filtre_region if filtre_region != "Toutes" else "Toutes"
                )
                st.download_button(
                    "📄 Imprimer Pointage PDF",
                    data=pdf_bytes,
                    file_name=f"Pointage_{get_now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            else:
                st.button("📄 Imprimer Pointage PDF", disabled=True, use_container_width=True)

        with exp2:
            if not df_view.empty:
                output_tab1 = io.BytesIO()
                df_tab1_ex = df_view[["Reference", "Client", "Region", "Livreur", "Date_Creation", "Date_Pointage", "Statut"]].copy()
                df_tab1_ex.columns = ["Référence", "Client", "Région", "Livreur", "Date Création", "Date Pointage", "Statut"]
                with pd.ExcelWriter(output_tab1, engine="openpyxl") as writer:
                    df_tab1_ex.to_excel(writer, index=False, sheet_name="Pointage_Filtre")
                st.download_button(
                    "📊 Exporter Liste (Excel)",
                    data=output_tab1.getvalue(),
                    file_name=f"Pointage_Export_{get_now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            else:
                st.button("📊 Exporter Liste (Excel)", disabled=True, use_container_width=True)

        st.markdown("<br>", unsafe_allow_html=True)

        if df_view.empty:
            st.info("Aucune facture enregistrée pour ces filtres.")
        else:
            for _, row in df_view.sort_values("N", ascending=False).head(100).iterrows():
                color = STATUT_COLORS.get(row["Statut"], "#94a3b8")
                bg = STATUT_BG.get(row["Statut"], "#f1f5f9")
                icon = STATUT_ICON.get(row["Statut"], "•")
                st.markdown(f"""
                    <div class="cheque-card" style="border-left-color: {color};">
                        <div class="cheque-main">
                            <div class="cheque-num">N° {int(row['N']) if pd.notna(row['N']) else '-'} — Réf: {row['Reference']}</div>
                            <div class="cheque-sub">📍 {row['Region']} | 🚚 {row['Livreur']} | 👤 {row['Client'][:35]}</div>
                            <div class="cheque-sub">📅 Création : {row['Date_Creation']}  |  Pointage : {row['Date_Pointage'] if pd.notna(row['Date_Pointage']) and row['Date_Pointage'] else '—'}</div>
                        </div>
                        <div style="text-align:right;">
                            <span class="statut-pill" style="background:{color};">{icon} {row['Statut']}</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            if len(df_view) > 100:
                st.caption(f"Affichage limité aux 100 dernières factures. Total : {len(df_view)}")

    # --- PANNEAU DROIT : POINTAGE RAPIDE + SELECTION EN MASSE ---
    with col_form:
        st.markdown('<div class="form-panel">', unsafe_allow_html=True)
        st.markdown("#### ✅ Pointage Rapide")
        st.caption("Modifiez le statut de factures individuelles ou sélectionnez-en plusieurs pour un changement en masse.")

        if not df_view.empty:
            # ── Tableau éditable (statut individuel) ──
            edited_df = st.data_editor(
                df_view[["Reference", "Statut"]].copy(),
                column_config={
                    "Reference": st.column_config.TextColumn("Facture", disabled=True),
                    "Statut": st.column_config.SelectboxColumn("Statut", options=STATUTS, required=True),
                },
                hide_index=True,
                use_container_width=True,
                key="editor_pointage"
            )

            if st.button("💾 Enregistrer les modifications", use_container_width=True, type="primary"):
                df_updated = df_factures.copy()
                for _c in ['Date_Pointage', 'Date_Creation', 'Statut']:
                    if _c in df_updated.columns:
                        df_updated[_c] = df_updated[_c].astype(object).fillna("")
                changed = 0
                for idx, row in edited_df.iterrows():
                    ref = row['Reference']
                    new_stat = row['Statut']
                    mask = df_updated['Reference'] == ref
                    if mask.any():
                        old_stat = df_updated.loc[mask, 'Statut'].values[0]
                        if new_stat != old_stat:
                            df_updated.loc[mask, 'Statut'] = new_stat
                            if new_stat != "En attente":
                                df_updated.loc[mask, 'Date_Pointage'] = get_now().strftime("%d/%m/%Y %H:%M")
                            changed += 1
                if changed > 0:
                    save_factures(df_updated)
                    log_action(st.session_state.current_user['username'], f"Pointage de {changed} factures", "Pointage Factures")
                    st.toast(f"✅ {changed} factures mises à jour", icon="💾")
                    st.rerun()
                else:
                    st.info("Aucune modification détectée.")

            st.divider()

            # ── Changement de statut EN MASSE avec SELECT ALL ──
            st.markdown("##### 🔀 Changement en masse")
            refs_dispo = df_view["Reference"].tolist()
            
            select_all = st.checkbox(
                f"Sélectionner TOUTES les factures filtrées ({len(refs_dispo)})",
                key="select_all_refs"
            )
            
            default_selected = refs_dispo if select_all else []

            selected_refs = st.multiselect(
                "Sélectionner les factures",
                options=refs_dispo,
                default=default_selected,
                placeholder="Choisir une ou plusieurs références…",
                key="multiselect_refs"
            )
            if selected_refs:
                st.caption(f"🎯 **{len(selected_refs)}** facture(s) sélectionnée(s)")
                nouveau_statut_masse = st.selectbox(
                    "Nouveau statut à appliquer",
                    STATUTS,
                    key="statut_masse"
                )
                if st.button(f"⚡ Appliquer '{nouveau_statut_masse}' aux {len(selected_refs)} factures",
                             use_container_width=True, type="primary"):
                    df_updated = df_factures.copy()
                    for _c in ['Date_Pointage', 'Date_Creation', 'Statut']:
                        if _c in df_updated.columns:
                            df_updated[_c] = df_updated[_c].astype(object).fillna("")
                    count = 0
                    for ref in selected_refs:
                        mask = df_updated['Reference'] == ref
                        if mask.any():
                            df_updated.loc[mask, 'Statut'] = nouveau_statut_masse
                            if nouveau_statut_masse != "En attente":
                                df_updated.loc[mask, 'Date_Pointage'] = get_now().strftime("%d/%m/%Y %H:%M")
                            count += 1
                    save_factures(df_updated)
                    log_action(st.session_state.current_user['username'],
                               f"Changement en masse : {count} factures → {nouveau_statut_masse}",
                               "Pointage Factures")
                    st.toast(f"✅ {count} factures mises à jour → {nouveau_statut_masse}", icon="⚡")
                    st.rerun()
        else:
            st.info("Sélectionnez des factures à gauche pour les pointer.")

        st.markdown('</div>', unsafe_allow_html=True)


# =========================================================
# --- TAB 2 : IMPORTATION ---
# =========================================================
with tabs[1]:
    st.markdown("### 📥 Importation des Factures (LogiPharm / Cmds & Rotation)")
    st.caption("Vous pouvez importer un fichier Excel de factures ou de **Cmds & Rotation** (`lot.xlsx`), ou synchroniser directement depuis la base Master Data.")

    st.markdown("<br>", unsafe_allow_html=True)

    col_up_file, col_sync_db = st.columns([1.5, 1])

    # ── OPTION A : UPLOAD D'UN FICHIER EXCEL ──
    with col_up_file:
        st.markdown("##### 📁 Importer un fichier Excel")
        uploaded_file = st.file_uploader("Choisissez le fichier Excel (ex: lot.xlsx ou export LogiPharm)", type=['xlsx'], key="uploader_pointage")
        
        if uploaded_file:
            try:
                xls = pd.ExcelFile(uploaded_file)
                sheet_names = xls.sheet_names
                
                # Détection automatique de la feuille Cmds & Rotation / Feuil2
                default_sheet_idx = 0
                for idx, s_name in enumerate(sheet_names):
                    s_lower = s_name.lower().strip()
                    if "cmd" in s_lower or "rotation" in s_lower or s_lower == "feuil2":
                        default_sheet_idx = idx
                        break

                if len(sheet_names) > 1:
                    chosen_sheet = st.selectbox(
                        "📄 Feuille Excel détectée dans ce fichier",
                        options=sheet_names,
                        index=default_sheet_idx,
                        key="select_excel_sheet"
                    )
                else:
                    chosen_sheet = sheet_names[0]

                df_import = pd.read_excel(xls, sheet_name=chosen_sheet)

                # Nettoyage & mapping intelligent des entêtes
                import unicodedata
                def clean_str(c):
                    c = str(c).strip().lower()
                    return ''.join(ch for ch in unicodedata.normalize('NFD', c) if unicodedata.category(ch) != 'Mn')

                raw_cols = df_import.columns.tolist()
                mapped_cols = {}
                for col in raw_cols:
                    c_clean = clean_str(col)
                    if c_clean in ['reference', 'reference', 'ref', 'b.l', 'n° ordre', 'n°ordre', 'nordre']:
                        mapped_cols[col] = 'reference'
                    elif c_clean in ['client', 'nom client', 'raison sociale']:
                        mapped_cols[col] = 'client'
                    elif c_clean in ['region', 'region', 'wilaya', 'zone']:
                        mapped_cols[col] = 'region'
                    elif any(k in c_clean for k in ['date creation', 'date creat', 'date validat', 'date']):
                        mapped_cols[col] = 'date_creation'

                df_import = df_import.rename(columns=mapped_cols)

                missing = [c for c in ['client', 'reference', 'region'] if c not in df_import.columns]

                if not missing:
                    if 'date_creation' not in df_import.columns:
                        df_import['date_creation'] = get_now().strftime("%d/%m/%Y %H:%M")

                    st.success(f"✅ Feuille `{chosen_sheet}` lue avec succès : **{len(df_import)}** lignes détectées.")

                    livreurs_list = personne_display_list(df_livreurs)
                    if not livreurs_list:
                        st.warning("⚠️ Aucun livreur n'est enregistré. Les factures seront 'Non assigné'.")
                        def_livreur = "Non assigné"
                    else:
                        def_livreur = st.selectbox("Assigner un livreur par défaut (Optionnel)", ["Automatique selon la région"] + livreurs_list, key="def_livreur_import")

                    if st.button("🚀 Intégrer les factures à la base de suivi", type="primary", use_container_width=True):
                        new_rows = []
                        existing_refs = set(df_factures['Reference'].astype(str).str.strip()) if not df_factures.empty else set()
                        next_n = int(df_factures["N"].max()) + 1 if not df_factures.empty and df_factures["N"].notna().any() else 1

                        added = 0
                        for _, row in df_import.iterrows():
                            ref = str(row['reference']).strip()
                            if ref and ref not in existing_refs and ref.lower() != 'nan':
                                livreur_assigne = "Non assigné"
                                if def_livreur != "Automatique selon la région":
                                    livreur_assigne = def_livreur
                                else:
                                    reg_str = str(row['region']).lower()
                                    if "alger 1" in reg_str:
                                        livreur_assigne = next((l for l in livreurs_list if "fethi" in l.lower()), "Non assigné")
                                    elif "alger 2" in reg_str:
                                        livreur_assigne = next((l for l in livreurs_list if "fares" in l.lower()), "Non assigné")

                                dt_val = str(row['date_creation']) if pd.notna(row['date_creation']) else get_now().strftime("%d/%m/%Y %H:%M")

                                new_rows.append({
                                    "N": next_n + added,
                                    "Livreur": livreur_assigne,
                                    "Region": str(row['region']).strip(),
                                    "Client": str(row['client']).strip(),
                                    "Reference": ref,
                                    "Date_Creation": dt_val,
                                    "Date_Pointage": "",
                                    "Statut": "En attente"
                                })
                                added += 1
                                existing_refs.add(ref)

                        if added > 0:
                            df_new = pd.DataFrame(new_rows)
                            df_updated = pd.concat([df_factures, df_new], ignore_index=True)
                            save_factures(df_updated)
                            log_action(st.session_state.current_user['username'], f"Import de {added} factures depuis {chosen_sheet}", "Pointage Factures")
                            st.success(f"🎉 {added} nouvelles factures ajoutées à la base de suivi !")
                            st.rerun()
                        else:
                            st.info("Toutes les références de cette feuille existent déjà dans la base.")

                else:
                    st.error(f"❌ Colonnes requis non trouvées dans `{chosen_sheet}` : {missing}")
                    st.caption(f"Colonnes disponibles : {list(raw_cols)}")

            except Exception as e:
                st.error(f"Erreur de lecture Excel : {e}")

    # ── OPTION B : SYNCHRONISATION DIRECTE DEPUIS MASTER DATA (CMDS & ROTATION) ──
    with col_sync_db:
        st.markdown("##### 🔄 Synchronisation Master Data")
        st.caption("Extrayez directement les références de factures stockées dans l'archive Master Data (`Cmds & Rotation`).")

        try:
            df_cmd_rot = load_gs_data("Cmd_Rotation", "data/db_cmd_rotation.csv", ["reference", "client", "region", "date_creation"])
            if not df_cmd_rot.empty and "reference" in df_cmd_rot.columns:
                existing_refs_sync = set(df_factures["Reference"].astype(str).str.strip()) if not df_factures.empty else set()
                pending_sync_df = df_cmd_rot[~df_cmd_rot["reference"].astype(str).str.strip().isin(existing_refs_sync)]
                nb_pending = len(pending_sync_df)

                st.markdown(f"""
                    <div style="background: rgba(59, 130, 246, 0.1); padding: 16px; border-radius: 14px; border: 1px solid rgba(59, 130, 246, 0.3); margin-bottom: 12px;">
                        <div style="font-weight: 700; color: #1e40af;">📋 Archive Cmds & Rotation</div>
                        <div style="font-size: 0.88rem; color: #3b82f6; margin-top: 4px;">
                            Total commandes : <b>{len(df_cmd_rot)}</b><br>
                            Factures à synchroniser : <b>{nb_pending}</b>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                if nb_pending > 0:
                    if st.button(f"⚡ Importer {nb_pending} factures depuis Master Data", type="primary", use_container_width=True):
                        next_n = int(df_factures["N"].max()) + 1 if not df_factures.empty and df_factures["N"].notna().any() else 1
                        new_sync_rows = []
                        added_sync = 0
                        for _, r in pending_sync_df.iterrows():
                            ref_v = str(r["reference"]).strip()
                            if ref_v and ref_v.lower() != 'nan':
                                cli_v = str(r.get("client", "Client inconnu")).strip()
                                reg_v = str(r.get("region", "Non spécifiée")).strip()
                                dt_v = str(r.get("date_creation", get_now().strftime("%d/%m/%Y %H:%M"))).strip()

                                new_sync_rows.append({
                                    "N": next_n + added_sync,
                                    "Livreur": "Non assigné",
                                    "Region": reg_v,
                                    "Client": cli_v,
                                    "Reference": ref_v,
                                    "Date_Creation": dt_v,
                                    "Date_Pointage": "",
                                    "Statut": "En attente"
                                })
                                added_sync += 1
                        if new_sync_rows:
                            df_updated = pd.concat([df_factures, pd.DataFrame(new_sync_rows)], ignore_index=True)
                            save_factures(df_updated)
                            log_action(st.session_state.current_user['username'], f"Sync Master Data: {added_sync} factures intégrées", "Pointage Factures")
                            st.toast(f"✅ {added_sync} factures intégrées depuis Master Data !", icon="⚡")
                            st.rerun()
                else:
                    st.success("✅ Toutes les factures de Cmds & Rotation sont déjà synchronisées !")
            else:
                st.info("Aucune archive `Cmds & Rotation` importée dans Master Data pour le moment.")
        except Exception as e_sync:
            st.error(f"Erreur de lecture Master Data : {e_sync}")

# =========================================================
# --- TAB 3 : LIVREURS ---
# =========================================================
def render_personnes_tab(worksheet, fallback, df, label_singulier, icon, show_sync=False):
    key_prefix = worksheet.lower()
    mode_key = f"mode_{key_prefix}"
    selected_key = f"selected_{key_prefix}"

    if mode_key not in st.session_state: st.session_state[mode_key] = "ajouter"
    if selected_key not in st.session_state: st.session_state[selected_key] = None

    col_list, col_panel = st.columns([1.4, 1])

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
                    if st.button("✏️", key=f"edit_{key_prefix}_{pos}_{row['ID']}", use_container_width=True):
                        st.session_state[mode_key] = "modifier"
                        st.session_state[selected_key] = row['ID']
                        st.rerun()

    with col_panel:
        b1, b2 = st.columns(2)
        with b1:
            if st.button("➕ Ajouter", key=f"btn_add_{key_prefix}", use_container_width=True, type="primary" if st.session_state[mode_key] == "ajouter" else "secondary"):
                st.session_state[mode_key] = "ajouter"
                st.session_state[selected_key] = None
                st.rerun()
        with b2:
            if st.button("✏️ Mod/Sup", key=f"btn_edit_{key_prefix}", use_container_width=True, type="primary" if st.session_state[mode_key] == "modifier" else "secondary"):
                st.session_state[mode_key] = "modifier"
                st.rerun()
        
        st.markdown('<div class="form-panel">', unsafe_allow_html=True)
        if st.session_state[mode_key] == "ajouter":
            st.markdown(f"#### ➕ Nouveau {label_singulier}")
            nom = st.text_input("NOM", key=f"nom_{key_prefix}")
            prenom = st.text_input("PRENOM", key=f"prenom_{key_prefix}")
            tel = st.text_input("TEL", key=f"tel_{key_prefix}")
            if st.button("💾 Enregistrer", key=f"save_{key_prefix}", use_container_width=True, type="primary"):
                if nom.strip():
                    new_id = str(uuid.uuid4())[:8]
                    new_row = {"ID": new_id, "Nom": nom.strip(), "Prenom": prenom.strip(), "Tel": tel.strip()}
                    df_new = pd.DataFrame([new_row])
                    df_updated = pd.concat([df, df_new], ignore_index=True)
                    save_personnes(df_updated, worksheet, fallback)
                    log_action(st.session_state.current_user['username'], f"Création {label_singulier} : {nom}", f"Gestion {label_singulier}s")
                    st.toast(f"✅ {label_singulier.capitalize()} ajouté", icon="💾")
                    st.rerun()
                else:
                    st.error("Le NOM est obligatoire.")
        elif st.session_state[mode_key] == "modifier":
            st.markdown(f"#### ✏️ Modifier / 🗑️ Supprimer")
            if df.empty:
                st.info("Aucune donnée à modifier.")
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
                    if st.button("💾 Enregistrer", key=f"save_edit_{key_prefix}", use_container_width=True, type="primary"):
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

with tabs[2]:
    render_personnes_tab(WORKSHEET_LIVREURS, FALLBACK_LIVREURS, df_livreurs, "livreur", "🚚")


# =========================================================
# --- TAB 4 : STATISTIQUES ---
# =========================================================
with tabs[3]:
    st.markdown("### 📈 Analyse Globale des Factures")
    if not df_factures.empty:
        c1, c2 = st.columns(2)
        with c1:
            fig_statut = px.pie(df_factures, names='Statut', title="Répartition par Statut", hole=0.4,
                                color='Statut', color_discrete_map=STATUT_COLORS)
            st.plotly_chart(fig_statut, use_container_width=True)
        with c2:
            fig_chauffeur = px.histogram(df_factures, x='Livreur', color='Statut', title="Performance par Livreur",
                                         barmode='group', color_discrete_map=STATUT_COLORS)
            st.plotly_chart(fig_chauffeur, use_container_width=True)
    else:
        st.info("Pas assez de données pour générer des statistiques.")


# =========================================================
# --- TAB 5 : IMPRESSION PDF / EXCEL ---
# =========================================================
with tabs[4]:
    st.markdown("### 🖨️ Impression du Bordereau de Pointage")
    st.caption("Sélectionnez la région et le livreur pour générer un bordereau personnalisé — seule la région choisie sera incluse dans le fichier téléchargé.")

    st.markdown("<br>", unsafe_allow_html=True)

    col_cfg1, col_cfg2 = st.columns(2)

    with col_cfg1:
        st.markdown("##### 📍 Région / Secteur à imprimer")
        regions_available = ["Toutes"] + sorted(
            df_factures["Region"].dropna().unique().tolist()
        ) if not df_factures.empty else ["Toutes"]
        region_impression = st.selectbox(
            "Choisir la Région",
            regions_available,
            key="region_impression"
        )
        if region_impression != "Toutes":
            nb_region = len(df_factures[df_factures["Region"] == region_impression])
            st.info(f"📦 **{nb_region}** factures dans cette région")
        else:
            st.info(f"📦 **{len(df_factures)}** factures au total")

    with col_cfg2:
        st.markdown("##### 👤 Choisir le Livreur pour cette mission")
        livreurs_list = personne_display_list(df_livreurs)
        livreur_options = ["Non attribué"] + livreurs_list
        livreur_impression = st.selectbox(
            "Assigner un Livreur",
            livreur_options,
            key="livreur_impression"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # --- APERÇU DE LA SÉLECTION ---
    df_print = df_factures.copy()
    if region_impression != "Toutes":
        df_print = df_print[df_print["Region"] == region_impression]

    if livreur_impression != "Non attribué":
        df_print = df_print.copy()
        df_print["Livreur"] = livreur_impression

    st.markdown(f"""
        <div style="background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
                    border: 2px solid #0ea5e9; border-radius: 16px; padding: 20px 24px; margin-bottom: 16px;">
            <div style="font-size: 1.1rem; font-weight: 800; color: #0369a1; margin-bottom: 8px;">🧾 Aperçu du Bordereau</div>
            <div style="color: #374151; font-size: 0.9rem;">
                <b>Région :</b> {region_impression} &nbsp;|&nbsp;
                <b>Livreur :</b> {livreur_impression} &nbsp;|&nbsp;
                <b>Nombre de factures :</b> {len(df_print)}
            </div>
        </div>
    """, unsafe_allow_html=True)

    if not df_print.empty:
        # Aperçu du tableau
        with st.expander(f"👁️ Prévisualiser les {len(df_print)} factures", expanded=False):
            st.dataframe(
                df_print[["Reference", "Client", "Date_Creation", "Statut"]].reset_index(drop=True),
                use_container_width=True,
                hide_index=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        btn1, btn2, _ = st.columns([1, 1, 1])

        with btn1:
            try:
                pdf_bytes = generate_factures_report_pdf(
                    df_print,
                    livreur_nom=livreur_impression,
                    region=region_impression
                )
                region_label = region_impression.replace(" ", "_") if region_impression != "Toutes" else "Toutes"
                st.download_button(
                    label="📄 Télécharger PDF",
                    data=pdf_bytes,
                    file_name=f"Pointage_{region_label}_{get_now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary"
                )
            except Exception as e:
                st.error(f"Erreur PDF : {e}")

        with btn2:
            try:
                output = io.BytesIO()
                df_excel = df_print[["Reference", "Client", "Region", "Livreur", "Date_Creation", "Statut"]].copy()
                df_excel.columns = ["Référence", "Client", "Région", "Livreur", "Date Création", "Statut"]
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    df_excel.to_excel(writer, index=False, sheet_name="Pointage")
                excel_bytes = output.getvalue()
                region_label = region_impression.replace(" ", "_") if region_impression != "Toutes" else "Toutes"
                st.download_button(
                    label="📊 Télécharger Excel",
                    data=excel_bytes,
                    file_name=f"Pointage_{region_label}_{get_now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            except Exception as e:
                st.error(f"Erreur Excel : {e}")
    else:
        st.warning("⚠️ Aucune facture disponible pour cette sélection.")

# =========================================================
# --- TAB 6 : ADMIN DB ---
# =========================================================
with tabs[5]:
    st.markdown("### 🗑️ Administration de la Base de Données")

    if not IS_ADMIN():
        st.error("🔒 Accès réservé aux **Administrateurs** et **Superviseurs**.")
        st.stop()

    st.markdown("""
        <div style="background: linear-gradient(135deg, #fff1f2 0%, #ffe4e6 100%);
                    border: 2px solid #fca5a5; border-radius: 16px; padding: 20px 24px; margin-bottom: 20px;">
            <div style="font-size: 1.1rem; font-weight: 800; color: #b91c1c; margin-bottom: 8px;">
                ⚠️ Zone de danger — Actions irréversibles
            </div>
            <div style="color: #7f1d1d; font-size: 0.9rem;">
                Les opérations ci-dessous suppriment définitivement des données de la base.
                Assurez-vous d'avoir exporté une sauvegarde avant de continuer.
            </div>
        </div>
    """, unsafe_allow_html=True)

    # --- Export de sauvegarde avant suppression ---
    with st.expander("📥 Télécharger une sauvegarde avant suppression", expanded=True):
        if not df_factures.empty:
            output_bck = io.BytesIO()
            with pd.ExcelWriter(output_bck, engine="openpyxl") as writer:
                df_factures.to_excel(writer, index=False, sheet_name="Backup_Factures")
            st.download_button(
                label="📊 Sauvegarder toutes les factures (Excel)",
                data=output_bck.getvalue(),
                file_name=f"Backup_Factures_{get_now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        else:
            st.info("La base est déjà vide.")

    st.divider()

    # --- Vider la base factures ---
    st.markdown("#### 🗑️ Vider la base des factures")
    st.caption(f"La base contient actuellement **{len(df_factures)}** facture(s).")

    confirm1 = st.checkbox(
        "Je comprends que cette action est **irréversible** et que toutes les factures seront supprimées.",
        key="confirm_wipe_1"
    )
    if confirm1:
        confirm2 = st.checkbox(
            "Je confirme vouloir **vider définitivement** la base des factures.",
            key="confirm_wipe_2"
        )
        if confirm2:
            st.warning("⚠️ Double confirmation obtenue. Le bouton ci-dessous effacera toutes les données.")
            if st.button("🚨 VIDER TOUTE LA BASE DES FACTURES", type="primary", use_container_width=True):
                df_vide = pd.DataFrame(columns=COLS_FACTURES)
                save_factures(df_vide)
                load_gs_data.clear()
                log_action(
                    st.session_state.current_user['username'],
                    "VIDAGE COMPLET de la base Suivi_Factures",
                    "Admin DB Pointage"
                )
                st.success("✅ Base vidée avec succès. Rechargement en cours…")
                st.rerun()

