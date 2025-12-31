"""
AI Q&A Interface View
"""
import streamlit as st
from typing import Dict
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ai.explainer import AIExplainer
from ai.recommender import Recommender


def render_qa_interface(study_analysis: Dict) -> None:
    """Render the AI Q&A interface."""
    st.markdown("## AI-Powered Insights")
    st.markdown("_Ask questions about the study data. AI provides read-only explanations._")
    
    explainer = AIExplainer()
    recommender = Recommender()
    
    # Quick question buttons
    st.markdown("### Quick Questions")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔍 Why is this study high risk?", use_container_width=True):
            st.session_state.ai_question = "Why is this study high risk?"
    with col2:
        if st.button("🏥 Which sites need attention?", use_container_width=True):
            st.session_state.ai_question = "Which sites need attention?"
    with col3:
        if st.button("📋 What are the quality issues?", use_container_width=True):
            st.session_state.ai_question = "What are the data quality issues?"
    
    st.markdown("---")
    
    # Custom question input
    question = st.text_input(
        "Or ask your own question:",
        value=st.session_state.get("ai_question", ""),
        placeholder="e.g., What are the main operational concerns?"
    )
    
    if question:
        st.markdown("---")
        st.markdown("### AI Response")
        
        with st.spinner("Analyzing..."):
            response = explainer.answer_question(question, study_analysis)
        
        st.markdown(response)
    
    st.markdown("---")
    
    # Role-based Recommendations
    st.markdown("### Role-Based Recommendations")
    st.markdown("_Advisory only - no actions are auto-executed._")
    
    role = st.selectbox("Select Your Role", ["Management", "CTT", "CRA"])
    
    if st.button("Generate Recommendations", type="primary"):
        with st.spinner("Generating recommendations..."):
            recs = recommender.generate_recommendations(study_analysis, role)
            formatted = recommender.format_recommendations(recs)
        
        st.markdown(formatted)
    
    st.markdown("---")
    
    # Explainability Note
    with st.expander("ℹ️ About AI Explainability"):
        st.markdown("""
        **This AI system is read-only and provides:**
        - Explanations of risk levels and their drivers
        - Summaries of data quality and operational issues
        - Role-aware advisory recommendations
        
        **The AI does NOT:**
        - Modify any data
        - Trigger automated actions
        - Make decisions on your behalf
        
        All insights are derived from the analyzed study data and rule-based logic.
        """)
