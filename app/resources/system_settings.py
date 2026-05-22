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


class InstallmentCalculatorResource(Resource):
    @auth_required
    def post(self):
        """Calculate installment plan for a product using current system settings"""
        current_user_obj = current_user()
        
        data = request.get_json()
        product_price = data.get('product_price')
        number_of_installments = data.get('number_of_installments')
        
        if not product_price:
            return {"error": "Product price is required"}, 400
        
        # Get current system settings
        down_payment_percentage = float(SystemSetting.get_value("down_payment_percentage", 40))
        merchant_fee_percentage = float(SystemSetting.get_value("merchant_fee_percentage", 10))
        late_fee_percentage = float(SystemSetting.get_value("late_fee_percentage", 10))
        service_fee = float(SystemSetting.get_value("service_fee", 0))
        
        if not number_of_installments:
            number_of_installments = int(SystemSetting.get_value("default_installments", 4))
        
        min_installments = int(SystemSetting.get_value("min_installments", 2))
        max_installments = int(SystemSetting.get_value("max_installments", 24))
        
        if number_of_installments < min_installments or number_of_installments > max_installments:
            return {"error": f"Installments must be between {min_installments} and {max_installments}"}, 400
        
        # Calculate using Tabital formula
        down_payment_amount = product_price * (down_payment_percentage / 100)
        remaining_balance = product_price - down_payment_amount + service_fee
        remaining_installments = number_of_installments - 1
        installment_amount = remaining_balance / remaining_installments if remaining_installments > 0 else remaining_balance
        
        merchant_fee_amount = product_price * (merchant_fee_percentage / 100)
        merchant_payout = product_price - merchant_fee_amount
        total_payable = product_price + service_fee
        
        # Generate payment schedule
        from datetime import datetime, timedelta
        payment_schedule = []
        current_date = datetime.now()
        
        # Down payment
        payment_schedule.append({
            "installment_number": 1,
            "amount": down_payment_amount,
            "due_date": current_date.strftime("%Y-%m-%d"),
            "status": "due_now",
            "description": "Down Payment (40% upfront)"
        })
        
        # Remaining installments
        for i in range(1, remaining_installments + 1):
            due_date = current_date + timedelta(days=30 * i)
            payment_schedule.append({
                "installment_number": i + 1,
                "amount": installment_amount,
                "due_date": due_date.strftime("%Y-%m-%d"),
                "status": "pending",
                "description": f"Installment {i + 1} of {number_of_installments}"
            })
        
        return {
            "product_price": product_price,
            "down_payment": {
                "percentage": down_payment_percentage,
                "amount": down_payment_amount
            },
            "remaining_balance": remaining_balance,
            "installment_details": {
                "total_installments": number_of_installments,
                "remaining_installments": remaining_installments,
                "installment_amount": installment_amount
            },
            "fees": {
                "service_fee": service_fee,
                "merchant_fee_percentage": merchant_fee_percentage,
                "merchant_fee_amount": merchant_fee_amount,
                "late_fee_percentage": late_fee_percentage
            },
            "totals": {
                "total_payable": total_payable,
                "merchant_payout": merchant_payout
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