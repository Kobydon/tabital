from flask_restful import Resource
from flask import request
from ..services.auth_service import register_user, login_user

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