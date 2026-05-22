# run.py
from app import create_app
from app.extensions import db
from app.models.user import User
from app.models.transaction import Transaction
from app.models.instalment import InstalmentPlan
from app.models.instalment_payment import InstalmentPayment
from app.models.dispute import Dispute
from app.models.document import Document
from app.models.notification_settings import NotificationSetting
from app.models.system_settings import SystemSetting, TransactionCharge
from app.models.support_ticket import SupportTicket, TicketMessage

app = create_app()

def init_system_settings():
    """Initialize default system settings if they don't exist"""
    from app.models.system_settings import SystemSetting
    
    default_settings = {
        "down_payment_percentage": {
            "value": 40,
            "type": "number",
            "description": "Percentage of product price paid upfront"
        },
        "merchant_fee_percentage": {
            "value": 10,
            "type": "number",
            "description": "Fee percentage deducted from merchant payout"
        },
        "late_fee_percentage": {
            "value": 10,
            "type": "number",
            "description": "Penalty percentage for overdue payments"
        },
        "service_fee": {
            "value": 0,
            "type": "number",
            "description": "Additional service fee charged to customer"
        },
        "min_installments": {
            "value": 2,
            "type": "number",
            "description": "Minimum number of installments allowed"
        },
        "max_installments": {
            "value": 24,
            "type": "number",
            "description": "Maximum number of installments allowed"
        },
        "default_installments": {
            "value": 4,
            "type": "number",
            "description": "Default number of installments"
        },
        "late_fee_grace_period_days": {
            "value": 3,
            "type": "number",
            "description": "Days after due date before late fee applies"
        },
        "installment_options": {
            "value": [
                {"months": 2, "label": "2 Months", "interest_rate": 3, "is_active": True},
                {"months": 3, "label": "3 Months", "interest_rate": 5, "is_active": True},
                {"months": 4, "label": "4 Months", "interest_rate": 7, "is_active": True},
                {"months": 6, "label": "6 Months", "interest_rate": 10, "is_active": True},
                {"months": 9, "label": "9 Months", "interest_rate": 13, "is_active": True},
                {"months": 12, "label": "12 Months", "interest_rate": 16, "is_active": True},
                {"months": 18, "label": "18 Months", "interest_rate": 22, "is_active": True},
                {"months": 24, "label": "24 Months", "interest_rate": 28, "is_active": True}
            ],
            "type": "json",
            "description": "Available installment plan options"
        }
    }
    
    admin_user = User.query.filter_by(role='admin').first()
    admin_id = admin_user.id if admin_user else None
    
    for key, setting_data in default_settings.items():
        existing = SystemSetting.query.filter_by(setting_key=key).first()
        if not existing:
            SystemSetting.set_value(
                key=key,
                value=setting_data["value"] if setting_data["type"] != "json" else __import__('json').dumps(setting_data["value"]),
                value_type=setting_data["type"],
                description=setting_data["description"],
                updated_by=admin_id
            )
            print(f"✅ Created setting: {key} = {setting_data['value']}")
        else:
            print(f"⚠️ Setting already exists: {key}")

if __name__ == "__main__":
    with app.app_context():
        # Create all tables
        db.create_all()
        print("✅ Database tables created successfully")
        
        # Initialize system settings
        init_system_settings()
        print("✅ System settings initialized")
        
    print("🚀 Starting Tabital Pay Server...")
    app.run(debug=True, host='0.0.0.0', port=5000)