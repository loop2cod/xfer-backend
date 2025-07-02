import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template
from typing import List, Optional
import logging
import ssl

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self):
        self.smtp_server = settings.SMTP_SERVER
        self.smtp_port = settings.SMTP_PORT
        self.username = settings.SMTP_USERNAME
        self.password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USERNAME
        self.from_name = settings.SMTP_FROM_NAME
        
        # Debug logging
        logger.info(f"Email service initialized with server: {self.smtp_server}, port: {self.smtp_port}")
        if self.username:
            logger.info(f"Using username: {self.username}")
        else:
            logger.warning("No SMTP username configured")

    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send an email with HTML content"""
        if not self.username or not self.password:
            logger.error("SMTP credentials not configured")
            return False

        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email

            # Add text content if provided
            if text_content:
                text_part = MIMEText(text_content, "plain")
                message.attach(text_part)

            # Add HTML content
            html_part = MIMEText(html_content, "html")
            message.attach(html_part)

            # Configure SSL context based on port
            if self.smtp_port == 465:
                # Port 465 uses direct SSL connection
                try:
                    context = ssl.create_default_context()
                    await aiosmtplib.send(
                        message,
                        hostname=self.smtp_server,
                        port=self.smtp_port,
                        use_tls=True,
                        username=self.username,
                        password=self.password,
                        tls_context=context,
                    )
                    logger.info(f"Email sent successfully to {to_email} using SSL (port 465)")
                    return True
                except Exception as e:
                    logger.warning(f"SSL connection failed, trying with relaxed SSL: {e}")
                    # Fallback with relaxed SSL - catch all exceptions, not just SSLError
                    try:
                        context = ssl.create_default_context()
                        context.check_hostname = False
                        context.verify_mode = ssl.CERT_NONE
                        
                        await aiosmtplib.send(
                            message,
                            hostname=self.smtp_server,
                            port=self.smtp_port,
                            use_tls=True,
                            username=self.username,
                            password=self.password,
                            tls_context=context,
                        )
                        logger.warning(f"Email sent successfully to {to_email} using relaxed SSL (port 465)")
                        return True
                    except Exception as e:
                        logger.error(f"Failed to send email using SSL (port 465): {e}")
                        return False
            else:
                # Port 587 uses STARTTLS
                try:
                    context = ssl.create_default_context()
                    await aiosmtplib.send(
                        message,
                        hostname=self.smtp_server,
                        port=self.smtp_port,
                        start_tls=True,
                        username=self.username,
                        password=self.password,
                        tls_context=context,
                    )
                    logger.info(f"Email sent successfully to {to_email} using STARTTLS (port 587)")
                    return True
                except Exception as e:
                    logger.warning(f"STARTTLS connection failed, trying with relaxed SSL: {e}")
                    # Fallback with relaxed SSL - catch all exceptions, not just SSLError
                    try:
                        context = ssl.create_default_context()
                        context.check_hostname = False
                        context.verify_mode = ssl.CERT_NONE
                        
                        await aiosmtplib.send(
                            message,
                            hostname=self.smtp_server,
                            port=self.smtp_port,
                            start_tls=True,
                            username=self.username,
                            password=self.password,
                            tls_context=context,
                        )
                        logger.warning(f"Email sent successfully to {to_email} using relaxed STARTTLS")
                        return True
                    except Exception as e:
                        logger.error(f"Failed to send email using STARTTLS: {e}")
                        return False

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False

    async def send_verification_email(self, to_email: str, verification_code: str) -> bool:
        """Send verification code email with professional HTML template"""
        subject = "Verify Your Email - LTSND"
    
        html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Email Verification - LTSND</title>
    </head>
    <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f8fafc; line-height: 1.6;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 40px 30px; text-align: center;">
                <h1 style="color: #ffffff; font-size: 32px; font-weight: bold; margin: 0; letter-spacing: 2px;">LTSND</h1>
            </div>
            
            <div style="padding: 40px 30px; text-align: center;">
                <h2 style="font-size: 24px; color: #2d3748; margin-bottom: 20px; font-weight: 600;">Welcome to Xfer!</h2>
                <p style="font-size: 16px; color: #4a5568; margin-bottom: 30px; line-height: 1.5;">
                    Thank you for choosing LETSND for your financial transfers. To complete your account setup, 
                    please verify your email address using the verification code below.
                </p>
                
                <div style="background-color: #f7fafc; border: 2px dashed #e2e8f0; border-radius: 12px; padding: 30px; margin: 30px 0; text-align: center;">
                    <div style="font-size: 36px; font-weight: bold; color: #667eea; font-family: 'Courier New', monospace; letter-spacing: 8px; margin: 0; text-shadow: 0 2px 4px rgba(102, 126, 234, 0.2);">{{ verification_code }}</div>
                    <div style="font-size: 14px; color: #718096; margin-top: 10px; text-transform: uppercase; letter-spacing: 1px;">Verification Code</div>
                </div>
                
                <div style="background-color: #fef5e7; color: #744210; padding: 15px; border-radius: 8px; font-size: 8px; margin: 20px 0; border-left: 4px solid #f6ad55;">
                    ⏰ <strong>Important:</strong> This verification code will expire in 10 minutes for security reasons.
                </div>
                
                <div style="background-color: #ebf8ff; color: #2c5282; padding: 15px; border-radius: 8px; font-size: 8px; margin: 20px 0; border-left: 4px solid #4299e1;">
                    🛡️ <strong>Security Tip:</strong> Never share this code with anyone. LETSND will never ask for your verification code via phone or email.
                </div>
                
                <p style="font-size: 6px; color: #4a5568; margin-bottom: 30px; line-height: 1.5;">
                    If you didn't request this verification code, please ignore this email. 
                    Your account will remain secure and no action is required.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    # Render template with verification code
        template = Template(html_template)
        html_content = template.render(verification_code=verification_code)
    
    # Plain text fallback
        text_content = f"""
    Welcome to Xfer!
    
    Your verification code is: {verification_code}
    
    This code will expire in 10 minutes.
    
    If you didn't request this code, please ignore this email.
    
    Best regards,
    The Xfer Team
    """
    
        return await self.send_email(
        to_email=to_email,
        subject=subject,
        html_content=html_content,
        text_content=text_content
        )


# Global email service instance
email_service = EmailService()