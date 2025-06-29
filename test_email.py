#!/usr/bin/env python3
"""
Test script for email functionality
Run this to test if Gmail SMTP is working with your credentials
"""

import asyncio
import os
from app.services.email import email_service
from app.core.config import settings

async def test_email():
    """Test email sending functionality"""
    
    print("🧪 Testing Email Configuration...")
    print("-" * 50)
    
    # Check configuration
    print(f"SMTP Server: {settings.SMTP_SERVER}")
    print(f"SMTP Port: {settings.SMTP_PORT}")
    print(f"SMTP Username: {settings.SMTP_USERNAME}")
    print(f"SMTP Password: {'*' * len(settings.SMTP_PASSWORD) if settings.SMTP_PASSWORD else 'NOT SET'}")
    print(f"From Email: {settings.SMTP_FROM_EMAIL}")
    print(f"From Name: {settings.SMTP_FROM_NAME}")
    print()
    
    if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
        print("❌ Error: Gmail credentials not configured in .env file")
        print("Please update your .env file with:")
        print("SMTP_USERNAME=your-gmail@gmail.com")
        print("SMTP_PASSWORD=your-16-character-app-password")
        return
    
    # Test email address (you can change this)
    test_email = input(f"Enter test email address (press Enter to use {settings.SMTP_USERNAME}): ").strip()
    if not test_email:
        test_email = settings.SMTP_USERNAME
    
    print(f"\n📧 Sending test verification email to: {test_email}")
    print("This may take a few seconds...")
    
    try:
        # Send test verification email
        success = await email_service.send_verification_email(test_email, "123456")
        
        if success:
            print("✅ SUCCESS! Email sent successfully!")
            print(f"Check the inbox for {test_email}")
            print("You should see a professional verification email with code: 123456")
        else:
            print("❌ FAILED! Email could not be sent")
            print("Check the logs above for specific error details")
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        print("\nTroubleshooting tips:")
        print("1. Verify Gmail App Password is correct (16 characters)")
        print("2. Ensure 2-Factor Authentication is enabled on Gmail")
        print("3. Check if 'Less secure app access' is disabled (it should be)")
        print("4. Try generating a new App Password")
        print("5. Check your internet connection")

if __name__ == "__main__":
    print("📧 Gmail SMTP Test Tool")
    print("=" * 50)
    
    try:
        asyncio.run(test_email())
    except KeyboardInterrupt:
        print("\n👋 Test cancelled by user")
    
    print("\nFor more help, check SSL_CERTIFICATE_FIX.md")