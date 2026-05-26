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
from sqlalchemy import or_

def login_user(identifier, password):
    """
    Login with phone OR business_email
    """

    # FIND USER BY PHONE OR BUSINESS EMAIL
    user = User.query.filter(
        or_(
            User.phone == identifier,
            User.business_email == identifier
        )
    ).first()

    # USER NOT FOUND
    if not user:
        raise Exception("Invalid phone/email or password")

    # VERIFY PASSWORD
    if not guard.pwd_ctx.verify(password, user.password):
        raise Exception("Invalid phone/email or password")

    # CHECK APPROVAL
    if user.status != "approved":
        raise Exception(
            "Account not approved yet. Please wait for admin approval."
        )

    # GENERATE TOKEN
    token = guard.encode_jwt_token(user)

    return token