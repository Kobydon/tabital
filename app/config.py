import os

from dotenv import load_dotenv

load_dotenv()


def _database_url():
    url = os.getenv("DATABASE_URL", "sqlite:///app.db")
    # Render/Heroku style URLs use the legacy "postgres://" scheme, which SQLAlchemy rejects
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def _csv(name, default=""):
    return [v.strip() for v in os.getenv(name, default).split(",") if v.strip()]


class Config:
    # All secrets come from the environment. Never commit real values; see .env.example
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = _database_url()
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"

    # Origins allowed to call the API from a browser
    CORS_ORIGINS = _csv("CORS_ORIGINS", "http://localhost:4200,https://app.tabitalpay.com")

    # Token lifetimes for flask_praetorian
    JWT_ACCESS_LIFESPAN = {"minutes": int(os.getenv("JWT_ACCESS_MINUTES", "60"))}
    JWT_REFRESH_LIFESPAN = {"days": int(os.getenv("JWT_REFRESH_DAYS", "7"))}

    # Mail settings for password reset
    MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "True") == "True"
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "False") == "True"
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER", os.getenv("MAIL_USERNAME"))
