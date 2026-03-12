import re
import os
import secrets

# Load .env from project root before any config reads os.environ.
try:
    from pathlib import Path
    from dotenv import load_dotenv
    _env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(_env_path)
except ImportError:
    pass

try:
    import redis
except ImportError:
    redis = None

import MySQLdb.cursors
from flask import Flask, jsonify, request, redirect, url_for, session
from flask_mysqldb import MySQL
from flask_restful import Resource, Api, reqparse
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash


# Defining globals
global app
global api
global mysql
global redis_client

redis_client = None
LOGIN_ATTEMPT_WINDOW_SECONDS = int(os.environ.get('LOGIN_ATTEMPT_WINDOW_SECONDS', '60'))
LOGIN_MAX_ATTEMPTS_PER_ACCOUNT = int(os.environ.get('LOGIN_MAX_ATTEMPTS_PER_ACCOUNT', '5'))
LOGIN_MAX_ATTEMPTS_PER_IP = int(os.environ.get('LOGIN_MAX_ATTEMPTS_PER_IP', '25'))


def _is_authenticated():
    return bool(session.get('loggedin'))


def _is_valid_csrf():
    csrf_header = request.headers.get('X-CSRF-Token')
    csrf_session = session.get('csrf_token')
    return bool(csrf_header and csrf_session and secrets.compare_digest(csrf_header, csrf_session))


def _get_redis_client():
    global redis_client
    if redis is None:
        raise RuntimeError('redis package is required for login rate limiting')
    if redis_client is None:
        redis_url = os.environ.get('REDIS_URL')
        if not redis_url:
            raise RuntimeError('REDIS_URL environment variable is required for login rate limiting')
        redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
        redis_client.ping()
    return redis_client


def _login_rate_limit_keys(remote_addr, username):
    normalized_username = username.strip().lower()
    ip_key = remote_addr or 'unknown'
    account_rate_limit_key = f'login:account:{normalized_username}'
    ip_rate_limit_key = f'login:ip:{ip_key}'
    return account_rate_limit_key, ip_rate_limit_key


def _get_attempt_count(key):
    value = _get_redis_client().get(key)
    if value is None:
        return 0
    return int(value)


def _check_login_rate_limit(remote_addr, username):
    account_key, ip_key = _login_rate_limit_keys(remote_addr, username)
    account_attempts = _get_attempt_count(account_key)
    ip_attempts = _get_attempt_count(ip_key)
    return (
        account_attempts < LOGIN_MAX_ATTEMPTS_PER_ACCOUNT
        and ip_attempts < LOGIN_MAX_ATTEMPTS_PER_IP
    )


def _record_login_failure(remote_addr, username):
    account_key, ip_key = _login_rate_limit_keys(remote_addr, username)
    pipeline = _get_redis_client().pipeline()
    pipeline.incr(account_key)
    pipeline.expire(account_key, LOGIN_ATTEMPT_WINDOW_SECONDS)
    pipeline.incr(ip_key)
    pipeline.expire(ip_key, LOGIN_ATTEMPT_WINDOW_SECONDS)
    pipeline.execute()


def _clear_login_failures(remote_addr, username):
    account_key, _ = _login_rate_limit_keys(remote_addr, username)
    _get_redis_client().delete(account_key)


# returns hello world when we use GET.
# returns the data that we send when we use POST.
class Hello(Resource):

    def get(self):
        return jsonify({'message': 'Hello'})

    def post(self):
        data = request.get_json()
        return jsonify({'data': data}), 201


# A simple function to calculate the square of a number
class Square(Resource):

    def get(self, num):
        return jsonify({'square': num ** 2})


class Register(Resource):
    def get(self):
        # Browser GET would otherwise 404 — POST only for real registration.
        return jsonify({
            'message': 'Registration endpoint — use POST only.',
            'method': 'POST',
            'content_type': 'application/json',
            'body': {
                'username': 'alphanumeric, 3–64 chars',
                'password': 'your password',
            },
        })

    def post(self):
        # Parse the arguments
        parser = reqparse.RequestParser()
        parser.add_argument('username', type=str, help='Registration Username')
        parser.add_argument('password', type=str, help='Registration Password')
        args = parser.parse_args()

        _userUser = args['username']
        _userPassword = args['password']

        if not _userUser or not _userPassword:
            return {'msg': 'Invalid registration details'}, 403

        elif not re.fullmatch(r'[A-Za-z0-9]{3,64}', _userUser):
            return {'msg': 'Invalid registration details'}, 403

        try:
            cursor = mysql.connection.cursor()
            cursor.execute('''SELECT * FROM accounts WHERE username = (%s) ''', (_userUser, ))
            account = cursor.fetchone()
            if account:
                return {'msg': 'Invalid registration details'}, 403

            hashed_password = generate_password_hash(_userPassword)
            cursor.execute(
                'INSERT INTO accounts (username, password) VALUES (%s, %s)',
                (_userUser, hashed_password)
            )
            mysql.connection.commit()
            return {'msg': 'You have successfully registered!'}, 201

        except Exception as e:
            print(str(e))
            return {'msg': 'Registration Error'}, 400


class Login(Resource):
    def get(self):
        # Browser GET would otherwise 404 — POST only for real login.
        return jsonify({
            'message': 'Login endpoint — use POST only.',
            'method': 'POST',
            'content_type': 'application/json',
            'body': {
                'username': '...',
                'password': '...',
            },
            'note': 'Response includes csrf_token; send as X-CSRF-Token on mutating requests with credentials.',
        })

    def post(self):
        # Parse the arguments
        parser = reqparse.RequestParser()
        parser.add_argument('username', type=str, help='Login Username')
        parser.add_argument('password', type=str, help='Login Password')
        args = parser.parse_args()

        _userUser = args['username']
        _userPassword = args['password']

        if not _userUser or not _userPassword:
            return {'msg': 'Invalid credentials'}, 403

        try:
            if not _check_login_rate_limit(request.remote_addr, _userUser):
                return {'msg': 'Too many login attempts. Please try again later.'}, 429

            cursor = mysql.connection.cursor()
            cursor.execute('''SELECT * FROM accounts WHERE username = (%s)''', (_userUser, ))
            account = cursor.fetchone()
            if account and check_password_hash(account['password'], _userPassword):
                session['loggedin'] = True
                session['id'] = account['id']
                session['username'] = account['username']
                csrf_token = secrets.token_urlsafe(32)
                session['csrf_token'] = csrf_token
                _clear_login_failures(request.remote_addr, _userUser)
                return {'msg': 'Logged in successfully !', 'csrf_token': csrf_token}, 201

            _record_login_failure(request.remote_addr, _userUser)
            return {'msg': 'Invalid credentials'}, 403

        except Exception as e:
            print(str(e))
            return {'msg': "Login Error"}, 400


class AllTasks(Resource):

    def get(self):
        if not _is_authenticated():
            return {'msg': 'Unauthorized'}, 401

        print("Getting all tasks")
        try:
            cur = mysql.connection.cursor()
            cur.execute(
                '''SELECT * FROM tasklist WHERE id IS NOT NULL AND user_id = %s''',
                (session.get('id'), )
            )
            all_tasks = cur.fetchall()
            if all_tasks:
                return jsonify(all_tasks)
        except Exception as e:
            print(str(e))
            return {'error': "Could not get all Tasks"}, 400

    def post(self):
        if not _is_authenticated():
            return {'msg': 'Unauthorized'}, 401
        if not _is_valid_csrf():
            return {'msg': 'CSRF validation failed'}, 403

        # Parse request for json, to create a task
        try:
            # Parse the arguments
            parser = reqparse.RequestParser()
            parser.add_argument('title', type=str, help='Title of Task to add')
            parser.add_argument('status', type=str, help='Completed status of Task to add')
            args = parser.parse_args()

            _taskTitle = args['title']
            _taskStatus = args['status']

            if _taskStatus:
                _taskStatus = 1
            else:
                _taskStatus = 0

            cur = mysql.connection.cursor()
            cur.execute(
                '''INSERT INTO tasklist (title, completed, user_id) VALUES (%s, %s, %s)''',
                (_taskTitle, str(_taskStatus), session.get('id'))
            )

            # Save sql work, close and load /alltasks
            mysql.connection.commit()
            cur.close()
            return redirect(url_for('alltasks'))
            # return {'Title': args['title'], 'Status': args['status']}

        except Exception as e:
            print(str(e))
            return {'error': "Could not post Task"}, 400


class TaskDetail(Resource):

    def get(self, task_id):
        if not _is_authenticated():
            return {'msg': 'Unauthorized'}, 401

        print("Getting details for Task by ID")
        try:
            cur = mysql.connection.cursor()
            cur.execute(
                '''SELECT * FROM tasklist WHERE id IS NOT NULL AND id = %s AND user_id = %s''',
                (task_id, session.get('id'))
            )
            all_tasks = cur.fetchall()

            if all_tasks:
                return jsonify(all_tasks)
        except Exception as e:
            print(str(e))
            return {'error': "Could not get Task by ID"}, 400

    def put(self, task_id):
        if not _is_authenticated():
            return {'msg': 'Unauthorized'}, 401
        if not _is_valid_csrf():
            return {'msg': 'CSRF validation failed'}, 403

        print("Updating details for Task")
        try:

            parser = reqparse.RequestParser()
            parser.add_argument('title', type=str, help='Title of Task to update')
            parser.add_argument('status', type=str, help='Completed status of Task')
            args = parser.parse_args()

            _taskTitle = args['title']
            _taskStatus = args['status']

            if _taskStatus:
                _taskStatus = str(1)
            else:
                _taskStatus = str(0)

            cur = mysql.connection.cursor()
            update_user_cmd = '''UPDATE tasklist SET title=%s, completed=%s WHERE id=%s AND user_id=%s'''
            cur.execute(update_user_cmd, (_taskTitle, _taskStatus, str(task_id), session.get('id')))

            # Save sql work, close and load /alltasks
            mysql.connection.commit()
            if cur.rowcount == 0:
                cur.close()
                return {'msg': 'Task not found'}, 404
            cur.close()
            return redirect(url_for('alltasks'))

        except Exception as e:
            print(str(e))
        return {'error': "Could not update Task details"}, 400

    def delete(self, task_id):
        if not _is_authenticated():
            return {'msg': 'Unauthorized'}, 401
        if not _is_valid_csrf():
            return {'msg': 'CSRF validation failed'}, 403

        print("Attempting to delete Task by ID")
        try:
            cur = mysql.connection.cursor()
            cur.execute(
                '''DELETE FROM tasklist WHERE id=%s AND user_id=%s''',
                (task_id, session.get('id'))
            )

            # Save sql work, close and load /alltasks
            mysql.connection.commit()
            if cur.rowcount == 0:
                cur.close()
                return {'msg': 'Task not found'}, 404
            cur.close()
            return redirect(url_for('alltasks'))

        except Exception as e:
            print(str(e))
            return {'error': "Could not update Task details"}, 400


def init_mysql_api_app():
    # sql conn with no named database, to allow creating of named database before route setting
    connection = None
    cursor = None
    print("\nInitializing database...")
    password = input("Root Password: ")
    try:
        connection = MySQLdb.connect(host="localhost",  # your host, usually localhost
                                     user="root",  # your username
                                     passwd=password,  # your password
                                     db="")
        cursor = connection.cursor()
        try:
            # Create database
            cursor.execute('CREATE DATABASE IF NOT EXISTS taskstack')
            cursor.execute('USE taskstack')

            # Create accounts table
            cursor.execute('''CREATE TABLE IF NOT EXISTS accounts (
                        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        username VARCHAR(100) NOT NULL UNIQUE,
                        password VARCHAR(255) NOT NULL)''')

            # Create tasklist table
            cursor.execute('''CREATE TABLE IF NOT EXISTS tasklist (
                        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
                        title VARCHAR(100) NOT NULL,
                        completed BOOLEAN NOT NULL DEFAULT 0,
                        user_id INT NULL)''')

            # Backfill schema for existing databases.
            cursor.execute("SHOW COLUMNS FROM tasklist LIKE 'user_id'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE tasklist ADD COLUMN user_id INT NULL")

            connection.commit()
            cursor.close()

        except MySQLdb.Error as err:
            print(f"Error: '{err}'")

    except MySQLdb.Error as err:
        print(f"Error: '{err}'")
    finally:
        # Close root connection
        if connection:
            connection.close()
        print("Created workspace with taskstack database")

        # creating a Flask app
        global app
        # Production build: default client/webapp_build (see scripts/build_frontend.py + client/README.md)
        _static = os.environ.get('FRONTEND_STATIC_FOLDER', './client/webapp_build')
        app = Flask(__name__, static_folder=_static, static_url_path='/')
        cors_origins = os.environ.get('CORS_ORIGINS')
        if not cors_origins:
            raise RuntimeError('CORS_ORIGINS must be set to explicit trusted origins')
        allowed_origins = [
            origin.strip()
            for origin in cors_origins.split(',')
            if origin.strip()
        ]
        if not allowed_origins or '*' in allowed_origins:
            raise RuntimeError('CORS_ORIGINS cannot be empty or include wildcard when using credentials')
        CORS(app, resources={r"/*": {"origins": allowed_origins}}, supports_credentials=True)

        # Serve React build at /. Must be a plain Flask view — not a RESTful Resource —
        # because send_static_file() returns a Response; RESTful would try to JSON-encode it.
        def serve_index():
            index_path = os.path.join(app.static_folder or '', 'index.html')
            if os.path.isfile(index_path):
                return app.send_static_file('index.html')
            return jsonify({
                'message': 'Frontend build not found.',
                'static_folder': app.static_folder,
                'hint': 'Build the React app so index.html exists, or use the API.',
                'try': {
                    'hello': '/home',
                    'register': 'POST /register',
                    'login': 'POST /login',
                    'tasks': 'GET /alltasks (after login)',
                },
            })

        app.add_url_rule('/', 'serve_index', serve_index, methods=['GET'])

        # creating an API object
        global api
        api = Api(app)

        # URL route handlers (no Resource for / — see serve_index above)
        api.add_resource(Hello, '/home', '/hello')
        api.add_resource(Square, '/square/<int:num>')
        api.add_resource(Register, '/register')
        api.add_resource(Login, '/login')
        api.add_resource(AllTasks, '/alltasks')
        api.add_resource(TaskDetail, '/task/<int:task_id>')

        mysql_login()


def mysql_login():
    # config Flasks Database login details
    print("\nLogin to database as a user:")
    database = "taskstack"
    username = input("Username: ")
    password = input("Password: ")
    secret_key = os.environ.get('FLASK_SECRET_KEY')
    if not secret_key:
        raise RuntimeError('FLASK_SECRET_KEY environment variable is required')

    app.secret_key = secret_key
    app.config['MYSQL_USER'] = username
    app.config['MYSQL_PASSWORD'] = password
    app.config['MYSQL_HOST'] = 'localhost'
    app.config['MYSQL_DB'] = database
    app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SECURE'] = os.environ.get('SESSION_COOKIE_SECURE', 'true').lower() == 'true'
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # create MySql object
    global mysql
    mysql = MySQL(app)


def main():

    init_mysql_api_app()
    # Run flask                                                
    app.run(host="localhost", port=int("5000"), debug=False, use_reloader=False)


if __name__ == '__main__':
    main()
    