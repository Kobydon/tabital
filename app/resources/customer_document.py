# resources/customer_document.py
from flask_restful import Resource, request
from flask_praetorian import auth_required, current_user
from ..models.user import User
from ..models.document import Document
from ..extensions import db
from datetime import datetime
import json
import os
import uuid
from werkzeug.utils import secure_filename

# Configuration
UPLOAD_FOLDER = 'uploads/kyc'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'pdf'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def safe_str(v): return v if v is not None else ""


class CustomerGetDocumentsResource(Resource):
    @auth_required
    def get(self):
        """Get customer's uploaded documents"""
        current_customer = current_user()
        
        if current_customer.role != "customer":
            return {"error": "Unauthorized"}, 403
        
        # Query using user_id (which can be customer_id)
        documents = Document.query.filter_by(
            user_id=current_customer.id
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


class CustomerUploadDocumentsResource(Resource):
    @auth_required
    def post(self):
        """Upload KYC documents (front and back of Ghana Card)"""
        current_customer = current_user()
        
        if current_customer.role != "customer":
            return {"error": "Unauthorized"}, 403
        
        # Check if files are present
        if 'front_image' not in request.files or 'back_image' not in request.files:
            return {"error": "Both front and back images are required"}, 400
        
        front_image = request.files['front_image']
        back_image = request.files['back_image']
        notes = request.form.get('notes', '')
        
        # Validate files
        if front_image.filename == '' or back_image.filename == '':
            return {"error": "No file selected"}, 400
        
        if not allowed_file(front_image.filename) or not allowed_file(back_image.filename):
            return {"error": f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"}, 400
        
        # Create upload directory if not exists
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)
        
        # Upload front image
        front_ext = front_image.filename.rsplit('.', 1)[1].lower()
        front_filename = f"front_{current_customer.customer_id}_{uuid.uuid4().hex}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{front_ext}"
        front_filepath = os.path.join(UPLOAD_FOLDER, front_filename)
        front_image.save(front_filepath)
        
        # Create document record for front image using user_id
        front_document = Document(
            document_id=Document.generate_document_id(Document),
            user_id=current_customer.id,  # Using user_id instead of merchant_id/customer_id
            document_type='kyc_front',
            document_name='Ghana Card (Front)',
            file_path=front_filepath,
            file_name=front_filename,
            file_size=os.path.getsize(front_filepath),
            mime_type=front_image.content_type,
            status='pending',
            uploaded_by=current_customer.id
        )
        db.session.add(front_document)
        
        # Upload back image
        back_ext = back_image.filename.rsplit('.', 1)[1].lower()
        back_filename = f"back_{current_customer.customer_id}_{uuid.uuid4().hex}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{back_ext}"
        back_filepath = os.path.join(UPLOAD_FOLDER, back_filename)
        back_image.save(back_filepath)
        
        # Create document record for back image using user_id
        back_document = Document(
            document_id=Document.generate_document_id(Document),
            user_id=current_customer.id,  # Using user_id instead of merchant_id/customer_id
            document_type='kyc_back',
            document_name='Ghana Card (Back)',
            file_path=back_filepath,
            file_name=back_filename,
            file_size=os.path.getsize(back_filepath),
            mime_type=back_image.content_type,
            status='pending',
            uploaded_by=current_customer.id
        )
        db.session.add(back_document)
        
        # Update customer KYC status
        current_customer.kyc_status = 'pending'
        
        db.session.commit()
        
        return {
            "message": "Documents uploaded successfully. Verification in progress.",
            "documents": [
                {
                    "id": front_document.id,
                    "document_id": front_document.document_id,
                    "document_name": front_document.document_name,
                    "status": front_document.status
                },
                {
                    "id": back_document.id,
                    "document_id": back_document.document_id,
                    "document_name": back_document.document_name,
                    "status": back_document.status
                }
            ]
        }, 201


class CustomerGetKYCStatusResource(Resource):
    @auth_required
    def get(self):
        """Get customer's KYC verification status"""
        current_customer = current_user()
        
        if current_customer.role != "customer":
            return {"error": "Unauthorized"}, 403
        
        # Get latest KYC documents
        kyc_documents = Document.query.filter_by(
            user_id=current_customer.id
        ).filter(
            Document.document_type.in_(['kyc_front', 'kyc_back'])
        ).all()
        
        # Determine overall KYC status
        status = current_customer.kyc_status or 'not_submitted'
        
        # Check if any document is rejected
        rejected_docs = [d for d in kyc_documents if d.status == 'rejected']
        if rejected_docs:
            status = 'rejected'
            rejection_reason = rejected_docs[0].rejection_reason
        else:
            rejection_reason = None
        
        return {
            "status": status,
            "level": current_customer.verification_level or 'basic',
            "submitted_at": min([d.created_at for d in kyc_documents]).isoformat() if kyc_documents else None,
            "verified_at": current_customer.kyc_completed_on.isoformat() if current_customer.kyc_completed_on else None,
            "rejection_reason": rejection_reason
        }, 200


class AdminVerifyDocumentResource(Resource):
    @auth_required
    def put(self, document_id):
        """Admin verifies or rejects a document"""
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
            
            # Check if all customer documents are verified
            customer_docs = Document.query.filter_by(
                user_id=document.user_id
            ).filter(
                Document.document_type.in_(['kyc_front', 'kyc_back'])
            ).all()
            
            all_verified = all(d.status == 'verified' for d in customer_docs)
            
            if all_verified:
                customer = User.query.get(document.user_id)
                if customer:
                    customer.kyc_status = 'verified'
                    customer.verification_level = 'verified'
                    customer.kyc_completed_on = datetime.now()
                    db.session.commit()
        
        elif action == 'reject':
            document.status = 'rejected'
            document.rejection_reason = rejection_reason
            document.verified_by = current_admin.id
            document.verified_at = datetime.now()
            
            # Update customer KYC status
            customer = User.query.get(document.user_id)
            if customer:
                customer.kyc_status = 'rejected'
            db.session.commit()
        
        else:
            return {"error": "Invalid action. Use 'verify' or 'reject'"}, 400
        
        db.session.commit()
        
        return {
            "message": f"Document {action}ed successfully",
            "document_id": document.document_id,
            "status": document.status
        }, 200


class AdminGetPendingKYCResource(Resource):
    @auth_required
    def get(self):
        """Admin gets all pending KYC verification requests"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        # Get customers with pending KYC who have uploaded documents
        pending_customers = User.query.filter(
            User.role == 'customer',
            User.kyc_status == 'pending'
        ).all()
        
        result = []
        for customer in pending_customers:
            documents = Document.query.filter_by(
                user_id=customer.id
            ).filter(
                Document.document_type.in_(['kyc_front', 'kyc_back'])
            ).all()
            
            if documents:
                result.append({
                    "customer_id": customer.id,
                    "customer_name": customer.full_name or customer.business_name,
                    "customer_phone": customer.phone,
                    "customer_email": customer.email,
                    "documents": [{
                        "id": d.id,
                        "document_id": d.document_id,
                        "document_name": d.document_name,
                        "file_path": d.file_path,
                        "status": d.status,
                        "uploaded_at": d.created_at.isoformat() if d.created_at else ""
                    } for d in documents]
                })
        
        return {
            "pending_verifications": result,
            "total": len(result)
        }, 200