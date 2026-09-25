from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate

from .config import Config
from .extensions import db, ma, guard, mail
from .models.user import User
from .routes import register_routes


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    if not app.config.get("SECRET_KEY"):
        if app.config.get("DEBUG"):
            import secrets
            app.config["SECRET_KEY"] = secrets.token_urlsafe(64)
            app.logger.warning("SECRET_KEY not set; using a random key for this debug session only")
        else:
            raise RuntimeError("SECRET_KEY environment variable must be set")

    CORS(
        app,
        resources={r"/*": {"origins": app.config["CORS_ORIGINS"]}},
        allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    )

    db.init_app(app)
    ma.init_app(app)
    mail.init_app(app)
    guard.init_app(app, User)
    Migrate(app, db)

    register_routes(app)
    register_commands(app)

    return app


def register_commands(app):
    import click

    @app.cli.command("create-admin")
    @click.option("--phone", required=True, help="Admin login phone number")
    @click.option("--name", default="Tabital Admin")
    @click.password_option()
    def create_admin(phone, name, password):
        """Create an admin account. Admins can't be created through the public API."""
        if User.query.filter_by(phone=phone).first():
            raise click.ClickException("A user with that phone number already exists")
        admin = User(phone=phone, full_name=name, role="admin", status="approved",
                     password=guard.hash_password(password))
        db.session.add(admin)
        db.session.commit()
        click.echo(f"Admin {phone} created")
