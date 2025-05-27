import sqlite3
import json
import hashlib
import base64
import hmac

import requests
from flask import Flask, request

app = Flask(__name__)
db_name = "user.db"
sql_file = "user.sql"
db_flag = False

LOGGING_SERVICE_URL = "http://micro4:5003/success"

# project 2
def create_db():
    conn = sqlite3.connect(db_name)

    with open(sql_file, 'r') as sql_startup:
        init_db = sql_startup.read()
    cursor = conn.cursor()
    cursor.executescript(init_db)
    conn.commit()
    conn.close()
    global db_flag
    db_flag = True
    return conn


def get_db():
    if not db_flag:
        create_db()
    conn = sqlite3.connect(db_name)
    return conn


def hashing(password, salt):
    return hashlib.sha256((password + salt).encode()).hexdigest()


def check(password):
    num = 0
    up = 0
    low = 0

    for x in password:
        if x.isnumeric():
            num = 1
        elif x.isupper():
            up = 1
        elif x.islower():
            low = 1

        if num * up * low:
            return True

    return False


@app.route('/create_user', methods=(['POST']))
def create_user():
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    username = request.form.get('username')
    email_address = request.form.get('email_address')
    group = request.form.get('group')
    password = request.form.get('password')
    salt = request.form.get('salt')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT username, email_address FROM users WHERE username = ? OR email_address = ?;",
                   (username, email_address))
    existing_user = cursor.fetchone()

    if existing_user:
        conn.close()
        return json.dumps({"status": 2 if existing_user[0] == username else 3, "pass_hash": "NULL"})

    if username.lower() in password.lower() or first_name.lower() in password.lower() or len(
            password) < 8 or last_name.lower() in password.lower():
        conn.close()
        return json.dumps({"status": 4, "pass_hash": "NULL"})

    if check(password):
        hash_password = hashing(password, salt)
        cursor.execute("""
                    INSERT INTO users (username, first_name, last_name, email_address, user_group, password, salt)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                """, (username, first_name, last_name, email_address, group, hash_password, salt))

        conn.commit()
        conn.close()

        LOGPARAM = {"event_type": "user_creation", "username": username, "filename": "NULL"}
        r = requests.post(url=LOGGING_SERVICE_URL, data=LOGPARAM)

        return json.dumps({"status": 1, "pass_hash": hash_password})

    else:
        conn.close()
        return json.dumps({"status": 4, "pass_hash": "NULL"})


def base64_url_encode(data):
    return base64.urlsafe_b64encode(data.encode('utf-8')).decode('utf-8')


def generate_jwt(username):
    header = {
        "alg": "HS256",
        "typ": "JWT"
    }
    header = base64_url_encode(json.dumps(header))

    payload = {
        "username": username
    }

    payload = base64_url_encode(json.dumps(payload))

    with open('key.txt', 'r') as f:
        key = f.read().strip()

    signature = hmac.new(key.encode('utf-8'), f"{header}.{payload}".encode('utf-8'), hashlib.sha256).hexdigest()
    jwt_token = f"{header}.{payload}.{signature}"
    return jwt_token


@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT id, password, salt FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    if not user:
        conn.close()
        return json.dumps({"status": 2, "jwt": "NULL"})

    user_id, store_pass, salt = user
    hash_password = hashing(password, salt)

    if hash_password != store_pass:
        conn.close()
        return json.dumps({"status": 2, "jwt": "NULL"})

    jwt_token = generate_jwt(username)

    conn.commit()
    conn.close()

    LOGPARAM = {'event_type': 'login', 'username': username, 'filename': 'NULL'}
    r = requests.post(url=LOGGING_SERVICE_URL, data=LOGPARAM)

    return json.dumps({"status": 1, "jwt": jwt_token})

@app.route('/document', methods=['POST'])
def document():
    jwt_token = request.form.get('jwt_token')

    encoded_header, encoded_payload, received_signature = jwt_token.split('.')
    payload = json.loads(base64.urlsafe_b64decode(encoded_payload + '==').decode('utf-8'))
    username = payload['username']

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        exist_user = cursor.fetchone()

        stored_jwt = generate_jwt(exist_user[1])
        if stored_jwt != jwt_token:
            conn.close()
            return json.dumps({})

        conn.commit()
        conn.close()

        return json.dumps({"user_id": int(exist_user[0]), "groups": exist_user[5], "username": exist_user[1]})
    except:
        conn.close()
        return json.dumps({})

@app.route('/get_user', methods=['POST'])
def get_user():
    user_id = request.form.get('user_id')

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        exist_user = cursor.fetchone()

        conn.commit()
        conn.close()

        return json.dumps({"user_id": int(exist_user[0]), "groups": exist_user[5], "username": exist_user[1]})
    except:
        conn.close()
        return json.dumps({})

@app.route('/clear', methods=['GET'])
def clear():
    create_db()
    return json.dumps({"status": 1, "message": "Database cleared"}), 200

