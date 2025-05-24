#!/usr/bin/env python3
"""
Email Notification Hook
This script sends email notifications when Codex events occur
"""

import os
import smtplib
import sys
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Configuration - Set these environment variables
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
EMAIL_TO = os.getenv('EMAIL_TO', '')
EMAIL_FROM = os.getenv('EMAIL_FROM', SMTP_USERNAME)

# Codex event data
EVENT_TYPE = os.getenv('CODEX_EVENT_TYPE', '')
SESSION_ID = os.getenv('CODEX_SESSION_ID', '')
TIMESTAMP = os.getenv('CODEX_TIMESTAMP', '')

def send_email(subject, body):
    """Send email notification"""
    if not all([SMTP_USERNAME, SMTP_PASSWORD, EMAIL_TO]):
        print("Error: Email configuration incomplete")
        print("Please set SMTP_USERNAME, SMTP_PASSWORD, and EMAIL_TO environment variables")
        return False
    
    try:
        # Create message
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = EMAIL_TO
        msg['Subject'] = subject
        
        # Add body to email
        msg.attach(MIMEText(body, 'plain'))
        
        # Create SMTP session
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()  # Enable security
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        
        # Send email
        text = msg.as_string()
        server.sendmail(EMAIL_FROM, EMAIL_TO, text)
        server.quit()
        
        print(f"Email notification sent to {EMAIL_TO}")
        return True
        
    except Exception as e:
        print(f"Error sending email: {e}")
        return False

def format_message():
    """Format the email message based on event type"""
    timestamp = datetime.fromisoformat(TIMESTAMP.replace('Z', '+00:00')) if TIMESTAMP else datetime.now()
    
    if EVENT_TYPE == 'session_start':
        model = os.getenv('CODEX_MODEL', 'unknown')
        provider = os.getenv('CODEX_PROVIDER', 'openai')
        subject = f"Codex Session Started - {SESSION_ID}"
        body = f"""
Codex session has started.

Session ID: {SESSION_ID}
Model: {model}
Provider: {provider}
Timestamp: {timestamp}
"""
    
    elif EVENT_TYPE == 'session_end':
        duration = os.getenv('CODEX_DURATION', '')
        subject = f"Codex Session Ended - {SESSION_ID}"
        duration_text = f"\nDuration: {int(duration) // 1000}s" if duration else ""
        body = f"""
Codex session has ended.

Session ID: {SESSION_ID}
Timestamp: {timestamp}{duration_text}
"""
    
    elif EVENT_TYPE == 'task_start':
        task_id = os.getenv('CODEX_TASK_ID', '')
        prompt = os.getenv('CODEX_PROMPT', '')
        subject = f"Codex Task Started - {task_id}"
        body = f"""
A new Codex task has started.

Session ID: {SESSION_ID}
Task ID: {task_id}
Prompt: {prompt}
Timestamp: {timestamp}
"""
    
    elif EVENT_TYPE == 'task_end':
        task_id = os.getenv('CODEX_TASK_ID', '')
        success = os.getenv('CODEX_SUCCESS', 'false') == 'true'
        status = "Successfully" if success else "Failed"
        subject = f"Codex Task {status} - {task_id}"
        body = f"""
Codex task has completed.

Session ID: {SESSION_ID}
Task ID: {task_id}
Status: {status}
Timestamp: {timestamp}
"""
    
    elif EVENT_TYPE == 'error':
        error = os.getenv('CODEX_ERROR', '')
        context = os.getenv('CODEX_CONTEXT', '')
        subject = f"Codex Error - {SESSION_ID}"
        context_text = f"\nContext: {context}" if context else ""
        body = f"""
An error occurred in Codex.

Session ID: {SESSION_ID}
Error: {error}{context_text}
Timestamp: {timestamp}
"""
    
    else:
        subject = f"Codex Event - {EVENT_TYPE}"
        body = f"""
Codex event occurred.

Session ID: {SESSION_ID}
Event Type: {EVENT_TYPE}
Timestamp: {timestamp}
"""
    
    return subject, body.strip()

def main():
    """Main function"""
    if not EVENT_TYPE:
        print("Error: CODEX_EVENT_TYPE not set")
        sys.exit(1)
    
    subject, body = format_message()
    success = send_email(subject, body)
    
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
