# resources/merchant_document.py
from flask_restful import Resource, request
from flask_praetorian import auth_required, current_user
from ..models.user import User
from ..models.document import Document
from ..extensions import db
from datetime import datetime
import os
import uuid
from werkzeug.utils import secure_filename

# Configuration
UPLOAD_FOLDER = 'uploads/merchant_documents'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'pdf'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def safe_str(v): return v if v is not None else ""


class MerchantGetDocumentsResource(Resource):
    @auth_required
    def get(self):
        """Get merchant's uploaded documents"""
        current_merchant = current_user()
        
        if current_merchant.role != "merchant":
            return {"error": "Unauthorized"}, 403
        
        documents = Document.query.filter_by(
            user_id=current_merchant.id
        ).order_by(Document.created_at.desc()).all()
        
        return {
            "documents": [{
                "id": d.id,
                "document_id": d.document_id,
                "document_name": d.document_name,
                "document_type": d.document_type,
                "status": d.status,
                "uploaded_at": d.created_at.isoformat() if d.created_at else "",
                "verified_at": d.verified_at.isoformat() if d.verified_at else "",
                "rejection_reason": d.rejection_reason
            } for d in documents]
        }, 200


class MerchantUploadDocumentsResource(Resource):
    @auth_required
    def post(self):
        """Upload merchant verification documents"""
        current_merchant = current_user()
        
        if current_merchant.role != "merchant":
            return {"error": "Unauthorized"}, 403
        
        # Check required files
        required_files = ['business_registration', 'tax_document', 'bank_statement']
        for file_key in required_files:
            if file_key not in request.files:
                return {"error": f"Missing required file: {file_key}"}, 400
            if request.files[file_key].filename == '':
                return {"error": f"Empty file for: {file_key}"}, 400
        
        # Create upload directory if not exists
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)
        
        notes = request.form.get('notes', '')
        uploaded_documents = []
        
        # Document configurations
        doc_configs = {
            'business_registration': {
                'name': 'Business Registration Certificate',
                'type': 'business_registration'
            },
            'tax_document': {
                'name': 'Tax Document (TIN/VAT)',
                'type': 'tax_document'
            },
            'bank_statement': {
                'name': 'Bank Account Statement/Confirmation',
                'type': 'bank_statement'
            }
        }
        
        for file_key, config in doc_configs.items():
            file = request.files[file_key]
            
            # Validate file type
            if not allowed_file(file.filename):
                return {"error": f"File type not allowed for {config['name']}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"}, 400
            
            # Generate unique filename
            ext = file.filename.rsplit('.', 1)[1].lower()
            filename = f"{file_key}_{current_merchant.id}_{uuid.uuid4().hex}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            
            # Save file
            file.save(filepath)
            
            # Create document record
            document = Document(
                document_id=Document.generate_document_id(Document),
                user_id=current_merchant.id,
                document_type=config['type'],
                document_name=config['name'],
                file_path=filepath,
                file_name=filename,
                file_size=os.path.getsize(filepath),
                mime_type=file.content_type,
                status='pending',
                uploaded_by=current_merchant.id
            )
            db.session.add(document)
            uploaded_documents.append({
                "id": document.id,
                "document_id": document.document_id,
                "document_name": document.document_name,
                "status": document.status
            })
        
        # Update merchant KYC status
        current_merchant.kyc_status = 'pending'
        
        db.session.commit()
        
        return {
            "message": "Documents uploaded successfully. Verification in progress.",
            "documents": uploaded_documents
        }, 201


class MerchantGetKYCStatusResource(Resource):
    @auth_required
    def get(self):
        """Get merchant's KYC verification status"""
        current_merchant = current_user()
        
        if current_merchant.role != "merchant":
            return {"error": "Unauthorized"}, 403
        
        # Get latest KYC documents
        kyc_documents = Document.query.filter_by(
            user_id=current_merchant.id
        ).filter(
            Document.document_type.in_(['business_registration', 'tax_document', 'bank_statement'])
        ).all()
        
        # Determine overall KYC status
        status = current_merchant.kyc_status or 'not_submitted'
        
        # Check if any document is rejected
        rejected_docs = [d for d in kyc_documents if d.status == 'rejected']
        if rejected_docs:
            status = 'rejected'
            rejection_reason = rejected_docs[0].rejection_reason
        else:
            rejection_reason = None
        
        # Check if all documents are verified
        all_verified = all(d.status == 'verified' for d in kyc_documents) if kyc_documents else False
        if all_verified and len(kyc_documents) >= 3:
            status = 'verified'
        
        return {
            "status": status,
            "level": current_merchant.verification_level or 'basic',
            "submitted_at": min([d.created_at for d in kyc_documents]).isoformat() if kyc_documents else None,
            "verified_at": current_merchant.kyc_completed_on.isoformat() if current_merchant.kyc_completed_on else None,
            "rejection_reason": rejection_reason
        }, 200


class MerchantGetBankDetailsResource(Resource):
    @auth_required
    def get(self):
        """Get merchant's bank details"""
        current_merchant = current_user()
        
        if current_merchant.role != "merchant":
            return {"error": "Unauthorized"}, 403
        
        return {
            "bank_name": safe_str(current_merchant.bank_name),
            "account_name": safe_str(current_merchant.account_name),
            "account_number": safe_str(current_merchant.account_number),
            "branch_name": safe_str(current_merchant.branch_name),
            "swift_code": safe_str(current_merchant.swift_code),
            "momo_name": safe_str(current_merchant.momo_name),
            "momo_number": safe_str(current_merchant.momo_number)
        }, 200


class MerchantUpdateBankDetailsResource(Resource):
    @auth_required
    def put(self):
        """Update merchant's bank details"""
        current_merchant = current_user()
        
        if current_merchant.role != "merchant":
            return {"error": "Unauthorized"}, 403
        
        data = request.get_json()
        
        # Update bank fields
        allowed_fields = ['bank_name', 'account_name', 'account_number', 'branch_name', 'swift_code', 'momo_name', 'momo_number']
        
        for field in allowed_fields:
            if field in data:
                setattr(current_merchant, field, data[field])
        
        db.session.commit()
        
        return {"message": "Bank details updated successfully"}, 200


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
                result.append({
                    "merchant_id": merchant.id,
                    "merchant_name": merchant.business_name or merchant.full_name,
                    "merchant_phone": merchant.phone,
                    "merchant_email": merchant.business_email or merchant.email,
                    "documents": [{
                        "id": d.id,
                        "document_id": d.document_id,
                        "document_name": d.document_name,
                        "document_type": d.document_type,
                        "file_path": d.file_path,
                        "status": d.status,
                        "uploaded_at": d.created_at.isoformat() if d.created_at else ""
                    } for d in documents],
                    "bank_details": {
                        "bank_name": merchant.bank_name,
                        "account_name": merchant.account_name,
                        "account_number": merchant.account_number
                    }
                })
        
        return {
            "pending_verifications": result,
            "total": len(result)
        }, 200


class AdminVerifyMerchantDocumentResource(Resource):
    @auth_required
    def put(self, document_id):
        """Admin verifies or rejects a merchant document"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        document = Document.query.get(document_id)
        if not document:
            return {"error": "Document not found"}, 404
        
        data = request.get_json()
        action = data.get('action')  # 'verify' or 'reject'
        rejection_reason = data.get('rejection_reason', '')
        
        if action == 'verify':
            document.status = 'verified'
            document.verified_by = current_admin.id
            document.verified_at = datetime.now()
            
            # Check if all merchant documents are verified
            merchant_docs = Document.query.filter_by(
                user_id=document.user_id
            ).filter(
                Document.document_type.in_(['business_registration', 'tax_document', 'bank_statement'])
            ).all()
            
            all_verified = all(d.status == 'verified' for d in merchant_docs) if merchant_docs else False
            
            if all_verified and len(merchant_docs) >= 3:
                merchant = User.query.get(document.user_id)
                if merchant:
                    merchant.kyc_status = 'verified'
                    merchant.verification_level = 'verified'
                    merchant.kyc_completed_on = datetime.now()
                    db.session.commit()
        
        elif action == 'reject':
            document.status = 'rejected'
            document.rejection_reason = rejection_reason
            document.verified_by = current_admin.id
            document.verified_at = datetime.now()
            
            # Update merchant KYC status
            merchant = User.query.get(document.user_id)
            if merchant:
                merchant.kyc_status = 'rejected'
            db.session.commit()
        
        else:
            return {"error": "Invalid action. Use 'verify' or 'reject'"}, 400
        
        db.session.commit()
        
        return {
            "message": f"Document {action}ed successfully",
            "document_id": document.document_id,
            "status": document.status
        }, 200


class AdminVerifyMerchantCompleteResource(Resource):
    @auth_required
    def put(self, merchant_id):
        """Admin verifies a merchant completely (all documents at once)"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        merchant = User.query.get(merchant_id)
        if not merchant or merchant.role != 'merchant':
            return {"error": "Merchant not found"}, 404
        
        data = request.get_json()
        action = data.get('action')  # 'verify' or 'reject'
        rejection_reason = data.get('rejection_reason', '')
        
        # Get all documents for this merchant
        documents = Document.query.filter_by(user_id=merchant.id).all()
        
        if action == 'verify':
            for doc in documents:
                doc.status = 'verified'
                doc.verified_by = current_admin.id
                doc.verified_at = datetime.now()
            
            merchant.kyc_status = 'verified'
            merchant.verification_level = 'verified'
            merchant.kyc_completed_on = datetime.now()
            db.session.commit()
            
            return {"message": "Merchant fully verified successfully"}, 200
        
        elif action == 'reject':
            for doc in documents:
                doc.status = 'rejected'
                doc.rejection_reason = rejection_reason
                doc.verified_by = current_admin.id
                doc.verified_at = datetime.now()
            
            merchant.kyc_status = 'rejected'
            db.session.commit()
            
            return {"message": f"Merchant verification rejected: {rejection_reason}"}, 200
        
        else:
            return {"error": "Invalid action. Use 'verify' or 'reject'"}, 400