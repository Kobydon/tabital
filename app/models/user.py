from ..extensions import db
import sqlalchemy as sa

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    phone = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='customer')  # admin, merchant, customer
    status = db.Column(db.String(50), default='pending')  # pending, approved, rejected
    
    # Role-specific IDs (auto-generated on approval)
    customer_id = db.Column(db.String(50), unique=True, nullable=True, index=True)
    merchant_id = db.Column(db.String(50), unique=True, nullable=True, index=True)

    # CUSTOMER FIELDS
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
    ref_phone = db.Column(db.String(100))
    ref_relationship = db.Column(db.String(100))
    shop_url = db.Column(db.String(200))
    
    # MERCHANT FIELDS
    business_name = db.Column(db.String(100))
    owner_name = db.Column(db.String(100))
    product_type = db.Column(db.String(100))
    has_shop = db.Column(db.String(10))
    years_in_business = db.Column(db.String(50))

    offers_credit = db.Column(db.String(10))
    price_range = db.Column(db.String(50))
    
    # NEW MERCHANT FIELDS
    business_type = db.Column(db.String(50))
    registration_number = db.Column(db.String(100))
    tax_id = db.Column(db.String(100))
    business_address = db.Column(db.String(200))
    business_phone = db.Column(db.String(20))
    business_email = db.Column(db.String(100))
    website = db.Column(db.String(200))
    description = db.Column(db.Text)
    total_products = db.Column(db.Integer, default=0)
    total_sales = db.Column(db.Float, default=0)
    rating = db.Column(db.Float, default=0)
    verified = db.Column(db.Boolean, default=False)

    payment_method = db.Column(db.String(50))
    momo_name = db.Column(db.String(100))
    momo_number = db.Column(db.String(100))

    bank_name = db.Column(db.String(100))
    account_name = db.Column(db.String(100))
    account_number = db.Column(db.String(100))
    
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, onupdate=db.func.now())

    # ============================================
    # REQUIRED FLASK-PRAETORIAN METHODS
    # ============================================
    
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
        """Get the next customer ID number"""
        from sqlalchemy import func
        
        # Get the maximum customer_id number
        result = db.session.query(
            func.max(func.substr(User.customer_id, 2).cast(sa.Integer))
        ).filter(User.customer_id.isnot(None)).scalar()
        
        if result:
            return result + 1
        return 1
    
    @staticmethod
    def get_next_merchant_id():
        """Get the next merchant ID number"""
        from sqlalchemy import func
        
        # Get the maximum merchant_id number
        result = db.session.query(
            func.max(func.substr(User.merchant_id, 2).cast(sa.Integer))
        ).filter(User.merchant_id.isnot(None)).scalar()
        
        if result:
            return result + 1
        return 1
    
    def generate_customer_id(self):
        """Generate a customer ID in format C001, C002, etc."""
        next_num = User.get_next_customer_id()
        return f"C{next_num:03d}"
    
    def generate_merchant_id(self):
        """Generate a merchant ID in format M001, M002, etc."""
        next_num = User.get_next_merchant_id()
        return f"M{next_num:03d}"