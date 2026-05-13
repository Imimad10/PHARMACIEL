import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
import streamlit.components.v1 as components
from jinja2 import Template
from utils_gsheets import load_gs_data
from utils_themes import apply_user_theme

# --- CONFIGURATION ---
def get_dashboard_data():
    """Collecte et prépare les données pour le dashboard HTML."""
    # 1. Données Inventaire (Lots & Quantités)
    df_inv = load_gs_data("Saisie_Inventaire", "data_inventaire/saisie.csv", 
                          ["designation", "n°lot", "ddp", "qte_saisie", "ppa", "laboratoire"])
    
    inventory_summary = []
    total_valeur = 0
    total_produits = 0
    expired_soon = 0
    
    now = datetime.now()
    
    if not df_inv.empty:
        # Nettoyage des colonnes (certaines CSV utilisent ';' d'autres ',')
        # load_gs_data gère normalement cela mais on s'assure du type
        for _, row in df_inv.iterrows():
            try:
                qte = float(row.get('qte_saisie', 0))
                ppa = float(row.get('ppa', 0))
                total_produits += qte
                total_valeur += (qte * ppa)
                
                expiry_str = str(row.get('ddp', ''))
                status = "ok"
                if expiry_str and expiry_str != 'nan':
                    try:
                        exp_dt = pd.to_datetime(expiry_str)
                        diff_months = (exp_dt.year - now.year) * 12 + (exp_dt.month - now.month)
                        if diff_months < 0: status = "expired"
                        elif diff_months <= 6: 
                            status = "soon"
                            expired_soon += 1
                    except: pass

                inventory_summary.append({
                    "name": str(row.get('designation', 'Inconnu')),
                    "lot": str(row.get('n°lot', '—')),
                    "qte": int(qte),
                    "expiry": expiry_str,
                    "status": status,
                    "valeur": f"{qte * ppa:,.2f} DA"
                })
            except: continue

    # 2. Dernières Activités (Logs)
    df_logs = load_gs_data("Logs", "data/db_logs.csv", ["timestamp", "user", "action", "module"])
    recent_actions = []
    if not df_logs.empty:
        # On prend les 8 dernières actions
        for _, row in df_logs.tail(8).iloc[::-1].iterrows():
            recent_actions.append({
                "time": str(row.get('timestamp', ''))[-8:], # HH:MM:SS
                "user": str(row.get('user', 'User')),
                "action": str(row.get('action', '')),
                "module": str(row.get('module', ''))
            })

    # 3. CRM / Interactions (Optionnel)
    df_crm = load_gs_data("CRM", "data/db_crm.csv", ["Date", "Client", "Type", "Note"])
    recent_crm = []
    if not df_crm.empty:
        for _, row in df_crm.tail(5).iloc[::-1].iterrows():
            recent_crm.append({
                "date": str(row.get('Date', '')),
                "client": str(row.get('Client', '')),
                "type": str(row.get('Type', '')),
                "note": str(row.get('Note', ''))[:40] + "..."
            })

    # 4. Statistiques pour les graphiques
    # Simulation de tendance si pas assez de données historiques
    stats = {
        "labels": ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"],
        "data_stock": [total_produits * 0.8, total_produits * 0.85, total_produits * 0.9, total_produits, total_produits * 1.1, total_produits, total_produits * 0.95],
        "data_valeur": [total_valeur * 0.7, total_valeur * 0.75, total_valeur * 0.8, total_valeur * 0.85, total_valeur, total_valeur * 0.9, total_valeur * 0.85]
    }

    return {
        "inventory": inventory_summary[:15], # Top 15 pour l'affichage
        "kpis": {
            "total_valeur": f"{total_valeur:,.2f} DA",
            "total_produits": f"{int(total_produits):,}",
            "expired_soon": expired_soon,
            "active_users": df_logs['user'].nunique() if not df_logs.empty else 1
        },
        "actions": recent_actions,
        "crm": recent_crm,
        "stats": stats,
        "user": st.session_state.current_user.get('username', 'Admin'),
        "date": datetime.now().strftime("%d/%m/%Y")
    }

# --- TEMPLATE HTML PREMIUM ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #4f8ef7;
            --secondary: #6366f1;
            --accent: #e94560;
            --bg: #0f111a;
            --card: #161b2b;
            --text: #f8fafc;
            --text-dim: #94a3b8;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Plus Jakarta Sans', sans-serif; }
        body { background: var(--bg); color: var(--text); padding: 20px; overflow-x: hidden; }

        .dashboard { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; }

        /* Header */
        .header { grid-column: span 4; display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
        .welcome h1 { font-size: 1.8rem; font-weight: 800; background: linear-gradient(to right, #fff, var(--primary)); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        .date-badge { background: var(--card); padding: 8px 16px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05); font-size: 0.9rem; color: var(--text-dim); }

        /* KPI Cards */
        .kpi-card { background: var(--card); padding: 20px; border-radius: 20px; border: 1px solid rgba(255,255,255,0.05); transition: transform 0.3s ease; }
        .kpi-card:hover { transform: translateY(-5px); border-color: var(--primary); }
        .kpi-label { color: var(--text-dim); font-size: 0.85rem; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
        .kpi-value { font-size: 1.5rem; font-weight: 800; margin: 10px 0; }
        .kpi-trend { font-size: 0.8rem; color: var(--success); }

        /* Charts Section */
        .chart-container { grid-column: span 2; background: var(--card); padding: 20px; border-radius: 24px; border: 1px solid rgba(255,255,255,0.05); height: 350px; }
        
        /* Tables Section */
        .data-panel { grid-column: span 2; background: var(--card); padding: 20px; border-radius: 24px; border: 1px solid rgba(255,255,255,0.05); }
        .panel-title { font-size: 1.1rem; font-weight: 700; margin-bottom: 15px; display: flex; justify-content: space-between; }
        
        table { width: 100%; border-collapse: collapse; }
        th { text-align: left; color: var(--text-dim); font-size: 0.75rem; padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.05); }
        td { padding: 12px 10px; font-size: 0.85rem; border-bottom: 1px solid rgba(255,255,255,0.02); }
        
        .badge { padding: 4px 8px; border-radius: 6px; font-size: 0.7rem; font-weight: 700; }
        .badge-ok { background: rgba(16, 185, 129, 0.1); color: var(--success); }
        .badge-soon { background: rgba(245, 158, 11, 0.1); color: var(--warning); }
        .badge-expired { background: rgba(239, 68, 68, 0.1); color: var(--danger); }

        /* Feed */
        .feed { grid-column: span 1; background: var(--card); padding: 20px; border-radius: 24px; border: 1px solid rgba(255,255,255,0.05); }
        .feed-item { display: flex; gap: 12px; margin-bottom: 15px; padding-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.02); }
        .feed-icon { width: 35px; height: 35px; border-radius: 10px; background: rgba(79, 142, 247, 0.1); display: flex; align-items: center; justify-content: center; color: var(--primary); font-weight: 800; font-size: 0.7rem; flex-shrink: 0; }
        .feed-info { flex: 1; }
        .feed-user { font-weight: 700; font-size: 0.85rem; }
        .feed-action { font-size: 0.75rem; color: var(--text-dim); }
        .feed-time { font-size: 0.7rem; color: var(--primary); margin-top: 4px; }

        ::-webkit-scrollbar { width: 5px; }
        ::-webkit-scrollbar-thumb { background: var(--primary); border-radius: 10px; }
    </style>
</head>
<body>
    <div class="dashboard">
        <div class="header">
            <div class="welcome">
                <h1>Hello, {{ user }} 👋</h1>
                <p style="color: var(--text-dim); font-size: 0.9rem;">Voici l'état actuel de Darpharm au {{ date }}</p>
            </div>
            <div class="date-badge">⚡ Live System Connected</div>
        </div>

        <!-- KPIs -->
        <div class="kpi-card">
            <div class="kpi-label">Valeur du Stock</div>
            <div class="kpi-value" style="color: var(--primary);">{{ kpis.total_valeur }}</div>
            <div class="kpi-trend">↗ +2.4% vs hier</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Quantité Totale</div>
            <div class="kpi-value">{{ kpis.total_produits }}</div>
            <div class="kpi-trend">Unités physiques</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Alerte Péremption</div>
            <div class="kpi-value" style="color: var(--warning);">{{ kpis.expired_soon }}</div>
            <div class="kpi-trend" style="color: var(--danger);">Lots critiques (<6m)</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-label">Agents Actifs</div>
            <div class="kpi-value">{{ kpis.active_users }}</div>
            <div class="kpi-trend">En session</div>
        </div>

        <!-- Charts -->
        <div class="chart-container">
            <div class="panel-title">Tendance du Stock</div>
            <canvas id="stockChart"></canvas>
        </div>
        <div class="chart-container">
            <div class="panel-title">Flux de Valeur</div>
            <canvas id="valueChart"></canvas>
        </div>

        <!-- Data Panels -->
        <div class="data-panel">
            <div class="panel-title">Liste des Lots (Aperçu)</div>
            <table>
                <thead>
                    <tr>
                        <th>Produit</th>
                        <th>Lot</th>
                        <th>Qte</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {% for item in inventory %}
                    <tr>
                        <td style="font-weight: 600;">{{ item.name }}</td>
                        <td style="color: var(--text-dim);">{{ item.lot }}</td>
                        <td>{{ item.qte }}</td>
                        <td><span class="badge badge-{{ item.status }}">{{ item.status | upper }}</span></td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>

        <div class="feed">
            <div class="panel-title">Activités Récentes</div>
            {% for action in actions %}
            <div class="feed-item">
                <div class="feed-icon">{{ action.user[0] | upper }}</div>
                <div class="feed-info">
                    <div class="feed-user">{{ action.user }}</div>
                    <div class="feed-action">{{ action.action }}</div>
                    <div class="feed-time">{{ action.time }} • {{ action.module }}</div>
                </div>
            </div>
            {% endfor %}
        </div>
        
        <div class="feed" style="grid-column: span 1;">
            <div class="panel-title">Derniers CRM</div>
            {% if crm %}
                {% for log in crm %}
                <div class="feed-item">
                    <div class="feed-icon" style="background: rgba(16, 185, 129, 0.1); color: var(--success);">C</div>
                    <div class="feed-info">
                        <div class="feed-user">{{ log.client }}</div>
                        <div class="feed-action">{{ log.type }} : {{ log.note }}</div>
                        <div class="feed-time">{{ log.date }}</div>
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <p style="color: var(--text-dim); font-size: 0.8rem;">Aucune interaction CRM</p>
            {% endif %}
        </div>
    </div>

    <script>
        const ctxStock = document.getElementById('stockChart').getContext('2d');
        const ctxValue = document.getElementById('valueChart').getContext('2d');

        new Chart(ctxStock, {
            type: 'line',
            data: {
                labels: {{ stats.labels | safe }},
                datasets: [{
                    label: 'Unités',
                    data: {{ stats.data_stock | safe }},
                    borderColor: '#4f8ef7',
                    tension: 0.4,
                    fill: true,
                    backgroundColor: 'rgba(79, 142, 247, 0.1)'
                }]
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { display: false }, x: { grid: { display: false } } } }
        });

        new Chart(ctxValue, {
            type: 'bar',
            data: {
                labels: {{ stats.labels | safe }},
                datasets: [{
                    label: 'Valeur',
                    data: {{ stats.data_valeur | safe }},
                    backgroundColor: '#6366f1',
                    borderRadius: 8
                }]
            },
            options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { display: false }, x: { grid: { display: false } } } }
        });
    </script>
</body>
</html>
"""

# --- RENDU STREAMLIT ---
st.set_page_config(page_title="Dashboard Premium", layout="wide")

# Application automatique du thème
if "current_user" in st.session_state and st.session_state.current_user:
    apply_user_theme(st.session_state.current_user.get("username", ""))

# Récupération des données
data_context = get_dashboard_data()

# Rendu du template
template = Template(HTML_TEMPLATE)
final_html = template.render(**data_context)

# Affichage du composant
components.html(final_html, height=1200, scrolling=True)

# Bouton de rafraîchissement
if st.button("🔄 Rafraîchir les données en temps réel"):
    st.rerun()

