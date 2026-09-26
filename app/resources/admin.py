from flask import json
from flask_restful import Resource, request
from flask_praetorian import auth_required, current_user
from sqlalchemy import Transaction

from app.models.purchase_order import PurchaseOrder
from ..models.user import User
from ..extensions import db
from datetime import datetime, timedelta

def safe_str(v): return v if v is not None else ""
def safe_int(v): return v if v is not None else 0
def safe_bool(v): return v if v is not None else False
def safe_float(v): return v if v is not None else 0.0


class PendingUsersResource(Resource):
    @auth_required
    def get(self):
        if current_user().role != "admin":
            return {"error": "Unauthorized"}, 403
        users = User.query.filter_by(status="pending").all()
        return [{
            "id": u.id, "customer_id": safe_str(u.customer_id), "merchant_id": safe_str(u.merchant_id),
            "phone": safe_str(u.phone), "role": safe_str(u.role), "business_name": safe_str(u.business_name),
            "full_name": safe_str(u.full_name), "owner_name": safe_str(u.owner_name),
            "national_id": safe_str(u.national_id), "city": safe_str(u.city),
            "income_range": safe_str(u.income_range), "status": safe_str(u.status),
            "created_at": u.created_at.isoformat() if u.created_at else ""
        } for u in users]


class ApproveUserResource(Resource):
    @auth_required
    def post(self, user_id):
        if current_user().role != "admin":
            return {"error": "Unauthorized"}, 403
        user = User.query.get(user_id)
        if not user:
            return {"error": "User not found"}, 404
        user.status = "approved"
        if user.role == "customer" and not user.customer_id:
            user.customer_id = user.generate_customer_id()
        elif user.role == "merchant" and not user.merchant_id:
            user.merchant_id = user.generate_merchant_id()
        db.session.commit()
        return {"message": "User approved", "user_id": user.id, "role": user.role,
                "customer_id": user.customer_id if user.role == "customer" else None,
                "merchant_id": user.merchant_id if user.role == "merchant" else None}


class RejectUserResource(Resource):
    @auth_required
    def post(self, user_id):
        if current_user().role != "admin":
            return {"error": "Unauthorized"}, 403
        user = User.query.get(user_id)
        if not user:
            return {"error": "User not found"}, 404
        user.status = "rejected"
        db.session.commit()
        return {"message": "User rejected"}


class GetCustomersResource(Resource):
    @auth_required
    def get(self):
        if current_user().role != "admin":
            return {"error": "Unauthorized"}, 403
        users = User.query.filter_by(role="customer").all()
        return [{
            "id": u.id, "customer_id": safe_str(u.customer_id), "phone": safe_str(u.phone),
            "role": safe_str(u.role), "business_name": safe_str(u.business_name),
            "full_name": safe_str(u.full_name), "national_id": safe_str(u.national_id),
            "city": safe_str(u.city), "income_range": safe_str(u.income_range),
            "status": safe_str(u.status), "created_at": u.created_at.isoformat() if u.created_at else "",
            "payment_plan": safe_str(u.payment_plan), "ref_name": safe_str(u.ref_name),
            "ref_phone": safe_str(u.ref_phone), "ref_relationship": safe_str(u.ref_relationship),
            "gps": safe_str(u.gps), "address": safe_str(u.address), "agree": safe_bool(u.agree),
            "designation": safe_str(u.designation), "company": safe_str(u.company),
            "dob": safe_str(u.dob), "product_name": safe_str(u.product_name),
            "total_price": safe_float(u.total_price), "payment_frequency": safe_str(u.payment_frequency)
        } for u in users]


class CustomerResource(Resource):
    @auth_required
    def get(self, customer_id):
        if current_user().role != "admin":
            return {"error": "Unauthorized"}, 403
        user = User.query.get(customer_id)
        if not user or user.role != "customer":
            return {"error": "Customer not found"}, 404
        return {
            "id": user.id, "customer_id": safe_str(user.customer_id), "phone": safe_str(user.phone),
            "role": safe_str(user.role), "business_name": safe_str(user.business_name),
            "full_name": safe_str(user.full_name), "national_id": safe_str(user.national_id),
            "city": safe_str(user.city), "income_range": safe_str(user.income_range),
            "status": safe_str(user.status), "created_at": user.created_at.isoformat() if user.created_at else "",
            "payment_plan": safe_str(user.payment_plan), "ref_name": safe_str(user.ref_name),
            "ref_phone": safe_str(user.ref_phone), "ref_relationship": safe_str(user.ref_relationship),
            "gps": safe_str(user.gps), "address": safe_str(user.address), "agree": safe_bool(user.agree)
        }

    @auth_required
    def put(self, customer_id):
        if current_user().role != "admin":
            return {"error": "Unauthorized"}, 403
        user = User.query.get(customer_id)
        if not user or user.role != "customer":
            return {"error": "Customer not found"}, 404
        data = request.get_json()
        allowed = ['full_name', 'business_name', 'phone', 'city', 'address', 'status',
                   'payment_plan', 'income_range', 'national_id', 'gps', 'ref_name', 'ref_phone', 'ref_relationship']
        for field in allowed:
            if field in data and data[field] is not None:
                setattr(user, field, data[field])
        db.session.commit()
        return {"message": "Customer updated successfully"}

    @auth_required
    def delete(self, customer_id):
        if current_user().role != "admin":
            return {"error": "Unauthorized"}, 403
        user = User.query.get(customer_id)
        if not user or user.role != "customer":
            return {"error": "Customer not found"}, 404
        name = user.full_name or user.business_name or user.phone
        db.session.delete(user)
        db.session.commit()
        return {"message": f"Customer {name} deleted successfully"}


class GetMerchantsResource(Resource):
    @auth_required
    def get(self):
        if current_user().role != "admin":
            return {"error": "Unauthorized"}, 403
        merchants = User.query.filter_by(role="merchant").all()
        return [{
            "id": m.id, "merchant_id": safe_str(m.merchant_id), "phone": safe_str(m.phone),
            "role": safe_str(m.role), "business_name": safe_str(m.business_name),
            "owner_name": safe_str(m.owner_name), "full_name": safe_str(m.full_name),
            "national_id": safe_str(m.national_id), "city": safe_str(m.city),
            "income_range": safe_str(m.income_range), "status": safe_str(m.status),
            "created_at": m.created_at.isoformat() if m.created_at else "",
            "payment_plan": safe_str(m.payment_plan), "product_type": safe_str(m.product_type),
            "has_shop": safe_str(m.has_shop), "shop_url": safe_str(m.shop_url),
            "years_in_business": safe_str(m.years_in_business), "offers_credit": safe_str(m.offers_credit),
            "price_range": safe_str(m.price_range), "payment_method": safe_str(m.payment_method),
            "momo_name": safe_str(m.momo_name), "momo_number": safe_str(m.momo_number),
            "bank_name": safe_str(m.bank_name), "account_name": safe_str(m.account_name),
            "account_number": safe_str(m.account_number), "business_type": safe_str(getattr(m, 'business_type', '')),
            "registration_number": safe_str(getattr(m, 'registration_number', '')),
            "tax_id": safe_str(getattr(m, 'tax_id', '')), "business_address": safe_str(getattr(m, 'business_address', '')),
            "business_phone": safe_str(getattr(m, 'business_phone', '')),
            "business_email": safe_str(getattr(m, 'business_email', '')), "website": safe_str(getattr(m, 'website', '')),
            "description": safe_str(getattr(m, 'description', '')), "total_products": safe_int(getattr(m, 'total_products', 0)),
            "total_sales": safe_float(getattr(m, 'total_sales', 0)), "rating": safe_float(getattr(m, 'rating', 0)),
            "verified": safe_bool(getattr(m, 'verified', False)), "address": safe_str(m.address),
            "gps": safe_str(m.gps), "agree": safe_bool(m.agree)
        } for m in merchants]


class MerchantResource(Resource):
    @auth_required
    def get(self, merchant_id):
        if current_user().role != "admin":
            return {"error": "Unauthorized"}, 403
        m = User.query.get(merchant_id)
        if not m or m.role != "merchant":
            return {"error": "Merchant not found"}, 404
        return {
            "id": m.id, "merchant_id": safe_str(m.merchant_id), "phone": safe_str(m.phone),
            "role": safe_str(m.role), "business_name": safe_str(m.business_name),
            "owner_name": safe_str(m.owner_name), "full_name": safe_str(m.full_name),
            "national_id": safe_str(m.national_id), "city": safe_str(m.city),
            "income_range": safe_str(m.income_range), "status": safe_str(m.status),
            "created_at": m.created_at.isoformat() if m.created_at else "",
            "payment_plan": safe_str(m.payment_plan), "product_type": safe_str(m.product_type),
            "has_shop": safe_str(m.has_shop), "shop_url": safe_str(m.shop_url),
            "years_in_business": safe_str(m.years_in_business), "offers_credit": safe_str(m.offers_credit),
            "price_range": safe_str(m.price_range), "payment_method": safe_str(m.payment_method),
            "momo_name": safe_str(m.momo_name), "momo_number": safe_str(m.momo_number),
            "bank_name": safe_str(m.bank_name), "account_name": safe_str(m.account_name),
            "account_number": safe_str(m.account_number), "business_type": safe_str(getattr(m, 'business_type', '')),
            "registration_number": safe_str(getattr(m, 'registration_number', '')),
            "tax_id": safe_str(getattr(m, 'tax_id', '')), "business_address": safe_str(getattr(m, 'business_address', '')),
            "business_phone": safe_str(getattr(m, 'business_phone', '')),
            "business_email": safe_str(getattr(m, 'business_email', '')), "website": safe_str(getattr(m, 'website', '')),
            "description": safe_str(getattr(m, 'description', '')), "total_products": safe_int(getattr(m, 'total_products', 0)),
            "total_sales": safe_float(getattr(m, 'total_sales', 0)), "rating": safe_float(getattr(m, 'rating', 0)),
            "verified": safe_bool(getattr(m, 'verified', False)), "address": safe_str(m.address),
            "gps": safe_str(m.gps), "agree": safe_bool(m.agree),
            "kyc_status": safe_str(getattr(m, 'kyc_status', '')),
            "verification_level": safe_str(getattr(m, 'verification_level', '')),
            "aml_screening": safe_str(getattr(m, 'aml_screening', '')),
            "commission_rate": safe_float(getattr(m, 'commission_rate', 2.5)),
            "pending_payout": safe_float(getattr(m, 'pending_payout', 0)),
            "next_settlement": safe_str(getattr(m, 'next_settlement', ''))
        }

    @auth_required
    def put(self, merchant_id):
        if current_user().role != "admin":
            return {"error": "Unauthorized"}, 403
        m = User.query.get(merchant_id)
        if not m or m.role != "merchant":
            return {"error": "Merchant not found"}, 404
        from .merchant_payouts import PAYOUT_FIELDS, PayoutError, apply_payout_details

        data = request.get_json() or {}
        allowed = ['full_name', 'business_name', 'owner_name', 'phone', 'city', 'address', 'status',
                   'payment_plan', 'income_range', 'national_id', 'gps', 'product_type', 'has_shop',
                   'shop_url', 'years_in_business', 'offers_credit', 'price_range', 'payment_method',
                   'business_type', 'registration_number', 'tax_id', 'business_address', 'business_phone',
                   'business_email', 'website', 'description', 'total_products', 'total_sales', 'rating', 'verified']
        for field in allowed:
            if field in data and data[field] is not None:
                setattr(m, field, data[field])
        try:
            apply_payout_details(m, {k: data[k] for k in PAYOUT_FIELDS if k in data and data[k] is not None},
                                 by_admin=True)
        except PayoutError as e:
            return {"error": str(e)}, 400
        db.session.commit()
        return {"message": "Merchant updated successfully"}

    @auth_required
    def delete(self, merchant_id):
        if current_user().role != "admin":
            return {"error": "Unauthorized"}, 403
        m = User.query.get(merchant_id)
        if not m or m.role != "merchant":
            return {"error": "Merchant not found"}, 404
        name = m.business_name or m.owner_name or m.phone
        db.session.delete(m)
        db.session.commit()
        return {"message": f"Merchant {name} deleted successfully"}


class MerchantStatsResource(Resource):
    @auth_required
    def get(self):
        """Get merchant statistics"""
        if current_user().role != "admin":
            return {"error": "Unauthorized"}, 403
        
        merchants = User.query.filter_by(role="merchant").all()
        
        total_merchants = len(merchants)
        active_merchants = len([m for m in merchants if m.status == "active"])
        pending_merchants = len([m for m in merchants if m.status == "pending"])
        verified_merchants = len([m for m in merchants if getattr(m, 'verified', False)])
        
        business_type_distribution = {}
        for merchant in merchants:
            biz_type = getattr(merchant, 'business_type', None)
            if not biz_type:
                biz_type = "Not specified"
            business_type_distribution[biz_type] = business_type_distribution.get(biz_type, 0) + 1
        
        cities_distribution = {}
        for merchant in merchants:
            if merchant.city:
                cities_distribution[merchant.city] = cities_distribution.get(merchant.city, 0) + 1
        
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_merchants = len([m for m in merchants if m.created_at >= thirty_days_ago])

        return {
            "total_merchants": total_merchants,
            "active_merchants": active_merchants,
            "pending_merchants": pending_merchants,
            "verified_merchants": verified_merchants,
            "recent_merchants": recent_merchants,
            "business_type_distribution": business_type_distribution,
            "top_cities": dict(sorted(cities_distribution.items(), key=lambda x: x[1], reverse=True)[:5])
        }


class MerchantKYCResource(Resource):
    @auth_required
    def put(self, merchant_id):
        if current_user().role != "admin":
            return {"error": "Unauthorized"}, 403
        m = User.query.get(merchant_id)
        if not m or m.role != "merchant":
            return {"error": "Merchant not found"}, 404
        data = request.get_json()
        if 'kyc_status' in data:
            m.kyc_status = data['kyc_status']
        if 'verification_level' in data:
            m.verification_level = data['verification_level']
        if 'aml_screening' in data:
            m.aml_screening = data['aml_screening']
        if data.get('kyc_status') == 'verified':
            m.kyc_completed_on = datetime.utcnow()
        db.session.commit()
        return {"message": "KYC updated successfully"}


class MerchantCommissionResource(Resource):
    @auth_required
    def put(self, merchant_id):
        if current_user().role != "admin":
            return {"error": "Unauthorized"}, 403
        m = User.query.get(merchant_id)
        if not m or m.role != "merchant":
            return {"error": "Merchant not found"}, 404
        data = request.get_json()
        if 'commission_rate' in data:
            m.commission_rate = data['commission_rate']
        db.session.commit()
        return {"message": "Commission updated", "commission_rate": safe_float(m.commission_rate)}


class MerchantSettlementResource(Resource):
    @auth_required
    def put(self, merchant_id):
        if current_user().role != "admin":
            return {"error": "Unauthorized"}, 403
        m = User.query.get(merchant_id)
        if not m or m.role != "merchant":
            return {"error": "Merchant not found"}, 404
        from .merchant_payouts import PayoutError, apply_payout_details

        data = request.get_json() or {}
        # pending_payout/next_settlement are no longer editable: they come from settlement batches
        try:
            apply_payout_details(m, {k: data[k] for k in ('bank_name', 'account_name', 'account_number') if k in data},
                                 by_admin=True)
        except PayoutError as e:
            return {"error": str(e)}, 400
        db.session.commit()
        return {"message": "Settlement updated"}


class VerifyMerchantResource(Resource):
    @auth_required
    def post(self, merchant_id):
        if current_user().role != "admin":
            return {"error": "Unauthorized"}, 403
        m = User.query.get(merchant_id)
        if not m or m.role != "merchant":
            return {"error": "Merchant not found"}, 404
        m.verified = True
        db.session.commit()
        return {"message": "Merchant verified successfully"}


# Add these missing classes for bulk operations and search
class BulkUpdateCustomersResource(Resource):
    @auth_required
    def patch(self):
        if current_user().role != "admin":
            return {"error": "Unauthorized"}, 403
        data = request.get_json()
        customer_ids = data.get('ids', [])
        update_data = data.get('data', {})
        allowed_fields = ['status', 'payment_plan', 'income_range']
        updated_count = 0
        for customer_id in customer_ids:
            user = User.query.get(customer_id)
            if user and user.role == "customer":
                for field in allowed_fields:
                    if field in update_data:
                        setattr(user, field, update_data[field])
                updated_count += 1
        db.session.commit()
        return {"message": f"Successfully updated {updated_count} customers"}


class SearchCustomersResource(Resource):
    @auth_required
    def get(self):
        if current_user().role != "admin":
            return {"error": "Unauthorized"}, 403
        search_term = request.args.get('search', '').strip()
        status = request.args.get('status', '').strip()
        city = request.args.get('city', '').strip()
        query = User.query.filter_by(role="customer")
        if search_term:
            query = query.filter(
                db.or_(
                    User.full_name.ilike(f'%{search_term}%'),
                    User.business_name.ilike(f'%{search_term}%'),
                    User.phone.ilike(f'%{search_term}%'),
                    User.city.ilike(f'%{search_term}%')
                )
            )
        if status:
            query = query.filter_by(status=status)
        if city:
            query = query.filter_by(city=city)
        users = query.all()
        return [{"id": u.id, "customer_id": safe_str(u.customer_id), "phone": safe_str(u.phone),
                 "full_name": safe_str(u.full_name), "business_name": safe_str(u.business_name),
                 "city": safe_str(u.city), "status": safe_str(u.status)} for u in users]


class CustomerStatsResource(Resource):
    @auth_required
    def get(self):
        if current_user().role != "admin":
            return {"error": "Unauthorized"}, 403
        customers = User.query.filter_by(role="customer").all()
        return {
            "total_customers": len(customers),
            "active_customers": len([c for c in customers if c.status == "active"]),
            "pending_customers": len([c for c in customers if c.status == "pending"]),
            "inactive_customers": len([c for c in customers if c.status == "inactive"])
        }


class ExportCustomersResource(Resource):
    @auth_required
    def get(self):
        from flask import Response
        import csv
        from io import StringIO
        if current_user().role != "admin":
            return {"error": "Unauthorized"}, 403
        customers = User.query.filter_by(role="customer").all()
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['ID', 'Customer ID', 'Full Name', 'Phone', 'City', 'Status', 'Join Date'])
        for c in customers:
            writer.writerow([c.id, safe_str(c.customer_id), safe_str(c.full_name), safe_str(c.phone),
                           safe_str(c.city), safe_str(c.status), c.created_at.isoformat() if c.created_at else ''])
        output.seek(0)
        return Response(output.getvalue(), mimetype='text/csv',
                       headers={'Content-Disposition': 'attachment; filename=customers.csv'})






class GetCurrentUserResource(Resource):

    @auth_required
    def get(self):

        user = current_user()

        if not user:
            return {
                "error": "User not found"
            }, 404

        return {
            "id": user.id,
            "merchant_id": safe_str(user.merchant_id),
            "customer_id": safe_str(user.customer_id),

            "phone": safe_str(user.phone),
            "role": safe_str(user.role),
            "status": safe_str(user.status),

            "business_name": safe_str(user.business_name),
            "owner_name": safe_str(user.owner_name),
            "full_name": safe_str(user.full_name),

            "business_email": safe_str(user.business_email),
            "business_phone": safe_str(user.business_phone),

            "business_address": safe_str(user.business_address),
            "business_type": safe_str(user.business_type),

            "website": safe_str(user.website),
            "description": safe_str(user.description),

            "city": safe_str(user.city),
            "gps": safe_str(user.gps),
            "address": safe_str(user.address),

            "verified": safe_bool(user.verified),

            "kyc_status": safe_str(user.kyc_status),
            "verification_level": safe_str(user.verification_level),

            "commission_rate": safe_float(user.commission_rate),
            "pending_payout": safe_float(user.pending_payout),

            "total_products": safe_int(user.total_products),
            "total_sales": safe_float(user.total_sales),

            "rating": safe_float(user.rating),

            "created_at": user.created_at.isoformat() if user.created_at else ""
        }
    


# resources/admin_orders.py - Updated approve method
# resources/admin_orders.py - Add missing imports at the top

from flask_restful import Resource, request
from flask_praetorian import auth_required, current_user
from ..models.purchase_order import PurchaseOrder
from ..models.transaction import Transaction
from ..models.instalment import InstalmentPlan
from ..models.instalment_payment import InstalmentPayment
from ..extensions import db
from datetime import datetime, timedelta
import json

def safe_str(v): return v if v is not None else ""

# resources/admin_orders.py
from flask_restful import Resource, request
from flask_praetorian import auth_required, current_user
from ..models.purchase_order import PurchaseOrder
from ..models.transaction import Transaction
from ..models.instalment import InstalmentPlan
from ..models.instalment_payment import InstalmentPayment
from ..extensions import db
from datetime import datetime, timedelta
import json

def safe_str(v): return v if v is not None else ""
# resources/admin_orders.py
from flask_restful import Resource, request
from flask_praetorian import auth_required, current_user
from ..models.purchase_order import PurchaseOrder
from ..models.transaction import Transaction
from ..models.instalment import InstalmentPlan
from ..models.instalment_payment import InstalmentPayment
from ..extensions import db
from datetime import datetime, timedelta
import json

class AdminApproveOrderResource(Resource):
    @auth_required
    def put(self, order_id):
        """Admin approves an order and creates instalment plan with payment schedule"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        order = PurchaseOrder.query.get(order_id)
        if not order:
            return {"error": "Order not found"}, 404
        
        if order.status == 'awaiting_payment':
            return {"error": "The customer hasn't paid the down payment yet"}, 400
        if order.status != 'pending':
            return {"error": f"Order already {order.status}"}, 400

        data = request.get_json() or {}

        # Order status is committed together with the plan, payments and transaction below
        order.status = 'approved'
        order.approved_at = datetime.now()
        order.admin_notes = data.get('admin_notes', '')

        from ..services import plan_engine
        from ..models.system_settings import SystemSetting

        # Calculate dates
        start_date = datetime.now()
        end_date = start_date
        if order.number_of_installments > 1:
            end_date = plan_engine.add_months(start_date, order.number_of_installments - 1)

        # Balance still owed after Payment 1 (down payment + delivery fee) = financed balance FB
        stored_schedule = json.loads(order.payment_schedule) if order.payment_schedule else []
        if stored_schedule:
            remaining_balance = float(sum(plan_engine.money(p['amount']) for p in stored_schedule[1:]))
        else:
            remaining_balance = order.total_payable - order.down_payment_amount

        # MDR is charged on the product value P, not on delivery fee (§5.2: MS = P x (1 - MDR))
        product_value = plan_engine.money(order.product_price) * (order.quantity or 1)
        mdr = plan_engine.rate(SystemSetting.get_value("merchant_fee_percentage", 10)) / 100
        commission_amount = (product_value * mdr).quantize(plan_engine.CENT)
        payout_amount = float(product_value - commission_amount)
        
        # Payment 1 (down payment + delivery fee): normally already collected at checkout
        # through Paystack. In the manual fallback (no Paystack), it's only marked paid when
        # the admin records the reference for money received; otherwise it waits for verification.
        if order.down_payment_status == 'paid':
            down_payment_reference = order.down_payment_reference
            down_payment_method = order.down_payment_method or 'paystack'
        else:
            down_payment_reference = (data.get('down_payment_reference') or '').strip()
            down_payment_method = (data.get('down_payment_method') or 'mobile_money').strip()
        down_payment_received = bool(down_payment_reference)

        # Orders placed before server-side pricing carry a browser-built schedule
        # (no 'type' field). Those amounts can't be trusted, so they must be re-placed.
        if not stored_schedule or any('type' not in item for item in stored_schedule):
            db.session.rollback()
            return {"error": "This order was priced by the old checkout. Reject it and ask the customer to place it again."}, 409
        try:
            instalment_plan = InstalmentPlan(
                plan_id=InstalmentPlan.generate_plan_id(InstalmentPlan),
                merchant_id=order.merchant_id,
                customer_id=order.customer_id,
                transaction_id=None,
                plan_name=order.product_name,
                description=order.product_description or "",
                total_amount=float(order.total_payable),
                down_payment=float(order.down_payment_amount),
                remaining_amount=float(remaining_balance),
                number_of_installments=int(order.number_of_installments),
                installment_amount=float(order.installment_amount),
                frequency='monthly',
                start_date=start_date,
                end_date=end_date,
                status='active',
                payment_status='partial' if down_payment_received else 'pending',
                paid_installments=1 if down_payment_received else 0,
                customer_name=order.customer.full_name or order.customer.business_name or "Customer",
                customer_phone=order.customer.phone or "",
                customer_email=order.customer.business_email or order.customer.email or ""
            )
            db.session.add(instalment_plan)
            db.session.flush()


            from ..services import ledger
            down_payment_row = None

            for item in stored_schedule:
                number = int(item['installment_number'])
                amount = float(plan_engine.money(item['amount']))
                due_date = datetime.strptime(item['due_date'][:10], '%Y-%m-%d')
                is_down_payment = number == 1

                if is_down_payment and down_payment_received:
                    status, paid_date, paid_amount = 'paid', start_date, amount
                elif is_down_payment:
                    status, paid_date, paid_amount = 'pending_verification', None, 0
                else:
                    status, paid_date, paid_amount = 'pending', None, 0

                row = InstalmentPayment(
                    payment_id=InstalmentPayment.generate_payment_id(InstalmentPayment),
                    plan_id=instalment_plan.id,
                    installment_number=number,
                    due_date=due_date,
                    paid_date=paid_date,
                    amount=amount,
                    paid_amount=paid_amount,
                    status=status,
                    payment_method=down_payment_method if is_down_payment and down_payment_received else None,
                    payment_reference=down_payment_reference if is_down_payment and down_payment_received else None,
                    late_fee=0,
                    late_fee_paid=False
                )
                db.session.add(row)
                db.session.flush()
                if is_down_payment:
                    down_payment_row = row

            transaction = Transaction(
                transaction_id=Transaction.generate_transaction_id(Transaction),
                customer_id=order.customer_id,
                merchant_id=order.merchant_id,
                amount=float(product_value),
                product_name=order.product_name,
                product_description=order.product_description or "",
                quantity=order.quantity or 1,
                payment_plan=f"{order.number_of_installments} Months",
                status='completed',
                payment_status='processing',
                delivery_address=order.delivery_address or "",
                transaction_date=datetime.now(),
                payout_amount=payout_amount
            )
            db.session.add(transaction)
            db.session.flush()
            instalment_plan.transaction_id = transaction.id
            order.transaction_id = transaction.id

            # Ledger: the contract, the merchant side, and the down payment if already received
            ledger.open_plan(instalment_plan, order.total_payable, commission_amount,
                             payout_amount, user=current_admin)
            if down_payment_received and down_payment_row is not None:
                ledger.payment_received(instalment_plan, down_payment_row, down_payment_row.amount,
                                        down_payment_reference, user=current_admin)

            db.session.commit()
        except Exception as e:
            return self._fail(f"Failed to approve order: {e}")

        return {
            "message": "Order approved and instalment plan created",
            "transaction_id": transaction.transaction_id,
            "plan_id": instalment_plan.plan_id,
            "payments_created": len(stored_schedule),
            "down_payment_status": "paid" if down_payment_received else "pending_verification",
            "order_total": float(order.total_payable),
            "merchant_fee": float(commission_amount),
            "payout_amount": payout_amount,
            "currency": "GHS"
        }, 200

    @staticmethod
    def _fail(message):
        db.session.rollback()
        return {"error": message}, 500
