"""
Site Drill-down View
"""
import streamlit as st
from typing import Dict, List
from .components import render_risk_badge, render_issue_table, render_severity_badge


def render_site_drilldown(study_analysis: Dict) -> None:
    """Render the site drill-down page."""
    site_risks = study_analysis.get("site_risks", {})
    quality_by_site = study_analysis.get("quality_issues", {}).get("by_site", {})
    operational_by_site = study_analysis.get("operational_issues", {}).get("by_site", {})
    
    if not site_risks:
        st.info("No site data available for this study.")
        return
    
    st.markdown("## Site Risk Analysis")
    
    # Site selector
    site_options = sorted(site_risks.keys(), key=lambda x: site_risks[x].get("weighted_score", 0), reverse=True)
    
    # Show high-risk sites first in selector
    selected_site = st.selectbox(
        "Select Site",
        site_options,
        format_func=lambda x: f"Site {x} - {site_risks[x].get('risk_level', 'Unknown')}"
    )
    
    if selected_site:
        site_data = site_risks.get(selected_site, {})
        
        st.markdown("---")
        
        # Site header
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### Site {selected_site}")
        with col2:
            render_risk_badge(site_data.get("risk_level", "Unknown"))
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Risk Score", round(site_data.get("weighted_score", 0), 1))
        with col2:
            st.metric("Quality Score", site_data.get("quality_score", 0))
        with col3:
            st.metric("Operational Score", site_data.get("operational_score", 0))
        with col4:
            st.metric("High Severity", site_data.get("high_severity_count", 0))
        
        st.markdown("---")
        
        # Contributing Factors
        st.markdown("### Why This Risk Level?")
        factors = site_data.get("contributing_factors", [])
        if factors:
            for factor in factors:
                st.markdown(f"- {factor}")
        else:
            st.success("No significant issues at this site.")
        
        st.markdown("---")
        
        # Issues for this site
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### Data Quality Issues")
            site_quality = quality_by_site.get(selected_site, [])
            if site_quality:
                render_issue_table(site_quality)
            else:
                st.success("No data quality issues.")
        
        with col2:
            st.markdown("### Operational Issues")
            site_operational = operational_by_site.get(selected_site, [])
            if site_operational:
                render_issue_table(site_operational)
            else:
                st.success("No operational issues.")
    
    st.markdown("---")
    
    # All Sites Summary Table
    st.markdown("### All Sites Summary")
    render_sites_summary_table(site_risks)


def render_sites_summary_table(site_risks: Dict) -> None:
    """Render a summary table of all sites."""
    html = '''
    <style>
        .sites-table { width: 100%; border-collapse: collapse; font-size: 14px; }
        .sites-table th { background: #1e293b; color: white; padding: 10px; text-align: left; }
        .sites-table td { padding: 8px; border-bottom: 1px solid #e2e8f0; }
        .sites-table tr:hover { background: #f1f5f9; }
    </style>
    <table class="sites-table">
        <tr>
            <th>Site</th>
            <th>Risk Level</th>
            <th>Score</th>
            <th>Quality Issues</th>
            <th>Operational Issues</th>
        </tr>
    '''
    
    # Sort by risk score
    sorted_sites = sorted(site_risks.items(), key=lambda x: x[1].get("weighted_score", 0), reverse=True)
    
    for site_id, data in sorted_sites:
        risk_level = data.get("risk_level", "Unknown")
        color = {"High Risk": "#dc2626", "Medium Risk": "#f97316", "Low Risk": "#16a34a"}.get(risk_level, "#6b7280")
        
        html += f'''
        <tr>
            <td><strong>Site {site_id}</strong></td>
            <td><span style="background-color: {color}; color: white; padding: 2px 8px; border-radius: 4px;">{risk_level}</span></td>
            <td>{round(data.get("weighted_score", 0), 1)}</td>
            <td>{data.get("quality_issue_count", 0)}</td>
            <td>{data.get("operational_issue_count", 0)}</td>
        </tr>
        '''
    
    html += '</table>'
    st.markdown(html, unsafe_allow_html=True)
