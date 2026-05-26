import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "supersecret")
    # SQLALCHEMY_DATABASE_URI = "sqlite:///app.db"
    SQLALCHEMY_DATABASE_URI = "postgresql://tabital_1170_user:qXPlHdfEAzWBqSC5Gu93NAkIX8i8R59N@dpg-d8aki10jo6nc73eqap4g-a.oregon-postgres.render.com/tabital_1170"
    # postgresql://tabital_user:fpH2JZk5dGWYRaGop6Uy44QFJqqBCyew@dpg-d7t11rjbc2fs73d814q0-a.oregon-postgres.render.com/tabital
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Mail Settings for Password Reset
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "True") == "True"
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "False") == "True"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "jxkalmhefacbuk@gmail.com")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "qhsf mguh pzuh dcmx")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", "jxkalmhefacbuk@gmail.com")