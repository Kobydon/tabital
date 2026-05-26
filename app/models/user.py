from ..extensions import db
import sqlalchemy as sa
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='customer')
    status = db.Column(db.String(50), default='pending')
    swift_code=db.Column(db.String(50),unique=True)
    # Role-specific IDs
    customer_id = db.Column(db.String(50), unique=True, nullable=True, index=True)
    merchant_id = db.Column(db.String(50), unique=True, nullable=True, index=True)

    # Customer Fields
    full_name = db.Column(db.String(100))
    dob = db.Column(db.String(50))
    national_id = db.Column(db.String(100))
    city = db.Column(db.String(100))
    gps = db.Column(db.String(200))
    agree = db.Column(db.Boolean, default=False)
    designation = db.Column(db.String(200))
    company = db.Column(db.String(200))
    address = db.Column(db.String(200))
    income_range = db.Column(db.String(100))
    product_name = db.Column(db.String(200))
    total_price = db.Column(db.Float)
    payment_plan = db.Column(db.String(50))
    payment_frequency = db.Column(db.String(50))
    ref_name = db.Column(db.String(100))
    ref_phone = db.Column(db.String(100),unique=True)
    ref_relationship = db.Column(db.String(100))
    shop_url = db.Column(db.String(200))
    
    # Merchant Fields
    business_name = db.Column(db.String(100))
    owner_name = db.Column(db.String(100))
    product_type = db.Column(db.String(100))
    has_shop = db.Column(db.String(10))
    years_in_business = db.Column(db.String(50))
    offers_credit = db.Column(db.String(10))
    price_range = db.Column(db.String(50))
    business_type = db.Column(db.String(50))
    registration_number = db.Column(db.String(100))
    tax_id = db.Column(db.String(100))
    business_address = db.Column(db.String(200))
    business_phone = db.Column(db.String(20),unique=True)
    business_email = db.Column(db.String(100),unique=True)
    email=db.Column(db.String(100),unique=True)
    website = db.Column(db.String(200),unique=True)
    description = db.Column(db.Text)
    total_products = db.Column(db.Integer, default=0)
    total_sales = db.Column(db.Float, default=0)
    rating = db.Column(db.Float, default=0)
    verified = db.Column(db.Boolean, default=False)
    payment_method = db.Column(db.String(50))
    momo_name = db.Column(db.String(100))
    momo_number = db.Column(db.String(100),unique=True)
    bank_name = db.Column(db.String(100))
    account_name = db.Column(db.String(100))
    account_number = db.Column(db.String(100),unique=True)
    
    # KYC Fields
    kyc_status = db.Column(db.String(50), default='pending')
    verification_level = db.Column(db.String(50), default='standard')
    aml_screening = db.Column(db.String(50), default='pending')
    kyc_completed_on = db.Column(db.DateTime)
    
    # Settlement Fields
    commission_rate = db.Column(db.Float, default=2.5)
    pending_payout = db.Column(db.Float, default=0)
    next_settlement = db.Column(db.String(50))
    
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, onupdate=db.func.now())

    # Flask-Praetorian Methods
    @property
    def identity(self):
        return str(self.id)
    
    @property
    def rolenames(self):
        return [self.role] if self.role else ['customer']
    
    @classmethod
    def lookup(cls, identity):
        return cls.query.filter(cls.phone == identity).first()
    
    @classmethod
    def identify(cls, id):
        return cls.query.get(id)
    
    def is_valid(self):
        return self.status == 'approved'
    
    @staticmethod
    def get_next_customer_id():
        from sqlalchemy import func
        result = db.session.query(
            func.max(func.substr(User.customer_id, 2).cast(sa.Integer))
        ).filter(User.customer_id.isnot(None)).scalar()
        return (result + 1) if result else 1
    
    @staticmethod
    def get_next_merchant_id():
        from sqlalchemy import func
        result = db.session.query(
            func.max(func.substr(User.merchant_id, 2).cast(sa.Integer))
        ).filter(User.merchant_id.isnot(None)).scalar()
        return (result + 1) if result else 1
    
    def generate_customer_id(self):
        return f"C{User.get_next_customer_id():03d}"
    
    def generate_merchant_id(self):
        return f"M{User.get_next_merchant_id():03d}"