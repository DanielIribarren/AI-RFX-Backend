"""
📧 Contact Request API - Email notifications for plan requests

Simple endpoint to send automated emails when users request plans.
Uses Flask-Mail for reliable email delivery.
"""
import os
import logging
from flask import Blueprint, request, jsonify
from flask_mail import Message
from typing import Dict, Any

from backend.utils.auth_middleware import jwt_required, get_current_user_id
from backend.core.database import get_database_client

logger = logging.getLogger(__name__)

# Blueprint
contact_bp = Blueprint('contact', __name__, url_prefix='/api')


def get_mail_instance():
    """Get Flask-Mail instance from app context"""
    from flask import current_app
    return current_app.extensions.get('mail')


@contact_bp.route('/contact-request', methods=['POST'])
@jwt_required
def send_contact_request():
    """
    📧 Send automated email for plan requests (AUTHENTICATED)
    
    POST /api/contact-request
    Headers: Authorization: Bearer <token>
    
    Request Body:
    {
        "plan_name": "Starter",
        "plan_price": "$49",
        "recipient_email": "iriyidan@gmail.com"
    }
    
    Note: user_email and user_name are obtained automatically from the authenticated user.
    
    Response:
    {
        "status": "success",
        "message": "Contact request sent successfully"
    }
    """
    try:
        # Get authenticated user ID from JWT
        user_id = get_current_user_id()
        
        if not user_id:
            return jsonify({
                'status': 'error',
                'message': 'User not authenticated'
            }), 401
        
        # Get user info from database
        db_client = get_database_client()
        user_data = db_client.client.table('users')\
            .select('email, full_name')\
            .eq('id', user_id)\
            .single()\
            .execute()
        
        if not user_data.data:
            logger.error(f"❌ User {user_id} not found in database")
            return jsonify({
                'status': 'error',
                'message': 'User not found'
            }), 404
        
        # Extract user info with fallbacks
        user_email = user_data.data.get('email')
        user_name = (
            user_data.data.get('full_name') or 
            user_email.split('@')[0].title() if user_email else 'User'
        )
        
        logger.info(f"📧 Contact request from authenticated user: {user_email} ({user_name})")
        
        # Get JSON data
        data = request.get_json()
        
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400
        
        # Validate required fields (now only plan info)
        required_fields = ['plan_name', 'plan_price', 'recipient_email']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return jsonify({
                'status': 'error',
                'message': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Get mail instance
        mail = get_mail_instance()
        if not mail:
            logger.error("❌ Flask-Mail not configured")
            return jsonify({
                'status': 'error',
                'message': 'Email service not configured'
            }), 500
        
        # Prepare email content
        subject = f"🎯 New Plan Request: {data['plan_name']} Plan"
        
        body = f"""
Hello,

A new plan request has been received from the checkout page.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
USER INFORMATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Name:  {user_name}
Email: {user_email}
User ID: {user_id}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PLAN DETAILS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Plan:  {data['plan_name']}
Price: {data['plan_price']}/month

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Please contact the user to set up this plan.

Best regards,
RFX Automation System
        """
        
        # Create message
        msg = Message(
            subject=subject,
            sender=os.getenv('MAIL_DEFAULT_SENDER', 'noreply@budyai.com'),
            recipients=[data['recipient_email']],
            body=body
        )
        
        # Send email
        mail.send(msg)
        
        logger.info(f"✅ Contact request email sent successfully to {data['recipient_email']}")
        logger.info(f"📋 Plan: {data['plan_name']} | User: {user_email} ({user_name})")
        
        return jsonify({
            'status': 'success',
            'message': 'Contact request sent successfully'
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error sending contact request email: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Failed to send email. Please try again or contact support.'
        }), 500


@contact_bp.route('/contact-request/test', methods=['GET'])
def test_email_config():
    """
    🧪 Test email configuration
    
    GET /api/contact-request/test
    
    Returns email configuration status (without sensitive data)
    """
    try:
        mail = get_mail_instance()
        
        if not mail:
            return jsonify({
                'status': 'error',
                'message': 'Flask-Mail not configured',
                'configured': False
            }), 500
        
        # Check environment variables (without exposing values)
        mail_server = os.getenv('MAIL_SERVER')
        mail_username = os.getenv('MAIL_USERNAME')
        mail_password = os.getenv('MAIL_PASSWORD')
        
        config_status = {
            'mail_server': bool(mail_server),
            'mail_username': bool(mail_username),
            'mail_password': bool(mail_password),
            'mail_server_value': mail_server if mail_server else 'Not configured',
        }
        
        all_configured = all([mail_server, mail_username, mail_password])
        
        return jsonify({
            'status': 'success' if all_configured else 'warning',
            'message': 'Email service configured' if all_configured else 'Email service partially configured',
            'configured': all_configured,
            'config': config_status
        }), 200
        
    except Exception as e:
        logger.error(f"❌ Error testing email config: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'configured': False
        }), 500
