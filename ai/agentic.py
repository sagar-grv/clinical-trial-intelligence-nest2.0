"""
Agentic AI Module - Autonomous task execution with human-in-the-loop approval

This module provides AI-powered automation for routine tasks:
- Auto-draft query resolution emails
- Generate site visit recommendations
- Suggest corrective actions
- Context-aware recommendations

IMPORTANT: All actions require user approval before execution.
"""
from typing import Dict, List, Optional
from datetime import datetime
import json


class AgenticAI:
    """
    Agentic AI for clinical trial automation.
    
    Key principle: AI PROPOSES, Human APPROVES
    - All drafts are marked as "pending_approval"
    - No action is taken without explicit user confirmation
    """
    
    def __init__(self, gemini_client=None):
        self.gemini_client = gemini_client
        self.pending_actions = []
        self.action_history = []
    
    def draft_query_resolution_email(self, issue: Dict, site_id: str, 
                                     study_name: str) -> Dict:
        """
        Auto-draft a query resolution request email for a specific issue.
        
        Returns a draft that requires user approval before sending.
        """
        issue_category = issue.get("issue_category", "data_issue")
        severity = issue.get("severity", "Medium")
        description = issue.get("description", "Issue detected")
        rule_id = issue.get("rule_id", "UNKNOWN")
        
        # Generate draft email
        draft = {
            "type": "email_draft",
            "status": "pending_approval",
            "created_at": datetime.utcnow().isoformat(),
            "target_site": site_id,
            "study": study_name,
            "issue_id": issue.get("issue_id"),
            "subject": f"[Action Required] Query Resolution: {issue_category.replace('_', ' ').title()} - {study_name}",
            "body": f"""Dear Site {site_id} Team,

We have identified a data quality issue in the {study_name} study that requires your attention.

**Issue Details:**
- Category: {issue_category.replace('_', ' ').title()}
- Severity: {severity}
- Description: {description}
- Rule ID: {rule_id}

**Required Action:**
Please review the affected data and submit corrections within 5 business days.

**Guidance:**
1. Access the eCRF system and navigate to the affected records
2. Review the flagged data points
3. Make necessary corrections or provide clarification
4. Mark the query as resolved once addressed

If you have questions or require additional context, please respond to this email.

Thank you for your prompt attention to this matter.

Best regards,
Clinical Trial Intelligence System
(This is an AI-drafted message pending approval)
""",
            "metadata": {
                "severity": severity,
                "rule_id": rule_id,
                "auto_generated": True,
                "requires_approval": True
            }
        }
        
        self.pending_actions.append(draft)
        return draft
    
    def draft_site_visit_recommendation(self, site_id: str, issues: List[Dict],
                                        study_name: str) -> Dict:
        """Generate a site visit recommendation based on issue patterns."""
        high_issues = [i for i in issues if i.get("severity") == "High"]
        total_issues = len(issues)
        
        # Determine urgency
        if len(high_issues) >= 3:
            urgency = "urgent"
            timeline = "within 2 weeks"
        elif len(high_issues) >= 1 or total_issues >= 5:
            urgency = "recommended"
            timeline = "within 30 days"
        else:
            urgency = "routine"
            timeline = "next scheduled visit"
        
        # Generate issue summary
        issue_summary = "\n".join([
            f"- [{i.get('severity')}] {i.get('description', 'Issue')}"
            for i in issues[:5]
        ])
        
        recommendation = {
            "type": "site_visit_recommendation",
            "status": "pending_review",
            "created_at": datetime.utcnow().isoformat(),
            "site_id": site_id,
            "study": study_name,
            "urgency": urgency,
            "recommended_timeline": timeline,
            "issue_count": total_issues,
            "high_severity_count": len(high_issues),
            "rationale": f"""Site {site_id} has accumulated {total_issues} issues ({len(high_issues)} high-severity).

Key Issues:
{issue_summary}

Recommended Action: Schedule a {urgency} monitoring visit {timeline}.
Focus Areas:
- Review data collection processes
- Verify source documentation
- Provide additional training if needed
""",
            "metadata": {
                "auto_generated": True,
                "requires_approval": True
            }
        }
        
        self.pending_actions.append(recommendation)
        return recommendation
    
    def suggest_corrective_action(self, issue: Dict) -> Dict:
        """Suggest specific corrective actions for an issue."""
        category = issue.get("issue_category", "unknown")
        
        # Rule-based suggestions (deterministic, auditable)
        action_map = {
            "missing_data": {
                "action": "Request data entry completion",
                "steps": [
                    "Identify missing fields in source documents",
                    "Contact site coordinator for data retrieval",
                    "Update eCRF with corrected values",
                    "Add comment explaining the delay"
                ],
                "owner": "Site Coordinator"
            },
            "query_backlog": {
                "action": "Prioritize query resolution",
                "steps": [
                    "Review oldest open queries first",
                    "Group related queries for efficient resolution",
                    "Schedule dedicated query review sessions",
                    "Escalate queries older than 14 days"
                ],
                "owner": "CRA"
            },
            "delayed_visits": {
                "action": "Reschedule patient visits",
                "steps": [
                    "Contact affected patients for rescheduling",
                    "Document reason for original delay",
                    "Update visit schedule in system",
                    "Assess protocol deviation if applicable"
                ],
                "owner": "Site"
            },
            "data_inconsistency": {
                "action": "Clean and standardize data",
                "steps": [
                    "Identify inconsistent data patterns",
                    "Verify against source documents",
                    "Apply data corrections",
                    "Add data management notes"
                ],
                "owner": "Data Manager"
            }
        }
        
        suggestion = action_map.get(category, {
            "action": "Review and address issue",
            "steps": ["Review issue details", "Determine root cause", "Implement correction"],
            "owner": "Study Team"
        })
        
        return {
            "type": "corrective_action",
            "status": "suggested",
            "issue_id": issue.get("issue_id"),
            "category": category,
            "suggested_action": suggestion["action"],
            "steps": suggestion["steps"],
            "suggested_owner": suggestion["owner"],
            "metadata": {
                "auto_generated": True,
                "confidence": "rule_verified"
            }
        }
    
    def get_pending_actions(self) -> List[Dict]:
        """Get all pending actions awaiting approval."""
        return [a for a in self.pending_actions if a.get("status") == "pending_approval"]
    
    def approve_action(self, action_index: int, approved_by: str = "user") -> Dict:
        """Approve a pending action for execution."""
        if 0 <= action_index < len(self.pending_actions):
            action = self.pending_actions[action_index]
            action["status"] = "approved"
            action["approved_at"] = datetime.utcnow().isoformat()
            action["approved_by"] = approved_by
            self.action_history.append(action)
            return action
        return {"error": "Action not found"}
    
    def reject_action(self, action_index: int, reason: str = "") -> Dict:
        """Reject a pending action."""
        if 0 <= action_index < len(self.pending_actions):
            action = self.pending_actions[action_index]
            action["status"] = "rejected"
            action["rejected_at"] = datetime.utcnow().isoformat()
            action["rejection_reason"] = reason
            self.action_history.append(action)
            return action
        return {"error": "Action not found"}
    
    def clear_pending(self):
        """Clear all pending actions."""
        self.pending_actions = []
    
    def get_action_summary(self) -> Dict:
        """Get summary of all actions."""
        return {
            "pending": len([a for a in self.pending_actions if a.get("status") == "pending_approval"]),
            "approved": len([a for a in self.action_history if a.get("status") == "approved"]),
            "rejected": len([a for a in self.action_history if a.get("status") == "rejected"]),
            "total_actions": len(self.pending_actions) + len(self.action_history)
        }


# Singleton instance
_agentic_ai_instance = None


def get_agentic_ai(gemini_client=None) -> AgenticAI:
    """Get or create the AgenticAI singleton."""
    global _agentic_ai_instance
    if _agentic_ai_instance is None:
        _agentic_ai_instance = AgenticAI(gemini_client)
    return _agentic_ai_instance
