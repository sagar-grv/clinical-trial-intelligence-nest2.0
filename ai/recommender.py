"""
Recommender - Generates role-aware recommendations
"""
from typing import Dict, List


class Recommender:
    """Generates advisory recommendations for clinical trial teams."""
    
    ROLES = ["CRA", "CTT", "Management"]
    
    def __init__(self):
        self.role_focus = {
            "CRA": ["site_level", "data_quality", "patient_visits"],
            "CTT": ["operational", "timelines", "queries"],
            "Management": ["study_level", "risk_overview", "resource_allocation"]
        }
    
    def generate_recommendations(self, study_analysis: Dict, role: str = "Management") -> List[Dict]:
        """Generate role-aware recommendations."""
        recommendations = []
        
        study_risk = study_analysis.get("study_risk", {})
        site_risks = study_analysis.get("site_risks", {})
        quality_issues = study_analysis.get("quality_issues", {})
        operational_issues = study_analysis.get("operational_issues", {})
        
        if role == "CRA":
            recommendations.extend(self._cra_recommendations(site_risks, quality_issues))
        elif role == "CTT":
            recommendations.extend(self._ctt_recommendations(site_risks, operational_issues))
        else:  # Management
            recommendations.extend(self._management_recommendations(study_risk, site_risks))
        
        return recommendations
    
    def _cra_recommendations(self, site_risks: Dict, quality_issues: Dict) -> List[Dict]:
        """Generate CRA-focused recommendations."""
        recs = []
        
        # High-risk site visits
        high_risk_sites = [sid for sid, data in site_risks.items() 
                          if data.get("risk_level") == "High Risk"]
        if high_risk_sites:
            recs.append({
                "priority": "High",
                "action": f"Schedule monitoring visits for high-risk sites: {', '.join(high_risk_sites[:5])}",
                "reason": "These sites have multiple data quality and operational issues",
                "triggered_by": ["high_risk_sites", "data_quality_issues"]
            })
        
        # Missing data follow-up
        quality_by_type = quality_issues.get("by_type", {})
        if "missing_crf_pages" in quality_by_type:
            count = len(quality_by_type["missing_crf_pages"])
            recs.append({
                "priority": "Medium",
                "action": f"Follow up on {count} missing CRF page issues with sites",
                "reason": "Missing CRF pages can impact data completeness and regulatory compliance",
                "triggered_by": ["missing_crf_pages"]
            })
        
        if "inactivated_forms" in quality_by_type:
            recs.append({
                "priority": "Medium",
                "action": "Review inactivated forms for appropriate documentation",
                "reason": "Inactivated forms should be properly documented with reasons",
                "triggered_by": ["inactivated_forms"]
            })
        
        return recs
    
    def _ctt_recommendations(self, site_risks: Dict, operational_issues: Dict) -> List[Dict]:
        """Generate CTT-focused recommendations."""
        recs = []
        
        op_by_type = operational_issues.get("by_type", {})
        
        # Query backlog
        if "query_backlog" in op_by_type:
            high_query_sites = [i.get("site_id") for i in op_by_type["query_backlog"] 
                               if i.get("severity") == "High"]
            if high_query_sites:
                recs.append({
                    "priority": "High",
                    "action": f"Escalate query resolution at sites: {', '.join(high_query_sites[:5])}",
                    "reason": "High query backlog can delay database lock",
                    "triggered_by": ["query_backlog"]
                })
        
        # Visit delays
        if "delayed_visits" in op_by_type:
            recs.append({
                "priority": "Medium",
                "action": "Review visit scheduling with sites showing delays",
                "reason": "Visit delays can impact enrollment timelines",
                "triggered_by": ["delayed_visits"]
            })
        
        # Data entry delays
        if "delayed_data_entry" in op_by_type:
            recs.append({
                "priority": "Medium",
                "action": "Implement data entry reminders for sites with delays",
                "reason": "Timely data entry ensures data quality and trial timelines",
                "triggered_by": ["delayed_data_entry"]
            })
        
        return recs
    
    def _management_recommendations(self, study_risk: Dict, site_risks: Dict) -> List[Dict]:
        """Generate Management-focused recommendations."""
        recs = []
        
        risk_level = study_risk.get("risk_level", "Low Risk")
        high_risk_count = study_risk.get("high_risk_sites", 0)
        total_sites = study_risk.get("total_sites", 0)
        
        if risk_level == "High Risk":
            recs.append({
                "priority": "High",
                "action": "Consider scheduling study-level risk review meeting",
                "reason": f"Study is high risk with {high_risk_count} of {total_sites} sites requiring attention",
                "triggered_by": ["study_high_risk"]
            })
        
        if high_risk_count > 0:
            recs.append({
                "priority": "High",
                "action": f"Allocate additional CRA resources to {high_risk_count} high-risk sites",
                "reason": "High-risk sites may need more frequent monitoring",
                "triggered_by": ["high_risk_sites"]
            })
        
        if study_risk.get("high_risk_pct", 0) > 20:
            recs.append({
                "priority": "Medium",
                "action": "Evaluate site training and support programs",
                "reason": f"{study_risk.get('high_risk_pct', 0)}% of sites are high risk",
                "triggered_by": ["high_risk_percentage"]
            })
        
        return recs
    
    def format_recommendations(self, recommendations: List[Dict]) -> str:
        """Format recommendations as readable text."""
        if not recommendations:
            return "No specific recommendations at this time."
        
        output = "## Recommendations\n\n"
        output += "_These are advisory recommendations only. No actions will be taken automatically._\n\n"
        
        for i, rec in enumerate(recommendations, 1):
            priority = rec.get("priority", "Medium")
            output += f"### {i}. [{priority}] {rec.get('action', '')}\n"
            output += f"**Why:** {rec.get('reason', '')}\n"
            output += f"**Triggered by:** {', '.join(rec.get('triggered_by', []))}\n\n"
        
        return output
