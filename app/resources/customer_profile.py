# resources/customer_profile.py
from flask_restful import Resource, request
from flask_praetorian import auth_required, current_user
from flask import request as flask_request
from ..models.user import User
from ..extensions import db
from datetime import datetime

def safe_str(v): return v if v is not None else ""

class CustomerGetProfileResource(Resource):
    @auth_required
    def get(self):
        """Get customer profile information"""
        current_customer = current_user()
        
        if current_customer.role != "customer":
            return {"error": "Unauthorized"}, 403
        
        return {
            "id": current_customer.id,
            "customer_id": safe_str(current_customer.customer_id),
            "full_name": safe_str(current_customer.full_name),
            "email": safe_str(current_customer.business_email or current_customer.email),
            "phone": safe_str(current_customer.phone),
            "business_name": safe_str(current_customer.business_name),
            "city": safe_str(current_customer.city),
            "address": safe_str(current_customer.address),
            "gps": safe_str(current_customer.gps),
            "status": safe_str(current_customer.status),
            "kyc_status": safe_str(current_customer.kyc_status),
            "income_range": safe_str(current_customer.income_range),
            "created_at": current_customer.created_at.isoformat() if current_customer.created_at else "",
            "total_spent": float(current_customer.total_sales or 0),
            "active_plans_count": 0
        }


class CustomerUpdateProfileResource(Resource):
    @auth_required
    def put(self):
        """Update customer profile information"""
        current_customer = current_user()
        
        if current_customer.role != "customer":
            return {"error": "Unauthorized"}, 403
        
        data = request.get_json()
        
        allowed_fields = ['full_name', 'business_name', 'email', 'city', 'address', 'gps', 'income_range']
        
        for field in allowed_fields:
            if field in data:
                setattr(current_customer, field, data[field])
        
        db.session.commit()
        
        return {"message": "Profile updated successfully"}, 200


class CustomerUpdatePasswordResource(Resource):
    @auth_required
    def put(self):
        """Update customer password"""
        current_customer = current_user()
        
        if current_customer.role != "customer":
            return {"error": "Unauthorized"}, 403
        
        data = request.get_json()
        current_password = data.get('current_password')
        new_password = data.get('new_password')
        
        if not current_password or not new_password:
            return {"error": "Current password and new password are required"}, 400
        
        # Verify current password
        from flask_praetorian import Praetorian
        guard = Praetorian()
        
        if not guard.authenticate(current_customer.phone, current_password):
            return {"error": "Current password is incorrect"}, 401
        
        if len(new_password) < 6:
            return {"error": "New password must be at least 6 characters"}, 400
        
        # Update password
        current_customer.password = guard.encrypt_password(new_password)
        db.session.commit()
        
        return {"message": "Password updated successfully"}, 200


class CustomerGetKYCStatusResource(Resource):
    @auth_required
    def get(self):
        """Get customer KYC status"""
        current_customer = current_user()
        
        if current_customer.role != "customer":
            return {"error": "Unauthorized"}, 403
        
        return {
            "status": safe_str(current_customer.kyc_status or 'not_submitted'),
            "level": safe_str(current_customer.verification_level or 'basic'),
            "submitted_at": current_customer.kyc_completed_on.isoformat() if current_customer.kyc_completed_on else None,
            "verified_at": current_customer.kyc_completed_on.isoformat() if current_customer.kyc_status == 'verified' else None,
            "rejection_reason": None
        }


class CustomerUploadKYCResource(Resource):
    @auth_required
    def post(self):
        """Upload KYC document"""
        current_customer = current_user()
        
        if current_customer.role != "customer":
            return {"error": "Unauthorized"}, 403
        
        # In production, handle file upload to cloud storage
        # For now, just update status
        document_type = request.form.get('document_type')
        
        if not document_type:
            return {"error": "Document type is required"}, 400
        
        # Update KYC status to pending if not already
        if current_customer.kyc_status in [None, 'not_submitted', 'rejected']:
            current_customer.kyc_status = 'pending'
            db.session.commit()
        
        return {
            "message": "Document uploaded successfully",
            "document_type": document_type,
            "status": "pending"
        }, 200


class CustomerGetActivityLogResource(Resource):
    @auth_required
    def get(self):
        """Get customer activity log"""
        current_customer = current_user()
        
        if current_customer.role != "customer":
            return {"error": "Unauthorized"}, 403
        
        # You can create an ActivityLog model or return sample data
        # For now, return sample activity logs
        return {
            "activities": [
                {
                    "id": 1,
                    "action": "Login",
                    "description": "Successful login",
                    "ip_address": flask_request.remote_addr,
                    "created_at": datetime.now().isoformat()
                },
                {
                    "id": 2,
                    "action": "Profile Update",
                    "description": "Updated profile information",
                    "ip_address": flask_request.remote_addr,
                    "created_at": datetime.now().isoformat()
                }
            ]
        }


