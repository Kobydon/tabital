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
        
        # if current_admin.role != 'admin':
        #     return {"error": "Unauthorized"}, 403
        
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
        """Update system settings"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        data = request.get_json()
        
        # Update each setting
        for key, value in data.items():
            if key == 'installment_options':
                setting_type = 'json'
                setting_value = json.dumps(value)
            elif isinstance(value, bool):
                setting_type = 'boolean'
                setting_value = str(value)
            elif isinstance(value, (int, float)):
                setting_type = 'number'
                setting_value = str(value)
            else:
                setting_type = 'string'
                setting_value = str(value)
            
            SystemSetting.set_value(
                key=key,
                value=setting_value,
                value_type=setting_type,
                updated_by=current_admin.id
            )
        
        return {"message": "Settings updated successfully"}, 200


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
        """Update installment options"""
        current_admin = current_user()
        
        if current_admin.role != 'admin':
            return {"error": "Unauthorized"}, 403
        
        data = request.get_json()
        options = data.get('installment_options', [])
        
        SystemSetting.set_value(
            key="installment_options",
            value=json.dumps(options),
            value_type="json",
            description="Available installment plan options",
            updated_by=current_admin.id
        )
        
        return {"message": "Installment options updated successfully"}, 200
from flask import request
from flask_restful import Resource
from flask_praetorian import auth_required, current_user
from datetime import datetime, timedelta


class InstallmentCalculatorResource(Resource):

    @auth_required
    def post(self):
        """Calculate installment plan"""

        current_user_obj = current_user()

        data = request.get_json() or {}

        product_price = float(data.get('product_price', 0))
        quantity = int(data.get('quantity', 1))
        number_of_installments = int(data.get('number_of_installments', 1))

        if product_price <= 0:
            return {"error": "Valid product price is required"}, 400

        # Product total
        total_price = product_price * quantity

        # System settings
        merchant_fee_percentage = float(
            SystemSetting.get_value("merchant_fee_percentage", 10)
        )

        late_fee_percentage = float(
            SystemSetting.get_value("late_fee_percentage", 10)
        )

        service_fee = float(
            SystemSetting.get_value("service_fee", 0)
        )

        delivery_fee = 50.0

        # ==========================================
        # DOWN PAYMENT RULES
        # ==========================================

        if number_of_installments == 1:
            down_payment_percentage = 100

        elif number_of_installments in [2, 3]:
            down_payment_percentage = 50

        elif number_of_installments == 4:
            down_payment_percentage = 40

        else:
            return {
                "error": "Only 1, 2, 3 and 4 installment plans are supported"
            }, 400

        # ==========================================
        # CALCULATIONS
        # ==========================================

        product_down_payment = (
            total_price * down_payment_percentage / 100
        )

        due_now_amount = (
            product_down_payment + delivery_fee
        )

        remaining_balance = (
            total_price - product_down_payment
        )

        remaining_installments = max(
            number_of_installments - 1,
            0
        )

        installment_amount = (
            remaining_balance / remaining_installments
            if remaining_installments > 0
            else 0
        )

        merchant_fee_amount = (
            total_price * merchant_fee_percentage / 100
        )

        merchant_payout = (
            total_price - merchant_fee_amount
        )

        total_payable = (
            total_price + delivery_fee + service_fee
        )

        # ==========================================
        # PAYMENT SCHEDULE
        # ==========================================

        payment_schedule = []

        current_date = datetime.now()

        # First payment
        payment_schedule.append({
            "installment_number": 1,
            "amount": round(due_now_amount, 2),
            "due_date": current_date.strftime("%Y-%m-%d"),
            "status": "due_now",
            "description": f"{down_payment_percentage}% Down Payment + Delivery Fee"
        })

        # Remaining payments
        for i in range(1, remaining_installments + 1):

            due_date = current_date + timedelta(days=(30 * i))

            if number_of_installments == 2:
                description = "Final Payment (Remaining 50%)"

            elif number_of_installments == 3:
                description = f"Payment {i + 1} of 3 (25%)"

            elif number_of_installments == 4:
                description = f"Payment {i + 1} of 4 (20%)"

            else:
                description = f"Installment {i + 1}"

            payment_schedule.append({
                "installment_number": i + 1,
                "amount": round(installment_amount, 2),
                "due_date": due_date.strftime("%Y-%m-%d"),
                "status": "pending",
                "description": description
            })

        return {
            "product_price": round(total_price, 2),

            "down_payment": {
                "percentage": down_payment_percentage,
                "amount": round(due_now_amount, 2)
            },

            "remaining_balance": round(
                remaining_balance,
                2
            ),

            "installment_details": {
                "total_installments": number_of_installments,
                "remaining_installments": remaining_installments,
                "installment_amount": round(
                    installment_amount,
                    2
                )
            },

            "fees": {
                "service_fee": service_fee,
                "delivery_fee": delivery_fee,
                "merchant_fee_percentage": merchant_fee_percentage,
                "merchant_fee_amount": round(
                    merchant_fee_amount,
                    2
                ),
                "late_fee_percentage": late_fee_percentage
            },

            "totals": {
                "total_payable": round(
                    total_payable,
                    2
                ),
                "merchant_payout": round(
                    merchant_payout,
                    2
                )
            },

            "payment_schedule": payment_schedule

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