from flask_restful import Resource, request
from flask_praetorian import auth_required, current_user
from ..models.user import User
from ..extensions import db, guard
from datetime import datetime

def safe_str(value):
    """Convert None to empty string, otherwise return the value"""
    return value if value is not None else ""

def safe_int(value):
    """Convert None to 0, otherwise return the value"""
    return value if value is not None else 0

def safe_bool(value):
    """Convert None to False, otherwise return the value"""
    return value if value is not None else False

def safe_float(value):
    """Convert None to 0.0, otherwise return the value"""
    return value if value is not None else 0.0


class PendingUsersResource(Resource):
    @auth_required
    def get(self):
        current_user_obj = current_user()

        if current_user_obj.role != "admin":
            return {"error": "Unauthorized"}, 403

        users = User.query.filter_by(status="pending").all()

        return [
            {
                "id": u.id,
                "customer_id": safe_str(u.customer_id),
                "merchant_id": safe_str(u.merchant_id),
                "phone": safe_str(u.phone),
                "role": safe_str(u.role),
                "business_name": safe_str(u.business_name),
                "full_name": safe_str(u.full_name),
                "owner_name": safe_str(u.owner_name),
                "national_id": safe_str(u.national_id),
                "city": safe_str(u.city),
                "income_range": safe_str(u.income_range),
                "status": safe_str(u.status),
                "created_at": u.created_at.isoformat() if u.created_at else "",
            } for u in users
        ]


class ApproveUserResource(Resource):
    @auth_required
    def post(self, user_id):
        current_user_obj = current_user()

        if current_user_obj.role != "admin":
            return {"error": "Unauthorized"}, 403

        user = User.query.get(user_id)

        if not user:
            return {"error": "User not found"}, 404

        user.status = "approved"
        
        # Generate role-specific ID based on user's role
        if user.role == "customer" and not user.customer_id:
            user.customer_id = user.generate_customer_id()
            print(f"✅ Generated Customer ID: {user.customer_id} for user {user.id}")
        elif user.role == "merchant" and not user.merchant_id:
            user.merchant_id = user.generate_merchant_id()
            print(f"✅ Generated Merchant ID: {user.merchant_id} for user {user.id}")
        
        db.session.commit()

        return {
            "message": "User approved",
            "user_id": user.id,
            "role": user.role,
            "customer_id": user.customer_id if user.role == "customer" else None,
            "merchant_id": user.merchant_id if user.role == "merchant" else None
        }


class RejectUserResource(Resource):
    @auth_required
    def post(self, user_id):
        current_user_obj = current_user()

        if current_user_obj.role != "admin":
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
        current_user_obj = current_user()

        if current_user_obj.role != "admin":
            return {"error": "Unauthorized"}, 403

        users = User.query.filter_by(role="customer").all()

        return [
            {
                "id": u.id,
                "customer_id": safe_str(u.customer_id),
                "phone": safe_str(u.phone),
                "role": safe_str(u.role),
                "business_name": safe_str(u.business_name),
                "full_name": safe_str(u.full_name),
                "national_id": safe_str(u.national_id),
                "city": safe_str(u.city),
                "income_range": safe_str(u.income_range),
                "status": safe_str(u.status),
                "created_at": u.created_at.isoformat() if u.created_at else "",
                "payment_plan": safe_str(u.payment_plan),
                "ref_name": safe_str(u.ref_name),
                "ref_phone": safe_str(u.ref_phone),
                "ref_relationship": safe_str(u.ref_relationship),
                "gps": safe_str(u.gps),
                "address": safe_str(u.address),
                "agree": safe_bool(u.agree),
                "designation": safe_str(u.designation),
                "company": safe_str(u.company),
                "dob": safe_str(u.dob),
                "product_name": safe_str(u.product_name),
                "total_price": safe_float(u.total_price),
                "payment_frequency": safe_str(u.payment_frequency),
            } for u in users
        ]


class CustomerResource(Resource):
    @auth_required
    def get(self, customer_id):
        """Get a single customer by ID"""
        current_user_obj = current_user()

        if current_user_obj.role != "admin":
            return {"error": "Unauthorized"}, 403

        user = User.query.get(customer_id)

        if not user:
            return {"error": "Customer not found"}, 404

        if user.role != "customer":
            return {"error": "User is not a customer"}, 400

        return {
            "id": user.id,
            "customer_id": safe_str(user.customer_id),
            "phone": safe_str(user.phone),
            "role": safe_str(user.role),
            "business_name": safe_str(user.business_name),
            "full_name": safe_str(user.full_name),
            "national_id": safe_str(user.national_id),
            "city": safe_str(user.city),
            "income_range": safe_str(user.income_range),
            "status": safe_str(user.status),
            "created_at": user.created_at.isoformat() if user.created_at else "",
            "payment_plan": safe_str(user.payment_plan),
            "ref_name": safe_str(user.ref_name),
            "ref_phone": safe_str(user.ref_phone),
            "ref_relationship": safe_str(user.ref_relationship),
            "gps": safe_str(user.gps),
            "address": safe_str(user.address),
            "agree": safe_bool(user.agree),
        }

    @auth_required
    def put(self, customer_id):
        """Update a customer"""
        current_user_obj = current_user()

        if current_user_obj.role != "admin":
            return {"error": "Unauthorized"}, 403

        user = User.query.get(customer_id)

        if not user:
            return {"error": "Customer not found"}, 404

        if user.role != "customer":
            return {"error": "User is not a customer"}, 400

        data = request.get_json()

        allowed_fields = [
            'full_name', 'business_name', 'phone', 'city', 'address',
            'status', 'payment_plan', 'income_range', 'national_id',
            'gps', 'ref_name', 'ref_phone', 'ref_relationship'
        ]

        for field in allowed_fields:
            if field in data and data[field] is not None:
                setattr(user, field, data[field])

        if 'email' in data and hasattr(user, 'email'):
            user.email = data['email']

        db.session.commit()

        return {
            "message": "Customer updated successfully",
            "customer": {
                "id": user.id,
                "customer_id": safe_str(user.customer_id),
                "phone": safe_str(user.phone),
                "role": safe_str(user.role),
                "business_name": safe_str(user.business_name),
                "full_name": safe_str(user.full_name),
                "national_id": safe_str(user.national_id),
                "city": safe_str(user.city),
                "income_range": safe_str(user.income_range),
                "status": safe_str(user.status),
                "created_at": user.created_at.isoformat() if user.created_at else "",
                "payment_plan": safe_str(user.payment_plan),
                "ref_name": safe_str(user.ref_name),
                "ref_phone": safe_str(user.ref_phone),
                "ref_relationship": safe_str(user.ref_relationship),
                "gps": safe_str(user.gps),
                "address": safe_str(user.address),
                "agree": safe_bool(user.agree),
            }
        }, 200

    @auth_required
    def delete(self, customer_id):
        """Delete a customer"""
        current_user_obj = current_user()

        if current_user_obj.role != "admin":
            return {"error": "Unauthorized"}, 403

        user = User.query.get(customer_id)

        if not user:
            return {"error": "Customer not found"}, 404

        if user.role != "customer":
            return {"error": "User is not a customer"}, 400

        customer_name = user.full_name or user.business_name or user.phone

        db.session.delete(user)
        db.session.commit()

        return {
            "message": f"Customer {customer_name} deleted successfully",
            "customer_id": customer_id
        }, 200


class BulkUpdateCustomersResource(Resource):
    @auth_required
    def patch(self):
        """Bulk update multiple customers"""
        current_user_obj = current_user()

        if current_user_obj.role != "admin":
            return {"error": "Unauthorized"}, 403

        data = request.get_json()
        customer_ids = data.get('ids', [])
        update_data = data.get('data', {})

        if not customer_ids:
            return {"error": "No customer IDs provided"}, 400

        if not update_data:
            return {"error": "No update data provided"}, 400

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

        return {
            "message": f"Successfully updated {updated_count} customers",
            "updated_count": updated_count
        }, 200


class SearchCustomersResource(Resource):
    @auth_required
    def get(self):
        """Search customers with advanced filters"""
        current_user_obj = current_user()

        if current_user_obj.role != "admin":
            return {"error": "Unauthorized"}, 403

        search_term = request.args.get('search', '').strip()
        status = request.args.get('status', '').strip()
        city = request.args.get('city', '').strip()
        payment_plan = request.args.get('payment_plan', '').strip()
        income_range = request.args.get('income_range', '').strip()
        start_date = request.args.get('start_date', '').strip()
        end_date = request.args.get('end_date', '').strip()

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
        if payment_plan:
            query = query.filter_by(payment_plan=payment_plan)
        if income_range:
            query = query.filter_by(income_range=income_range)
        if start_date:
            query = query.filter(User.created_at >= start_date)
        if end_date:
            query = query.filter(User.created_at <= end_date)

        users = query.all()

        return [
            {
                "id": u.id,
                "customer_id": safe_str(u.customer_id),
                "phone": safe_str(u.phone),
                "full_name": safe_str(u.full_name),
                "business_name": safe_str(u.business_name),
                "city": safe_str(u.city),
                "status": safe_str(u.status),
                "payment_plan": safe_str(u.payment_plan),
                "income_range": safe_str(u.income_range),
                "created_at": u.created_at.isoformat() if u.created_at else "",
                "address": safe_str(u.address),
            } for u in users
        ]


class CustomerStatsResource(Resource):
    @auth_required
    def get(self):
        """Get customer statistics"""
        current_user_obj = current_user()

        if current_user_obj.role != "admin":
            return {"error": "Unauthorized"}, 403

        customers = User.query.filter_by(role="customer").all()
        
        total_customers = len(customers)
        active_customers = len([c for c in customers if c.status == "active"])
        pending_customers = len([c for c in customers if c.status == "pending"])
        inactive_customers = len([c for c in customers if c.status == "inactive"])
        
        income_distribution = {}
        for customer in customers:
            if customer.income_range:
                income_distribution[customer.income_range] = income_distribution.get(customer.income_range, 0) + 1
        
        payment_plan_distribution = {}
        for customer in customers:
            plan = customer.payment_plan or "none"
            payment_plan_distribution[plan] = payment_plan_distribution.get(plan, 0) + 1
        
        cities_distribution = {}
        for customer in customers:
            if customer.city:
                cities_distribution[customer.city] = cities_distribution.get(customer.city, 0) + 1
        
        from datetime import datetime, timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_customers = len([c for c in customers if c.created_at >= thirty_days_ago])

        return {
            "total_customers": total_customers,
            "active_customers": active_customers,
            "pending_customers": pending_customers,
            "inactive_customers": inactive_customers,
            "recent_customers": recent_customers,
            "income_distribution": income_distribution,
            "payment_plan_distribution": payment_plan_distribution,
            "top_cities": dict(sorted(cities_distribution.items(), key=lambda x: x[1], reverse=True)[:5])
        }


class ExportCustomersResource(Resource):
    @auth_required
    def get(self):
        """Export customers to CSV format"""
        from flask import Response
        import csv
        from io import StringIO

        current_user_obj = current_user()

        if current_user_obj.role != "admin":
            return {"error": "Unauthorized"}, 403

        customers = User.query.filter_by(role="customer").all()

        output = StringIO()
        writer = csv.writer(output)

        writer.writerow([
            'ID', 'Customer ID', 'Full Name', 'Business Name', 'Phone', 'National ID',
            'City', 'Address', 'GPS', 'Status', 'Payment Plan',
            'Income Range', 'Join Date', 'Referrer Name', 'Referrer Phone',
            'Referrer Relationship'
        ])

        for customer in customers:
            writer.writerow([
                customer.id,
                safe_str(customer.customer_id),
                safe_str(customer.full_name),
                safe_str(customer.business_name),
                safe_str(customer.phone),
                safe_str(customer.national_id),
                safe_str(customer.city),
                safe_str(customer.address),
                safe_str(customer.gps),
                safe_str(customer.status),
                safe_str(customer.payment_plan),
                safe_str(customer.income_range),
                customer.created_at.strftime('%Y-%m-%d %H:%M:%S') if customer.created_at else '',
                safe_str(customer.ref_name),
                safe_str(customer.ref_phone),
                safe_str(customer.ref_relationship)
            ])

        output.seek(0)
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=customers_{datetime.utcnow().strftime("%Y%m%d")}.csv',
                'Content-Type': 'text/csv'
            }
        )


# ============================================================================
# MERCHANT RESOURCES
# ============================================================================

class GetMerchantsResource(Resource):
    @auth_required
    def get(self):
        """Get all merchants"""
        current_user_obj = current_user()

        if current_user_obj.role != "admin":
            return {"error": "Unauthorized"}, 403

        merchants = User.query.filter_by(role="merchant").all()

        return [
            {
                "id": m.id,
                "merchant_id": safe_str(m.merchant_id),
                "phone": safe_str(m.phone),
                "role": safe_str(m.role),
                "business_name": safe_str(m.business_name),
                "owner_name": safe_str(m.owner_name),
                "full_name": safe_str(m.full_name),
                "national_id": safe_str(m.national_id),
                "city": safe_str(m.city),
                "income_range": safe_str(m.income_range),
                "status": safe_str(m.status),
                "created_at": m.created_at.isoformat() if m.created_at else "",
                "payment_plan": safe_str(m.payment_plan),
                "product_type": safe_str(m.product_type),
                "has_shop": safe_str(m.has_shop),
                "shop_url": safe_str(m.shop_url),
                "years_in_business": safe_str(m.years_in_business),
                "offers_credit": safe_str(m.offers_credit),
                "price_range": safe_str(m.price_range),
                "payment_method": safe_str(m.payment_method),
                "momo_name": safe_str(m.momo_name),
                "momo_number": safe_str(m.momo_number),
                "bank_name": safe_str(m.bank_name),
                "account_name": safe_str(m.account_name),
                "account_number": safe_str(m.account_number),
                "business_type": safe_str(getattr(m, 'business_type', '')),
                "registration_number": safe_str(getattr(m, 'registration_number', '')),
                "tax_id": safe_str(getattr(m, 'tax_id', '')),
                "business_address": safe_str(getattr(m, 'business_address', '')),
                "business_phone": safe_str(getattr(m, 'business_phone', '')),
                "business_email": safe_str(getattr(m, 'business_email', '')),
                "website": safe_str(getattr(m, 'website', '')),
                "description": safe_str(getattr(m, 'description', '')),
                "total_products": safe_int(getattr(m, 'total_products', 0)),
                "total_sales": safe_float(getattr(m, 'total_sales', 0)),
                "rating": safe_float(getattr(m, 'rating', 0)),
                "verified": safe_bool(getattr(m, 'verified', False)),
                "address": safe_str(m.address),
                "gps": safe_str(m.gps),
                "agree": safe_bool(m.agree),
            } for m in merchants
        ]


class MerchantResource(Resource):
    @auth_required
    def get(self, merchant_id):
        """Get single merchant by ID"""
        current_user_obj = current_user()

        if current_user_obj.role != "admin":
            return {"error": "Unauthorized"}, 403

        merchant = User.query.get(merchant_id)

        if not merchant:
            return {"error": "Merchant not found"}, 404

        if merchant.role != "merchant":
            return {"error": "User is not a merchant"}, 400

        return {
            "id": merchant.id,
            "merchant_id": safe_str(merchant.merchant_id),
            "phone": safe_str(merchant.phone),
            "role": safe_str(merchant.role),
            "business_name": safe_str(merchant.business_name),
            "owner_name": safe_str(merchant.owner_name),
            "full_name": safe_str(merchant.full_name),
            "national_id": safe_str(merchant.national_id),
            "city": safe_str(merchant.city),
            "income_range": safe_str(merchant.income_range),
            "status": safe_str(merchant.status),
            "created_at": merchant.created_at.isoformat() if merchant.created_at else "",
            "payment_plan": safe_str(merchant.payment_plan),
            "product_type": safe_str(merchant.product_type),
            "has_shop": safe_str(merchant.has_shop),
            "shop_url": safe_str(merchant.shop_url),
            "years_in_business": safe_str(merchant.years_in_business),
            "offers_credit": safe_str(merchant.offers_credit),
            "price_range": safe_str(merchant.price_range),
            "payment_method": safe_str(merchant.payment_method),
            "momo_name": safe_str(merchant.momo_name),
            "momo_number": safe_str(merchant.momo_number),
            "bank_name": safe_str(merchant.bank_name),
            "account_name": safe_str(merchant.account_name),
            "account_number": safe_str(merchant.account_number),
            "business_type": safe_str(getattr(merchant, 'business_type', '')),
            "registration_number": safe_str(getattr(merchant, 'registration_number', '')),
            "tax_id": safe_str(getattr(merchant, 'tax_id', '')),
            "business_address": safe_str(getattr(merchant, 'business_address', '')),
            "business_phone": safe_str(getattr(merchant, 'business_phone', '')),
            "business_email": safe_str(getattr(merchant, 'business_email', '')),
            "website": safe_str(getattr(merchant, 'website', '')),
            "description": safe_str(getattr(merchant, 'description', '')),
            "total_products": safe_int(getattr(merchant, 'total_products', 0)),
            "total_sales": safe_float(getattr(merchant, 'total_sales', 0)),
            "rating": safe_float(getattr(merchant, 'rating', 0)),
            "verified": safe_bool(getattr(merchant, 'verified', False)),
            "address": safe_str(merchant.address),
            "gps": safe_str(merchant.gps),
            "agree": safe_bool(merchant.agree),
        }

    @auth_required
    def put(self, merchant_id):
        """Update merchant"""
        current_user_obj = current_user()

        if current_user_obj.role != "admin":
            return {"error": "Unauthorized"}, 403

        merchant = User.query.get(merchant_id)

        if not merchant:
            return {"error": "Merchant not found"}, 404

        if merchant.role != "merchant":
            return {"error": "User is not a merchant"}, 400

        data = request.get_json()

        allowed_fields = [
            'full_name', 'business_name', 'owner_name', 'phone', 'city', 'address',
            'status', 'payment_plan', 'income_range', 'national_id',
            'gps', 'product_type', 'has_shop', 'shop_url', 'years_in_business',
            'offers_credit', 'price_range', 'payment_method',
            'momo_name', 'momo_number', 'bank_name', 'account_name', 'account_number',
            'business_type', 'registration_number', 'tax_id', 'business_address',
            'business_phone', 'business_email', 'website', 'description',
            'total_products', 'total_sales', 'rating', 'verified'
        ]

        for field in allowed_fields:
            if field in data and data[field] is not None:
                setattr(merchant, field, data[field])

        db.session.commit()

        return {
            "message": "Merchant updated successfully",
            "merchant": {
                "id": merchant.id,
                "merchant_id": safe_str(merchant.merchant_id),
                "business_name": safe_str(merchant.business_name),
                "owner_name": safe_str(merchant.owner_name),
                "phone": safe_str(merchant.phone),
                "status": safe_str(merchant.status),
                "verified": safe_bool(getattr(merchant, 'verified', False))
            }
        }, 200

    @auth_required
    def delete(self, merchant_id):
        """Delete merchant"""
        current_user_obj = current_user()

        if current_user_obj.role != "admin":
            return {"error": "Unauthorized"}, 403

        merchant = User.query.get(merchant_id)

        if not merchant:
            return {"error": "Merchant not found"}, 404

        if merchant.role != "merchant":
            return {"error": "User is not a merchant"}, 400

        merchant_name = merchant.business_name or merchant.owner_name or merchant.phone

        db.session.delete(merchant)
        db.session.commit()

        return {
            "message": f"Merchant {merchant_name} deleted successfully",
            "merchant_id": merchant_id
        }, 200


class VerifyMerchantResource(Resource):
    @auth_required
    def post(self, merchant_id):
        """Verify a merchant"""
        current_user_obj = current_user()

        if current_user_obj.role != "admin":
            return {"error": "Unauthorized"}, 403

        merchant = User.query.get(merchant_id)

        if not merchant:
            return {"error": "Merchant not found"}, 404

        if merchant.role != "merchant":
            return {"error": "User is not a merchant"}, 400

        setattr(merchant, 'verified', True)
        db.session.commit()

        return {"message": "Merchant verified successfully"}, 200


class MerchantStatsResource(Resource):
    @auth_required
    def get(self):
        """Get merchant statistics"""
        current_user_obj = current_user()

        if current_user_obj.role != "admin":
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