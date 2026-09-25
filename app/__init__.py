from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate

from .config import Config
from .extensions import db, ma, guard, mail
from .models.user import User
from .models import ledger as _ledger_model  # noqa: F401  (registers the ledger table)
from .models import payment_intent as _payment_intent_model  # noqa: F401
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

    @app.cli.command("ledger-backfill")
    @click.option("--dry-run", is_flag=True, help="Report what would be written without saving")
    def ledger_backfill(dry_run):
        """Create ledger entries for plans made before the ledger existed.

        Uses the recorded plan and payment rows: contract total, paid instalments and
        late fees. Plans that already have ledger entries are skipped.
        """
        from decimal import Decimal
        from .models.instalment import InstalmentPlan
        from .models.instalment_payment import InstalmentPayment
        from .services import ledger

        created = 0
        for plan in InstalmentPlan.query.order_by(InstalmentPlan.id).all():
            if ledger.has_entries(plan):
                continue
            ledger.record(plan, "plan_opened", plan.total_amount, note="Backfill: contract total payable")
            payments = InstalmentPayment.query.filter_by(plan_id=plan.id).all()
            for p in payments:
                if p.late_fee and (p.late_fee_paid or p.status != 'paid'):
                    ledger.late_fee_charged(plan, p, p.late_fee)
                if p.status == 'paid':
                    paid = p.paid_amount or (Decimal(str(p.amount)) + Decimal(str(p.late_fee or 0)))
                    ledger.payment_received(plan, p, paid, p.payment_reference or "backfill")
            created += 1
        if dry_run:
            db.session.rollback()
            click.echo(f"Dry run: would backfill {created} plan(s)")
        else:
            db.session.commit()
            click.echo(f"Backfilled {created} plan(s)")
