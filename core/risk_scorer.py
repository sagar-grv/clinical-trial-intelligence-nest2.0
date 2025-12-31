"""
Risk Scoring Engine - Calculates site and study level risks
"""
from typing import Dict, List
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import RISK_WEIGHTS


class RiskScorer:
    """Calculates risk scores for sites and studies."""
    
    def __init__(self):
        self.weights = RISK_WEIGHTS
        self.severity_scores = {"High": 3, "Medium": 2, "Low": 1, "None": 0}
    
    def calculate_issue_score(self, issues: List[Dict]) -> float:
        total = sum(self.severity_scores.get(i.get("severity", "Low"), 0) for i in issues)
        return total
    
    def calculate_site_risk(self, quality_issues: List[Dict], operational_issues: List[Dict]) -> Dict:
        quality_score = self.calculate_issue_score(quality_issues)
        operational_score = self.calculate_issue_score(operational_issues)
        
        high_quality = sum(1 for i in quality_issues if i.get("severity") == "High")
        high_operational = sum(1 for i in operational_issues if i.get("severity") == "High")
        
        weighted_score = (quality_score * self.weights["data_quality"] + 
                         operational_score * self.weights["operational"])
        
        if high_quality >= 1 and high_operational >= 1:
            risk_level = "High Risk"
        elif weighted_score >= 8 or high_quality >= 2 or high_operational >= 2:
            risk_level = "High Risk"
        elif weighted_score >= 4 or high_quality >= 1 or high_operational >= 1:
            risk_level = "Medium Risk"
        else:
            risk_level = "Low Risk"
        
        factors = []
        if high_quality > 0:
            factors.append(f"{high_quality} high-severity data quality issues")
        if high_operational > 0:
            factors.append(f"{high_operational} high-severity operational issues")
        
        return {
            "risk_level": risk_level,
            "weighted_score": round(weighted_score, 2),
            "quality_score": quality_score,
            "operational_score": operational_score,
            "quality_issue_count": len(quality_issues),
            "operational_issue_count": len(operational_issues),
            "high_severity_count": high_quality + high_operational,
            "contributing_factors": factors
        }
    
    def calculate_study_risk(self, site_risks: Dict[str, Dict]) -> Dict:
        if not site_risks:
            return {"risk_level": "Low Risk", "total_sites": 0, "high_risk_sites": 0,
                    "medium_risk_sites": 0, "low_risk_sites": 0, "contributing_factors": []}
        
        counts = {"High Risk": 0, "Medium Risk": 0, "Low Risk": 0}
        for risk_data in site_risks.values():
            level = risk_data.get("risk_level", "Low Risk")
            counts[level] = counts.get(level, 0) + 1
        
        total_sites = len(site_risks)
        high_pct = (counts["High Risk"] / total_sites) * 100 if total_sites > 0 else 0
        med_pct = (counts["Medium Risk"] / total_sites) * 100 if total_sites > 0 else 0
        
        if counts["High Risk"] >= 3 or high_pct >= 30:
            study_risk = "High Risk"
        elif counts["High Risk"] >= 1 or (med_pct + high_pct) >= 50:
            study_risk = "Medium Risk"
        else:
            study_risk = "Low Risk"
        
        factors = []
        if counts["High Risk"] > 0:
            factors.append(f"{counts['High Risk']} high-risk sites ({round(high_pct, 1)}%)")
        if counts["Medium Risk"] > 0:
            factors.append(f"{counts['Medium Risk']} medium-risk sites")
        
        return {
            "risk_level": study_risk, "total_sites": total_sites,
            "high_risk_sites": counts["High Risk"], "medium_risk_sites": counts["Medium Risk"],
            "low_risk_sites": counts["Low Risk"], "high_risk_pct": round(high_pct, 1),
            "contributing_factors": factors
        }
    
    def score_all_sites(self, quality_by_site: Dict, operational_by_site: Dict) -> Dict[str, Dict]:
        all_sites = set(quality_by_site.keys()) | set(operational_by_site.keys())
        site_risks = {}
        for site_id in all_sites:
            if site_id == "Study-wide":
                continue
            site_risks[site_id] = self.calculate_site_risk(
                quality_by_site.get(site_id, []), operational_by_site.get(site_id, []))
            site_risks[site_id]["site_id"] = site_id
        return site_risks
