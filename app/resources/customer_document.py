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
import base64

# Configuration
from pathlib import Path

# Make sure the upload folder path is correct
# Try multiple possible paths to find the files
UPLOAD_FOLDER = Path('uploads/kyc')
ALT_UPLOAD_FOLDER = Path('/app/uploads/kyc')  # For Docker
CWD_UPLOAD_FOLDER = Path.cwd() / 'uploads' / 'kyc'
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
        """Upload KYC documents (Ghana Card, Salary Certificate, Bank Statement)"""
        current_customer = current_user()
        
        if current_customer.role != "customer":
            return {"error": "Unauthorized"}, 403
        
        # Debug: Log all received files
        print(f"Received files: {list(request.files.keys())}")
        print(f"Form data: {request.form}")
        
        # Required files - MUST MATCH FRONTEND KEYS
        required_files = ['front_image', 'back_image', 'salary_certificate', 'bank_statement']
        for file_key in required_files:
            if file_key not in request.files:
                return {"error": f"Missing required file: {file_key}"}, 400
            file = request.files[file_key]
            if file.filename == '':
                return {"error": f"Empty file for: {file_key}"}, 400
            print(f"File {file_key}: {file.filename}, size: {len(file.read()) if file else 0}")
            file.seek(0)  # Reset file pointer after reading
        
        # Create upload directory if not exists
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)
        
        notes = request.form.get('notes', '')
        uploaded_documents = []
        
        # Document configurations - KEYS MUST MATCH FRONTEND
        doc_configs = {
            'front_image': {
                'name': 'Ghana Card (Front)',
                'type': 'kyc_front'
            },
            'back_image': {
                'name': 'Ghana Card (Back)',
                'type': 'kyc_back'
            },
            'salary_certificate': {
                'name': 'Salary Certificate',
                'type': 'salary_certificate'
            },
            'bank_statement': {
                'name': '3 Months Bank Statement',
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
            customer_id = current_customer.customer_id or f"C{current_customer.id:03d}"
            filename = f"{file_key}_{customer_id}_{uuid.uuid4().hex}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            
            # Save file
            file.save(filepath)
            
            # Create document record
            document = Document(
                document_id=Document.generate_document_id(Document),
                user_id=current_customer.id,
                document_type=config['type'],
                document_name=config['name'],
                file_path=filepath,
                file_name=filename,
                file_size=os.path.getsize(filepath),
                mime_type=file.content_type,
                status='pending',
                uploaded_by=current_customer.id
            )
            db.session.add(document)
            uploaded_documents.append({
                "id": document.id,
                "document_id": document.document_id,
                "document_name": document.document_name,
                "status": document.status
            })
        
        # Update customer KYC status
        current_customer.kyc_status = 'pending'
        
        db.session.commit()
        
        return {
            "message": "Documents uploaded successfully. Verification in progress.",
            "documents": uploaded_documents
        }, 201


class CustomerUploadOptionalDocumentResource(Resource):
    @auth_required
    def post(self):
        """Upload optional KYC document"""
        current_customer = current_user()
        
        if current_customer.role != "customer":
            return {"error": "Unauthorized"}, 403
        
        if 'document' not in request.files:
            return {"error": "No file provided"}, 400
        
        file = request.files['document']
        document_type = request.form.get('document_type', '')
        document_name = request.form.get('document_name', 'Optional Document')
        
        if file.filename == '':
            return {"error": "No file selected"}, 400
        
        if not allowed_file(file.filename):
            return {"error": f"File type not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"}, 400
        
        if not os.path.exists(UPLOAD_FOLDER):
            os.makedirs(UPLOAD_FOLDER)
        
        ext = file.filename.rsplit('.', 1)[1].lower()
        customer_id = current_customer.customer_id or f"C{current_customer.id:03d}"
        filename = f"{document_type}_{customer_id}_{uuid.uuid4().hex}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        
        document = Document(
            document_id=Document.generate_document_id(Document),
            user_id=current_customer.id,
            document_type=document_type,
            document_name=document_name,
            file_path=filepath,
            file_name=filename,
            file_size=os.path.getsize(filepath),
            mime_type=file.content_type,
            status='pending',
            uploaded_by=current_customer.id
        )
        db.session.add(document)
        db.session.commit()
        
        return {
            "message": f"{document_name} uploaded successfully",
            "document": {
                "id": document.id,
                "document_id": document.document_id,
                "document_name": document.document_name,
                "status": document.status
            }
        }, 201


class CustomerGetKYCStatusResource(Resource):
    @auth_required
    def get(self):
        """Get customer's KYC verification status"""
        current_customer = current_user()
        
        if current_customer.role != "customer":
            return {"error": "Unauthorized"}, 403
        
        # Get all KYC documents
        kyc_documents = Document.query.filter_by(
            user_id=current_customer.id
        ).filter(
            Document.document_type.in_(['kyc_front', 'kyc_back', 'salary_certificate', 'bank_statement'])
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
        
        # Check if all required documents are verified
        required_types = ['kyc_front', 'kyc_back', 'salary_certificate', 'bank_statement']
        existing_types = [d.document_type for d in kyc_documents]
        all_required_present = all(t in existing_types for t in required_types)
        
        if all_required_present and all(d.status == 'verified' for d in kyc_documents if d.document_type in required_types):
            status = 'verified'
        
        return {
            "status": status,
            "level": current_customer.verification_level or 'basic',
            "submitted_at": min([d.created_at for d in kyc_documents]).isoformat() if kyc_documents else None,
            "verified_at": current_customer.kyc_completed_on.isoformat() if current_customer.kyc_completed_on else None,
            "rejection_reason": rejection_reason
        }, 200


# ============================================
# ADMIN KYC MANAGEMENT RESOURCES
# ============================================
# resources/customer_document.py

class AdminGetPendingCustomerKYCResource(Resource):
    @auth_required
    def get(self):
        """Admin gets all pending customer KYC verification requests"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        # Get customers with pending KYC
        pending_customers = User.query.filter(
            User.role == 'customer',
            User.kyc_status == 'pending'
        ).all()
        
        result = []
        for customer in pending_customers:
            # Get all documents for this customer
            documents = Document.query.filter_by(
                user_id=customer.id
            ).order_by(Document.created_at.desc()).all()
            
            if documents:
                documents_data = []
                for doc in documents:
                    file_data = None
                    
                    # Try multiple possible paths
                    possible_paths = [
                        doc.file_path,  # Path stored in DB
                        str(UPLOAD_FOLDER / doc.file_name),
                        str(ALT_UPLOAD_FOLDER / doc.file_name),
                        str(CWD_UPLOAD_FOLDER / doc.file_name),
                        f"uploads/kyc/{doc.file_name}",
                        f"/app/uploads/kyc/{doc.file_name}"
                    ]
                    
                    print(f"Looking for file: {doc.file_name}")
                    
                    for path in possible_paths:
                        if path and os.path.exists(path):
                            try:
                                with open(path, 'rb') as f:
                                    file_data = base64.b64encode(f.read()).decode('utf-8')
                                    print(f"✅ Loaded file: {doc.file_name} from {path}, size: {len(file_data)} chars")
                                break  # Exit loop once file is found
                            except Exception as e:
                                print(f"Error reading {path}: {str(e)}")
                    
                    if not file_data:
                        print(f"❌ File not found: {doc.file_name}")
                    
                    documents_data.append({
                        "id": doc.id,
                        "document_id": doc.document_id,
                        "document_name": doc.document_name,
                        "document_type": doc.document_type,
                        "status": doc.status,
                        "uploaded_at": doc.created_at.isoformat() if doc.created_at else None,
                        "file_data": file_data,  # This MUST have the base64 data
                        "file_name": doc.file_name,
                        "file_size": doc.file_size,
                        "mime_type": doc.mime_type,
                        "rejection_reason": doc.rejection_reason,
                        "verified_at": doc.verified_at.isoformat() if doc.verified_at else None
                    })
                
                result.append({
                    "customer_id": customer.id,
                    "customer_name": customer.full_name or customer.business_name,
                    "phone": customer.phone,
                    "email": customer.business_email or customer.email,
                    "kyc_status": customer.kyc_status,
                    "verification_level": customer.verification_level or 'basic',
                    "submitted_at": min([d.created_at for d in documents]).isoformat() if documents else None,
                    "documents": documents_data
                })
        
        return {
            "pending_verifications": result,
            "total": len(result)
        }, 200
class AdminGetVerifiedCustomerKYCResource(Resource):
    @auth_required
    def get(self):
        """Admin gets all verified customer KYC"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        verified_customers = User.query.filter(
            User.role == 'customer',
            User.kyc_status == 'verified'
        ).all()
        
        result = []
        for customer in verified_customers:
            result.append({
                "customer_id": customer.id,
                "customer_name": customer.full_name or customer.business_name,
                "phone": customer.phone,
                "email": customer.business_email or customer.email,
                "kyc_status": customer.kyc_status,
                "verified_at": customer.kyc_completed_on.isoformat() if customer.kyc_completed_on else None,
                "verification_level": customer.verification_level
            })
        
        return {
            "verified_customers": result,
            "total": len(result)
        }, 200


class AdminGetRejectedCustomerKYCResource(Resource):
    @auth_required
    def get(self):
        """Admin gets all rejected customer KYC"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        rejected_customers = User.query.filter(
            User.role == 'customer',
            User.kyc_status == 'rejected'
        ).all()
        
        result = []
        for customer in rejected_customers:
            # Get rejection reason from documents
            rejected_docs = Document.query.filter_by(
                user_id=customer.id,
                status='rejected'
            ).first()
            
            result.append({
                "customer_id": customer.id,
                "customer_name": customer.full_name or customer.business_name,
                "phone": customer.phone,
                "email": customer.business_email or customer.email,
                "kyc_status": customer.kyc_status,
                "rejection_reason": rejected_docs.rejection_reason if rejected_docs else None,
                "rejected_at": rejected_docs.verified_at.isoformat() if rejected_docs and rejected_docs.verified_at else None
            })
        
        return {
            "rejected_customers": result,
            "total": len(result)
        }, 200
class AdminGetCustomerKYCDetailResource(Resource):
    @auth_required
    def get(self, customer_id):
        """Admin gets specific customer's KYC details with file previews"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        customer = User.query.get(customer_id)
        if not customer or customer.role != 'customer':
            return {"error": "Customer not found"}, 404
        
        documents = Document.query.filter_by(
            user_id=customer.id
        ).order_by(Document.created_at.desc()).all()
        
        documents_data = []
        for doc in documents:
            file_data = None
            
            # Try multiple possible paths
            possible_paths = [
                doc.file_path,
                f"uploads/kyc/{doc.file_name}",
                f"/app/uploads/kyc/{doc.file_name}",
                os.path.join(os.getcwd(), 'uploads', 'kyc', doc.file_name)
            ]
            
            for path in possible_paths:
                if path and os.path.exists(path):
                    try:
                        with open(path, 'rb') as f:
                            file_data = base64.b64encode(f.read()).decode('utf-8')
                        break
                    except Exception as e:
                        print(f"Error reading file: {str(e)}")
            
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
            "customer": {
                "id": customer.id,
                "full_name": customer.full_name,
                "phone": customer.phone,
                "email": customer.business_email or customer.email,
                "kyc_status": customer.kyc_status,
                "verification_level": customer.verification_level,
                "kyc_completed_on": customer.kyc_completed_on.isoformat() if customer.kyc_completed_on else None
            },
            "documents": documents_data
        }, 200
class AdminRejectCustomerKYCResource(Resource):
    @auth_required
    def put(self, customer_id):
        """Admin rejects a customer's KYC verification"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        data = request.get_json()
        rejection_reason = data.get('rejection_reason', '')
        
        if not rejection_reason:
            return {"error": "Rejection reason is required"}, 400
        
        customer = User.query.get(customer_id)
        if not customer or customer.role != 'customer':
            return {"error": "Customer not found"}, 404
        
        try:
            # Update all documents to rejected
            documents = Document.query.filter_by(user_id=customer.id).all()
            for doc in documents:
                doc.status = 'rejected'
                doc.rejection_reason = rejection_reason
                doc.verified_by = current_admin.id
                doc.verified_at = datetime.now()
            
            # Update customer KYC status
            customer.kyc_status = 'rejected'
            
            db.session.commit()
            
            return {
                "message": "Customer KYC verification rejected",
                "customer_id": customer.id,
                "status": "rejected",
                "rejection_reason": rejection_reason
            }, 200
            
        except Exception as e:
            db.session.rollback()
            print(f"Error rejecting customer KYC: {str(e)}")
            return {"error": f"Failed to reject KYC: {str(e)}"}, 500


# Add these to your existing customer_document.py
# resources/customer_document.py



class AdminGetPendingCustomerKYCResource(Resource):
    @auth_required
    def get(self):
        """Admin gets all pending customer KYC verification requests"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        # Get customers with pending KYC
        pending_customers = User.query.filter(
            User.role == 'customer',
            User.kyc_status == 'pending'
        ).all()
        
        result = []
        for customer in pending_customers:
            # Get all documents for this customer
            documents = Document.query.filter_by(
                user_id=customer.id
            ).order_by(Document.created_at.desc()).all()
            
            if documents:
                documents_data = []
                for doc in documents:
                    file_data = None
                    # Check multiple possible file paths
                    possible_paths = [
                        doc.file_path,
                        f"uploads/kyc/{doc.file_name}",
                        f"/app/uploads/kyc/{doc.file_name}",
                        os.path.join(os.getcwd(), 'uploads', 'kyc', doc.file_name)
                    ]
                    
                    for path in possible_paths:
                        if path and os.path.exists(path):
                            try:
                                with open(path, 'rb') as f:
                                    file_data = base64.b64encode(f.read()).decode('utf-8')
                                    print(f"✅ Loaded customer file: {doc.file_name}, size: {len(file_data)} chars")
                                break
                            except Exception as e:
                                print(f"Error reading {path}: {str(e)}")
                    
                    if not file_data:
                        print(f"❌ Customer file not found: {doc.file_name}")
                    
                    documents_data.append({
                        "id": doc.id,
                        "document_id": doc.document_id,
                        "document_name": doc.document_name,
                        "document_type": doc.document_type,
                        "status": doc.status,
                        "uploaded_at": doc.created_at.isoformat() if doc.created_at else None,
                        "file_data": file_data,  # This MUST be included
                        "file_name": doc.file_name,
                        "file_size": doc.file_size,
                        "mime_type": doc.mime_type,
                        "rejection_reason": doc.rejection_reason,
                        "verified_at": doc.verified_at.isoformat() if doc.verified_at else None
                    })
                
                result.append({
                    "customer_id": customer.id,
                    "customer_name": customer.full_name or customer.business_name,
                    "phone": customer.phone,
                    "email": customer.business_email or customer.email,
                    "kyc_status": customer.kyc_status,
                    "verification_level": customer.verification_level or 'basic',
                    "submitted_at": min([d.created_at for d in documents]).isoformat() if documents else None,
                    "documents": documents_data
                })
        
        return {
            "pending_verifications": result,
            "total": len(result)
        }, 200
    
class AdminGetVerifiedCustomerKYCResource(Resource):
    @auth_required
    def get(self):
        """Admin gets all verified customer KYC"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        verified_customers = User.query.filter(
            User.role == 'customer',
            User.kyc_status == 'verified'
        ).all()
        
        result = []
        for customer in verified_customers:
            result.append({
                "customer_id": customer.id,
                "customer_name": customer.full_name or customer.business_name,
                "phone": customer.phone,
                "email": customer.business_email or customer.email,
                "kyc_status": customer.kyc_status,
                "verified_at": customer.kyc_completed_on.isoformat() if customer.kyc_completed_on else None,
                "verification_level": customer.verification_level
            })
        
        return {
            "verified_customers": result,
            "total": len(result)
        }, 200


class AdminGetRejectedCustomerKYCResource(Resource):
    @auth_required
    def get(self):
        """Admin gets all rejected customer KYC"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        rejected_customers = User.query.filter(
            User.role == 'customer',
            User.kyc_status == 'rejected'
        ).all()
        
        result = []
        for customer in rejected_customers:
            rejected_docs = Document.query.filter_by(
                user_id=customer.id,
                status='rejected'
            ).first()
            
            result.append({
                "customer_id": customer.id,
                "customer_name": customer.full_name or customer.business_name,
                "phone": customer.phone,
                "email": customer.business_email or customer.email,
                "kyc_status": customer.kyc_status,
                "rejection_reason": rejected_docs.rejection_reason if rejected_docs else None,
                "rejected_at": rejected_docs.verified_at.isoformat() if rejected_docs and rejected_docs.verified_at else None
            })
        
        return {
            "rejected_customers": result,
            "total": len(result)
        }, 200


class AdminApproveCustomerKYCResource(Resource):
    @auth_required
    def put(self, customer_id):
        """Admin approves a customer's KYC verification"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        customer = User.query.get(customer_id)
        if not customer or customer.role != 'customer':
            return {"error": "Customer not found"}, 404
        
        try:
            documents = Document.query.filter_by(user_id=customer.id).all()
            for doc in documents:
                doc.status = 'verified'
                doc.verified_by = current_admin.id
                doc.verified_at = datetime.now()
            
            customer.kyc_status = 'verified'
            customer.verification_level = 'verified'
            customer.kyc_completed_on = datetime.now()
            customer.status = 'approved'
            
            db.session.commit()
            
            return {
                "message": "Customer KYC approved successfully",
                "customer_id": customer.id,
                "status": "verified"
            }, 200
            
        except Exception as e:
            db.session.rollback()
            print(f"Error approving customer KYC: {str(e)}")
            return {"error": f"Failed to approve KYC: {str(e)}"}, 500




class AdminRejectCustomerKYCResource(Resource):
    @auth_required
    def put(self, customer_id):
        """Admin rejects a customer's KYC verification"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        data = request.get_json()
        rejection_reason = data.get('rejection_reason', '')
        
        if not rejection_reason:
            return {"error": "Rejection reason is required"}, 400
        
        customer = User.query.get(customer_id)
        if not customer or customer.role != 'customer':
            return {"error": "Customer not found"}, 404
        
        try:
            documents = Document.query.filter_by(user_id=customer.id).all()
            for doc in documents:
                doc.status = 'rejected'
                doc.rejection_reason = rejection_reason
                doc.verified_by = current_admin.id
                doc.verified_at = datetime.now()
            
            customer.kyc_status = 'rejected'
            
            db.session.commit()
            
            return {
                "message": "Customer KYC rejected",
                "customer_id": customer.id,
                "status": "rejected",
                "rejection_reason": rejection_reason
            }, 200
            
        except Exception as e:
            db.session.rollback()
            print(f"Error rejecting customer KYC: {str(e)}")
            return {"error": f"Failed to reject KYC: {str(e)}"}, 500


class AdminApproveCustomerDocumentResource(Resource):
    @auth_required
    def put(self, document_id):
        """Admin approves a customer document"""
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
            
            customer_docs = Document.query.filter_by(user_id=document.user_id).all()
            all_verified = all(d.status == 'verified' for d in customer_docs)
            
            if all_verified:
                customer = User.query.get(document.user_id)
                if customer:
                    customer.kyc_status = 'verified'
                    customer.verification_level = 'verified'
                    customer.kyc_completed_on = datetime.now()
                    customer.status = 'approved'
            
            db.session.commit()
            
            return {
                "message": "Document approved successfully",
                "document_id": document.document_id,
                "status": "verified"
            }, 200
            
        except Exception as e:
            db.session.rollback()
            print(f"Error approving document: {str(e)}")
            return {"error": f"Failed to approve document: {str(e)}"}, 500


class AdminRejectCustomerDocumentResource(Resource):
    @auth_required
    def put(self, document_id):
        """Admin rejects a customer document"""
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
            
            customer = User.query.get(document.user_id)
            if customer:
                customer.kyc_status = 'rejected'
            
            db.session.commit()
            
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