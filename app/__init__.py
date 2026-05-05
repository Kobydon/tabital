# app.py or __init__.py
from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from .extensions import db, ma, guard
from .config import Config
from .routes import register_routes
from .models.user import User

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # ✅ Configure CORS properly
    CORS(app, 
         resources={r"/*": {
             "origins": ["http://localhost:4200", "http://127.0.0.1:4200"],
             "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
             "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
             "expose_headers": ["Content-Type", "Authorization"],
             "supports_credentials": True,
             "max_age": 3600
         }})

    db.init_app(app)
    ma.init_app(app)
    guard.init_app(app, User)
    
    # ✅ Initialize Flask-Migrate
    migrate = Migrate(app, db)

    register_routes(app)

    return app