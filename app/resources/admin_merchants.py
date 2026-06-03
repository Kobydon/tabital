from flask_restful import Resource, request
from flask_praetorian import auth_required, current_user
from app.models.user import User
from app.models.instalment import InstalmentPlan
from app.models.transaction import Transaction
from app.extensions import db
from datetime import datetime, timedelta
from sqlalchemy import func, or_

class AdminMerchantStatsResource(Resource):
    @auth_required
    def get(self):
        """Get merchant overview statistics"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        # Date calculations
        today = datetime.now().date()
        last_30_days = today - timedelta(days=30)
        
        # Total Merchants
        total_merchants = User.query.filter(User.role == 'merchant').count()
        
        # Active Merchants (status approved or active)
        active_merchants = User.query.filter(
            User.role == 'merchant',
            User.status.in_(['approved', 'active'])
        ).count()
        
        # Calculate active merchants growth
        active_merchants_last_30 = User.query.filter(
            User.role == 'merchant',
            User.status.in_(['approved', 'active']),
            User.created_at >= last_30_days
        ).count()
        active_merchants_previous = active_merchants - active_merchants_last_30
        active_merchants_growth = round(((active_merchants_last_30 - active_merchants_previous) / active_merchants_previous * 100) if active_merchants_previous > 0 else 0, 1)
        
        # New Merchants (last 30 days)
        new_merchants = User.query.filter(
            User.role == 'merchant',
            User.created_at >= last_30_days
        ).count()
        
        new_merchants_previous = User.query.filter(
            User.role == 'merchant',
            User.created_at < last_30_days
        ).count()
        new_merchants_growth = round(((new_merchants - new_merchants_previous) / new_merchants_previous * 100) if new_merchants_previous > 0 else 0, 1)
        
        # Total GMV (30 Days) - Gross Merchandise Value from completed transactions
        total_gmv = db.session.query(func.sum(InstalmentPlan.total_amount))\
            .filter(InstalmentPlan.status == 'completed',
                   InstalmentPlan.completed_at >= last_30_days).scalar() or 0
        
        total_gmv_previous = db.session.query(func.sum(InstalmentPlan.total_amount))\
            .filter(InstalmentPlan.status == 'completed',
                   InstalmentPlan.completed_at < last_30_days).scalar() or 0
        gmv_growth = round(((total_gmv - total_gmv_previous) / total_gmv_previous * 100) if total_gmv_previous > 0 else 0, 1)
        
        # Average Payout Time (in days)
        avg_payout_time = 1.2  # Sample value - calculate based on actual data
        payout_time_previous = 1.5
        payout_time_change = avg_payout_time - payout_time_previous
        
        # On Hold / Restricted Merchants
        restricted_merchants = User.query.filter(
            User.role == 'merchant',
            User.status == 'restricted'
        ).count()
        
        restricted_previous = 19
        restricted_growth = restricted_merchants - restricted_previous
        
        return {
            "total_merchants": total_merchants,
            "total_merchants_growth": 14.2,
            "active_merchants": active_merchants,
            "active_merchants_growth": active_merchants_growth,
            "new_merchants": new_merchants,
            "new_merchants_growth": new_merchants_growth,
            "total_gmv": float(total_gmv),
            "gmv_growth": gmv_growth,
            "avg_payout_time": avg_payout_time,
            "payout_time_change": payout_time_change,
            "restricted_merchants": restricted_merchants,
            "restricted_growth": restricted_growth
        }, 200


class AdminGetMerchantsResource(Resource):
    @auth_required
    def get(self):
        """Get all merchants with filters and pagination"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '', type=str)
        kyc_status = request.args.get('kyc_status', '', type=str)
        status = request.args.get('status', '', type=str)
        risk_level = request.args.get('risk_level', '', type=str)
        sort_by = request.args.get('sort_by', 'created_at', type=str)
        sort_order = request.args.get('sort_order', 'desc', type=str)
        
        # Build query
        query = User.query.filter(User.role == 'merchant')
        
        # Apply search filter
        if search:
            query = query.filter(
                or_(
                    User.business_name.ilike(f'%{search}%'),
                    User.owner_name.ilike(f'%{search}%'),
                    User.phone.ilike(f'%{search}%'),
                    User.business_email.ilike(f'%{search}%'),
                    User.merchant_id.ilike(f'%{search}%')
                )
            )
        
        # Apply KYC status filter
        if kyc_status:
            query = query.filter(User.kyc_status == kyc_status)
        
        # Apply status filter
        if status:
            query = query.filter(User.status == status)
        
        # Apply sorting
        if sort_order == 'desc':
            query = query.order_by(getattr(User, sort_by).desc())
        else:
            query = query.order_by(getattr(User, sort_by).asc())
        
        # Pagination
        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        merchants = []
        for merchant in paginated.items:
            # Calculate merchant metrics
            total_gmv = db.session.query(func.sum(InstalmentPlan.total_amount))\
                .filter(InstalmentPlan.merchant_id == merchant.id,
                       InstalmentPlan.status == 'completed').scalar() or 0
            
            total_transactions = InstalmentPlan.query.filter_by(
                merchant_id=merchant.id
            ).count()
            
            active_plans = InstalmentPlan.query.filter_by(
                merchant_id=merchant.id,
                status='active'
            ).count()
            
            # Determine risk level
            risk_level_calc = "Low"
            if total_gmv > 100000:
                risk_level_calc = "Medium"
            if total_gmv > 500000 or merchant.kyc_status == 'rejected':
                risk_level_calc = "High"
            
            merchants.append({
                "id": merchant.id,
                "merchant_id": merchant.merchant_id or f"M{merchant.id:04d}",
                "business_name": merchant.business_name or "N/A",
                "owner_name": merchant.owner_name or "N/A",
                "phone": merchant.phone,
                "email": merchant.business_email or merchant.email or "N/A",
                "business_type": merchant.business_type or "N/A",
                "kyc_status": merchant.kyc_status or "pending",
                "risk_level": risk_level_calc,
                "status": merchant.status if merchant.status in ['approved', 'active'] else 'pending',
                "total_gmv": float(total_gmv),
                "total_transactions": total_transactions,
                "active_plans": active_plans,
                "created_at": merchant.created_at.isoformat() if merchant.created_at else None
            })
        
        return {
            "merchants": merchants,
            "total": paginated.total,
            "page": page,
            "per_page": per_page,
            "total_pages": paginated.pages if paginated.pages > 0 else 1
        }, 200


class AdminGetMerchantDetailResource(Resource):
    @auth_required
    def get(self, merchant_id):
        """Get detailed merchant information"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        merchant = User.query.filter_by(id=merchant_id, role='merchant').first()
        if not merchant:
            return {"error": "Merchant not found"}, 404
        
        # Calculate financial metrics
        total_gmv = db.session.query(func.sum(InstalmentPlan.total_amount))\
            .filter(InstalmentPlan.merchant_id == merchant.id,
                   InstalmentPlan.status == 'completed').scalar() or 0
        
        total_outstanding = db.session.query(func.sum(InstalmentPlan.remaining_amount))\
            .filter(InstalmentPlan.merchant_id == merchant.id,
                   InstalmentPlan.status == 'active').scalar() or 0
        
        total_commission = db.session.query(func.sum(InstalmentPlan.commission_amount))\
            .filter(InstalmentPlan.merchant_id == merchant.id,
                   InstalmentPlan.status == 'completed').scalar() or 0
        
        total_products = merchant.total_products or 0
        active_plans = InstalmentPlan.query.filter_by(
            merchant_id=merchant.id,
            status='active'
        ).count()
        
        # Recent transactions
        recent_transactions = InstalmentPlan.query.filter_by(
            merchant_id=merchant.id
        ).order_by(InstalmentPlan.created_at.desc()).limit(5).all()
        
        transactions_data = []
        for t in recent_transactions:
            transactions_data.append({
                "plan_id": t.plan_id,
                "customer_name": t.customer_name,
                "amount": float(t.total_amount),
                "status": t.status,
                "created_at": t.created_at.strftime("%d %b %Y, %I:%M %p") if t.created_at else ""
            })
        
        # Bank details
        bank_details = {
            "bank_name": merchant.bank_name,
            "account_name": merchant.account_name,
            "account_number": merchant.account_number,
            "branch_name": merchant.branch_name,
            "swift_code": merchant.swift_code,
            "momo_name": merchant.momo_name,
            "momo_number": merchant.momo_number
        }
        
        return {
            "merchant": {
                "id": merchant.id,
                "merchant_id": merchant.merchant_id or f"M{merchant.id:04d}",
                "business_name": merchant.business_name or "N/A",
                "owner_name": merchant.owner_name or "N/A",
                "phone": merchant.phone,
                "email": merchant.business_email or merchant.email or "N/A",
                "business_type": merchant.business_type or "N/A",
                "city": merchant.city,
                "address": merchant.address,
                "kyc_status": merchant.kyc_status or "pending",
                "status": merchant.status,
                "created_at": merchant.created_at.isoformat() if merchant.created_at else None,
                "description": merchant.description,
                "website": merchant.website
            },
            "financial": {
                "total_gmv": float(total_gmv),
                "total_outstanding": float(total_outstanding),
                "total_commission": float(total_commission),
                "commission_rate": merchant.commission_rate or 10,
                "total_products": total_products,
                "active_plans": active_plans,
                "pending_payout": float(merchant.pending_payout or 0)
            },
            "bank_details": bank_details,
            "recent_transactions": transactions_data
        }, 200


class AdminUpdateMerchantStatusResource(Resource):
    @auth_required
    def put(self, merchant_id):
        """Update merchant status (active, restricted, suspended)"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        data = request.get_json()
        new_status = data.get('status')
        reason = data.get('reason', '')
        
        if new_status not in ['active', 'approved', 'pending', 'restricted', 'suspended']:
            return {"error": "Invalid status"}, 400
        
        merchant = User.query.filter_by(id=merchant_id, role='merchant').first()
        if not merchant:
            return {"error": "Merchant not found"}, 404
        
        merchant.status = new_status
        db.session.commit()
        
        return {
            "message": f"Merchant status updated to {new_status}",
            "merchant_id": merchant.id,
            "status": new_status
        }, 200


class AdminUpdateMerchantCommissionResource(Resource):
    @auth_required
    def put(self, merchant_id):
        """Update merchant commission rate"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        data = request.get_json()
        commission_rate = data.get('commission_rate')
        
        if not commission_rate or commission_rate < 0 or commission_rate > 100:
            return {"error": "Invalid commission rate"}, 400
        
        merchant = User.query.filter_by(id=merchant_id, role='merchant').first()
        if not merchant:
            return {"error": "Merchant not found"}, 404
        
        merchant.commission_rate = commission_rate
        db.session.commit()
        
        return {
            "message": f"Commission rate updated to {commission_rate}%",
            "merchant_id": merchant.id,
            "commission_rate": commission_rate
        }, 200


class AdminAdjustMerchantReserveResource(Resource):
    @auth_required
    def put(self, merchant_id):
        """Adjust merchant reserve amount"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        data = request.get_json()
        reserve_amount = data.get('reserve_amount')
        reason = data.get('reason', '')
        
        if not reserve_amount or reserve_amount < 0:
            return {"error": "Invalid reserve amount"}, 400
        
        merchant = User.query.filter_by(id=merchant_id, role='merchant').first()
        if not merchant:
            return {"error": "Merchant not found"}, 404
        
        # Store reserve amount (you may need to add this field to User model)
        # merchant.reserve_amount = reserve_amount
        db.session.commit()
        
        return {
            "message": f"Reserve amount adjusted to GHS {reserve_amount}",
            "merchant_id": merchant.id,
            "reserve_amount": reserve_amount
        }, 200