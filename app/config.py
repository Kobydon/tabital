import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "supersecret")
    SQLALCHEMY_DATABASE_URI = "postgresql://tabital_user:fpH2JZk5dGWYRaGop6Uy44QFJqqBCyew@dpg-d7t11rjbc2fs73d814q0-a.oregon-postgres.render.com/tabital"
    # sqlite:///app.db
    # SQLALCHEMY_DATABASE_URI = "postgresql://tabital_user:fpH2JZk5dGWYRaGop6Uy44QFJqqBCyew@dpg-d7t11rjbc2fs73d814q0-a.oregon-postgres.render.com/tabital"
    # 
    SQLALCHEMY_TRACK_MODIFICATIONS = False
