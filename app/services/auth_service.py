from ..models.user import User
from ..extensions import db, guard

def register_user(data):
    user = User(**data)

    user.password = guard.hash_password(data.get("password"))

    # 👇 IMPORTANT LOGIC
    if user.role == "admin":
        user.status = "approved"
    else:
        user.status = "pending"

    db.session.add(user)
    db.session.commit()

    return user
# ============================================
# auth.py - ALTERNATIVE APPROACH
# ============================================

def login_user(identifier, password):
    """
    Login using either phone number OR business_email with password
    Blocks users who are not approved
    """
    # Try to find user by phone OR business_email
    user = None
    
    # Try by phone
    user = User.query.filter(User.phone == identifier).first()
    
    # If not found by phone, try by business_email
    if not user:
        user = User.query.filter(User.business_email == identifier).first()
    
    # If still not found, try by email
    if not user:
        user = User.query.filter(User.email == identifier).first()
    
    if not user:
        raise Exception("Invalid phone number/email or password")

    
    # Alternative: Use guard.authenticate with the found user
    # or implement password check manually
    from werkzeug.security import check_password_hash
    
    if not check_password_hash(user.password, password):
        raise Exception("Invalid phone number/email or password")
    
    # 🚫 BLOCK UNAPPROVED USERS
    if user.status != "approved":
        raise Exception("Account not approved yet. Please wait for admin approval.")
    
    # Generate and return token
    from flask_praetorian import Praetorian
    guard = Praetorian()
    token = guard.encode_jwt_token(user)
    return token