"""Password guessing is limited per account (existing or not) and per IP, and the limit is checked first."""
from datetime import datetime, timedelta

from app.extensions import db
from app.models.login_attempt import LoginAttempt

from tests.test_ledger import app_ctx, make_user  # noqa: F401  (fixture)


def _login(client, phone, password, ip="10.0.0.1"):
    return client.post("/login", json={"phone": phone, "password": password},
                       headers={"X-Forwarded-For": ip})


def test_account_locks_after_five_failures_even_with_the_right_password(app_ctx):  # noqa: F811
    client = app_ctx.test_client()
    make_user("customer", "0200000301")
    for _ in range(5):
        assert _login(client, "0200000301", "wrong-pass").status_code == 401
    res = _login(client, "0200000301", "Secret123!")
    assert res.status_code == 429 and "Too many" in res.get_json()["error"]

    # Once the window has passed, the right password works and clears the count
    LoginAttempt.query.update({LoginAttempt.created_at: datetime.utcnow() - timedelta(minutes=16)})
    db.session.commit()
    assert _login(client, "0200000301", "Secret123!").status_code == 200
    assert _login(client, "0200000301", "wrong-pass").status_code == 401     # counting starts again


def test_unknown_accounts_look_the_same(app_ctx):  # noqa: F811
    client = app_ctx.test_client()
    for _ in range(5):
        res = _login(client, "0200009999", "whatever1")
        assert res.status_code == 401 and res.get_json()["error"] == "Invalid phone or password"
    assert _login(client, "0200009999", "whatever1").status_code == 429


def test_success_resets_the_count(app_ctx):  # noqa: F811
    client = app_ctx.test_client()
    make_user("customer", "0200000302")
    for _ in range(4):
        _login(client, "0200000302", "wrong-pass")
    assert _login(client, "0200000302", "Secret123!").status_code == 200
    for _ in range(4):
        assert _login(client, "0200000302", "wrong-pass").status_code == 401
    assert _login(client, "0200000302", "Secret123!").status_code == 200


def test_one_ip_trying_many_accounts_is_limited(app_ctx):  # noqa: F811
    client = app_ctx.test_client()
    app_ctx.config["LOGIN_MAX_FAILURES_PER_IP"] = 6
    make_user("customer", "0200000303")
    for i in range(6):
        _login(client, f"02000070{i:02d}", "guess-pass", ip="10.9.9.9")
    assert _login(client, "0200000303", "Secret123!", ip="10.9.9.9").status_code == 429
    assert _login(client, "0200000303", "Secret123!", ip="10.1.1.1").status_code == 200
