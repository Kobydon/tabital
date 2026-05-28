from flask_restful import Resource, request
from flask_praetorian import auth_required, current_user
from ..models.user import User
from ..models.document import Document
from ..extensions import db
from datetime import datetime
import os
import base64
# resources/admin_kyc.py - Update the get method

class AdminGetPendingMerchantKYCResource(Resource):
    @auth_required
    def get(self):
        """Admin gets all pending merchant KYC verification requests"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        # Get merchants with pending KYC who have uploaded documents
        pending_merchants = User.query.filter(
            User.role == 'merchant',
            User.kyc_status == 'pending'
        ).all()
        
        result = []
        for merchant in pending_merchants:
            documents = Document.query.filter_by(
                user_id=merchant.id
            ).all()
            
            if documents:
                documents_data = []
                for doc in documents:
                    file_data = None
                    # Read the file and convert to base64
                    if doc.file_path and os.path.exists(doc.file_path):
                        try:
                            with open(doc.file_path, 'rb') as f:
                                file_data = base64.b64encode(f.read()).decode('utf-8')
                                print(f"Loaded file: {doc.file_name}, size: {len(file_data)} chars")
                        except Exception as e:
                            print(f"Error reading file {doc.file_path}: {str(e)}")
                            file_data = None
                    else:
                        print(f"File not found: {doc.file_path}")
                    
                    documents_data.append({
                        "id": doc.id,
                        "document_id": doc.document_id,
                        "document_name": doc.document_name,
                        "document_type": doc.document_type,
                        "status": doc.status,
                        "uploaded_at": doc.created_at.isoformat() if doc.created_at else "",
                        "file_data": file_data,  # Now includes base64 data
                        "file_name": doc.file_name,
                        "file_size": doc.file_size,
                        "mime_type": doc.mime_type,
                        "rejection_reason": doc.rejection_reason
                    })
                
                result.append({
                    "merchant_id": merchant.id,
                    "merchant_name": merchant.business_name or merchant.full_name,
                    "owner_name": merchant.owner_name,
                    "phone": merchant.phone,
                    "business_email": merchant.business_email or merchant.email,
                    "city": merchant.city,
                    "address": merchant.address,
                    "kyc_status": merchant.kyc_status,
                    "verification_level": merchant.verification_level or 'basic',
                    "submitted_at": min([d.created_at for d in documents]).isoformat() if documents else None,
                    "documents": documents_data,
                    "bank_details": {
                        "bank_name": merchant.bank_name,
                        "account_name": merchant.account_name,
                        "account_number": merchant.account_number,
                        "branch_name": merchant.branch_name,
                        "swift_code": merchant.swift_code,
                        "momo_name": merchant.momo_name,
                        "momo_number": merchant.momo_number
                    }
                })
        
        return {
            "pending_verifications": result,
            "total": len(result)
        }, 200

class AdminGetVerifiedKYCResource(Resource):
    @auth_required
    def get(self):
        """Get all verified merchants"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        verified_merchants = User.query.filter(
            User.role == 'merchant',
            User.kyc_status == 'verified'
        ).all()
        
        result = []
        for merchant in verified_merchants:
            result.append({
                "merchant_id": merchant.id,
                "merchant_name": merchant.business_name or merchant.full_name,
                "owner_name": merchant.owner_name,
                "phone": merchant.phone,
                "email": merchant.business_email or merchant.email,
                "kyc_status": merchant.kyc_status,
                "verified_at": merchant.kyc_completed_on.isoformat() if merchant.kyc_completed_on else None,
                "verification_level": merchant.verification_level
            })
        
        return {
            "verified_merchants": result,
            "total": len(result)
        }, 200


class AdminGetRejectedKYCResource(Resource):
    @auth_required
    def get(self):
        """Get all rejected merchants"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        rejected_merchants = User.query.filter(
            User.role == 'merchant',
            User.kyc_status == 'rejected'
        ).all()
        
        result = []
        for merchant in rejected_merchants:
            # Get rejection reason from documents
            rejected_docs = Document.query.filter_by(
                user_id=merchant.id,
                status='rejected'
            ).first()
            
            result.append({
                "merchant_id": merchant.id,
                "merchant_name": merchant.business_name or merchant.full_name,
                "owner_name": merchant.owner_name,
                "phone": merchant.phone,
                "email": merchant.business_email or merchant.email,
                "kyc_status": merchant.kyc_status,
                "rejection_reason": rejected_docs.rejection_reason if rejected_docs else None,
                "rejected_at": rejected_docs.verified_at.isoformat() if rejected_docs and rejected_docs.verified_at else None
            })
        
        return {
            "rejected_merchants": result,
            "total": len(result)
        }, 200
class AdminGetMerchantKYCResource(Resource):
    @auth_required
    def get(self, merchant_id):
        """Get specific merchant's KYC details"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        merchant = User.query.get(merchant_id)
        if not merchant or merchant.role != 'merchant':
            return {"error": "Merchant not found"}, 404
        
        documents = Document.query.filter_by(
            user_id=merchant.id
        ).order_by(Document.created_at.desc()).all()
        
        documents_data = []
        for doc in documents:
            file_data = None
            if doc.file_path and os.path.exists(doc.file_path):
                try:
                    with open(doc.file_path, 'rb') as f:
                        file_data = base64.b64encode(f.read()).decode('utf-8')
                except Exception as e:
                    print(f"Error reading file: {str(e)}")
                    file_data = None
            
            documents_data.append({
                "id": doc.id,
                "document_id": doc.document_id,
                "document_name": doc.document_name,
                "document_type": doc.document_type,
                "status": doc.status,
                "uploaded_at": doc.created_at.isoformat() if doc.created_at else None,
                "file_data": file_data,
                "file_name": doc.file_name,
                "file_size": doc.file_size,
                "mime_type": doc.mime_type,
                "rejection_reason": doc.rejection_reason,
                "verified_at": doc.verified_at.isoformat() if doc.verified_at else None,
                "verified_by": doc.verified_by
            })
        
        return {
            "merchant": {
                "id": merchant.id,
                "business_name": merchant.business_name,
                "owner_name": merchant.owner_name,
                "phone": merchant.phone,
                "email": merchant.business_email or merchant.email,
                "city": merchant.city,
                "address": merchant.address,
                "kyc_status": merchant.kyc_status,
                "verification_level": merchant.verification_level,
                "kyc_completed_on": merchant.kyc_completed_on.isoformat() if merchant.kyc_completed_on else None
            },
            "documents": documents_data,
            "bank_details": {
                "bank_name": merchant.bank_name,
                "account_name": merchant.account_name,
                "account_number": merchant.account_number,
                "branch_name": merchant.branch_name,
                "swift_code": merchant.swift_code,
                "momo_name": merchant.momo_name,
                "momo_number": merchant.momo_number
            }
        }, 200
# resources/admin_kyc.py

from flask_restful import Resource, request
from flask_praetorian import auth_required, current_user
from ..models.user import User
from ..models.document import Document
from app.models.notifications import Notifications
from ..extensions import db
from datetime import datetime
import os
import base64
import json

class AdminApproveKYCResource(Resource):
    @auth_required
    def put(self, merchant_id):
        """Approve a merchant's KYC verification"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        merchant = User.query.get(merchant_id)
        if not merchant or merchant.role != 'merchant':
            return {"error": "Merchant not found"}, 404
        
        try:
            # Update all documents to verified
            documents = Document.query.filter_by(user_id=merchant.id).all()
            for doc in documents:
                doc.status = 'verified'
                doc.verified_by = current_admin.id
                doc.verified_at = datetime.now()
            
            # Update merchant KYC status
            merchant.kyc_status = 'verified'
            merchant.verification_level = 'verified'
            merchant.kyc_completed_on = datetime.now()
            
            db.session.commit()
            
            # Create notification for the merchant
            notification_title = "✅ KYC Verification Approved"
            notification_message = f"""Congratulations! Your KYC verification has been approved. 
Your account is now fully verified and you can now:
• Add and manage products
• Receive payments
• Access all merchant features
• Apply for merchant loans

Thank you for completing your verification."""
            
            Notifications.create_notification(
                user_id=merchant.id,
                user_role='merchant',
                title=notification_title,
                message=notification_message,
                type='kyc',
                link='/merchant/dashboard',
                action_text='Go to Dashboard',
                extra_data={
                    'kyc_status': 'verified',
                    'approved_by': current_admin.id,
                    'approved_by_name': current_admin.full_name or 'Admin',
                    'approved_at': datetime.now().isoformat()
                }
            )
            
            # Also create notification for admin (optional)
            Notifications.create_notification(
                user_id=current_admin.id,
                user_role='admin',
                title=f"Merchant KYC Approved",
                message=f"KYC verification for {merchant.business_name or merchant.full_name} has been approved.",
                type='kyc',
                link='/admin/kyc-verification',
                action_text='View Details',
                extra_data={
                    'merchant_id': merchant.id,
                    'merchant_name': merchant.business_name or merchant.full_name,
                    'action': 'approved'
                }
            )
            
            return {
                "message": "KYC verification approved successfully",
                "merchant_id": merchant.id,
                "status": "verified",
                "notification_sent": True
            }, 200
            
        except Exception as e:
            db.session.rollback()
            print(f"Error approving KYC: {str(e)}")
            return {"error": f"Failed to approve KYC: {str(e)}"}, 500


class AdminRejectKYCResource(Resource):
    @auth_required
    def put(self, merchant_id):
        """Reject a merchant's KYC verification with reason"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        data = request.get_json()
        rejection_reason = data.get('rejection_reason', '')
        
        if not rejection_reason:
            return {"error": "Rejection reason is required"}, 400
        
        merchant = User.query.get(merchant_id)
        if not merchant or merchant.role != 'merchant':
            return {"error": "Merchant not found"}, 404
        
        try:
            # Update all documents to rejected
            documents = Document.query.filter_by(user_id=merchant.id).all()
            for doc in documents:
                doc.status = 'rejected'
                doc.rejection_reason = rejection_reason
                doc.verified_by = current_admin.id
                doc.verified_at = datetime.now()
            
            # Update merchant KYC status
            merchant.kyc_status = 'rejected'
            
            db.session.commit()
            
            # Create notification for the merchant
            notification_title = "❌ KYC Verification Rejected"
            notification_message = f"""Your KYC verification has been rejected.

Rejection Reason: {rejection_reason}

Please review the following issues:
• Ensure all documents are clear and readable
• Check that documents are not expired
• Verify that all information matches your business registration
• Make sure all required documents are uploaded

Please upload corrected documents for re-verification."""
            
            Notifications.create_notification(
                user_id=merchant.id,
                user_role='merchant',
                title=notification_title,
                message=notification_message,
                type='kyc',
                link='/merchant/documents',
                action_text='Upload Documents Again',
                extra_data={
                    'kyc_status': 'rejected',
                    'rejection_reason': rejection_reason,
                    'rejected_by': current_admin.id,
                    'rejected_by_name': current_admin.full_name or 'Admin',
                    'rejected_at': datetime.now().isoformat()
                }
            )
            
            # Also create notification for admin
            Notifications.create_notification(
                user_id=current_admin.id,
                user_role='admin',
                title=f"Merchant KYC Rejected",
                message=f"KYC verification for {merchant.business_name or merchant.full_name} has been rejected.\nReason: {rejection_reason}",
                type='kyc',
                link='/admin/kyc-verification',
                action_text='View Details',
                extra_data={
                    'merchant_id': merchant.id,
                    'merchant_name': merchant.business_name or merchant.full_name,
                    'rejection_reason': rejection_reason,
                    'action': 'rejected'
                }
            )
            
            return {
                "message": "KYC verification rejected",
                "merchant_id": merchant.id,
                "status": "rejected",
                "rejection_reason": rejection_reason,
                "notification_sent": True
            }, 200
            
        except Exception as e:
            db.session.rollback()
            print(f"Error rejecting KYC: {str(e)}")
            return {"error": f"Failed to reject KYC: {str(e)}"}, 500


class AdminApproveDocumentResource(Resource):
    @auth_required
    def put(self, document_id):
        """Approve a single document"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        document = Document.query.get(document_id)
        if not document:
            return {"error": "Document not found"}, 404
        
        try:
            document.status = 'verified'
            document.verified_by = current_admin.id
            document.verified_at = datetime.now()
            
            # Check if all merchant documents are verified
            merchant_docs = Document.query.filter_by(
                user_id=document.user_id
            ).all()
            
            all_verified = all(d.status == 'verified' for d in merchant_docs)
            
            if all_verified and len(merchant_docs) >= 3:
                merchant = User.query.get(document.user_id)
                if merchant:
                    merchant.kyc_status = 'verified'
                    merchant.verification_level = 'verified'
                    merchant.kyc_completed_on = datetime.now()
                    
                    # Send notification for full verification
                    Notifications.create_notification(
                        user_id=merchant.id,
                        user_role='merchant',
                        title="✅ KYC Verification Complete",
                        message=f"Congratulations! All your documents have been verified. Your account is now fully verified.",
                        type='kyc',
                        link='/merchant/dashboard',
                        action_text='Go to Dashboard',
                        extra_data={'kyc_status': 'verified'}
                    )
            
            db.session.commit()
            
            # Send notification for document approval
            Notifications.create_notification(
                user_id=document.user_id,
                user_role='merchant',
                title=f"Document Approved: {document.document_name}",
                message=f"Your {document.document_name} has been approved. {'Your account is now fully verified!' if all_verified else 'Please wait for other documents to be reviewed.'}",
                type='kyc',
                link='/merchant/documents',
                action_text='View Documents',
                extra_data={'document_id': document.id, 'document_type': document.document_type}
            )
            
            return {
                "message": "Document approved successfully",
                "document_id": document.document_id,
                "status": "verified",
                "all_verified": all_verified if 'all_verified' in locals() else False
            }, 200
            
        except Exception as e:
            db.session.rollback()
            print(f"Error approving document: {str(e)}")
            return {"error": f"Failed to approve document: {str(e)}"}, 500


class AdminRejectDocumentResource(Resource):
    @auth_required
    def put(self, document_id):
        """Reject a single document with reason"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        data = request.get_json()
        rejection_reason = data.get('rejection_reason', '')
        
        if not rejection_reason:
            return {"error": "Rejection reason is required"}, 400
        
        document = Document.query.get(document_id)
        if not document:
            return {"error": "Document not found"}, 404
        
        try:
            document.status = 'rejected'
            document.rejection_reason = rejection_reason
            document.verified_by = current_admin.id
            document.verified_at = datetime.now()
            
            # Update merchant KYC status
            merchant = User.query.get(document.user_id)
            if merchant:
                merchant.kyc_status = 'rejected'
            
            db.session.commit()
            
            # Send notification for document rejection
            Notifications.create_notification(
                user_id=document.user_id,
                user_role='merchant',
                title=f"Document Rejected: {document.document_name}",
                message=f"""Your {document.document_name} has been rejected.

Reason: {rejection_reason}

Please upload a corrected version of this document for re-verification.""",
                type='kyc',
                link='/merchant/documents',
                action_text='Upload Again',
                extra_data={
                    'document_id': document.id,
                    'document_type': document.document_type,
                    'rejection_reason': rejection_reason
                }
            )
            
            return {
                "message": "Document rejected",
                "document_id": document.document_id,
                "status": "rejected",
                "rejection_reason": rejection_reason
            }, 200
            
        except Exception as e:
            db.session.rollback()
            print(f"Error rejecting document: {str(e)}")
            return {"error": f"Failed to reject document: {str(e)}"}, 500

class AdminApproveDocumentResource(Resource):
    @auth_required
    def put(self, document_id):
        """Approve a single document"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        document = Document.query.get(document_id)
        if not document:
            return {"error": "Document not found"}, 404
        
        document.status = 'verified'
        document.verified_by = current_admin.id
        document.verified_at = datetime.now()
        
        # Check if all merchant documents are verified
        merchant_docs = Document.query.filter_by(
            user_id=document.user_id
        ).all()
        
        all_verified = all(d.status == 'verified' for d in merchant_docs)
        
        if all_verified and len(merchant_docs) >= 3:
            merchant = User.query.get(document.user_id)
            if merchant:
                merchant.kyc_status = 'verified'
                merchant.verification_level = 'verified'
                merchant.kyc_completed_on = datetime.now()
        
        db.session.commit()
        
        return {
            "message": "Document approved successfully",
            "document_id": document.document_id,
            "status": "verified"
        }, 200


class AdminRejectDocumentResource(Resource):
    @auth_required
    def put(self, document_id):
        """Reject a single document with reason"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        data = request.get_json()
        rejection_reason = data.get('rejection_reason', '')
        
        if not rejection_reason:
            return {"error": "Rejection reason is required"}, 400
        
        document = Document.query.get(document_id)
        if not document:
            return {"error": "Document not found"}, 404
        
        document.status = 'rejected'
        document.rejection_reason = rejection_reason
        document.verified_by = current_admin.id
        document.verified_at = datetime.now()
        
        # Update merchant KYC status
        merchant = User.query.get(document.user_id)
        if merchant:
            merchant.kyc_status = 'rejected'
        
        db.session.commit()
        
        return {
            "message": "Document rejected",
            "document_id": document.document_id,
            "status": "rejected",
            "rejection_reason": rejection_reason
        }, 200