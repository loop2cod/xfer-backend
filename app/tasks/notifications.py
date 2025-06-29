import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio
import logging
from typing import Optional

from app.worker import celery_app
from app.db.database import AsyncSessionLocal
from app.models.user import User
from app.models.transfer import TransferRequest
from app.core.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(name="app.tasks.notifications.send_transfer_notification")
def send_transfer_notification(transfer_id: str, notification_type: str):
    """Send transfer notification to user"""
    return asyncio.run(_send_transfer_notification_async(transfer_id, notification_type))


async def _send_transfer_notification_async(transfer_id: str, notification_type: str):
    """Send transfer notification async"""
    async with AsyncSessionLocal() as db:
        try:
            # Get transfer with user info
            result = await db.execute(
                select(TransferRequest, User).join(User).where(TransferRequest.id == transfer_id)
            )
            transfer_user = result.first()
            
            if not transfer_user:
                logger.error(f"Transfer {transfer_id} or user not found")
                return {"status": "error", "message": "Transfer or user not found"}
            
            transfer, user = transfer_user
            
            # Prepare email content based on notification type
            subject, body = _prepare_email_content(transfer, user, notification_type)
            
            if not subject or not body:
                return {"status": "error", "message": "Invalid notification type"}
            
            # Send email
            email_sent = await _send_email(user.email, subject, body)
            
            if email_sent:
                logger.info(f"Notification sent to {user.email} for transfer {transfer_id}")
                return {"status": "success", "message": "Notification sent"}
            else:
                return {"status": "error", "message": "Failed to send email"}
            
        except Exception as e:
            logger.error(f"Error sending notification for transfer {transfer_id}: {e}")
            return {"status": "error", "message": str(e)}


@celery_app.task(name="app.tasks.notifications.send_kyc_notification")
def send_kyc_notification(user_id: str, kyc_status: str):
    """Send KYC status notification"""
    return asyncio.run(_send_kyc_notification_async(user_id, kyc_status))


async def _send_kyc_notification_async(user_id: str, kyc_status: str):
    """Send KYC notification async"""
    async with AsyncSessionLocal() as db:
        try:
            # Get user
            result = await db.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            
            if not user:
                logger.error(f"User {user_id} not found")
                return {"status": "error", "message": "User not found"}
            
            # Prepare email content
            subject, body = _prepare_kyc_email_content(user, kyc_status)
            
            # Send email
            email_sent = await _send_email(user.email, subject, body)
            
            if email_sent:
                logger.info(f"KYC notification sent to {user.email}")
                return {"status": "success", "message": "KYC notification sent"}
            else:
                return {"status": "error", "message": "Failed to send email"}
            
        except Exception as e:
            logger.error(f"Error sending KYC notification for user {user_id}: {e}")
            return {"status": "error", "message": str(e)}


def _prepare_email_content(transfer: TransferRequest, user: User, notification_type: str) -> tuple[Optional[str], Optional[str]]:
    """Prepare email content based on notification type"""
    
    user_name = f"{user.first_name} {user.last_name}".strip() or user.email
    
    if notification_type == "transfer_created":
        subject = "Transfer Request Created - Xfer"
        body = f"""
Dear {user_name},

Your transfer request has been created successfully.

Transfer Details:
- ID: {transfer.id}
- Type: {transfer.type.replace('-', ' to ').title()}
- Amount: {transfer.amount} {transfer.currency}
- Fee: {transfer.fee} {transfer.currency}
- Net Amount: {transfer.net_amount} {transfer.currency}
- Status: {transfer.status.title()}

We will process your request shortly and notify you of any updates.

Best regards,
Xfer Team
        """
    
    elif notification_type == "transfer_completed":
        subject = "Transfer Completed - Xfer"
        body = f"""
Dear {user_name},

Great news! Your transfer has been completed successfully.

Transfer Details:
- ID: {transfer.id}
- Amount: {transfer.amount} {transfer.currency}
- Net Amount: {transfer.net_amount} {transfer.currency}
- Status: Completed
- Completed At: {transfer.completed_at}

Thank you for using Xfer!

Best regards,
Xfer Team
        """
    
    elif notification_type == "transfer_failed":
        subject = "Transfer Failed - Xfer"
        body = f"""
Dear {user_name},

Unfortunately, your transfer request has failed.

Transfer Details:
- ID: {transfer.id}
- Amount: {transfer.amount} {transfer.currency}
- Status: Failed
- Reason: {transfer.status_message or 'Processing error'}

Please contact our support team if you need assistance.

Best regards,
Xfer Team
        """
    
    elif notification_type == "transfer_processing":
        subject = "Transfer Processing - Xfer"
        body = f"""
Dear {user_name},

Your transfer is now being processed.

Transfer Details:
- ID: {transfer.id}
- Amount: {transfer.amount} {transfer.currency}
- Status: Processing
- Confirmations: {transfer.confirmation_count}/{transfer.required_confirmations}

We'll notify you once the transfer is completed.

Best regards,
Xfer Team
        """
    
    else:
        return None, None
    
    return subject, body


def _prepare_kyc_email_content(user: User, kyc_status: str) -> tuple[str, str]:
    """Prepare KYC email content"""
    
    user_name = f"{user.first_name} {user.last_name}".strip() or user.email
    
    if kyc_status == "approved":
        subject = "KYC Approved - Xfer"
        body = f"""
Dear {user_name},

Congratulations! Your KYC verification has been approved.

You can now access all features of your Xfer account, including:
- Higher transfer limits
- Faster processing times
- Premium support

Thank you for completing the verification process.

Best regards,
Xfer Team
        """
    
    elif kyc_status == "rejected":
        subject = "KYC Review Required - Xfer"
        body = f"""
Dear {user_name},

We need additional information to complete your KYC verification.

Please log in to your account and review the requirements. If you have questions, please contact our support team.

Best regards,
Xfer Team
        """
    
    else:  # pending
        subject = "KYC Submitted - Xfer"
        body = f"""
Dear {user_name},

Thank you for submitting your KYC documents.

We are currently reviewing your information and will notify you once the verification is complete. This process typically takes 1-3 business days.

Best regards,
Xfer Team
        """
    
    return subject, body


async def _send_email(to_email: str, subject: str, body: str) -> bool:
    """Send email using SMTP"""
    try:
        if not all([settings.SMTP_SERVER, settings.SMTP_USERNAME, settings.SMTP_PASSWORD]):
            logger.warning("Email configuration incomplete, skipping email send")
            return False
        
        # Create message
        msg = MIMEMultipart()
        msg['From'] = settings.SMTP_USERNAME
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        # Send email
        server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        text = msg.as_string()
        server.sendmail(settings.SMTP_USERNAME, to_email, text)
        server.quit()
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False