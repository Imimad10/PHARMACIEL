import streamlit as st
import pandas as pd
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
df_livreurs = get_personnes(WORKSHEET_LIVREURS, FALLBACK_LIVREURS)

tabs = st.tabs(["📊 Tableau de Bord", "📥 Importation", "🚚 Livreurs", "📈 Statistiques"])

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
        f1, f2, f3 = st.columns(3)
        filtre_statut = f1.selectbox("Filtrer par statut", ["Tous"] + STATUTS, key="f_statut")
        filtre_region = f2.selectbox("Filtrer par région", ["Toutes"] + sorted(df_factures["Region"].dropna().unique().tolist()) if not df_factures.empty else ["Toutes"])
        filtre_livreur = f3.selectbox("Filtrer par livreur", ["Tous"] + sorted(df_factures["Livreur"].dropna().unique().tolist()) if not df_factures.empty else ["Tous"])

        df_view = df_factures.copy()
        if not df_view.empty:
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

    # --- FORMULAIRE D'ACTION RAPIDE (colonne droite) ---
    with col_form:
        st.markdown('<div class="form-panel">', unsafe_allow_html=True)
        st.markdown("#### ✅ Pointage Rapide")
        st.caption("Changez rapidement le statut d'une ou plusieurs factures en sélectionnant dans le tableau.")
        
        if not df_view.empty:
            edited_df = st.data_editor(
                df_view[["Reference", "Statut"]].copy(),
                column_config={
                    "Reference": st.column_config.TextColumn("Facture", disabled=True),
                    "Statut": st.column_config.SelectboxColumn("Action (Statut)", options=STATUTS, required=True),
                },
                hide_index=True,
                use_container_width=True,
                key="editor_pointage"
            )
            
            if st.button("💾 Enregistrer les pointages", use_container_width=True, type="primary"):
                # On met à jour la base principale df_factures avec les changements
                df_updated = df_factures.copy()
                changed = 0
                for idx, row in edited_df.iterrows():
                    ref = row['Reference']
                    new_stat = row['Statut']
                    old_stat = df_updated.loc[df_updated['Reference'] == ref, 'Statut'].values[0]
                    if new_stat != old_stat:
                        df_updated.loc[df_updated['Reference'] == ref, 'Statut'] = new_stat
                        if new_stat != "En attente":
                            df_updated.loc[df_updated['Reference'] == ref, 'Date_Pointage'] = get_now().strftime("%d/%m/%Y %H:%M")
                        changed += 1
                
                if changed > 0:
                    save_factures(df_updated)
                    log_action(st.session_state.current_user['username'], f"Pointage de {changed} factures", "Pointage Factures")
                    st.toast(f"✅ {changed} factures mises à jour", icon="💾")
                    st.rerun()
                else:
                    st.info("Aucune modification détectée.")
        else:
            st.info("Sélectionnez des factures à gauche pour les pointer.")

        st.markdown('</div>', unsafe_allow_html=True)


# =========================================================
# --- TAB 2 : IMPORTATION ---
# =========================================================
with tabs[1]:
    st.markdown("### 📥 Importation depuis LogiPharm (Excel)")
    st.write("Le fichier Excel doit contenir les colonnes : `Client`, `Référence`, `Date Création`, `Région`.")
    
    uploaded_file = st.file_uploader("Choisissez le fichier Excel d'export", type=['xlsx'])
    
    if uploaded_file:
        try:
            df_import = pd.read_excel(uploaded_file)
            
            # Nettoyage des entêtes
            import unicodedata
            def clean_col(c):
                c = str(c).strip().lower()
                return ''.join(ch for ch in unicodedata.normalize('NFD', c) if unicodedata.category(ch) != 'Mn')
            
            df_import.columns = [clean_col(c) for c in df_import.columns]
            
            cols_obligatoires = ['client', 'reference', 'region']
            missing = [c for c in cols_obligatoires if c not in df_import.columns]
            
            if not missing:
                date_col = 'date creation'
                if date_col not in df_import.columns:
                    if 'date creat' in df_import.columns:
                        date_col = 'date creat'
                    else:
                        df_import[date_col] = get_now().strftime("%d/%m/%Y %H:%M")
                
                st.success(f"✅ Fichier lu avec succès : {len(df_import)} lignes détectées.")
                
                # Affectation Livreurs Automatique ou Manuelle
                livreurs_list = personne_display_list(df_livreurs)
                if not livreurs_list:
                    st.warning("⚠️ Aucun livreur n'est enregistré. Vous ne pourrez pas affecter de livreur.")
                    def_livreur = "Non assigné"
                else:
                    def_livreur = st.selectbox("Assigner un livreur par défaut pour ce lot d'import (Optionnel)", ["Automatique selon la région"] + livreurs_list)
                
                if st.button("🚀 Intégrer les factures à la base de suivi", type="primary"):
                    new_rows = []
                    existing_refs = set(df_factures['Reference'].astype(str)) if not df_factures.empty else set()
                    
                    next_n = int(df_factures["N"].max()) + 1 if not df_factures.empty and df_factures["N"].notna().any() else 1
                    
                    added = 0
                    for _, row in df_import.iterrows():
                        ref = str(row['reference']).strip()
                        if ref not in existing_refs:
                            # Logique d'affectation basique
                            livreur_assigne = "Non assigné"
                            if def_livreur != "Automatique selon la région":
                                livreur_assigne = def_livreur
                            else:
                                reg_str = str(row['region']).lower()
                                if "alger 1" in reg_str:
                                    livreur_assigne = next((l for l in livreurs_list if "fethi" in l.lower()), "Non assigné")
                                elif "alger 2" in reg_str:
                                    livreur_assigne = next((l for l in livreurs_list if "fares" in l.lower()), "Non assigné")
                            
                            new_rows.append({
                                "N": next_n + added,
                                "Livreur": livreur_assigne,
                                "Region": str(row['region']).strip(),
                                "Client": str(row['client']).strip(),
                                "Reference": ref,
                                "Date_Creation": str(row[date_col]),
                                "Date_Pointage": "",
                                "Statut": "En attente"
                            })
                            added += 1
                    
                    if added > 0:
                        df_new = pd.DataFrame(new_rows)
                        df_updated = pd.concat([df_factures, df_new], ignore_index=True)
                        save_factures(df_updated)
                        log_action(st.session_state.current_user['username'], f"Import de {added} factures", "Pointage Factures")
                        st.success(f"🎉 {added} nouvelles factures ajoutées à la base de suivi !")
                    else:
                        st.info("Aucune nouvelle facture à ajouter (toutes les références existent déjà).")
                    
            else:
                st.error(f"❌ Colonnes manquantes dans l'Excel : {missing}")
                st.write(f"Colonnes trouvées : {list(df_import.columns)}")
                
        except Exception as e:
            st.error(f"Erreur de lecture Excel : {e}")

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
