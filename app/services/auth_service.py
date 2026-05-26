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

def login_user(identifier, password):
    """
    Login using either phone number OR business_email with password
    Blocks users who are not approved
    
    Args:
        identifier: Can be phone number OR business_email
        password: User's password
    
    Returns:
        JWT token if authentication successful
    """
    # Try to authenticate using guard with identifier (handles both phone and email)
    user = guard.authenticate(identifier, password)
    
    if not user:
        raise Exception("Invalid phone number/email or password")
    
    # 🚫 BLOCK UNAPPROVED USERS
    if user.status != "approved":
        raise Exception("Account not approved yet. Please wait for admin approval.")
    
    # Generate and return token for approved users only
    token = guard.encode_jwt_token(user)
    return token