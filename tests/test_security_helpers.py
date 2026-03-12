import sys
import types
import importlib
from pathlib import Path

from flask import Flask, session

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _install_import_stubs():
    if "MySQLdb" not in sys.modules:
        mysqldb_module = types.ModuleType("MySQLdb")
        cursors_module = types.ModuleType("MySQLdb.cursors")
        mysqldb_module.cursors = cursors_module
        sys.modules["MySQLdb"] = mysqldb_module
        sys.modules["MySQLdb.cursors"] = cursors_module

    if "flask_mysqldb" not in sys.modules:
        flask_mysqldb_module = types.ModuleType("flask_mysqldb")

        class DummyMySQL:
            def __init__(self, *args, **kwargs):
                self.args = args
                self.kwargs = kwargs

        flask_mysqldb_module.MySQL = DummyMySQL
        sys.modules["flask_mysqldb"] = flask_mysqldb_module


_install_import_stubs()
main = importlib.import_module("main")


def _create_app():
    app = Flask(__name__)
    app.secret_key = "test-secret"
    return app


def test_login_rate_limit_keys_normalize_username_and_ip():
    account_key, ip_key = main._login_rate_limit_keys("127.0.0.1", "  MiXeDUser ")
    assert account_key == "login:account:mixeduser"
    assert ip_key == "login:ip:127.0.0.1"


def test_is_authenticated_depends_on_loggedin_session_flag():
    app = _create_app()
    with app.test_request_context("/"):
        assert main._is_authenticated() is False
        session["loggedin"] = True
        assert main._is_authenticated() is True


def test_is_valid_csrf_requires_matching_header_and_session_token():
    app = _create_app()
    with app.test_request_context("/", headers={"X-CSRF-Token": "abc"}):
        session["csrf_token"] = "abc"
        assert main._is_valid_csrf() is True

    with app.test_request_context("/", headers={"X-CSRF-Token": "wrong"}):
        session["csrf_token"] = "abc"
        assert main._is_valid_csrf() is False
