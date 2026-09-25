# Lets pytest import the `app` package from the repository root, and points the app
# at a throwaway SQLite database before app.config is imported.
import os
import tempfile

_TEST_DB = os.path.join(tempfile.gettempdir(), "tabital_test.db")
os.environ["DATABASE_URL"] = "sqlite:///" + _TEST_DB.replace("\\", "/")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ["FLASK_DEBUG"] = "0"
