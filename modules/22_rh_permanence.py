import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
from utils_gsheets import load_gs_data, save_gs_data, show_sync_ui
from utils_ia import ask_ai
from utils_sound import play_sound

# --- CONFIGURATION ---
WORKSHEET_NAME = "DB_RH_Gestion"
FALLBACK_PATH = "data/db_rh.csv"
UPLOAD_DIR = "data/justificatifs"
os.makedirs(UPLOAD_DIR, exist_ok=True)

COLUMNS = ["ID", "Date_Debut", "Date_Fin", "Agent", "Type", "Statut", "Commentaire", "Justificatif_Path", "Date_Creation"]

# --- UI ---
st.title("📅 Gestion RH & Planning")
st.markdown("### Permanences, Vacances et Absences")

show_sync_ui(WORKSHEET_NAME, FALLBACK_PATH, COLUMNS)
df_rh = load_gs_data(WORKSHEET_NAME, FALLBACK_PATH, COLUMNS)

# --- 1. LOGIQUE WEEKEND & PERMANENCE ---
def is_weekend(dt):
    # En Algérie (ou selon la demande), Vendredi (4) et Samedi (5) sont weekend
    # Dans Python datetime: Lundi=0, Mardi=1, ..., Vendredi=4, Samedi=5, Dimanche=6
    return dt.weekday() in [4, 5]

today = datetime.now()


tabs = st.tabs(["🕒 Permanence Samedi", "🏥 Absences & Congés", "📋 Planning Global", "🛡️ Validation Admin", "🏢 Équipes RDC & 1er Étage"])

# --- RÉCUPÉRATION AGENTS ---
from utils_gsheets import DB_USERS_WORKSHEET, DB_USERS_FALLBACK, USER_COLUMNS
df_users = load_gs_data(DB_USERS_WORKSHEET, DB_USERS_FALLBACK, USER_COLUMNS)

user_map = {}          # username ou Nom -> "Nom Prénom"
display_to_username = {} # "Nom Prénom" -> username
agents_display_list = []

if not df_users.empty:
    for _, urow in df_users.iterrows():
        u_name   = str(urow.get('username', '')).strip()
        u_nom    = str(urow.get('nom', '') or '').strip()
        u_prenom = str(urow.get('prenom', '') or '').strip()
        
        disp = f"{u_nom} {u_prenom}".strip() if (u_nom or u_prenom) else u_name
        if disp and u_name:
            user_map[u_name] = disp
            user_map[disp] = disp
            display_to_username[disp] = u_name
            if disp not in agents_display_list:
                agents_display_list.append(disp)

agents_display_list = sorted(agents_display_list)
if not agents_display_list:
    agents_display_list = ["Bousserouel Imad", "Ayoub", "Islem", "Seif"]

def format_agent_display(agent_raw):
    """Retourne le Nom + Prénom de l'agent si disponible."""
    if not agent_raw: return ""
    agent_str = str(agent_raw).strip()
    return user_map.get(agent_str, agent_str)

# --- TAB 1 : PERMANENCE SAMEDI ---
with tabs[0]:
    st.subheader("🕒 Planifier la permanence du Samedi (09h-15h)")
    st.info("Utilisez ce formulaire pour désigner l'agent qui assurera le service minimal ce samedi.")
    
    with st.form("form_permanence"):
        c1, c2 = st.columns(2)
        agent_p = c1.selectbox("Collaborateur désigné", agents_display_list, key="p_agent")
        date_p = c2.date_input("Samedi concerné", value=today + timedelta(days=(5 - today.weekday()) % 7))
        
        obs_p = st.text_input("Commentaire (Optionnel)")
        
        if st.form_submit_button("📅 Enregistrer la Permanence", use_container_width=True, type="primary"):
            new_row = {
                "ID": len(df_rh) + 1,
                "Date_Debut": date_p.strftime("%Y-%m-%d"),
                "Date_Fin": date_p.strftime("%Y-%m-%d"),
                "Agent": agent_p,
                "Type": "Permanence Samedi",
                "Statut": "Validé",
                "Commentaire": obs_p,
                "Justificatif_Path": "",
                "Date_Creation": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            df_rh = pd.concat([df_rh, pd.DataFrame([new_row])], ignore_index=True)
            save_gs_data(df_rh, WORKSHEET_NAME, FALLBACK_PATH)
            st.success(f"✅ Permanence enregistrée pour **{agent_p}** le {date_p}")
            st.rerun()

# --- TAB 2 : ABSENCES & CONGÉS ---
with tabs[1]:
    st.subheader("🏥 Déclarer une Absence ou un Congé")
    with st.form("form_absences"):
        c1, c2 = st.columns(2)
        agent_a = c1.selectbox("Collaborateur concerné", agents_display_list, key="a_agent")
        type_a = c2.selectbox("Type d'absence", ["Congé Annuel", "Maladie", "Récupération", "Absence Autorisée", "Urgence"])
        
        d1 = c1.date_input("Date de début", value=today, key="a_d1")
        d2 = c2.date_input("Date de fin (Inclus)", value=today, key="a_d2")
        
        uploaded_file = st.file_uploader("📎 Justificatif (PDF, JPG, PNG)", type=["pdf", "png", "jpg", "jpeg"])
        comm_a = st.text_area("Motif / Observations")
        
        if st.form_submit_button("🚀 Envoyer la demande", use_container_width=True, type="primary"):
            file_path = ""
            if uploaded_file:
                fname = f"JUST_{agent_a}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_file.name}"
                file_path = os.path.join(UPLOAD_DIR, fname)
                with open(file_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
            
            new_row = {
                "ID": len(df_rh) + 1,
                "Date_Debut": d1.strftime("%Y-%m-%d"),
                "Date_Fin": d2.strftime("%Y-%m-%d"),
                "Agent": agent_a,
                "Type": type_a,
                "Statut": "En attente",
                "Commentaire": comm_a,
                "Justificatif_Path": file_path,
                "Date_Creation": datetime.now().strftime("%Y-%m-%d %H:%M")
            }
            df_rh = pd.concat([df_rh, pd.DataFrame([new_row])], ignore_index=True)
            save_gs_data(df_rh, WORKSHEET_NAME, FALLBACK_PATH)
            st.success("✅ Demande envoyée pour validation admin.")
            st.rerun()

# --- TAB 3 : PLANNING GLOBAL ---
with tabs[2]:
    st.subheader("📊 Suivi du Personnel")

    is_admin_rh = st.session_state.current_user.get('role') == 'Admin'

    df_view = df_rh.copy()
    if not df_view.empty and 'Agent' in df_view.columns:
        df_view['Agent'] = df_view['Agent'].apply(format_agent_display)
    
    # Filtres simples
    c_f1, c_f2, c_f3 = st.columns(3)
    f_agent = c_f1.multiselect("Filtrer par agent", agents_display_list)
    f_type = c_f2.multiselect("Type d'événement", df_rh['Type'].unique() if not df_rh.empty else [])
    
    FRENCH_MONTHS = {
        1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril", 5: "Mai", 6: "Juin",
        7: "Juillet", 8: "Août", 9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
    }
    
    month_options = ["Tous"]
    month_map = {}
    target_year = today.year
    target_month = today.month
    
    if not df_rh.empty and 'Date_Debut' in df_rh.columns:
        dates = pd.to_datetime(df_rh['Date_Debut'], errors='coerce')
        valid_dates = df_rh[dates.notna()]
        if not valid_dates.empty:
            parsed_dates = pd.to_datetime(valid_dates['Date_Debut'])
            yms = parsed_dates.apply(lambda d: (d.year, d.month)).unique()
            sorted_yms = sorted(list(yms), reverse=True)
            for y, m in sorted_yms:
                label = f"{FRENCH_MONTHS[m]} {y}"
                month_options.append(label)
                month_map[label] = (y, m)
                
    f_month = c_f3.selectbox("Période (Mois)", month_options, index=0)
    
    df_filtered = df_view.copy()
    if f_agent: df_filtered = df_filtered[df_filtered['Agent'].isin(f_agent)]
    if f_type:  df_filtered = df_filtered[df_filtered['Type'].isin(f_type)]
    
    if f_month != "Tous":
        target_year, target_month = month_map[f_month]
        import calendar
        start_of_month = pd.Timestamp(datetime(target_year, target_month, 1))
        end_of_month   = pd.Timestamp(datetime(target_year, target_month, calendar.monthrange(target_year, target_month)[1]))
        parsed_start = pd.to_datetime(df_filtered['Date_Debut'], errors='coerce')
        parsed_end   = pd.to_datetime(df_filtered['Date_Fin'],   errors='coerce').fillna(parsed_start)
        overlap_mask = (parsed_start <= end_of_month) & (parsed_end >= start_of_month)
        df_filtered = df_filtered[overlap_mask]

    # ── Tableau interactif ──────────────────────────────────────────
    if df_filtered.empty:
        st.info("Aucun enregistrement pour cette sélection.")
    else:
        # En-têtes tableau
        hdr = st.columns([1.2, 2, 2, 1.5, 2, 1, 1])
        for h, t in zip(hdr, ["ID", "Agent", "Type", "Statut", "Période", "✏️ Modifier", "🗑️ Supprimer"]):
            h.markdown(f"**{t}**")
        st.markdown("<hr style='margin:4px 0;'>", unsafe_allow_html=True)

        for view_idx, view_row in df_filtered.sort_values("Date_Debut", ascending=False).iterrows():
            row_id  = view_row.get('ID', view_idx)
            agent_d = str(view_row.get('Agent', ''))
            type_d  = str(view_row.get('Type', ''))
            statut  = str(view_row.get('Statut', ''))
            date_d  = str(view_row.get('Date_Debut', ''))
            date_f  = str(view_row.get('Date_Fin', ''))
            periode = date_d if date_d == date_f else f"{date_d} → {date_f}"

            statut_color = {"Validé": "#10b981", "En attente": "#f59e0b", "Rejeté": "#ef4444"}.get(statut, "#64748b")

            c_id, c_ag, c_ty, c_st, c_pe, c_ed, c_dl = st.columns([1.2, 2, 2, 1.5, 2, 1, 1])
            c_id.caption(f"#{row_id}")
            c_ag.write(agent_d)
            c_ty.write(type_d)
            c_st.markdown(f"<span style='color:{statut_color};font-weight:700;font-size:.82rem;'>{statut}</span>", unsafe_allow_html=True)
            c_pe.caption(periode)

            edit_key = f"edit_btn_{view_idx}"
            del_key  = f"del_btn_{view_idx}"

            if is_admin_rh:
                if c_ed.button("✏️", key=edit_key, help="Modifier cet enregistrement"):
                    st.session_state[f"editing_{view_idx}"] = True
                if c_dl.button("🗑️", key=del_key, help="Supprimer cet enregistrement"):
                    df_rh = df_rh.drop(index=view_idx).reset_index(drop=True)
                    save_gs_data(df_rh, WORKSHEET_NAME, FALLBACK_PATH)
                    st.success(f"✅ Entrée #{row_id} supprimée.")
                    st.rerun()
            else:
                c_ed.write("—")
                c_dl.write("—")

            # Formulaire d'édition inline
            if is_admin_rh and st.session_state.get(f"editing_{view_idx}", False):
                with st.container():
                    st.markdown(f"<div style='background:#f0f9ff;border:1px solid #bae6fd;border-radius:12px;padding:16px;margin:6px 0;'>", unsafe_allow_html=True)
                    st.markdown(f"**✏️ Modifier l'entrée #{row_id}**")
                    with st.form(f"form_edit_row_{view_idx}"):
                        e1, e2 = st.columns(2)
                        new_agent  = e1.selectbox("Agent", agents_display_list,
                                                   index=agents_display_list.index(agent_d) if agent_d in agents_display_list else 0,
                                                   key=f"e_agent_{view_idx}")
                        new_type   = e2.selectbox("Type", ["Permanence Samedi", "Congé Annuel", "Maladie",
                                                            "Récupération", "Absence Autorisée", "Urgence"],
                                                   index=["Permanence Samedi", "Congé Annuel", "Maladie",
                                                          "Récupération", "Absence Autorisée", "Urgence"].index(type_d)
                                                   if type_d in ["Permanence Samedi", "Congé Annuel", "Maladie",
                                                                  "Récupération", "Absence Autorisée", "Urgence"] else 0,
                                                   key=f"e_type_{view_idx}")
                        e3, e4 = st.columns(2)
                        try:
                            d_debut_val = pd.to_datetime(date_d).date()
                        except Exception:
                            d_debut_val = today.date()
                        try:
                            d_fin_val = pd.to_datetime(date_f).date()
                        except Exception:
                            d_fin_val = today.date()
                        new_debut  = e3.date_input("Date début",  value=d_debut_val, key=f"e_debut_{view_idx}")
                        new_fin    = e4.date_input("Date fin",    value=d_fin_val,   key=f"e_fin_{view_idx}")
                        new_statut = e1.selectbox("Statut", ["Validé", "En attente", "Rejeté"],
                                                   index=["Validé", "En attente", "Rejeté"].index(statut)
                                                   if statut in ["Validé", "En attente", "Rejeté"] else 0,
                                                   key=f"e_statut_{view_idx}")
                        new_comm   = e2.text_input("Commentaire", value=str(view_row.get('Commentaire', '') or ''),
                                                    key=f"e_comm_{view_idx}")

                        sb1, sb2 = st.columns(2)
                        if sb1.form_submit_button("💾 Enregistrer", use_container_width=True, type="primary"):
                            df_rh.at[view_idx, 'Agent']      = new_agent
                            df_rh.at[view_idx, 'Type']       = new_type
                            df_rh.at[view_idx, 'Date_Debut'] = new_debut.strftime("%Y-%m-%d")
                            df_rh.at[view_idx, 'Date_Fin']   = new_fin.strftime("%Y-%m-%d")
                            df_rh.at[view_idx, 'Statut']     = new_statut
                            df_rh.at[view_idx, 'Commentaire']= new_comm
                            save_gs_data(df_rh, WORKSHEET_NAME, FALLBACK_PATH)
                            st.session_state[f"editing_{view_idx}"] = False
                            st.success(f"✅ Entrée #{row_id} mise à jour !")
                            st.rerun()
                        if sb2.form_submit_button("✖ Annuler", use_container_width=True):
                            st.session_state[f"editing_{view_idx}"] = False
                            st.rerun()
                    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    c_btn1, c_btn2 = st.columns(2)
    with c_btn1:
        if st.button("🤖 Analyser la couverture (IA)", use_container_width=True):
            with st.spinner("Analyse..."):
                res = ask_ai(f"Analyse ce planning : {df_filtered.to_string()}. Y a-t-il des anomalies ?")
                st.info(res)
                
    with c_btn2:
        model_pdf = st.selectbox(
            "Modèle de Planning :",
            ["Modèle Classique (Avec Mme Samra)", "Modèle Équipe RDC (Sans Mme Samra)"],
            key="planning_model_choice"
        )
        model_param = "Classique" if "Classique" in model_pdf else "RDC"
        pdf_title = "PLANNING & PERMANENCES"
        if f_month != "Tous":
            pdf_title    = f"PLANNING & PERMANENCES - {f_month.upper()}"
            pdf_filename = f"Planning_RH_{target_year}_{target_month:02d}.pdf"
        else:
            pdf_filename = f"Planning_RH_Global_{datetime.now().strftime('%Y%m%d')}.pdf"
        from utils_pdf import generate_rh_planning_pdf
        pdf_bytes = generate_rh_planning_pdf(df_filtered, title=pdf_title, model=model_param)
        st.download_button("📥 Télécharger le Planning (PDF)", pdf_bytes, pdf_filename,
                           "application/pdf", use_container_width=True)

    # ── Zone Danger : Vider tout le planning ───────────────────────
    if is_admin_rh:
        st.markdown("---")
        with st.expander("⚠️ Zone Danger — Vider le Planning", expanded=False):
            st.warning("⚠️ Cette action supprime **TOUS** les enregistrements du planning RH de façon irréversible.")
            confirm_clear = st.checkbox("Je confirme vouloir vider entièrement le planning RH", key="confirm_clear_rh")
            if st.button("🗑️ Vider tout le Planning RH", type="primary", use_container_width=True, disabled=not confirm_clear):
                df_rh = pd.DataFrame(columns=COLUMNS)
                save_gs_data(df_rh, WORKSHEET_NAME, FALLBACK_PATH)
                st.success("✅ Le planning RH a été entièrement vidé.")
                st.rerun()

# --- TAB 4 : VALIDATION ADMIN ---
with tabs[3]:
    st.subheader("🛡️ Espace de Validation")
    if st.session_state.current_user.get('role') != 'Admin':
        st.warning("Accès réservé aux administrateurs.")
    else:
        df_pending = df_rh[df_rh['Statut'] == "En attente"]
        if df_pending.empty:
            st.success("✅ Aucune demande en attente.")
        else:
            st.info(f"📋 {len(df_pending)} demande(s) en attente de validation.")
            for idx, row in df_pending.iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns([3, 1])
                    agent_disp = format_agent_display(row['Agent'])
                    c1.write(f"**{agent_disp}** — {row['Type']}")
                    c1.caption(f"Du {row['Date_Debut']} au {row['Date_Fin']}")
                    if row.get('Commentaire'):
                        c1.caption(f"💬 {row['Commentaire']}")
                    
                    if row.get('Justificatif_Path') and os.path.exists(str(row['Justificatif_Path'])):
                        with open(row['Justificatif_Path'], "rb") as f:
                            c2.download_button("📂 Justificatif", f,
                                               file_name=os.path.basename(row['Justificatif_Path']),
                                               key=f"dl_{idx}")
                    
                    b1, b2, b3 = st.columns(3)
                    if b1.button("✅ Valider", key=f"v_{idx}", use_container_width=True):
                        df_rh.at[idx, 'Statut'] = "Validé"
                        save_gs_data(df_rh, WORKSHEET_NAME, FALLBACK_PATH)
                        st.rerun()
                    if b2.button("❌ Rejeter", key=f"r_{idx}", use_container_width=True):
                        df_rh.at[idx, 'Statut'] = "Rejeté"
                        save_gs_data(df_rh, WORKSHEET_NAME, FALLBACK_PATH)
                        st.rerun()
                    if b3.button("🗑️ Supprimer", key=f"d_{idx}", use_container_width=True):
                        df_rh = df_rh.drop(index=idx).reset_index(drop=True)
                        save_gs_data(df_rh, WORKSHEET_NAME, FALLBACK_PATH)
                        st.rerun()

# --- TAB 5 : GESTION ÉQUIPES RDC & 1ER ÉTAGE ---
with tabs[4]:
    st.subheader("🏢 Composition & Échanges d'Équipes (RDC / 1er Étage)")
    st.caption("Modifiez l'affectation des collaborateurs entre le Rez-de-Chaussée (RDC) et le 1er Étage pour mettre à jour automatiquement les plannings et rapports PDF.")
    
    from utils_pdf import load_teams_config, save_teams_config, is_rdc, DEFAULT_RDC_LIST
    
    is_admin = st.session_state.get('current_user', {}).get('role') == 'Admin'
    if not is_admin:
        st.warning("🔒 Seuls les administrateurs peuvent modifier la composition des équipes.")
    
    teams_cfg = load_teams_config()
    
    # Séparer les collaborateurs actuels
    rdc_agents = [ag for ag in agents_display_list if is_rdc(ag)]
    etage_agents = [ag for ag in agents_display_list if not is_rdc(ag)]
    
    col_rdc, col_etage = st.columns(2)
    with col_rdc:
        st.markdown("#### ⬇️ Équipe RDC (Rez-de-Chaussée)")
        st.info(f"**{len(rdc_agents)} collaborateur(s)**")
        for a in rdc_agents:
            st.write(f"• **{a}**")
            
    with col_etage:
        st.markdown("#### ⬆️ Équipe 1er Étage")
        st.success(f"**{len(etage_agents)} collaborateur(s)**")
        for a in etage_agents:
            st.write(f"• **{a}**")
            
    st.markdown("---")
    
    if is_admin:
        st.markdown("### 🔄 1. Échange Direct (Permutation rapide)")
        st.caption("Permutez directement les postes d'un collaborateur du RDC et d'un collaborateur du 1er Étage.")
        
        with st.form("form_swap_teams"):
            c_swap1, c_swap2 = st.columns(2)
            ag_rdc_sel = c_swap1.selectbox("Collaborateur actuellement au RDC :", rdc_agents if rdc_agents else ["Aucun"], key="swap_rdc_sel")
            ag_etage_sel = c_swap2.selectbox("Collaborateur actuellement au 1er Étage :", etage_agents if etage_agents else ["Aucun"], key="swap_etage_sel")
            
            if st.form_submit_button("🔄 Permuter les 2 collaborateurs", use_container_width=True, type="primary"):
                if ag_rdc_sel == "Aucun" or ag_etage_sel == "Aucun":
                    st.error("⚠️ Veuillez sélectionner deux collaborateurs valides.")
                else:
                    # Mettre à jour la config
                    current_rdc_cfg = set(teams_cfg.get("rdc", list(DEFAULT_RDC_LIST)))
                    current_etage_cfg = set(teams_cfg.get("etage", []))
                    
                    # On retire ag_rdc_sel de RDC et on l'ajoute à Etage
                    current_rdc_cfg.discard(ag_rdc_sel)
                    current_etage_cfg.add(ag_rdc_sel)
                    
                    # On retire ag_etage_sel de Etage et on l'ajoute à RDC
                    current_etage_cfg.discard(ag_etage_sel)
                    current_rdc_cfg.add(ag_etage_sel)
                    
                    save_teams_config({"rdc": list(current_rdc_cfg), "etage": list(current_etage_cfg)})
                    st.success(f"✅ Échange réussi entre **{ag_rdc_sel}** (maintenant 1er Étage) et **{ag_etage_sel}** (maintenant RDC) !")
                    st.rerun()

        st.markdown("---")
        st.markdown("### 🛠️ 2. Affectation Sélection Globale")
        st.caption("Cochez tous les collaborateurs devant appartenir à l'Équipe RDC. Les autres iront automatiquement au 1er Étage.")
        
        with st.form("form_global_teams"):
            selected_rdc = st.multiselect(
                "Sélectionnez les membres du RDC :",
                options=agents_display_list,
                default=rdc_agents,
                key="multiselect_rdc_teams"
            )
            
            if st.form_submit_button("💾 Enregistrer la composition des équipes", use_container_width=True):
                selected_etage = [ag for ag in agents_display_list if ag not in selected_rdc]
                save_teams_config({"rdc": selected_rdc, "etage": selected_etage})
                st.success("✅ Configuration des équipes mise à jour avec succès !")
                st.rerun()
                
        with st.expander("⚙️ Réinitialisation des équipes", expanded=False):
            if st.button("🔄 Réinitialiser aux équipes par défaut", use_container_width=True):
                save_teams_config({"rdc": list(DEFAULT_RDC_LIST), "etage": []})
                st.success("✅ Équipes réinitialisées aux valeurs par défaut.")
                st.rerun()



