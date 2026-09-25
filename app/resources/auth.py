from flask import request
from flask_restful import Resource

from app.models.user import User
from ..services.auth_service import AuthError, RegistrationError, login_user, register_user


class RegisterResource(Resource):
    def post(self):
        data = request.get_json() or {}
        try:
            register_user(data)
        except RegistrationError as e:
            return {"error": e.message, "field": e.field, e.field: e.message}, e.status
        return {"message": "User registered successfully"}, 201


class LoginResource(Resource):
    def post(self):
        data = request.get_json() or {}
        try:
            token = login_user(data.get("phone"), data.get("password"))
        except AuthError as e:
            return {"error": e.message, "message": e.message}, e.status
        return {"access_token": token}, 200


class CheckUserExistsResource(Resource):
    def post(self):
        data = request.get_json() or {}
        business_email = (data.get('business_email') or '').strip().lower()
        phone = (data.get('phone') or '').strip()

        response = {
            'email_exists': False,
            'phone_exists': False
        }

        if business_email and User.query.filter_by(business_email=business_email).first():
            response['email_exists'] = True
            response['email_message'] = 'This email is already registered. Please login instead.'

        if phone and User.query.filter_by(phone=phone).first():
            response['phone_exists'] = True
            response['phone_message'] = 'This phone number is already registered. Please login instead.'

        return response
