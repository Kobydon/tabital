# resources/system_settings.py
from flask_restful import Resource, request
from flask_praetorian import auth_required, current_user
from ..models.system_settings import SystemSetting
from ..extensions import db
from datetime import datetime
import json

class SystemSettingsResource(Resource):
    @auth_required
    def get(self):
        """Get all system settings"""
        current_admin = current_user()

        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        settings = SystemSetting.query.all()
        
        # Format response for frontend
        result = {}
        for s in settings:
            if s.setting_type == 'json':
                result[s.setting_key] = json.loads(s.setting_value)
            elif s.setting_type == 'number':
                result[s.setting_key] = float(s.setting_value) if '.' in s.setting_value else int(s.setting_value)
            elif s.setting_type == 'boolean':
                result[s.setting_key] = s.setting_value.lower() == 'true'
            else:
                result[s.setting_key] = s.setting_value
        
        return result, 200
    
    @auth_required
    def put(self):
        """Retired: wrote any key and value without validation or an audit trail."""
        if current_user().role != 'admin':
            return {"error": "Unauthorized"}, 403
        return {"error": "Settings are changed on the Business Settings page now (validated, with a reason). "
                         "Use PUT /admin/business-settings."}, 410


class InstallmentOptionsResource(Resource):
    @auth_required
    def get(self):
        """Get installment options"""
        current_user_obj = current_user()
        
        # Admin or merchant can access
        if current_user_obj.role not in ['admin', 'merchant']:
            return {"error": "Unauthorized"}, 403
        
        options = SystemSetting.get_value("installment_options", [])
        return {"installment_options": options}, 200
    
    @auth_required
    def put(self):
        """Retired: the plans on offer are fixed by the plan engine (Pay in 2/3/4 and full, §4)."""
        if current_user().role != 'admin':
            return {"error": "Unauthorized"}, 403
        return {"error": "Instalment options can't be edited: the plans on offer are set by the business rules (§4)."}, 410
from flask import request
from flask_restful import Resource
from flask_praetorian import auth_required, current_user
from datetime import datetime, timedelta


class InstallmentCalculatorResource(Resource):

    @auth_required
    def post(self):
        """Calculate installment plan"""

        from ..services import plan_engine, risk

        current_user_obj = current_user()
        data = request.get_json() or {}

        # A customer's quote uses their risk tier's Pay in 4 down payment, so the Shop
        # shows exactly what /customer/purchase will charge
        tier_dp_rate = None
        credit = None
        if current_user_obj.role == 'customer':
            decision, _ = risk.decide(current_user_obj)
            credit = risk.decision_view(decision)
            if decision.eligible:
                tier_dp_rate = decision.pay_in_4_dp_rate

        try:
            product_price = plan_engine.money(data.get('product_price', 0))
            quantity = int(data.get('quantity', 1))
            number_of_installments = int(data.get('number_of_installments', 1))
            plan = plan_engine.quote(product_price, quantity, number_of_installments, SystemSetting.get_value,
                                     pay_in_4_dp_rate=tier_dp_rate, in_store=bool(data.get('in_store')))
        except (plan_engine.PlanError, ArithmeticError, TypeError, ValueError) as e:
            return {"error": str(e) or "Invalid plan request"}, 400

        f = float
        late_fee_percentage = f(SystemSetting.get_value("late_fee_percentage", 10))

        # This is a quote only. /customer/purchase recalculates from the stored product price.
        return {
            "product_price": f(plan["price"]),
            "down_payment": {
                "percentage": f(plan["down_payment_rate"] * 100),
                "amount": f(plan["down_payment"])
            },
            "due_now": f(plan["due_now"]),
            "remaining_balance": f(plan["financed_balance"]),
            "installment_details": {
                "total_installments": plan["n_payments"],
                "remaining_installments": plan["deferred_payments"],
                "installment_amount": f(plan["installment_amount"])
            },
            "fees": {
                "service_fee": f(plan["service_fee"]),
                "delivery_fee": f(plan["delivery_fee"]),
                "merchant_fee_percentage": f(plan["merchant_fee_rate"] * 100),
                "merchant_fee_amount": f(plan["merchant_fee"]),
                "late_fee_percentage": late_fee_percentage
            },
            "totals": {
                "total_payable": f(plan["total_payable"]),
                "merchant_payout": f(plan["merchant_settlement"])
            },
            "payment_schedule": plan_engine.schedule_to_json(plan["schedule"]),
            # For customers: eligibility and available limit, so the Shop can warn before checkout
            "credit": credit
        }, 200

class LateFeeCalculatorResource(Resource):
    @auth_required
    def post(self):
        """Calculate late fee for overdue payment"""
        current_user_obj = current_user()
        
        data = request.get_json()
        overdue_amount = data.get('overdue_amount')
        late_fee_percentage = float(SystemSetting.get_value("late_fee_percentage", 10))
        
        if not overdue_amount:
            return {"error": "Overdue amount is required"}, 400
        
        late_fee = overdue_amount * (late_fee_percentage / 100)
        total_due = overdue_amount + late_fee
        
        return {
            "original_amount": overdue_amount,
            "late_fee_percentage": late_fee_percentage,
            "late_fee": late_fee,
            "total_due": total_due,
            "grace_period_days": int(SystemSetting.get_value("late_fee_grace_period_days", 3))
        }, 200