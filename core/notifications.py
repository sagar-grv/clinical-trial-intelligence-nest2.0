"""
Notification Service - Email/Slack notifications for clinical trial alerts
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional
from datetime import datetime


class NotificationService:
    """Handles email and messaging notifications for alerts."""
    
    def __init__(self):
        self.email_config = {
            "smtp_server": "",
            "smtp_port": 587,
            "sender_email": "",
            "sender_password": "",
            "enabled": False
        }
        self.notification_log = []
    
    def configure_email(self, smtp_server: str, smtp_port: int, 
                       sender_email: str, sender_password: str):
        """Configure email settings."""
        self.email_config = {
            "smtp_server": smtp_server,
            "smtp_port": smtp_port,
            "sender_email": sender_email,
            "sender_password": sender_password,
            "enabled": True
        }
    
    def is_configured(self) -> bool:
        """Check if email is configured."""
        return self.email_config.get("enabled", False)
    
    def send_email(self, recipients: List[str], subject: str, body: str, 
                   html_body: Optional[str] = None) -> Dict:
        """Send email notification."""
        result = {
            "success": False,
            "message": "",
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if not self.is_configured():
            result["message"] = "Email not configured"
            return result
        
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.email_config["sender_email"]
            msg["To"] = ", ".join(recipients)
            
            # Add text body
            text_part = MIMEText(body, "plain")
            msg.attach(text_part)
            
            # Add HTML body if provided
            if html_body:
                html_part = MIMEText(html_body, "html")
                msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.email_config["smtp_server"], 
                            self.email_config["smtp_port"]) as server:
                server.starttls()
                server.login(self.email_config["sender_email"], 
                           self.email_config["sender_password"])
                server.sendmail(self.email_config["sender_email"], 
                              recipients, msg.as_string())
            
            result["success"] = True
            result["message"] = f"Email sent to {len(recipients)} recipients"
            
            # Log notification
            self.notification_log.append({
                "type": "email",
                "recipients": recipients,
                "subject": subject,
                "timestamp": result["timestamp"],
                "success": True
            })
            
        except Exception as e:
            result["message"] = f"Email failed: {str(e)}"
            self.notification_log.append({
                "type": "email",
                "recipients": recipients,
                "subject": subject,
                "timestamp": result["timestamp"],
                "success": False,
                "error": str(e)
            })
        
        return result
    
    def send_alert_notification(self, alert: Dict, recipients: List[str]) -> Dict:
        """Send notification for a specific alert."""
        severity_icons = {
            "critical": "🔴",
            "warning": "🟡",
            "info": "🔵"
        }
        
        icon = severity_icons.get(alert.get("severity", "info"), "🔵")
        
        subject = f"{icon} Clinical Trial Alert: {alert.get('title', 'Alert')}"
        
        body = f"""
Clinical Trial Intelligence Alert
==================================

{alert.get('title', 'Alert')}

Severity: {alert.get('severity', 'Unknown').upper()}
Type: {alert.get('alert_type', 'Unknown')}

Message:
{alert.get('message', 'No message')}

Rule Details:
- Rule ID: {alert.get('rule_id', 'N/A')}
- Threshold: {alert.get('threshold_value', 'N/A')}
- Actual Value: {alert.get('actual_value', 'N/A')}

Generated: {alert.get('created_at', 'Unknown')}

---
This is an automated notification from the Clinical Trial Intelligence system.
"""
        
        html_body = f"""
<html>
<body style="font-family: Arial, sans-serif; background: #f5f5f5; padding: 20px;">
<div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; overflow: hidden;">
    <div style="background: {'#ef4444' if alert.get('severity') == 'critical' else '#f59e0b' if alert.get('severity') == 'warning' else '#3b82f6'}; 
                color: white; padding: 20px; text-align: center;">
        <h1 style="margin: 0;">{icon} Clinical Trial Alert</h1>
    </div>
    <div style="padding: 20px;">
        <h2>{alert.get('title', 'Alert')}</h2>
        <p><strong>Severity:</strong> {alert.get('severity', 'Unknown').upper()}</p>
        <p>{alert.get('message', 'No message')}</p>
        
        <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
            <h4 style="margin-top: 0;">Rule Evidence</h4>
            <p><strong>Rule ID:</strong> <code>{alert.get('rule_id', 'N/A')}</code></p>
            <p><strong>Threshold:</strong> {alert.get('threshold_value', 'N/A')}</p>
            <p><strong>Actual Value:</strong> {alert.get('actual_value', 'N/A')}</p>
        </div>
        
        <p style="color: #666; font-size: 12px;">
            Generated: {alert.get('created_at', 'Unknown')}
        </p>
    </div>
    <div style="background: #f8f9fa; padding: 10px; text-align: center; font-size: 12px; color: #666;">
        Clinical Trial Intelligence - Enterprise Edition
    </div>
</div>
</body>
</html>
"""
        
        return self.send_email(recipients, subject, body, html_body)
    
    def send_digest(self, study_name: str, alerts: List[Dict], 
                   recipients: List[str]) -> Dict:
        """Send daily/weekly digest of alerts."""
        subject = f"📊 Clinical Trial Digest: {study_name}"
        
        alert_summary = "\n".join([
            f"- [{a.get('severity', '').upper()}] {a.get('title', 'Alert')}"
            for a in alerts
        ])
        
        body = f"""
Clinical Trial Intelligence - Alert Digest
===========================================

Study: {study_name}
Total Active Alerts: {len(alerts)}

Summary:
{alert_summary}

---
This is an automated digest from the Clinical Trial Intelligence system.
"""
        
        return self.send_email(recipients, subject, body)
    
    def get_notification_log(self, limit: int = 20) -> List[Dict]:
        """Get recent notification history."""
        return self.notification_log[-limit:][::-1]  # Newest first
    
    def queue_notification(self, alert: Dict, recipients: List[str], 
                          delay_minutes: int = 0) -> Dict:
        """Queue a notification (for batching multiple alerts)."""
        # In production, this would use a proper queue like Celery/Redis
        # For now, just log it and return
        queued = {
            "alert_id": alert.get("alert_id"),
            "recipients": recipients,
            "delay_minutes": delay_minutes,
            "queued_at": datetime.utcnow().isoformat(),
            "status": "queued"
        }
        self.notification_log.append(queued)
        return queued


# Singleton instance
notification_service = NotificationService()


def get_notification_service() -> NotificationService:
    """Get the notification service singleton."""
    return notification_service
