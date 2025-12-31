"""
Reusable UI Components
"""
import streamlit as st
from typing import Dict, List
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import SEVERITY_COLORS, RISK_COLORS


def render_risk_badge(risk_level: str) -> None:
    """Render a colored risk badge."""
    color = RISK_COLORS.get(risk_level, "#6b7280")
    st.markdown(
        f'<span style="background-color: {color}; color: white; padding: 4px 12px; '
        f'border-radius: 16px; font-weight: 600; font-size: 14px;">{risk_level}</span>',
        unsafe_allow_html=True
    )


def render_metric_card(title: str, value: str, delta: str = None, color: str = None) -> None:
    """Render a metric card with optional delta."""
    st.metric(label=title, value=value, delta=delta)


def render_severity_badge(severity: str) -> str:
    """Return HTML for a severity badge."""
    color = SEVERITY_COLORS.get(severity, "#6b7280")
    return f'<span style="background-color: {color}; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px;">{severity}</span>'


def render_issue_table(issues: List[Dict], max_rows: int = 10) -> None:
    """Render a table of issues."""
    if not issues:
        st.info("No issues found.")
        return
    
    # Build table HTML
    html = '''
    <style>
        .issue-table { width: 100%; border-collapse: collapse; font-size: 14px; }
        .issue-table th { background: #1e293b; color: white; padding: 10px; text-align: left; }
        .issue-table td { padding: 8px; border-bottom: 1px solid #e2e8f0; }
        .issue-table tr:hover { background: #f1f5f9; }
    </style>
    <table class="issue-table">
        <tr>
            <th>Severity</th>
            <th>Type</th>
            <th>Description</th>
            <th>Count</th>
        </tr>
    '''
    
    for issue in issues[:max_rows]:
        severity_badge = render_severity_badge(issue.get("severity", "Low"))
        issue_type = issue.get("type", "").replace("_", " ").title()
        description = issue.get("description", "")
        count = issue.get("count", "-")
        
        html += f'''
        <tr>
            <td>{severity_badge}</td>
            <td>{issue_type}</td>
            <td>{description}</td>
            <td>{count}</td>
        </tr>
        '''
    
    html += '</table>'
    
    if len(issues) > max_rows:
        html += f'<p style="color: #64748b; font-size: 12px;">Showing {max_rows} of {len(issues)} issues</p>'
    
    st.markdown(html, unsafe_allow_html=True)


def render_site_risk_chart(site_risks: Dict) -> None:
    """Render a chart showing site risk distribution."""
    import plotly.express as px
    import pandas as pd
    
    if not site_risks:
        st.info("No site data available.")
        return
    
    # Prepare data
    data = []
    for site_id, risk_data in site_risks.items():
        data.append({
            "Site": site_id,
            "Risk Level": risk_data.get("risk_level", "Unknown"),
            "Score": risk_data.get("weighted_score", 0),
            "Quality Issues": risk_data.get("quality_issue_count", 0),
            "Operational Issues": risk_data.get("operational_issue_count", 0)
        })
    
    df = pd.DataFrame(data)
    
    # Color mapping
    color_map = {"High Risk": "#dc2626", "Medium Risk": "#f97316", "Low Risk": "#16a34a"}
    
    fig = px.bar(
        df, x="Site", y="Score",
        color="Risk Level",
        color_discrete_map=color_map,
        title="Site Risk Scores",
        hover_data=["Quality Issues", "Operational Issues"]
    )
    fig.update_layout(
        xaxis_tickangle=-45,
        height=400,
        showlegend=True,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_category_distribution(categories: Dict) -> None:
    """Render a pie chart of file categories."""
    import plotly.express as px
    import pandas as pd
    
    data = [{"Category": cat, "Count": len(files)} for cat, files in categories.items()]
    df = pd.DataFrame(data)
    
    fig = px.pie(
        df, values="Count", names="Category",
        title="Files by Category",
        color_discrete_sequence=px.colors.qualitative.Set2
    )
    fig.update_layout(height=300)
    
    st.plotly_chart(fig, use_container_width=True)
