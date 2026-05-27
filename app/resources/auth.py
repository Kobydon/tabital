from flask_restful import Resource
from flask import request
from ..services.auth_service import register_user, login_user
from flask import request
from app.models.user import User # 
class RegisterResource(Resource):
    def post(self):
        data = request.json
        register_user(data)
        return {"message": "User registered successfully"}


class LoginResource(Resource):
    def post(self):
        data = request.json

        token = login_user(
            data.get("phone"),
            data.get("password")
        )

        return {"access_token": token}  # FIXED: changed 'toke' to 'token'


class CheckUserExistsResource(Resource):
    def post(self):
        data = request.json
        business_email = data.get('business_email')
        phone = data.get('phone')
        
        response = {
            'email_exists': False,
            'phone_exists': False
        }
        
        if business_email:
            user = User.query.filter_by(business_email=business_email).first()
            if user:
                response['email_exists'] = True
                response['email_message'] = f'Email {business_email} is already registered. Please login instead.'
        
        if phone:
            user = User.query.filter_by(phone=phone).first()
            if user:
                response['phone_exists'] = True
                response['phone_message'] = f'Phone number {phone} is already registered. Please login instead.'
        
        return response