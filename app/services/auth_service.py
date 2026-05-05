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


def login_user(phone, password):
    user = guard.authenticate(phone, password)

    # 🚫 BLOCK UNAPPROVED USERS
    if user.status != "approved":
        raise Exception("Account not approved yet")

    token = guard.encode_jwt_token(user)
    return token