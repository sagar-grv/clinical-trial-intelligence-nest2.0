"""
Clinical Trial Intelligence System - Enterprise Edition
A Streamlit-based dashboard with database storage and Gemini AI integration
"""
import streamlit as st
import sys
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from database.storage import DatabaseStorage
from database.models import ProcessingStatus, AnalysisStatus, init_database
from core.pipeline import ProcessingPipeline
from core.worker import start_async_analysis, AnalysisWorker
from ai.gemini_client import GeminiClient

# Initialize database on startup
init_database("database/clinical_trials.db")

# Page configuration
st.set_page_config(
    page_title="Clinical Trial Intelligence",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize theme in session state
if "theme" not in st.session_state:
    st.session_state.theme = "dark"  # Default theme

# Theme color schemes
THEMES = {
    "light": {
        "bg": "#ffffff",
        "bg_secondary": "#f8fafc",
        "text": "#1e293b",
        "text_muted": "#64748b",
        "sidebar_bg": "linear-gradient(180deg, #0f172a 0%, #1e293b 100%)",
        "sidebar_text": "#ffffff",
        "card_bg": "linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)",
        "card_shadow": "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
        "table_header": "#1e293b",
        "table_row_hover": "#f8fafc",
        "border": "#e2e8f0",
        "accent": "#3b82f6",
        "tab_bg": "#f1f5f9",
    },
    "dark": {
        "bg": "#0f172a",
        "bg_secondary": "#1e293b",
        "text": "#f1f5f9",
        "text_muted": "#94a3b8",
        "sidebar_bg": "linear-gradient(180deg, #020617 0%, #0f172a 100%)",
        "sidebar_text": "#ffffff",
        "card_bg": "linear-gradient(135deg, #1e293b 0%, #334155 100%)",
        "card_shadow": "0 4px 6px -1px rgba(0, 0, 0, 0.3)",
        "table_header": "#334155",
        "table_row_hover": "#1e293b",
        "border": "#334155",
        "accent": "#60a5fa",
        "tab_bg": "#1e293b",
    },
    "blue": {
        "bg": "#0c1929",
        "bg_secondary": "#112240",
        "text": "#ccd6f6",
        "text_muted": "#8892b0",
        "sidebar_bg": "linear-gradient(180deg, #0a192f 0%, #112240 100%)",
        "sidebar_text": "#64ffda",
        "card_bg": "linear-gradient(135deg, #112240 0%, #1d3a5c 100%)",
        "card_shadow": "0 4px 20px rgba(2, 12, 27, 0.7)",
        "table_header": "#1d3a5c",
        "table_row_hover": "#112240",
        "border": "#233554",
        "accent": "#64ffda",
        "tab_bg": "#112240",
    }
}

# Get current theme colors
theme = THEMES[st.session_state.theme]

# Custom CSS with theme support
st.markdown(f"""
<style>
    /* Main container */
    .main .block-container {{
        padding-top: 2rem;
        padding-bottom: 2rem;
    }}
    
    .stApp {{
        background-color: {theme['bg']};
    }}
    
    .stMarkdown, p, span {{
        color: {theme['text']};
    }}
    
    /* Headers */
    h1, h2, h3 {{
        color: {theme['text']};
    }}
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {{
        background: {theme['sidebar_bg']};
    }}
    [data-testid="stSidebar"] .stMarkdown {{
        color: {theme['sidebar_text']};
    }}
    [data-testid="stSidebar"] h1, 
    [data-testid="stSidebar"] h2, 
    [data-testid="stSidebar"] h3 {{
        color: {theme['sidebar_text']};
    }}
    [data-testid="stSidebar"] p {{
        color: {theme['sidebar_text']};
    }}
    
    /* Metrics */
    [data-testid="stMetricValue"] {{
        font-size: 2rem;
        font-weight: 700;
        color: {theme['text']};
    }}
    [data-testid="stMetricLabel"] {{
        color: {theme['text_muted']};
    }}
    
    /* Cards */
    .stMetric {{
        background: {theme['card_bg']};
        padding: 1rem;
        border-radius: 12px;
        box-shadow: {theme['card_shadow']};
    }}
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
    }}
    .stTabs [data-baseweb="tab"] {{
        background-color: {theme['tab_bg']};
        border-radius: 8px;
        padding: 8px 16px;
        color: {theme['text']};
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {theme['accent']};
        color: white;
    }}
    
    /* Upload area */
    .uploadedFile {{
        background: {theme['bg_secondary']};
        border: 2px dashed {theme['accent']};
        border-radius: 12px;
        padding: 20px;
    }}
    
    /* Risk badges */
    .risk-high {{ background: #ef4444; color: white; padding: 4px 12px; border-radius: 20px; }}
    .risk-medium {{ background: #f59e0b; color: white; padding: 4px 12px; border-radius: 20px; }}
    .risk-low {{ background: #22c55e; color: white; padding: 4px 12px; border-radius: 20px; }}
    
    /* Table styling */
    .data-table {{ width: 100%; border-collapse: collapse; font-size: 14px; margin-top: 10px; }}
    .data-table th {{ background: {theme['table_header']}; color: white; padding: 12px; text-align: left; }}
    .data-table td {{ padding: 10px; border-bottom: 1px solid {theme['border']}; color: {theme['text']}; }}
    .data-table tr:hover {{ background: {theme['table_row_hover']}; }}
    
    /* Buttons */
    .stButton button {{
        border-radius: 8px;
    }}
    
    /* Expander */
    .streamlit-expanderHeader {{
        background: {theme['bg_secondary']};
        color: {theme['text']};
        border-radius: 8px;
    }}
    
    /* Info/Success/Warning/Error boxes */
    .stAlert {{
        border-radius: 8px;
    }}
    
    /* Hide Streamlit branding */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_storage():
    """Initialize and cache database storage."""
    return DatabaseStorage("database/clinical_trials.db")


@st.cache_resource
def get_pipeline():
    """Initialize and cache processing pipeline."""
    return ProcessingPipeline("database/clinical_trials.db")


def get_gemini(api_key: str = None):
    """Initialize Gemini client with optional API key."""
    # Check session state for API key first
    if api_key is None:
        api_key = st.session_state.get("gemini_api_key")
    
    return GeminiClient(api_key=api_key)


def render_file_upload():
    """Render file upload interface with study selection."""
    st.markdown("## 📤 Upload Clinical Trial Files")
    st.markdown("Upload Excel files (.xlsx, .xls) to a clinical trial study.")
    
    storage = get_storage()
    pipeline = get_pipeline()
    
    # Study Selection Section
    st.markdown("### 📋 Select or Create Study")
    
    studies = storage.get_all_studies()
    study_options = ["➕ Create New Study"] + [s.study_name for s in studies]
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        selected_study_option = st.selectbox("Choose Study", study_options)
    
    with col2:
        if selected_study_option == "➕ Create New Study":
            new_study_name = st.text_input("New Study Name", placeholder="e.g., PROTOCOL-2024-001")
        else:
            new_study_name = None
    
    st.markdown("---")
    
    # File Upload Section
    uploaded_files = st.file_uploader(
        "Drag and drop files here",
        type=["xlsx", "xls"],
        accept_multiple_files=True,
        help="All files will be assigned to the selected study."
    )
    
    if uploaded_files:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{len(uploaded_files)} file(s) selected**")
        
        with col2:
            if st.button("🚀 Process All", type="primary"):
                # Determine study
                if selected_study_option == "➕ Create New Study":
                    if not new_study_name:
                        st.error("Please enter a study name")
                        return
                    study = storage.create_study(new_study_name)
                else:
                    study = storage.get_study_by_name(selected_study_option)
                
                if not study:
                    st.error("Failed to create/find study")
                    return
                
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, uploaded_file in enumerate(uploaded_files):
                    status_text.text(f"Processing {uploaded_file.name}...")
                    
                    # Read file bytes
                    file_bytes = uploaded_file.read()
                    
                    # Save to database WITH STUDY ID
                    file_record = storage.save_uploaded_file(
                        filename=uploaded_file.name,
                        file_bytes=file_bytes
                    )
                    
                    # Assign to study
                    storage.assign_file_to_study(file_record.file_id, study.study_id)
                    
                    # Process file
                    result = pipeline.process_file(file_record.file_id)
                    
                    progress_bar.progress((i + 1) / len(uploaded_files))
                
                status_text.text("✅ All files processed!")
                
                st.success(f"✅ Successfully processed {len(uploaded_files)} file(s) for study '{study.study_name}'")
                
                # Start Async Analysis
                status_text.text("🚀 Starting background analysis...")
                start_async_analysis(study.study_id)
                st.info("Analysis queued in background. You can navigate away.")
                
                st.session_state["selected_study_id"] = study.study_id
        
        # Show file preview
        st.markdown("### 📋 Selected Files")
        for f in uploaded_files:
            with st.expander(f"📄 {f.name} ({f.size / 1024:.1f} KB)"):
                try:
                    xl = pd.ExcelFile(f)
                    st.markdown(f"**Sheets:** {', '.join(xl.sheet_names)}")
                except:
                    st.markdown("_Preview not available_")


def render_files_list():
    """Render list of uploaded files."""
    st.markdown("## 📁 Uploaded Files")
    
    storage = get_storage()
    files = storage.get_all_files()
    
    if not files:
        st.info("No files uploaded yet. Use the Upload tab to add files.")
        return
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    summary = storage.get_system_summary()
    
    with col1:
        st.metric("Total Files", summary["total_files"])
    with col2:
        st.metric("Tables Extracted", summary["total_tables"])
    with col3:
        st.metric("Issues Detected", summary["total_issues"])
    with col4:
        st.metric("Processed", summary["completed_files"])
    
    st.markdown("---")
    
    # Files table
    html = '''<table class="data-table">
        <tr>
            <th>File Name</th>
            <th>Status</th>
            <th>Tables</th>
            <th>Upload Time</th>
            <th>Actions</th>
        </tr>
    '''
    
    status_colors = {
        "completed": "#22c55e",
        "processing": "#3b82f6",
        "pending": "#f59e0b",
        "failed": "#ef4444"
    }
    
    for f in files:
        status = f.processing_status
        color = status_colors.get(status, "#6b7280")
        timestamp = f.upload_timestamp.strftime("%Y-%m-%d %H:%M") if f.upload_timestamp else ""
        table_count = len(f.extracted_tables) if f.extracted_tables else 0
        
        html += f'''
        <tr>
            <td><strong>{f.filename}</strong></td>
            <td><span style="background:{color}; color:white; padding:2px 8px; border-radius:4px;">{status}</span></td>
            <td>{table_count}</td>
            <td>{timestamp}</td>
            <td>
                <a href="?file_id={f.file_id}" style="color:#3b82f6;">View Details</a>
            </td>
        </tr>
        '''
    
    html += '</table>'
    st.markdown(html, unsafe_allow_html=True)
    
    # File selection for detailed view
    st.markdown("---")
    st.markdown("### 🔍 Select File for Details")
    
    file_options = {f.filename: f.file_id for f in files}
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        selected_file = st.selectbox("Choose a file", list(file_options.keys()))
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Spacing
        if st.button("📊 View Analysis", type="primary"):
            if selected_file:
                st.session_state["selected_file_id"] = file_options[selected_file]
                st.rerun()


def render_file_analysis(file_id: int):
    """Render detailed analysis for a specific file."""
    storage = get_storage()
    pipeline = get_pipeline()
    
    analysis = pipeline.get_full_analysis(file_id)
    
    if "error" in analysis:
        st.error(analysis["error"])
        return
    
    file_info = analysis.get("file", {})
    tables_info = analysis.get("tables", {})
    issues_info = analysis.get("issues", {})
    result = analysis.get("analysis", {})
    audit_info = analysis.get("audit")
    
    # Header
    st.markdown(f"## 📊 Analysis: {file_info.get('filename', 'Unknown')}")
    
    # Risk badge
    risk_level = result.get("risk_level", "Unknown") if result else "Pending"
    risk_class = "high" if "High" in risk_level else "medium" if "Medium" in risk_level else "low"
    st.markdown(f'<span class="risk-{risk_class}">{risk_level}</span>', unsafe_allow_html=True)
    
    # Extraction Audit Banner
    if audit_info:
        total_sheets = audit_info.get("total_sheets", 0)
        processed_sheets = audit_info.get("processed_sheets", 0)
        sheets_without = audit_info.get("sheets_without_tables", [])
        warnings = audit_info.get("warnings", [])
        
        # Show completeness status
        if processed_sheets == total_sheets:
            st.success(f"✅ **Extraction Complete**: {processed_sheets}/{total_sheets} sheets processed")
        else:
            st.warning(f"⚠️ **Incomplete Extraction**: {processed_sheets}/{total_sheets} sheets processed")
        
        # Show warnings if any
        if warnings:
            with st.expander(f"⚠️ {len(warnings)} Extraction Warning(s)", expanded=False):
                for w in warnings:
                    st.markdown(f"- {w}")
    
    # Key metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Tables Extracted", tables_info.get("total_tables", 0))
    with col2:
        st.metric("Sheets Processed", tables_info.get("total_sheets", 0))
    with col3:
        st.metric("Total Issues", issues_info.get("total_issues", 0))
    with col4:
        high_sev = issues_info.get("by_severity", {}).get("High", 0)
        st.metric("High Severity", high_sev)
    
    # Tabs for different views
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 Extracted Tables",
        "⚠️ Issues & Traceability",
        "🤖 AI Insights",
        "📈 Summary",
        "🔍 Audit Trail"
    ])
    
    with tab1:
        render_extracted_tables(file_id, tables_info)
    
    with tab2:
        render_issues_traceability(file_id, issues_info)
    
    with tab3:
        render_ai_insights(file_id, analysis)
    
    with tab4:
        render_analysis_summary(analysis)
    
    with tab5:
        render_audit_trail(file_id, audit_info)


def render_extracted_tables(file_id: int, tables_info: Dict):
    """Render extracted tables view."""
    st.markdown("### Tables Extracted from All Sheets")
    
    by_sheet = tables_info.get("by_sheet", {})
    
    if not by_sheet:
        st.info("No tables extracted yet.")
        return
    
    for sheet_name, tables in by_sheet.items():
        with st.expander(f"📄 Sheet: {sheet_name} ({len(tables)} tables)"):
            for table in tables:
                st.markdown(f"**Table {table['table_index'] + 1}** - Type: {table.get('detected_type', 'Unknown')}")
                st.markdown(f"- Rows: {table['row_count']}, Columns: {table['column_count']}")
                st.markdown(f"- Headers: `{', '.join(table.get('headers', [])[:5])}...`" if table.get('headers') else "")
                st.markdown("---")


def render_issues_traceability(file_id: int, issues_info: Dict):
    """Render issues with full traceability and RULE EVIDENCE."""
    st.markdown("### Detected Issues with Traceability")
    
    # Trust badge legend
    st.markdown("""
    **Confidence Badges:** 
    ✅ **Rule-Verified** (deterministic) | 
    ⚠️ **AI-Explained** (advisory) | 
    🧪 **Needs Review** (edge case)
    """)
    
    # Severity breakdown
    by_severity = issues_info.get("by_severity", {})
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown(f"🔴 **High:** {by_severity.get('High', 0)}")
    with col2:
        st.markdown(f"🟡 **Medium:** {by_severity.get('Medium', 0)}")
    with col3:
        st.markdown(f"🟢 **Low:** {by_severity.get('Low', 0)}")
    
    st.markdown("---")
    
    # Issues table with traceability
    issues = issues_info.get("issues", [])
    
    if not issues:
        st.success("✅ No issues detected!")
        return
    
    # Filter
    severity_filter = st.selectbox("Filter by Severity", ["All", "High", "Medium", "Low"])
    
    if severity_filter != "All":
        issues = [i for i in issues if i.get("severity") == severity_filter]
    
    # Confidence badge mapping
    confidence_badges = {
        "rule_verified": "✅",
        "ai_explained": "⚠️",
        "needs_review": "🧪"
    }
    
    # Pagination Logic
    items_per_page = 50
    if "issue_page" not in st.session_state:
        st.session_state.issue_page = 0
    
    total_pages = max(1, (len(issues) - 1) // items_per_page + 1)
    current_page = st.session_state.issue_page
    
    # Reset page if filter changed size
    if current_page >= total_pages:
        current_page = 0
        st.session_state.issue_page = 0
        
    start_idx = current_page * items_per_page
    end_idx = start_idx + items_per_page
    
    paginated_issues = issues[start_idx:end_idx]
    
    html = '''<table class="data-table">
        <tr>
            <th>Trust</th>
            <th>Severity</th>
            <th>Rule ID</th>
            <th>Description</th>
            <th>Trigger</th>
            <th>Sheet</th>
            <th>Site</th>
        </tr>
    '''
    
    severity_colors = {"High": "#ef4444", "Medium": "#f59e0b", "Low": "#22c55e"}
    
    for issue in paginated_issues:
        sev = issue.get("severity", "Low")
        color = severity_colors.get(sev, "#6b7280")
        confidence = issue.get("confidence_level", "rule_verified")
        badge = confidence_badges.get(confidence, "✅")
        rule_id = issue.get("rule_id", "-")
        trigger = issue.get("trigger_condition", "-")
        actual = issue.get("actual_value", "-")
        threshold = issue.get("threshold_value", "-")
        
        # Format trigger with actual value
        trigger_display = f"{trigger}" if trigger != "-" else "-"
        if actual != "-" and actual:
            trigger_display += f" (actual: {actual})"
        
        html += f'''
        <tr>
            <td title="{confidence}">{badge}</td>
            <td><span style="background:{color}; color:white; padding:2px 8px; border-radius:4px;">{sev}</span></td>
            <td><code>{rule_id}</code></td>
            <td>{issue.get("description", "")}</td>
            <td style="font-size:12px;">{trigger_display}</td>
            <td>{issue.get("sheet_name", "-")}</td>
            <td>{issue.get("site_id", "-")}</td>
        </tr>
        '''
    
    html += '</table>'
    st.markdown(html, unsafe_allow_html=True)
    
    # Pagination Controls
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("⬅️ Previous", disabled=current_page == 0):
            st.session_state.issue_page -= 1
            st.rerun()
    with col2:
        st.markdown(f"**Page {current_page + 1} of {total_pages}** ({len(issues)} total issues)", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align: center; color: gray;'>Showing rows {start_idx + 1} - {min(end_idx, len(issues))}</p>", unsafe_allow_html=True)
    with col3:
        if st.button("Next ➡️", disabled=current_page == total_pages - 1):
            st.session_state.issue_page += 1
            st.rerun()
    
    # Rule Evidence Expandable Panel
    with st.expander("📋 **Rule Evidence Details** (Proof Layer)"):
        st.markdown("""
        Each issue is detected by a **deterministic rule**. Below is the evidence for each finding:
        """)
        
        for issue in issues[:10]:
            rule_id = issue.get("rule_id", "Unknown")
            trigger = issue.get("trigger_condition", "N/A")
            threshold = issue.get("threshold_value", "N/A")
            actual = issue.get("actual_value", "N/A")
            sheet = issue.get("sheet_name", "N/A")
            
            st.markdown(f"""
            **Rule: `{rule_id}`**
            - **Condition:** {trigger}
            - **Threshold:** {threshold} | **Actual:** {actual}
            - **Source:** Sheet '{sheet}'
            - **Confidence:** ✅ Rule-Verified (deterministic)
            ---
            """)


def render_ai_insights(file_id: int, analysis: Dict):
    """Render AI-generated insights."""
    st.markdown("### 🤖 AI-Powered Insights")
    
    gemini = get_gemini()
    pipeline = get_pipeline()
    
    # Build analytics JSON for Gemini
    tables_info = analysis.get("tables", {})
    issues_info = analysis.get("issues", {})
    result = analysis.get("analysis", {})
    
    analytics_json = {
        "file_id": file_id,
        "total_tables": tables_info.get("total_tables", 0),
        "total_sheets": tables_info.get("total_sheets", 0),
        "table_types": tables_info.get("by_type", {}),
        "risk_level": result.get("risk_level") if result else "Unknown",
        "risk_score": result.get("risk_score", 0) if result else 0,
        "issues_summary": issues_info
    }
    
    # Quick insights
    st.markdown("#### Quick Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 Generate Summary"):
            with st.spinner("Generating AI summary..."):
                insight = gemini.generate_insight(analytics_json, "summary")
                st.markdown(insight.get("insight", "No insight generated"))
    
    with col2:
        if st.button("💡 Explain Risk Level"):
            with st.spinner("Analyzing risk factors..."):
                insight = gemini.generate_insight(analytics_json, "explanation")
                st.markdown(insight.get("insight", "No insight generated"))
    
    st.markdown("---")
    
    # Q&A Interface
    st.markdown("#### Ask Questions")
    
    question = st.text_input("Ask about this file's data", placeholder="e.g., What are the main issues?")
    
    if question:
        with st.spinner("Thinking..."):
            answer = gemini.answer_question(question, analytics_json)
            st.markdown(f"**Answer:** {answer.get('answer', 'Unable to answer')}")
    
    # Previous insights
    insights = analysis.get("insights", [])
    if insights:
        st.markdown("---")
        st.markdown("#### Previous AI Insights")
        for insight in insights[:3]:
            with st.expander(f"💬 {insight.get('prompt_type', 'Insight')} - {insight.get('generation_timestamp', '')[:10]}"):
                st.markdown(insight.get("output_text", ""))


def render_analysis_summary(analysis: Dict):
    """Render analysis summary."""
    st.markdown("### 📈 Analysis Summary")
    
    file_info = analysis.get("file", {})
    tables_info = analysis.get("tables", {})
    issues_info = analysis.get("issues", {})
    result = analysis.get("analysis", {})
    
    # File info
    st.markdown("#### File Information")
    st.markdown(f"- **Filename:** {file_info.get('filename', 'Unknown')}")
    st.markdown(f"- **Size:** {file_info.get('file_size', 0) / 1024:.1f} KB")
    st.markdown(f"- **Uploaded:** {file_info.get('upload_timestamp', 'Unknown')}")
    st.markdown(f"- **Status:** {file_info.get('processing_status', 'Unknown')}")
    
    st.markdown("---")
    
    # Table summary
    st.markdown("#### Table Breakdown")
    by_type = tables_info.get("by_type", {})
    for table_type, count in by_type.items():
        st.markdown(f"- **{table_type}:** {count} tables")
    
    st.markdown("---")
    
    # Issue breakdown
    st.markdown("#### Issue Breakdown")
    by_category = issues_info.get("by_category", {})
    for category, count in by_category.items():
        st.markdown(f"- **{category}:** {count} issues")


def render_audit_trail(file_id: int, audit_info: Optional[Dict]):
    """Render extraction audit trail."""
    st.markdown("### 🔍 Extraction Audit Trail")
    
    if not audit_info:
        st.info("No audit information available. File may need reprocessing.")
        return
    
    # Completeness summary
    st.markdown("#### Sheet Completeness")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Sheets", audit_info.get("total_sheets", 0))
    with col2:
        st.metric("Processed", audit_info.get("processed_sheets", 0))
    with col3:
        st.metric("With Tables", audit_info.get("sheets_with_tables", 0))
    
    # Sheets without tables
    sheets_without = audit_info.get("sheets_without_tables", [])
    if sheets_without:
        st.warning(f"⚠️ **{len(sheets_without)} sheet(s) have no detectable tables:**")
        for sheet in sheets_without:
            st.markdown(f"- {sheet}")
    
    st.markdown("---")
    
    # Sheet details
    st.markdown("#### Per-Sheet Breakdown")
    sheet_details = audit_info.get("sheet_details", {})
    
    if sheet_details:
        html = '''<table class="data-table">
            <tr>
                <th>Sheet Name</th>
                <th>Tables</th>
                <th>Rows</th>
                <th>Source Type</th>
            </tr>
        '''
        for sheet_name, details in sheet_details.items():
            source_type = details.get("source_type", "primary")
            badge_color = "#22c55e" if source_type == "primary" else "#f59e0b"
            html += f'''
            <tr>
                <td>{sheet_name}</td>
                <td>{details.get("tables", 0)}</td>
                <td>{details.get("rows", 0)}</td>
                <td><span style="background:{badge_color}; color:white; padding:2px 8px; border-radius:4px;">{source_type}</span></td>
            </tr>
            '''
        html += '</table>'
        st.markdown(html, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Warnings
    warnings = audit_info.get("warnings", [])
    if warnings:
        st.markdown("#### Warnings")
        for w in warnings:
            st.markdown(f"- ⚠️ {w}")
    else:
        st.success("✅ No extraction warnings")


def render_study_dashboard(study_id: int):
    """Render study-level dashboard with ROLE-SPECIFIC content."""
    pipeline = get_pipeline()
    storage = get_storage()
    
    study = storage.get_study_by_id(study_id)
    if not study:
        st.error("Study not found")
        return

    # Check Method: Cache vs Live
    analysis = None
    
    # Check Async Status
    if study.analysis_status in [AnalysisStatus.PENDING.value, AnalysisStatus.RUNNING.value]:
        st.info(f"⏳ Analysis in progress... ({study.analysis_progress}%)")
        st.progress(study.analysis_progress / 100)
        col1, col2 = st.columns([1, 4])
        with col1:
             if st.button("🔄 Refresh Status", key="refresh_status"):
                 st.rerun()
        
        # If we have cached data from BEFORE, we can show it with a warning
        if study.cached_analytics:
            st.warning("⚠️ Viewing cached data while new analysis runs.")
            analysis = study.cached_analytics
        else:
            st.stop() # Stop rendering if no data available
            
    elif study.cached_analytics:
        # FAST PATH: Read from Cache
        analysis = study.cached_analytics
        # Ensure it's a dict (SQLAlchemy JSON type usually returns dict)
        if isinstance(analysis, str):
            import json
            try:
                analysis = json.loads(analysis)
            except:
                analysis = {}
    
    else:
        # Fallback (Legacy or first run without cache)
        analysis = pipeline.get_study_full_analysis(study_id)

    if not analysis or "error" in analysis:
        st.error(analysis.get("error", "Failed to load analysis"))
        return
    
    study_info = analysis.get("study", {})
    files_info = analysis.get("files", {})
    issues_info = analysis.get("issues", {})
    risk_info = analysis.get("risk", {})
    
    # Get current user role
    user_role = st.session_state.get("user_role", "CTT")
    
    # Role-specific header
    role_headers = {
        "CTT": ("🎯 CTT Dashboard", "Strategic Overview"),
        "CRA": ("🔍 CRA Dashboard", "Site Monitoring Focus"),
        "Site": ("🏥 Site Dashboard", "Compliance & Actions")
    }
    header_title, header_subtitle = role_headers.get(user_role, ("📊 Dashboard", ""))
    
    st.markdown(f"## {header_title}: {study_info.get('study_name', 'Unknown')}")
    st.caption(f"*{header_subtitle}*")
    
    # Risk badge
    risk_level = risk_info.get("level", "Unknown")
    risk_class = "high" if "High" in str(risk_level) else "medium" if "Medium" in str(risk_level) else "low"
    st.markdown(f'<span class="risk-{risk_class}">{risk_level}</span>', unsafe_allow_html=True)
    
    # ROLE-SPECIFIC METRICS
    if user_role == "CTT":
        # CTT: Strategic metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Files", files_info.get("total", 0))
        with col2:
            st.metric("Risk Score", f"{risk_info.get('score', 0):.1f}")
        with col3:
            st.metric("Unique Issues", issues_info.get("total_unique_issues", 0))
        with col4:
            st.metric("Sites at Risk", issues_info.get("sites_affected", 0))
    
    elif user_role == "CRA":
        # CRA: Site-focused metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Sites to Monitor", issues_info.get("sites_affected", 0))
        with col2:
            high_issues = issues_info.get("by_severity", {}).get("High", 0)
            st.metric("High Priority", high_issues, delta=None if high_issues == 0 else "⚠️")
        with col3:
            st.metric("Open Queries", issues_info.get("by_category", {}).get("query_backlog", 0))
        with col4:
            st.metric("Pending Actions", issues_info.get("total_unique_issues", 0))
    
    else:  # Site
        # Site: Compliance metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            compliance_pct = 100 - min(issues_info.get("total_unique_issues", 0) * 5, 100)
            st.metric("Compliance %", f"{compliance_pct}%")
        with col2:
            st.metric("Issues to Resolve", issues_info.get("total_unique_issues", 0))
        with col3:
            medium_issues = issues_info.get("by_severity", {}).get("Medium", 0)
            st.metric("Medium Priority", medium_issues)
        with col4:
            low_issues = issues_info.get("by_severity", {}).get("Low", 0)
            st.metric("Low Priority", low_issues)
    
    # De-duplication indicator
    raw_issues = issues_info.get("total_raw_issues", 0)
    unique_issues = issues_info.get("total_unique_issues", 0)
    if raw_issues > 0:
        dedup_ratio = (raw_issues - unique_issues) / raw_issues * 100
        st.info(f"📊 **De-duplication**: {raw_issues} raw issues → {unique_issues} unique ({dedup_ratio:.0f}% removed)")
    
    # ROLE-SPECIFIC TABS
    if user_role == "CTT":
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Strategic Overview",
            "📁 All Files",
            "🤖 AI Insights",
            "📈 Risk Trends",
            "🤝 AI Actions"
        ])
    elif user_role == "CRA":
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "🏥 Site Issues",
            "📋 Action Items",
            "🔍 Monitoring Focus",
            "📈 Site Trends",
            "🤝 AI Actions"
        ])
    else:  # Site
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "✅ Compliance Status",
            "📋 My Tasks",
            "📁 Submitted Files",
            "📈 Progress",
            "🤝 AI Actions"
        ])
    
    with tab1:
        # ROLE-SPECIFIC TAB 1 CONTENT
        if user_role == "CTT":
            # CTT: Strategic Overview
            st.markdown("### 📊 Strategic Risk Overview")
            
            st.markdown("#### Risk Distribution")
            by_severity = issues_info.get("by_severity", {})
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🔴 High Risk Issues", by_severity.get("High", 0))
            with col2:
                st.metric("🟡 Medium Risk Issues", by_severity.get("Medium", 0))
            with col3:
                st.metric("🟢 Low Risk Issues", by_severity.get("Low", 0))
            
            st.markdown("---")
            st.markdown("#### Issue Categories")
            by_category = issues_info.get("by_category", {})
            if by_category:
                for cat, count in sorted(by_category.items(), key=lambda x: x[1], reverse=True):
                    pct = count / max(issues_info.get("total_unique_issues", 1), 1) * 100
                    st.progress(pct / 100, text=f"**{cat}**: {count} issues ({pct:.0f}%)")
            
            st.markdown("---")
            st.markdown("#### Key Recommendations")
            high_count = by_severity.get("High", 0)
            if high_count > 0:
                st.error(f"⚠️ **Action Required**: {high_count} high-severity issues need immediate attention")
            else:
                st.success("✅ No critical issues - study is on track")
        
        elif user_role == "CRA":
            # CRA: Site Issues Focus
            st.markdown("### 🏥 Sites Requiring Attention")
            
            issues_list = issues_info.get("issues", [])
            sites_with_issues = {}
            for issue in issues_list:
                site_id = issue.get("site_id", "Unknown")
                if site_id not in sites_with_issues:
                    sites_with_issues[site_id] = {"high": 0, "medium": 0, "low": 0, "issues": []}
                sev = issue.get("severity", "Low").lower()
                sites_with_issues[site_id][sev] = sites_with_issues[site_id].get(sev, 0) + 1
                sites_with_issues[site_id]["issues"].append(issue)
            
            if sites_with_issues:
                for site_id, site_data in sorted(sites_with_issues.items(), key=lambda x: x[1]["high"], reverse=True):
                    priority = "🔴" if site_data["high"] > 0 else "🟡" if site_data["medium"] > 0 else "🟢"
                    with st.expander(f"{priority} Site {site_id} - {site_data['high']} high, {site_data['medium']} medium"):
                        for issue in site_data["issues"][:5]:
                            st.markdown(f"- **{issue.get('issue_category')}**: {issue.get('description', '')}")
                        if len(site_data["issues"]) > 5:
                            st.caption(f"+{len(site_data['issues']) - 5} more issues")
            else:
                st.info("No site-specific issues detected")
        
        else:  # Site
            # Site: Compliance Status
            st.markdown("### ✅ Compliance Status")
            
            total_issues = issues_info.get("total_unique_issues", 0)
            compliance_pct = 100 - min(total_issues * 5, 100)
            
            if compliance_pct >= 80:
                st.success(f"🟢 **Compliance Score: {compliance_pct}%** - Good standing")
            elif compliance_pct >= 50:
                st.warning(f"🟡 **Compliance Score: {compliance_pct}%** - Improvement needed")
            else:
                st.error(f"🔴 **Compliance Score: {compliance_pct}%** - Critical attention required")
            
            st.markdown("---")
            st.markdown("#### Issues to Resolve")
            by_severity = issues_info.get("by_severity", {})
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("High Priority", by_severity.get("High", 0))
            with col2:
                st.metric("Medium Priority", by_severity.get("Medium", 0))
            with col3:
                st.metric("Low Priority", by_severity.get("Low", 0))
    
    with tab2:
        # Files in study
        st.markdown("### 📁 Files in Study")
        
        files_list = files_info.get("list", [])
        if files_list:
            for f in files_list:
                with st.expander(f"📄 {f.get('filename', 'Unknown')}"):
                    st.markdown(f"- **Status**: {f.get('processing_status', 'Unknown')}")
                    st.markdown(f"- **Tables**: {f.get('table_count', 0)}")
                    if st.button("📊 View File Details", key=f"file_{f.get('file_id')}"):
                        st.session_state["selected_file_id"] = f.get("file_id")
                        st.rerun()
        else:
            st.info("No files in this study yet.")
    
    with tab3:
        # AI Insights for study
        st.markdown("### 🤖 Study-Level AI Insights")
        
        study = storage.get_study_by_id(study_id)
        if study and study.risk_level:
            st.markdown(f"""
            **Study Risk Assessment**
            
            This study is classified as **{study.risk_level}** with a risk score of **{study.risk_score:.1f}**.
            
            - **Files Analyzed**: {files_info.get('total', 0)}
            - **Unique Issues**: {issues_info.get('total_unique_issues', 0)}
            - **Sites Affected**: {issues_info.get('sites_affected', 0)}
            """)
            
            if st.button("🔄 Regenerate AI Insights"):
                with st.spinner("Generating study insights..."):
                    result = pipeline.generate_study_insights(study_id)
                    if "insight" in result:
                        st.success("Insights generated!")
                        st.markdown(result["insight"])
        else:
            st.info("No insights available. Process files first.")
    
    with tab4:
        # TREND VISUALIZATION (NEW)
        st.markdown("### 📈 Risk Trend Analysis")
        
        # Get trend data
        trend_data = storage.get_risk_trend(study_id, limit=20)
        latest_trend = storage.get_latest_trend(study_id)
        
        # Trend indicator
        trend_status = latest_trend.get("trend", "stable")
        delta = latest_trend.get("delta", 0)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            trend_icon = "📈" if trend_status == "worsening" else "📉" if trend_status == "improving" else "➡️"
            trend_color = "red" if trend_status == "worsening" else "green" if trend_status == "improving" else "gray"
            st.markdown(f"**Trend:** {trend_icon} {trend_status.title()}")
        with col2:
            delta_text = f"+{delta:.2f}" if delta > 0 else f"{delta:.2f}" if delta < 0 else "0.00"
            st.markdown(f"**Change:** {delta_text}")
        with col3:
            st.markdown(f"**Snapshots:** {len(trend_data)}")
        
        st.markdown("---")
        
        if trend_data and len(trend_data) > 0:
            import plotly.graph_objects as go
            
            # Prepare chart data
            timestamps = [t["snapshot_time"][:16] for t in trend_data]  # Trim to minutes
            scores = [t["risk_score"] for t in trend_data]
            levels = [t["risk_level"] for t in trend_data]
            
            # Create Plotly figure
            fig = go.Figure()
            
            # Add line trace
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=scores,
                mode='lines+markers',
                name='Risk Score',
                line=dict(color='#3b82f6', width=3),
                marker=dict(size=8),
                hovertemplate='<b>%{x}</b><br>Risk Score: %{y:.2f}<extra></extra>'
            ))
            
            # Add threshold lines
            fig.add_hline(y=12, line_dash="dash", line_color="red", annotation_text="High Risk (>=12)")
            fig.add_hline(y=5, line_dash="dash", line_color="orange", annotation_text="Medium Risk (>=5)")
            
            # Update layout
            fig.update_layout(
                title="Risk Score Over Time",
                xaxis_title="Analysis Time",
                yaxis_title="Risk Score",
                template="plotly_dark" if st.session_state.get("theme") == "dark" else "plotly_white",
                height=400,
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Summary stats
            if len(scores) > 1:
                avg_score = sum(scores) / len(scores)
                max_score = max(scores)
                min_score = min(scores)
                
                st.markdown("#### Summary Statistics")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Average", f"{avg_score:.2f}")
                with col2:
                    st.metric("Peak", f"{max_score:.2f}")
                with col3:
                    st.metric("Lowest", f"{min_score:.2f}")
        else:
            st.info("📊 No trend data yet. Upload and analyze more files to see risk trends over time.")
        
        st.markdown("---")
        
        # Study info
        st.markdown("#### Study Details")
        st.markdown(f"""
        - **Study Name**: {study_info.get('study_name', 'Unknown')}
        - **Created**: {study_info.get('created_at', 'Unknown')[:10] if study_info.get('created_at') else 'Unknown'}
        - **Total Files**: {files_info.get('total', 0)}
        - **Current Risk Level**: {risk_level}
        - **Current Risk Score**: {risk_info.get('score', 0):.1f}
        """)
    
    with tab5:
        # AGENTIC AI PANEL (NEW)
        st.markdown("### 🤝 AI-Powered Actions")
        st.caption("*AI proposes, Human approves* - All actions require your approval before execution.")
        
        # Import agentic AI
        from ai.agentic import get_agentic_ai
        agentic = get_agentic_ai()
        
        st.markdown("---")
        
        # Action Generation Section
        st.markdown("#### 📧 Generate Action Drafts")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📧 Draft Query Resolution Emails", use_container_width=True):
                issues_list = issues_info.get("issues", [])
                study_name = study_info.get("study_name", "Study")
                
                if issues_list:
                    # Generate drafts for high-severity issues
                    high_issues = [i for i in issues_list if i.get("severity") == "High"][:3]
                    
                    for issue in high_issues:
                        site_id = issue.get("site_id", "Unknown")
                        agentic.draft_query_resolution_email(issue, site_id, study_name)
                    
                    st.success(f"✅ Generated {len(high_issues)} email drafts - see below for approval")
                else:
                    st.info("No issues to generate emails for")
        
        with col2:
            if st.button("🏥 Generate Site Visit Recommendations", use_container_width=True):
                issues_list = issues_info.get("issues", [])
                study_name = study_info.get("study_name", "Study")
                
                # Group issues by site
                sites_issues = {}
                for issue in issues_list:
                    site_id = issue.get("site_id", "Unknown")
                    if site_id not in sites_issues:
                        sites_issues[site_id] = []
                    sites_issues[site_id].append(issue)
                
                # Generate recommendation for top site
                if sites_issues:
                    top_site = max(sites_issues.items(), key=lambda x: len(x[1]))
                    agentic.draft_site_visit_recommendation(top_site[0], top_site[1], study_name)
                    st.success(f"✅ Generated site visit recommendation for Site {top_site[0]}")
                else:
                    st.info("No site-specific issues to analyze")
        
        st.markdown("---")
        
        # Pending Actions Section
        pending = agentic.get_pending_actions()
        
        if pending:
            st.markdown(f"#### 📋 Pending Actions ({len(pending)})")
            st.warning("⚠️ Review and approve/reject each action before it is executed.")
            
            for idx, action in enumerate(pending):
                action_type = action.get("type", "action")
                
                with st.expander(f"📝 {action_type.replace('_', ' ').title()} - {action.get('target_site', action.get('site_id', 'N/A'))}", expanded=True):
                    
                    if action_type == "email_draft":
                        st.markdown(f"**To:** Site {action.get('target_site')}")
                        st.markdown(f"**Subject:** {action.get('subject')}")
                        st.text_area("Email Body", action.get("body", ""), height=200, disabled=True, key=f"body_{idx}")
                    
                    elif action_type == "site_visit_recommendation":
                        st.markdown(f"**Site:** {action.get('site_id')}")
                        st.markdown(f"**Urgency:** {action.get('urgency', 'N/A').upper()}")
                        st.markdown(f"**Timeline:** {action.get('recommended_timeline')}")
                        st.markdown(action.get("rationale", ""))
                    
                    # Approval buttons
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✅ Approve", key=f"approve_{idx}", type="primary"):
                            agentic.approve_action(idx, user_role)
                            st.success("Action approved!")
                            st.rerun()
                    with col2:
                        if st.button("❌ Reject", key=f"reject_{idx}"):
                            agentic.reject_action(idx, "User rejected")
                            st.info("Action rejected")
                            st.rerun()
        else:
            st.info("🤖 No pending actions. Click buttons above to generate AI-powered drafts.")
        
        # Action Summary
        summary = agentic.get_action_summary()
        if summary.get("total_actions", 0) > 0:
            st.markdown("---")
            st.markdown("#### 📊 Action Summary")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Pending", summary.get("pending", 0))
            with col2:
                st.metric("Approved", summary.get("approved", 0))
            with col3:
                st.metric("Rejected", summary.get("rejected", 0))


def main():
    """Main application entry point."""
    # Initialize session state for API key
    if "gemini_api_key" not in st.session_state:
        st.session_state.gemini_api_key = None
    
    # Sidebar
    with st.sidebar:
        st.markdown("# 🔬 Clinical Trial")
        st.markdown("# Intelligence")
        st.markdown("### Enterprise Edition")
        
        # Theme selector
        st.markdown("---")
        st.markdown("### 🎨 Theme")
        theme_options = {"🌙 Dark": "dark", "☀️ Light": "light", "🌊 Blue": "blue"}
        current_theme_name = next((k for k, v in theme_options.items() if v == st.session_state.theme), "🌙 Dark")
        
        selected_theme = st.selectbox(
            "Select theme",
            options=list(theme_options.keys()),
            index=list(theme_options.keys()).index(current_theme_name),
            label_visibility="collapsed"
        )
        
        if theme_options[selected_theme] != st.session_state.theme:
            st.session_state.theme = theme_options[selected_theme]
            st.rerun()
        
        # Role selector (NEW)
        st.markdown("---")
        st.markdown("### 👤 User Role")
        
        # Initialize role in session state
        if "user_role" not in st.session_state:
            st.session_state.user_role = "CTT"
        
        role_options = {
            "🎯 CTT (Clinical Trial Team)": "CTT",
            "🔍 CRA (Clinical Research Associate)": "CRA",
            "🏥 Site (Investigational Site)": "Site"
        }
        current_role_name = next((k for k, v in role_options.items() if v == st.session_state.user_role), "🎯 CTT (Clinical Trial Team)")
        
        selected_role = st.selectbox(
            "Select role",
            options=list(role_options.keys()),
            index=list(role_options.keys()).index(current_role_name),
            label_visibility="collapsed"
        )
        
        if role_options[selected_role] != st.session_state.user_role:
            st.session_state.user_role = role_options[selected_role]
            st.rerun()
        
        st.markdown("---")
        
        # System status
        storage = get_storage()
        summary = storage.get_system_summary()
        studies = storage.get_all_studies()
        
        st.markdown("### 📊 System Status")
        st.markdown(f"**Studies:** {len(studies)}")
        st.markdown(f"**Files:** {summary['total_files']}")
        st.markdown(f"**Tables:** {summary['total_tables']}")
        st.markdown(f"**Issues:** {summary['total_issues']}")
        
        # ALERTS PANEL (NEW)
        user_role = st.session_state.get("user_role", "CTT")
        alerts = storage.get_alerts_for_role(user_role)
        
        if alerts:
            st.markdown("---")
            st.markdown(f"### 🚨 Alerts ({len(alerts)})")
            
            for alert in alerts[:3]:  # Show top 3
                severity_icon = "🔴" if alert.severity == "critical" else "🟡" if alert.severity == "warning" else "🔵"
                with st.expander(f"{severity_icon} {alert.title[:25]}...", expanded=(alert.severity == "critical")):
                    st.markdown(alert.message)
                    st.caption(f"Rule: `{alert.rule_id}` | {alert.created_at.strftime('%m/%d %H:%M')}")
                    if st.button("✅ Acknowledge", key=f"ack_{alert.alert_id}"):
                        storage.acknowledge_alert(alert.alert_id, user_role)
                        st.rerun()
        
        # NOTIFICATION SETTINGS (NEW)
        st.markdown("---")
        with st.expander("📧 Notification Settings"):
            st.markdown("**Email Notifications**")
            
            # Initialize notification recipients in session state
            if "notification_recipients" not in st.session_state:
                st.session_state.notification_recipients = ""
            
            recipients = st.text_input(
                "Recipients (comma-separated emails)",
                value=st.session_state.notification_recipients,
                placeholder="user@example.com, manager@example.com"
            )
            st.session_state.notification_recipients = recipients
            
            notify_critical = st.checkbox("🔴 Notify on Critical Alerts", value=True)
            notify_warning = st.checkbox("🟡 Notify on Warning Alerts", value=False)
            
            st.caption("*Configure SMTP in production for actual email delivery*")
        
        st.markdown("---")
        
        # Studies List (NEW - Study-centric navigation)
        if studies:
            st.markdown("### 📋 Studies")
            for study in studies[:10]:  # Show top 10
                risk_emoji = "🔴" if study.risk_level == "High Risk" else "🟡" if study.risk_level == "Medium Risk" else "🟢"
                if st.button(f"{risk_emoji} {study.study_name[:20]}...", key=f"study_{study.study_id}"):
                    st.session_state["selected_study_id"] = study.study_id
                    st.session_state["selected_file_id"] = None
                    st.rerun()
            st.markdown("---")
        
        # Gemini AI Configuration
        st.markdown("### 🤖 Gemini AI")
        
        # Check current status
        gemini = get_gemini()
        
        if gemini.is_available:
            st.markdown("🟢 **Status:** Connected")
            if st.button("🔄 Reset API Key"):
                st.session_state.gemini_api_key = None
                st.rerun()
        else:
            st.markdown("🟡 **Status:** Not Connected")
            st.caption("Enter your Google API key below to enable AI features")
            
            # API Key input (password field for security)
            api_key_input = st.text_input(
                "Google API Key",
                type="password",
                placeholder="Enter your API key...",
                help="Your API key is stored securely in session only and never saved to disk."
            )
            
            if st.button("🔑 Connect AI", type="primary"):
                if api_key_input:
                    st.session_state.gemini_api_key = api_key_input
                    st.rerun()
                else:
                    st.error("Please enter an API key")
        
        st.markdown("---")
        st.markdown("### ℹ️ About")
        st.markdown("""
        **Enterprise Features:**
        - Study-level analytics
        - Cross-file de-duplication
        - Multi-table extraction
        - Gemini AI study insights
        - Full traceability
        
        **Security:**
        - API key stored in memory only
        - Never written to disk
        - Cleared on session end
        """)
    
    # Check for selected study or file
    selected_study_id = st.session_state.get("selected_study_id")
    selected_file_id = st.session_state.get("selected_file_id")
    
    # Main content - tabs
    if selected_file_id:
        # File drill-down view
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("← Back to Study"):
                del st.session_state["selected_file_id"]
                st.rerun()
        
        render_file_analysis(selected_file_id)
    
    elif selected_study_id:
        # Study dashboard (DEFAULT for study-scoped view)
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("← All Studies"):
                del st.session_state["selected_study_id"]
                st.rerun()
        
        render_study_dashboard(selected_study_id)
    
    else:
        # Main tabs for upload and management
        tab1, tab2, tab3 = st.tabs(["📤 Upload Files", "📁 Manage Files", "📊 All Studies"])
        
        with tab1:
            render_file_upload()
        
        with tab2:
            render_files_list()
        
        with tab3:
            render_studies_list()


def render_studies_list():
    """Render list of all studies."""
    st.markdown("## 📊 All Studies")
    
    storage = get_storage()
    studies = storage.get_all_studies()
    
    if not studies:
        st.info("No studies created yet. Upload files to create your first study.")
        return
    
    # Studies table
    for study in studies:
        risk_emoji = "🔴" if study.risk_level == "High Risk" else "🟡" if study.risk_level == "Medium Risk" else "🟢"
        
        with st.expander(f"{risk_emoji} **{study.study_name}** - {len(study.files) if study.files else 0} files"):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Files", len(study.files) if study.files else 0)
            with col2:
                st.metric("Unique Issues", study.unique_issues or 0)
            with col3:
                st.metric("Risk Score", f"{study.risk_score:.1f}" if study.risk_score else "N/A")
            with col4:
                if st.button("📊 View Dashboard", key=f"view_study_{study.study_id}"):
                    st.session_state["selected_study_id"] = study.study_id
                    st.rerun()


if __name__ == "__main__":
    main()
