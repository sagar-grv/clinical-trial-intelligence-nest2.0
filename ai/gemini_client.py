"""
Gemini AI Client - Read-only AI integration for insights and explanations
"""
from typing import Dict, List, Optional
import os
import json


class GeminiClient:
    """
    Gemini AI integration for clinical trial intelligence.
    
    Constraints:
    - Read-only: Gemini cannot modify data
    - Structured input: Only receives JSON analytics, not raw Excel
    - Advisory output: All insights are recommendations, not actions
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GOOGLE_API_KEY")
        self.model = None
        self._initialized = False
        
        if self.api_key:
            self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Gemini client."""
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
            self._initialized = True
        except ImportError:
            print("Warning: google-generativeai not installed. AI features disabled.")
        except Exception as e:
            print(f"Warning: Failed to initialize Gemini: {e}")
    
    @property
    def is_available(self) -> bool:
        """Check if Gemini API is available."""
        return self._initialized and self.model is not None
    
    def generate_insight(self, analytics_json: Dict, prompt_type: str = "summary") -> Dict:
        """
        Generate insights from structured analytics data.
        
        Args:
            analytics_json: Structured analytics output (NOT raw Excel data)
            prompt_type: Type of insight (summary, explanation, pattern)
        
        Returns:
            {
                "success": bool,
                "insight": str,
                "prompt_type": str,
                "input_summary": str
            }
        """
        if not self.is_available:
            return self._fallback_insight(analytics_json, prompt_type)
        
        try:
            prompt = self._build_prompt(analytics_json, prompt_type)
            response = self.model.generate_content(prompt)
            
            return {
                "success": True,
                "insight": response.text,
                "prompt_type": prompt_type,
                "input_summary": self._summarize_input(analytics_json)
            }
        except Exception as e:
            return {
                "success": False,
                "insight": f"AI generation failed: {str(e)}. Using fallback analysis.",
                "prompt_type": prompt_type,
                "error": str(e)
            }
    
    def _build_prompt(self, analytics_json: Dict, prompt_type: str) -> str:
        """Build appropriate prompt based on type."""
        base_context = """You are an AI assistant for clinical trial intelligence. 
You are analyzing STRUCTURED ANALYTICS DATA (not raw patient data).
Your role is READ-ONLY: explain findings, identify patterns, and provide recommendations.
You must NOT suggest any automated actions. All recommendations are advisory for human review.
Keep responses concise and actionable for clinical trial teams."""

        analytics_summary = json.dumps(analytics_json, indent=2, default=str)[:4000]  # Limit size
        
        prompts = {
            "summary": f"""{base_context}

Provide a executive summary of this clinical trial file analysis:

{analytics_summary}

Include:
1. Overall risk assessment (1-2 sentences)
2. Key findings (top 3)
3. Recommended focus areas""",
            
            "explanation": f"""{base_context}

Explain WHY this file has its risk level based on the detected issues:

{analytics_summary}

Use non-technical language. Reference specific issue counts and types.
Explain the clinical significance of the findings.""",
            
            "pattern": f"""{base_context}

Analyze patterns across the extracted tables in this file:

{analytics_summary}

Identify:
1. Cross-table correlations (if any)
2. Recurring issues across sheets
3. Data quality trends""",
            
            "recommendation": f"""{base_context}

Based on this analysis, provide role-specific recommendations:

{analytics_summary}

Provide structured recommendations for:
- CRA (Clinical Research Associate): Site-level actions
- CTT (Clinical Trial Team): Data quality focus
- Management: Resource allocation priorities

Remember: All recommendations are ADVISORY ONLY. No automated actions.""",

            "qa": f"""{base_context}

Answer questions about this clinical trial data based on the analytics:

{analytics_summary}

Provide clear, specific answers referencing the data provided.""",

            "comparison": f"""{base_context}

Compare these two clinical trial studies:

{analytics_summary}

Analyze and provide:
1. Key differences in risk profiles between the studies
2. Which study has better data quality and why
3. Common issues appearing in both studies
4. Specific recommendations for each study
5. Which study requires more immediate attention

Be specific and reference actual numbers from the data."""
        }
        
        return prompts.get(prompt_type, prompts["summary"])
    
    def _fallback_insight(self, analytics_json: Dict, prompt_type: str) -> Dict:
        """Generate rule-based insight when Gemini is unavailable."""
        insight = "**AI Analysis (Rule-Based Fallback)**\n\n"
        
        # Handle both file-level and study-level JSON structures
        total_tables = analytics_json.get("total_tables", 0)
        
        # File-level structure
        if "issues_summary" in analytics_json:
            total_issues = analytics_json.get("issues_summary", {}).get("total_issues", 0)
            high_severity = analytics_json.get("issues_summary", {}).get("by_severity", {}).get("High", 0)
            risk_level = analytics_json.get("risk_level", "Unknown")
        # Study-level structure
        else:
            total_issues = analytics_json.get("unique_issues", 0)
            high_severity = analytics_json.get("issues_by_severity", {}).get("High", 0)
            risk_level = analytics_json.get("risk_level", "Unknown")
            total_tables = analytics_json.get("total_tables", 0)
        
        # Study-specific fields
        study_name = analytics_json.get("study_name")
        total_files = analytics_json.get("total_files", 0)
        sites_affected = analytics_json.get("sites_affected", 0)
        
        if prompt_type in ["summary", "study_insight"]:
            if study_name:
                insight += f"**Study:** {study_name}\n"
                insight += f"**Files Analyzed:** {total_files}\n"
                insight += f"**Sites Affected:** {sites_affected}\n\n"
            
            insight += f"**Risk Level:** {risk_level}\n\n"
            insight += f"**Key Metrics:**\n"
            insight += f"- {total_tables} tables extracted and analyzed\n"
            insight += f"- {total_issues} unique issues detected (de-duplicated)\n"
            insight += f"- {high_severity} high severity issues requiring attention\n\n"
            
            if high_severity > 0:
                insight += "**Recommendation:** Prioritize review of high-severity issues before database lock.\n"
            else:
                insight += "**Status:** No critical issues detected. Continue routine monitoring.\n"
        
        elif prompt_type == "explanation":
            insight += f"This {'study' if study_name else 'file'} is classified as **{risk_level}** because:\n\n"
            
            if high_severity > 3:
                insight += "- Multiple high-severity issues indicate significant data quality concerns\n"
            elif high_severity > 0:
                insight += "- Some high-severity issues require attention\n"
            
            if total_issues > 20:
                insight += "- High volume of total issues across tables\n"
            
            insight += f"\nThe analysis covered {total_tables} tables"
            if total_files > 0:
                insight += f" across {total_files} files"
            insight += ".\n"
        
        elif prompt_type == "recommendation":
            insight += "**Role-Based Recommendations:**\n\n"
            insight += "**CRA:** Review flagged sites and schedule monitoring visits as needed.\n\n"
            insight += "**CTT:** Focus on resolving high-severity data quality issues first.\n\n"
            insight += "**Management:** Monitor overall study risk metrics in weekly reviews.\n"
        
        return {
            "success": True,
            "insight": insight,
            "prompt_type": prompt_type,
            "fallback": True
        }
    
    def _summarize_input(self, analytics_json: Dict) -> str:
        """Create a brief summary of input data (for audit trail)."""
        return f"Tables: {analytics_json.get('total_tables', 0)}, Issues: {analytics_json.get('issues_summary', {}).get('total_issues', 0)}"
    
    def answer_question(self, question: str, analytics_json: Dict) -> Dict:
        """Answer a specific question about the analytics data."""
        if not self.is_available:
            return self._fallback_qa(question, analytics_json)
        
        try:
            prompt = f"""{self._build_prompt(analytics_json, "qa")}

User Question: {question}

Provide a clear, specific answer based only on the data provided above."""
            
            response = self.model.generate_content(prompt)
            
            return {
                "success": True,
                "answer": response.text,
                "question": question
            }
        except Exception as e:
            return self._fallback_qa(question, analytics_json)
    
    def _fallback_qa(self, question: str, analytics_json: Dict) -> Dict:
        """Fallback Q&A when Gemini unavailable."""
        question_lower = question.lower()
        
        total_tables = analytics_json.get("total_tables", 0)
        total_issues = analytics_json.get("issues_summary", {}).get("total_issues", 0)
        risk_level = analytics_json.get("risk_level", "Unknown")
        
        if "risk" in question_lower:
            answer = f"The current risk level is **{risk_level}** based on {total_issues} detected issues across {total_tables} tables."
        elif "table" in question_lower or "extract" in question_lower:
            answer = f"**{total_tables} tables** were extracted from this file across multiple sheets."
        elif "issue" in question_lower:
            answer = f"**{total_issues} issues** were detected. Check the Issues tab for full traceability."
        else:
            answer = f"This file has {total_tables} extracted tables with {total_issues} issues. Risk level: {risk_level}."
        
        return {
            "success": True,
            "answer": answer,
            "question": question,
            "fallback": True
        }
