import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import uuid
from utils_gsheets import load_gs_data, save_gs_data

# ─── CONFIGURATION ────────────────────────────────────────────────────────────
AFFECT_WORKSHEET = "Affectation_Livreurs"
AFFECT_FALLBACK  = "data/db_affectations.csv"
AFFECT_COLS      = [
    "id_affectation", "nom_livreur", "secteur_actif",
    "date_debut", "date_fin", "est_actuel", "modifie_par"
]

# ─── UTILITAIRE EXPORTÉ ────────────────────────────────────────────────────────
def get_secteur_actuel(nom_livreur: str, df_affectations: pd.DataFrame) -> str:
    """
    Retourne le secteur actif du livreur selon la table d'affectation.
    Retourne '' si aucune affectation active trouvée.
    """
    if df_affectations.empty or "nom_livreur" not in df_affectations.columns:
        return ""
    mask = (
        (df_affectations["nom_livreur"].astype(str).str.strip().str.lower() == str(nom_livreur).strip().lower()) &
        (df_affectations["est_actuel"].astype(str).str.strip().str.upper().isin(["TRUE", "1", "OUI", "VRAI"]))
    )
    found = df_affectations[mask]
    if found.empty:
        return ""
    return str(found.iloc[0]["secteur_actif"]).strip()


def get_all_current_assignments(df_affectations: pd.DataFrame) -> dict:
    """Retourne un dict {nom_livreur: secteur_actif} pour toutes les affectations actuelles."""
    if df_affectations.empty:
        return {}
    mask = df_affectations["est_actuel"].astype(str).str.strip().str.upper().isin(["TRUE", "1", "OUI", "VRAI"])
    current = df_affectations[mask]
    return dict(zip(current["nom_livreur"].astype(str), current["secteur_actif"].astype(str)))


# ─── CSS PREMIUM ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800;900&family=Sora:wght@400;700;800&display=swap');

    .aff-title {
        font-family: 'Sora', sans-serif;
        font-weight: 800;
        font-size: 2rem;
        background: linear-gradient(90deg, #0052FF, #7B2CBF);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .aff-subtitle {
        font-family: 'Inter', sans-serif;
        color: #64748b;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }

    /* Livreur Cards */
    .livreur-card {
        background: linear-gradient(135deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
        border: 1px solid rgba(255,255,255,0.1);
        border-radius: 18px;
        padding: 20px 24px;
        margin-bottom: 12px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        transition: all 0.3s ease;
        box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    }
    .livreur-card:hover {
        border-color: rgba(0,82,255,0.4);
        transform: translateY(-2px);
        box-shadow: 0 10px 30px rgba(0,82,255,0.12);
    }
    .livreur-name {
        font-family: 'Sora', sans-serif;
        font-weight: 700;
        font-size: 1.05rem;
        color: #1e293b;
    }
    .secteur-badge {
        display: inline-block;
        padding: 5px 14px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 700;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        background: linear-gradient(135deg, #0052FF22, #7B2CBF22);
        color: #0052FF;
        border: 1px solid #0052FF44;
    }
    .date-badge {
        font-size: 0.75rem;
        color: #94a3b8;
        font-weight: 600;
    }
    .history-dot {
        width: 12px; height: 12px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 8px;
        flex-shrink: 0;
    }
    .history-dot.current { background: #10b981; box-shadow: 0 0 8px #10b98166; }
    .history-dot.past { background: #94a3b8; }
    .history-row {
        display: flex;
        align-items: center;
        padding: 10px 0;
        border-bottom: 1px solid rgba(255,255,255,0.05);
        font-size: 0.88rem;
    }

    /* Form card */
    .form-card {
        background: rgba(0,82,255,0.03);
        border: 1px solid rgba(0,82,255,0.12);
        border-radius: 18px;
        padding: 24px;
        margin-top: 10px;
    }
    .alert-success {
        background: rgba(16,185,129,0.1);
        border-left: 4px solid #10b981;
        border-radius: 10px;
        padding: 14px 18px;
        color: #065f46;
        font-weight: 600;
        margin: 10px 0;
    }
    .alert-warning {
        background: rgba(245,158,11,0.1);
        border-left: 4px solid #f59e0b;
        border-radius: 10px;
        padding: 14px 18px;
        color: #92400e;
        font-weight: 600;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)



# ─── CONTRÔLE D'ACCÈS (ADMIN & SUPERVISEUR) ──────────────────────────────────
if 'current_user' not in st.session_state or not st.session_state.current_user:
    st.warning("🔒 Connexion requise.")
    st.stop()

user_role = str(st.session_state.current_user.get('role', 'Saisie')).strip()
if user_role not in ['Admin', 'Superviseur', 'Manager']:
    st.error("⛔ Accès réservé aux Administrateurs et Superviseurs.")
    st.stop()

# ─── HEADER ───────────────────────────────────────────────────────────────────
st.markdown('<h1 class="aff-title">🚚 Affectation & Flotte</h1>', unsafe_allow_html=True)
st.markdown('<p class="aff-subtitle">Gérez les affectations secteur/région de chaque livreur. Toute modification est historisée sans écraser les opérations passées.</p>', unsafe_allow_html=True)


# ─── CHARGEMENT DES DONNÉES ───────────────────────────────────────────────────
def load_affectations() -> pd.DataFrame:
    df = load_gs_data(AFFECT_WORKSHEET, AFFECT_FALLBACK, AFFECT_COLS)
    if df.empty:
        df = pd.DataFrame(columns=AFFECT_COLS)
    # Normaliser est_actuel
    if "est_actuel" in df.columns:
        df["est_actuel"] = df["est_actuel"].astype(str).str.strip()
    return df

def save_affectations(df: pd.DataFrame):
    save_gs_data(df, AFFECT_WORKSHEET, AFFECT_FALLBACK)


def load_livreurs_base():
    """Charge la liste des livreurs depuis la table Livreurs existante."""
    df = load_gs_data("Livreurs", "data_expedition/livreurs.csv", ["Nom", "Prénom", "Téléphone", "Secteur"])
    return df


def affecter_livreur(nom_livreur: str, nouveau_secteur: str, modifie_par: str, df_aff: pd.DataFrame) -> pd.DataFrame:
    """
    Crée une nouvelle affectation pour un livreur :
    1. Ferme toutes ses affectations actuelles (est_actuel = False, date_fin = aujourd'hui)
    2. Insère une nouvelle ligne (est_actuel = True)
    JAMAIS de modification des tables Expéditions ou Réclamations.
    """
    today_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Fermer les affectations actuelles de ce livreur
    mask_actuel = (
        (df_aff["nom_livreur"].astype(str).str.strip().str.lower() == nom_livreur.strip().lower()) &
        (df_aff["est_actuel"].astype(str).str.strip().str.upper().isin(["TRUE", "1", "OUI", "VRAI"]))
    )
    if mask_actuel.any():
        df_aff.loc[mask_actuel, "est_actuel"] = "False"
        df_aff.loc[mask_actuel, "date_fin"]   = today_str

    # Créer la nouvelle affectation
    new_id = str(uuid.uuid4())[:8].upper()
    new_row = pd.DataFrame([{
        "id_affectation": f"AFF-{new_id}",
        "nom_livreur":    nom_livreur.strip(),
        "secteur_actif":  nouveau_secteur.strip(),
        "date_debut":     today_str,
        "date_fin":       "",
        "est_actuel":     "True",
        "modifie_par":    modifie_par,
    }])
    df_aff = pd.concat([df_aff, new_row], ignore_index=True)
    return df_aff


# ─── CHARGEMENT ───────────────────────────────────────────────────────────────
df_aff = load_affectations()
df_livreurs_base = load_livreurs_base()

# Liste consolidée des livreurs (depuis table Livreurs + historique affectations)
livreurs_from_base = df_livreurs_base["Nom"].dropna().astype(str).tolist() if not df_livreurs_base.empty else []
livreurs_from_aff  = df_aff["nom_livreur"].dropna().astype(str).unique().tolist() if not df_aff.empty else []
all_livreurs = sorted(set(livreurs_from_base + livreurs_from_aff))

# Liste des secteurs
secteurs_base = []
if not df_livreurs_base.empty and "Secteur" in df_livreurs_base.columns:
    secteurs_base = df_livreurs_base["Secteur"].dropna().astype(str).unique().tolist()
if not df_aff.empty and "secteur_actif" in df_aff.columns:
    secteurs_base += df_aff["secteur_actif"].dropna().astype(str).unique().tolist()
secteurs_base = sorted(set([s for s in secteurs_base if s and s.lower() not in ["nan", ""]]))

# ─── TABS ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs([
    "📋 Affectations Actuelles",
    "📜 Historique Complet",
    "➕ Nouvelle Affectation"
])


# ══════════════════════════════════════════════════════════════════
# TAB 1 — AFFECTATIONS ACTUELLES
# ══════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("### 📋 État Actuel des Affectations Secteur / Livreur")

    # Construire la vue actuelle (un livreur = une ligne)
    if not df_aff.empty:
        mask_cur = df_aff["est_actuel"].astype(str).str.strip().str.upper().isin(["TRUE", "1", "OUI", "VRAI"])
        df_current = df_aff[mask_cur].copy()
    else:
        df_current = pd.DataFrame(columns=AFFECT_COLS)

    # Livreurs sans affectation
    livreurs_sans_aff = [l for l in all_livreurs if l.lower() not in
                         [x.lower() for x in df_current["nom_livreur"].astype(str).tolist()]]

    # KPIs rapides
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("👥 Total Livreurs", len(all_livreurs))
    k2.metric("✅ Affectés", len(df_current))
    k3.metric("⚠️ Non affectés", len(livreurs_sans_aff))
    k4.metric("🗺️ Secteurs actifs", df_current["secteur_actif"].nunique() if not df_current.empty else 0)

    st.markdown("---")

    if df_current.empty:
        st.info("ℹ️ Aucune affectation active enregistrée. Utilisez l'onglet ➕ Nouvelle Affectation pour en créer.")
    else:
        # Graphique répartition par secteur
        col_chart, col_table = st.columns([1, 2])
        with col_chart:
            df_pie = df_current.groupby("secteur_actif").size().reset_index(name="Nb")
            fig_pie = px.pie(df_pie, values="Nb", names="secteur_actif", hole=0.5,
                             color_discrete_sequence=px.colors.sequential.Blues_r,
                             title="Répartition par Secteur")
            fig_pie.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                  height=280, margin=dict(t=40, l=10, r=10, b=10))
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_table:
            st.markdown("#### Livreurs & Secteurs Actifs")
            for _, row in df_current.sort_values("nom_livreur").iterrows():
                debut_str = str(row.get("date_debut", ""))[:10] if pd.notna(row.get("date_debut")) else "—"
                st.markdown(f"""
                <div class="livreur-card">
                    <div>
                        <div class="livreur-name">🚴 {row['nom_livreur']}</div>
                        <div class="date-badge">📅 Depuis le {debut_str} · ID: {row.get('id_affectation','—')}</div>
                    </div>
                    <div>
                        <span class="secteur-badge">{row['secteur_actif']}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)

    if livreurs_sans_aff:
        st.markdown("---")
        st.warning(f"⚠️ **{len(livreurs_sans_aff)} livreur(s) sans affectation active** : {', '.join(livreurs_sans_aff)}")
        st.info("💡 Rendez-vous dans l'onglet **➕ Nouvelle Affectation** pour leur attribuer un secteur.")


    # Modification rapide inline
    st.markdown("---")
    st.markdown("### ✏️ Modifier une Affectation")
    if not df_current.empty:
        col_mod1, col_mod2, col_mod3 = st.columns([2, 2, 1])
        livreur_a_modifier = col_mod1.selectbox(
            "Choisir le livreur à réaffecter",
            sorted(df_current["nom_livreur"].astype(str).tolist()),
            key="mod_livreur_sel"
        )
        # Pré-remplir le secteur actuel
        secteur_actuel_livreur = get_secteur_actuel(livreur_a_modifier, df_aff)
        secteur_options = secteurs_base if secteurs_base else ["ALGER", "BLIDA", "TIPAZA", "BOUMERDES", "MEDEA"]
        if secteur_actuel_livreur and secteur_actuel_livreur not in secteur_options:
            secteur_options = [secteur_actuel_livreur] + secteur_options

        idx_cur = secteur_options.index(secteur_actuel_livreur) if secteur_actuel_livreur in secteur_options else 0
        nouveau_secteur_mod = col_mod2.selectbox("Nouveau secteur", secteur_options, index=idx_cur, key="mod_secteur_sel")
        nouveau_secteur_libre = col_mod2.text_input("Ou saisir un secteur libre", placeholder="ex: SETIF", key="mod_secteur_libre")

        col_mod3.write("##")
        if col_mod3.button("💾 Enregistrer", key="btn_mod_aff", type="primary", use_container_width=True):
            secteur_final = nouveau_secteur_libre.strip() if nouveau_secteur_libre.strip() else nouveau_secteur_mod
            if secteur_final == secteur_actuel_livreur:
                st.warning("⚠️ Le secteur sélectionné est identique à l'affectation actuelle. Aucune modification effectuée.")
            else:
                admin_user = st.session_state.get("current_user", {}).get("username", "admin")
                df_aff = affecter_livreur(livreur_a_modifier, secteur_final, admin_user, df_aff)
                save_affectations(df_aff)
                st.markdown(f"""
                <div class="alert-success">
                    ✅ Affectation mise à jour ! <b>{livreur_a_modifier}</b> → Secteur : <b>{secteur_final}</b><br>
                    <small>L'historique précédent est conservé. Seules les nouvelles opérations utiliseront ce secteur.</small>
                </div>
                """, unsafe_allow_html=True)
                st.rerun()
    else:
        st.info("Aucune affectation active à modifier pour l'instant.")


# ══════════════════════════════════════════════════════════════════
# TAB 2 — HISTORIQUE COMPLET
# ══════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### 📜 Historique Complet des Affectations")
    st.info("🔒 **Principe de traçabilité** : Les affectations passées ne sont jamais supprimées. "
            "Chaque changement de secteur est archivé avec sa date de prise d'effet et de fin.")

    if df_aff.empty:
        st.info("Aucun historique disponible.")
    else:
        # Filtre par livreur
        livreur_hist = st.selectbox("Filtrer par livreur", ["Tous"] + sorted(df_aff["nom_livreur"].dropna().unique().tolist()), key="hist_livreur")
        df_hist = df_aff.copy() if livreur_hist == "Tous" else df_aff[df_aff["nom_livreur"] == livreur_hist]
        df_hist = df_hist.sort_values(["nom_livreur", "date_debut"], ascending=[True, False])

        # Affichage timeline
        for livreur_name, grp in df_hist.groupby("nom_livreur"):
            with st.expander(f"🚴 {livreur_name} — {len(grp)} affectation(s)", expanded=(livreur_hist == livreur_name)):
                for _, row in grp.iterrows():
                    is_cur = str(row.get("est_actuel", "")).strip().upper() in ["TRUE", "1", "OUI", "VRAI"]
                    dot_cls = "current" if is_cur else "past"
                    label_cur = "🟢 ACTUEL" if is_cur else "⚫ TERMINÉ"
                    debut = str(row.get("date_debut", ""))[:16] if pd.notna(row.get("date_debut")) else "—"
                    fin = str(row.get("date_fin", ""))[:16] if pd.notna(row.get("date_fin")) and str(row.get("date_fin", "")) else "En cours"
                    modif = str(row.get("modifie_par", "—"))

                    st.markdown(f"""
                    <div class="history-row">
                        <span class="history-dot {dot_cls}"></span>
                        <div style="flex:1;">
                            <b>{row['secteur_actif']}</b>
                            <span style="margin-left:12px; font-size:0.75rem; color:#94a3b8;">{label_cur}</span>
                        </div>
                        <div style="text-align:right; font-size:0.78rem; color:#64748b;">
                            📅 {debut} → {fin}<br>
                            <small>par {modif}</small>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### 📊 Volume d'affectations par livreur")
        df_count = df_aff.groupby("nom_livreur").size().reset_index(name="Nb Affectations")
        fig_bar = px.bar(df_count.sort_values("Nb Affectations", ascending=False),
                         x="nom_livreur", y="Nb Affectations",
                         color="Nb Affectations", color_continuous_scale="Blues",
                         labels={"nom_livreur": "Livreur"})
        fig_bar.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                               height=320, margin=dict(t=20, l=10, r=10, b=10))
        st.plotly_chart(fig_bar, use_container_width=True)

        # Export CSV
        csv_export = df_aff.to_csv(index=False).encode("utf-8")
        st.download_button("📥 Exporter l'historique complet (CSV)", csv_export, "historique_affectations.csv", "text/csv")


# ══════════════════════════════════════════════════════════════════
# TAB 3 — NOUVELLE AFFECTATION
# ══════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("### ➕ Créer ou Initialiser une Affectation")
    st.markdown('<div class="form-card">', unsafe_allow_html=True)

    col_f1, col_f2 = st.columns(2)

    with col_f1:
        st.markdown("#### 👤 Livreur")
        mode_livreur = st.radio("Source livreur", ["Sélectionner existant", "Saisir manuellement"], horizontal=True, key="new_aff_mode")
        if mode_livreur == "Sélectionner existant":
            choix_livreur = st.selectbox("Livreur", all_livreurs if all_livreurs else ["(aucun livreur enregistré)"], key="new_aff_livreur_sel")
            nom_livreur_final = choix_livreur
        else:
            nom_livreur_final = st.text_input("Nom complet du livreur", placeholder="ex: Rachid B.", key="new_aff_livreur_txt")

        # Afficher affectation actuelle si existe
        if nom_livreur_final:
            aff_actuelle = get_secteur_actuel(nom_livreur_final, df_aff)
            if aff_actuelle:
                st.markdown(f"""
                <div class="alert-warning">
                    ⚠️ Ce livreur a déjà une affectation active : <b>{aff_actuelle}</b><br>
                    <small>Elle sera automatiquement clôturée si vous validez une nouvelle affectation.</small>
                </div>
                """, unsafe_allow_html=True)

    with col_f2:
        st.markdown("#### 🗺️ Secteur / Région")
        secteur_options_new = secteurs_base if secteurs_base else [
            "ALGER", "BLIDA", "TIPAZA", "BOUMERDES", "MEDEA",
            "TIZI OUZOU", "BEJAIA", "JIJEL", "SETIF", "ANNABA"
        ]
        secteur_choisi = st.selectbox("Secteur (liste)", secteur_options_new, key="new_aff_secteur_sel")
        secteur_libre   = st.text_input("Ou saisir un secteur personnalisé", placeholder="ex: CONSTANTINE", key="new_aff_secteur_txt")
        secteur_final   = secteur_libre.strip() if secteur_libre.strip() else secteur_choisi

        date_effet = st.date_input("📅 Date de prise d'effet", value=datetime.now().date(), key="new_aff_date")
        st.caption("La date de prise d'effet est enregistrée mais l'affectation devient active immédiatement.")

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("")
    col_btn1, col_btn2 = st.columns([3, 1])

    with col_btn2:
        btn_creer = st.button("✅ Créer l'Affectation", type="primary", use_container_width=True, key="btn_creer_aff")

    if btn_creer:
        if not nom_livreur_final or nom_livreur_final.strip() in ["", "(aucun livreur enregistré)"]:
            st.error("❌ Veuillez sélectionner ou saisir un nom de livreur.")
        elif not secteur_final:
            st.error("❌ Veuillez choisir ou saisir un secteur.")
        else:
            admin_user = st.session_state.get("current_user", {}).get("username", "admin")
            df_aff = affecter_livreur(nom_livreur_final.strip(), secteur_final, admin_user, df_aff)
            save_affectations(df_aff)
            st.success(f"🎉 Affectation créée ! **{nom_livreur_final}** → **{secteur_final}** (depuis le {date_effet.strftime('%d/%m/%Y')})")
            st.info("💡 Les nouvelles expéditions attribuées à ce livreur utiliseront automatiquement ce secteur.")
            st.rerun()

    # Résumé des affectations actives
    st.markdown("---")
    st.markdown("#### 📋 Récapitulatif des Affectations Actuelles")
    assignments = get_all_current_assignments(df_aff)
    if assignments:
        df_recap = pd.DataFrame(list(assignments.items()), columns=["Livreur", "Secteur Actif"])
        st.dataframe(df_recap.sort_values("Livreur"), use_container_width=True, hide_index=True)
    else:
        st.info("Aucune affectation active enregistrée.")
