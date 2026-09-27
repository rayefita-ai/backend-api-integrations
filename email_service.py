import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

__all__ = ['send_email_notification', 'get_templated_email']


def send_email_notification(recipient_email, subject, body, user_id=None):
    """
    Sends an email notification via SMTP and logs the message if user_id is provided.
    """
    sender_email = os.environ.get('MAIL_USERNAME')
    sender_password = os.environ.get('MAIL_PASSWORD')

    if not sender_email or not sender_password:
        print("Email configuration missing (MAIL_USERNAME/MAIL_PASSWORD).")
        return False

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
    server.starttls()
    server.login(sender_email, sender_password)
    server.send_message(msg)
    server.quit()

    # Audit Logging
    if user_id:
        try:
            from app import get_db_connection, get_cursor
            conn, db_type = get_db_connection()
            c = get_cursor(conn, db_type)
            c.execute("INSERT INTO email_logs (user_id, subject, body) VALUES (%s, %s, %s)", (user_id, subject, body))
            conn.commit()
            conn.close()
        except Exception as log_err:
            print(f"Log Error: {log_err}")

    return True


def get_templated_email(event_type, name, admin_text=None):
    """
    Retrieves and formats an email template from the database based on the event type.
    """
    try:
        from app import get_db_connection, get_cursor
        conn, db_type = get_db_connection()
        c = get_cursor(conn, db_type)
        c.execute("SELECT subject, body FROM email_templates WHERE event_type = %s", (event_type,))
        row = c.fetchone()
        conn.close()

        if row:
            subject = row[0].replace('{{name}}', name)
            body = row[1].replace('{{name}}', name)
            if admin_text:
                body = body.replace('{{admin_text}}', admin_text)
            return subject, body
    finally:
        if 'conn' in locals() and conn:
            conn.close()
    return None, None
