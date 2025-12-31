"""
Study Overview View
"""
import streamlit as st
from typing import Dict
from .components import render_risk_badge, render_issue_table, render_site_risk_chart, render_category_distribution


def render_study_overview(study_analysis: Dict) -> None:
    """Render the study overview page."""
    study_id = study_analysis.get("study_id", "Unknown")
    study_risk = study_analysis.get("study_risk", {})
    
    # Header with risk badge
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"## Study {study_id} Overview")
    with col2:
        render_risk_badge(study_risk.get("risk_level", "Unknown"))
    
    st.markdown("---")
    
    # Key Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Sites", study_risk.get("total_sites", 0))
    with col2:
        st.metric("High Risk Sites", study_risk.get("high_risk_sites", 0),
                 delta=None if study_risk.get("high_risk_sites", 0) == 0 else "⚠️")
    with col3:
        st.metric("Quality Issues", study_analysis.get("quality_issues", {}).get("total_issues", 0))
    with col4:
        st.metric("Operational Issues", study_analysis.get("operational_issues", {}).get("total_issues", 0))
    
    st.markdown("---")
    
    # Two column layout
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Site Risk Distribution")
        site_risks = study_analysis.get("site_risks", {})
        render_site_risk_chart(site_risks)
    
    with col2:
        st.markdown("### File Categories")
        categories = study_analysis.get("categories", {})
        render_category_distribution(categories)
    
    st.markdown("---")
    
    # Contributing Factors
    st.markdown("### Contributing Factors")
    factors = study_risk.get("contributing_factors", [])
    if factors:
        for factor in factors:
            st.markdown(f"- {factor}")
    else:
        st.info("No significant risk factors identified.")
    
    st.markdown("---")
    
    # Issues Summary Tabs
    tab1, tab2 = st.tabs(["Data Quality Issues", "Operational Issues"])
    
    with tab1:
        quality_issues = study_analysis.get("quality_issues", {}).get("issues", [])
        render_issue_table(quality_issues)
    
    with tab2:
        operational_issues = study_analysis.get("operational_issues", {}).get("issues", [])
        render_issue_table(operational_issues)
