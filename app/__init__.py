from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate

from .config import Config
from .extensions import db, ma, guard, mail
from .models.user import User
from .models import ledger as _ledger_model  # noqa: F401  (registers the ledger table)
from .models import payment_intent as _payment_intent_model  # noqa: F401
from .models import risk_assessment as _risk_assessment_model  # noqa: F401
from .models import message_outbox as _message_outbox_model  # noqa: F401
from .models import payment_method as _payment_method_model  # noqa: F401
from .models import settlement as _settlement_model  # noqa: F401
from .models import identity as _identity_model  # noqa: F401
from .models import deferment as _deferment_model  # noqa: F401
from .models import pii_access as _pii_access_model  # noqa: F401
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
        allow_headers=["Content-Type", "Authorization", "X-Requested-With", "X-Device-Id", "X-Device-Flags"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    )

    db.init_app(app)
    ma.init_app(app)
    mail.init_app(app)
    guard.init_app(app, User)
    Migrate(app, db)

    register_routes(app)
    register_commands(app)
    register_pii_masking(app)
    register_access_control(app)

    return app


def register_pii_masking(app):
    """Admin screens get masked personal data by default (services/pii.py).

    Applies to JSON responses under /admin/. The audited reveal endpoint (/admin/pii/…) is the
    only way to see a full value.
    """
    import json
    from flask import request
    from .services import pii

    @app.after_request
    def _mask_admin_pii(response):
        path = request.path or ""
        if not path.startswith("/admin/") or path.startswith("/admin/pii/"):
            return response
        if response.status_code >= 400 or not response.is_json or response.direct_passthrough:
            return response
        data = response.get_json(silent=True)
        if data is None:
            return response
        response.set_data(json.dumps(pii.mask_payload(data)))
        return response


def register_access_control(app):
    """Management Access (services/access.py): checked once for every request an admin makes."""
    from flask import request
    from .services import access

    @app.before_request
    def _management_access():
        if request.method == "OPTIONS" or "Authorization" not in request.headers:
            return None
        try:
            data = guard.extract_jwt_token(guard.read_token_from_header())
            user = User.query.get(data.get("id"))
        except Exception:        # bad or expired token: the endpoint's own auth check answers
            return None
        if not user or user.role != "admin" or access.is_management(user):
            return None
        if access.needs_management(request.method, request.path):
            return {"error": access.MESSAGE, "code": "management_required"}, 403
        return None


def register_commands(app):
    import click

    @app.cli.command("create-admin")
    @click.option("--phone", required=True, help="Admin login phone number")
    @click.option("--name", default="Tabital Admin")
    @click.option("--management", is_flag=True, help="Give Management Access (approvals, rates, reveals)")
    @click.password_option()
    def create_admin(phone, name, management, password):
        """Create an admin account. Admins can't be created through the public API.

        New admins get operations (read-only) access unless --management is given.
        """
        from .services import access
        if User.query.filter_by(phone=phone).first():
            raise click.ClickException("A user with that phone number already exists")
        level = access.MANAGEMENT if management else access.OPERATIONS
        admin = User(phone=phone, full_name=name, role="admin", status="approved", admin_level=level,
                     password=guard.hash_password(password))
        db.session.add(admin)
        db.session.commit()
        click.echo(f"Admin {phone} created with {level} access")

    @app.cli.command("set-admin-access")
    @click.option("--phone", required=True)
    @click.option("--level", required=True, type=click.Choice(["management", "operations"]))
    def set_admin_access(phone, level):
        """Change an admin's access from the server (e.g. to set up the first manager)."""
        admin = User.query.filter_by(phone=phone, role="admin").first()
        if not admin:
            raise click.ClickException("No admin with that phone number")
        admin.admin_level = level
        db.session.commit()
        click.echo(f"{phone} now has {level} access")

    @app.cli.command("run-daily")
    @click.option("--date", "run_date", default=None, help="Service as of this date (YYYY-MM-DD); default today")
    @click.option("--no-reminders", is_flag=True)
    @click.option("--no-autopay", is_flag=True)
    def run_daily_command(run_date, no_reminders, no_autopay):
        """Daily servicing: late fees, DPD buckets, collections stages, reminders, autopay.

        Schedule once a day, e.g. a Render cron job at 06:00 Africa/Accra (06:00 UTC).
        """
        from datetime import datetime as _dt
        from .services import servicing
        day = _dt.strptime(run_date, "%Y-%m-%d").date() if run_date else None
        summary = servicing.run_daily(day, send_reminders=not no_reminders, run_autopay=not no_autopay)
        for key, value in summary.to_dict().items():
            click.echo(f"{key}: {value}")

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
