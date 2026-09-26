# Lets pytest import the `app` package from the repository root, and points the app
# at a throwaway SQLite database before app.config is imported.
import os
import tempfile

# One file per test run, so two runs at the same time (e.g. a reviewer and a developer) don't share it
_TEST_DB = os.path.join(tempfile.gettempdir(), f"tabital_test_{os.getpid()}.db")
os.environ["DATABASE_URL"] = "sqlite:///" + _TEST_DB.replace("\\", "/")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ["FLASK_DEBUG"] = "0"


def pytest_sessionfinish(session, exitstatus):
    try:
        os.remove(_TEST_DB)
    except OSError:
        pass
