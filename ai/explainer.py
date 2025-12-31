"""
AI Explainer - Generates natural language explanations for insights
"""
from typing import Dict, List, Optional


class AIExplainer:
    """Generates clear, non-technical explanations for clinical trial insights."""
    
    def __init__(self):
        self.issue_descriptions = {
            "missing_lab_names": "Missing laboratory names in the data",
            "missing_reference_ranges": "Missing reference ranges for lab values",
            "missing_crf_pages": "Missing Case Report Form pages",
            "inactivated_forms": "Forms that have been inactivated",
            "delayed_visits": "Patient visits that are behind schedule",
            "projection_slippage": "Visit projections that are not being met",
            "query_backlog": "Open data queries awaiting resolution",
            "delayed_data_entry": "Data entry that is delayed after patient visits"
        }
    
    def explain_study_risk(self, study_analysis: Dict) -> str:
        """Generate explanation for why a study has its risk level."""
        study_risk = study_analysis.get("study_risk", {})
        risk_level = study_risk.get("risk_level", "Unknown")
        
        explanation = f"## Study Risk Assessment: {risk_level}\n\n"
        
        if risk_level == "High Risk":
            explanation += "This study requires **immediate attention**. "
        elif risk_level == "Medium Risk":
            explanation += "This study has some concerns that should be monitored. "
        else:
            explanation += "This study is performing well overall. "
        
        # Add site breakdown
        total = study_risk.get("total_sites", 0)
        high = study_risk.get("high_risk_sites", 0)
        medium = study_risk.get("medium_risk_sites", 0)
        
        if total > 0:
            explanation += f"\n\n**Site Summary:**\n"
            explanation += f"- {high} of {total} sites ({study_risk.get('high_risk_pct', 0)}%) are high risk\n"
            explanation += f"- {medium} sites are medium risk\n"
            explanation += f"- {total - high - medium} sites are performing well\n"
        
        # Add contributing factors
        factors = study_risk.get("contributing_factors", [])
        if factors:
            explanation += f"\n**Key Concerns:**\n"
            for factor in factors:
                explanation += f"- {factor}\n"
        
        return explanation
    
    def explain_site_risk(self, site_id: str, site_risk: Dict, 
                          quality_issues: List[Dict], operational_issues: List[Dict]) -> str:
        """Generate explanation for why a site has its risk level."""
        risk_level = site_risk.get("risk_level", "Unknown")
        
        explanation = f"## Site {site_id}: {risk_level}\n\n"
        
        if risk_level == "High Risk":
            explanation += "This site needs **priority intervention**. "
            explanation += "Multiple issues are present affecting both data quality and operations.\n\n"
        elif risk_level == "Medium Risk":
            explanation += "This site has some issues that should be addressed proactively.\n\n"
        else:
            explanation += "This site is performing within acceptable parameters.\n\n"
        
        # Detail quality issues
        if quality_issues:
            explanation += "**Data Quality Issues:**\n"
            for issue in quality_issues:
                desc = issue.get("description", self.issue_descriptions.get(issue.get("type", ""), ""))
                severity = issue.get("severity", "")
                explanation += f"- [{severity}] {desc}\n"
        
        # Detail operational issues
        if operational_issues:
            explanation += "\n**Operational Issues:**\n"
            for issue in operational_issues:
                desc = issue.get("description", self.issue_descriptions.get(issue.get("type", ""), ""))
                severity = issue.get("severity", "")
                explanation += f"- [{severity}] {desc}\n"
        
        return explanation
    
    def answer_question(self, question: str, study_analysis: Dict) -> str:
        """Answer a natural language question about the study."""
        question_lower = question.lower()
        
        study_id = study_analysis.get("study_id", "Unknown")
        study_risk = study_analysis.get("study_risk", {})
        site_risks = study_analysis.get("site_risks", {})
        quality_issues = study_analysis.get("quality_issues", {})
        operational_issues = study_analysis.get("operational_issues", {})
        
        # Query backlog specific questions
        if "backlog" in question_lower:
            return self._explain_backlog(site_risks, operational_issues)
        
        # Missing labs contribution
        if "missing" in question_lower and "lab" in question_lower:
            return self._explain_missing_labs_impact(quality_issues, study_risk)
        
        # Specific site questions "why site X"
        import re
        site_match = re.search(r'site\s*(\d+)', question_lower)
        if site_match and ("why" in question_lower or "flag" in question_lower):
            site_id_q = site_match.group(1)
            return self._explain_specific_site(site_id_q, site_risks, quality_issues, operational_issues)
        
        # Top/main issues
        if "top" in question_lower or "main" in question_lower or "frequent" in question_lower:
            if "operational" in question_lower:
                return self._explain_top_issues(operational_issues, "operational")
            else:
                return self._explain_top_issues(quality_issues, "quality")
        
        # Why is study high risk?
        if "why" in question_lower and "risk" in question_lower:
            return self.explain_study_risk(study_analysis)
        
        # Which sites need attention?
        if "site" in question_lower and ("attention" in question_lower or "need" in question_lower):
            return self._explain_sites_needing_attention(site_risks, quality_issues, operational_issues)
        
        # What are the main data quality issues?
        if "quality" in question_lower:
            return self._explain_quality_issues(quality_issues)
        
        # What are the operational issues?
        if "operational" in question_lower:
            return self._explain_operational_issues(operational_issues)
        
        # Default summary
        return self.explain_study_risk(study_analysis)
    
    def _explain_backlog(self, site_risks: Dict, operational_issues: Dict) -> str:
        """Explain which sites have the biggest query backlog."""
        explanation = "## Query Backlog Analysis\n\n"
        
        backlog_issues = operational_issues.get("by_type", {}).get("query_backlog", [])
        
        if not backlog_issues:
            return explanation + "No significant query backlog detected in this study."
        
        # Sort by count
        sorted_issues = sorted(backlog_issues, key=lambda x: x.get("count", 0), reverse=True)
        
        explanation += "**Sites with highest query backlog:**\n\n"
        for issue in sorted_issues[:5]:
            site_id = issue.get("site_id", "Unknown")
            count = issue.get("count", 0)
            severity = issue.get("severity", "Low")
            
            site_risk = site_risks.get(site_id, {})
            risk_level = site_risk.get("risk_level", "Unknown")
            
            explanation += f"### Site {site_id}\n"
            explanation += f"- **{count} open queries** (Severity: {severity})\n"
            explanation += f"- Site Risk Level: {risk_level}\n"
            explanation += f"- **Why:** High query counts indicate data entry issues or delayed query resolution, "
            explanation += "which delays database lock and can impact study timelines.\n\n"
        
        return explanation
    
    def _explain_missing_labs_impact(self, quality_issues: Dict, study_risk: Dict) -> str:
        """Explain how missing labs contributed to overall study risk."""
        explanation = "## Missing Labs Impact Analysis\n\n"
        
        lab_issues = quality_issues.get("by_type", {}).get("missing_lab_names", [])
        range_issues = quality_issues.get("by_type", {}).get("missing_reference_ranges", [])
        
        total_lab_issues = len(lab_issues) + len(range_issues)
        total_issues = quality_issues.get("total_issues", 0)
        
        if total_lab_issues == 0:
            return explanation + "No missing lab data issues detected in this study."
        
        contribution_pct = (total_lab_issues / total_issues * 100) if total_issues > 0 else 0
        
        explanation += f"**Missing lab data accounts for {total_lab_issues} of {total_issues} "
        explanation += f"quality issues ({contribution_pct:.1f}%)**\n\n"
        
        if lab_issues:
            explanation += "### Missing Lab Names\n"
            for issue in lab_issues[:3]:
                explanation += f"- {issue.get('description', '')} (from: {issue.get('file', '')})\n"
        
        if range_issues:
            explanation += "\n### Missing Reference Ranges\n"
            for issue in range_issues[:3]:
                explanation += f"- {issue.get('description', '')} (from: {issue.get('file', '')})\n"
        
        explanation += "\n**Impact:** Missing lab data affects data completeness and can impact "
        explanation += "regulatory submissions. Sites with lab data issues should be prioritized for follow-up."
        
        return explanation
    
    def _explain_specific_site(self, site_id: str, site_risks: Dict, 
                                quality_issues: Dict, operational_issues: Dict) -> str:
        """Explain why a specific site was flagged."""
        # Find matching site (handle different formats)
        matching_site = None
        for sid in site_risks.keys():
            if str(sid) == str(site_id) or sid.endswith(site_id):
                matching_site = sid
                break
        
        if not matching_site:
            return f"## Site {site_id}\n\nNo data found for Site {site_id} in this study."
        
        site_risk = site_risks.get(matching_site, {})
        site_quality = quality_issues.get("by_site", {}).get(matching_site, [])
        site_operational = operational_issues.get("by_site", {}).get(matching_site, [])
        
        return self.explain_site_risk(matching_site, site_risk, site_quality, site_operational)
    
    def _explain_top_issues(self, issues_data: Dict, issue_category: str) -> str:
        """Explain the top/most frequent issues."""
        explanation = f"## Top {issue_category.title()} Issues\n\n"
        
        by_type = issues_data.get("by_type", {})
        
        if not by_type:
            return explanation + f"No {issue_category} issues detected."
        
        # Count by type
        type_counts = [(t, len(issues)) for t, issues in by_type.items()]
        type_counts.sort(key=lambda x: x[1], reverse=True)
        
        explanation += "**Most frequent issues (by count):**\n\n"
        for issue_type, count in type_counts:
            type_desc = self.issue_descriptions.get(issue_type, issue_type)
            explanation += f"1. **{type_desc}**: {count} occurrences\n"
            
            # Show contributing sites
            issues = by_type.get(issue_type, [])
            sites_affected = set()
            for issue in issues:
                site = issue.get("site_id")
                if site:
                    sites_affected.add(site)
            if sites_affected:
                explanation += f"   - Affects sites: {', '.join(list(sites_affected)[:5])}\n"
        
        return explanation

    
    def _explain_sites_needing_attention(self, site_risks: Dict, 
                                          quality_issues: Dict, operational_issues: Dict) -> str:
        """Explain which sites need attention and why."""
        explanation = "## Sites Requiring Attention\n\n"
        
        high_risk = [(sid, data) for sid, data in site_risks.items() 
                     if data.get("risk_level") == "High Risk"]
        medium_risk = [(sid, data) for sid, data in site_risks.items() 
                       if data.get("risk_level") == "Medium Risk"]
        
        if high_risk:
            explanation += "### High Priority Sites\n"
            for site_id, data in high_risk:
                factors = data.get("contributing_factors", [])
                explanation += f"\n**Site {site_id}**\n"
                for f in factors:
                    explanation += f"- {f}\n"
        
        if medium_risk:
            explanation += "\n### Monitor These Sites\n"
            for site_id, data in medium_risk:
                factors = data.get("contributing_factors", [])
                explanation += f"\n**Site {site_id}**\n"
                for f in factors:
                    explanation += f"- {f}\n"
        
        if not high_risk and not medium_risk:
            explanation += "All sites are currently performing well with no major concerns."
        
        return explanation
    
    def _explain_quality_issues(self, quality_results: Dict) -> str:
        """Explain data quality issues."""
        explanation = "## Data Quality Issues\n\n"
        
        by_type = quality_results.get("by_type", {})
        by_severity = quality_results.get("by_severity", {})
        
        if by_severity:
            explanation += f"**Summary:** {by_severity.get('High', 0)} high, "
            explanation += f"{by_severity.get('Medium', 0)} medium, {by_severity.get('Low', 0)} low severity\n\n"
        
        for issue_type, issues in by_type.items():
            type_desc = self.issue_descriptions.get(issue_type, issue_type)
            explanation += f"### {type_desc}\n"
            for issue in issues[:5]:  # Limit to 5 per type
                explanation += f"- {issue.get('description', '')}\n"
            if len(issues) > 5:
                explanation += f"- _...and {len(issues) - 5} more_\n"
            explanation += "\n"
        
        if not by_type:
            explanation += "No data quality issues detected."
        
        return explanation
    
    def _explain_operational_issues(self, operational_results: Dict) -> str:
        """Explain operational issues."""
        explanation = "## Operational Issues\n\n"
        
        by_type = operational_results.get("by_type", {})
        by_severity = operational_results.get("by_severity", {})
        
        if by_severity:
            explanation += f"**Summary:** {by_severity.get('High', 0)} high, "
            explanation += f"{by_severity.get('Medium', 0)} medium, {by_severity.get('Low', 0)} low severity\n\n"
        
        for issue_type, issues in by_type.items():
            type_desc = self.issue_descriptions.get(issue_type, issue_type)
            explanation += f"### {type_desc}\n"
            for issue in issues[:5]:
                explanation += f"- {issue.get('description', '')}\n"
            if len(issues) > 5:
                explanation += f"- _...and {len(issues) - 5} more_\n"
            explanation += "\n"
        
        if not by_type:
            explanation += "No operational issues detected."
        
        return explanation
