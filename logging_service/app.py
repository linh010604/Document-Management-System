import base64
import sqlite3
import os
import json
import requests
from flask import Flask, request

app = Flask(__name__)
db_name = "logs.db"
sql_file = "logs.sql"
db_flag = False

USER_SERVICE_URL = "http://micro1:5000/document"
DOCUMENT_SERVICE_URL = 'http://micro2:5001/search'


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


@app.route('/success', methods=['POST'])
def success():
    event_type = request.form.get('event_type')
    username = request.form.get('username')
    filename = request.form.get('filename')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(''' INSERT INTO logs (event_type, username, filename)
                        VALUES (?, ?, ?)
                    ''', (event_type, username, filename))
    conn.commit()

    conn.close()

    return json.dumps({'status': 1})


@app.route('/view_log', methods=['GET'])
def view():
    username = request.args.get('username')
    filename = request.args.get('filename')
    jwt_token = request.headers.get('Authorization', '').split(' ')[-1]

    conn = get_db()
    cursor = conn.cursor()

    try:
        encoded_header, encoded_payload, received_signature = jwt_token.split('.')
        payload = json.loads(base64.urlsafe_b64decode(encoded_payload + '==').decode('utf-8'))
        sent_username = payload['username']

        PARAMS = {'jwt_token': jwt_token}

        r = requests.post(url=USER_SERVICE_URL, data=PARAMS)
        data = r.json()
        user_id = None

        if data:
            user_id = int(data["user_id"])
        else:
            conn.close()
            return json.dumps({"status": 2, "data": "NULL"})

        res = {'status': 1, 'data': dict()}

        if filename:
            DOCPARAMS = {'filename': filename}
            r = requests.post(url=DOCUMENT_SERVICE_URL, data=DOCPARAMS)
            doc_data = r.json()
            groups = json.loads(doc_data['groups'])
            groups = json.loads(groups)

            if data['groups'] not in groups.values():
                conn.close()
                return json.dumps({"status": 3, 'data': "NULL"})

            cursor.execute("SELECT * FROM logs WHERE filename = ?", (filename,))
            logs = cursor.fetchall()

            for i in range(1, len(logs)+1):
                res['data'][i] = {
                    'event': logs[i-1][1],
                    'user': logs[i-1][2],
                    'filename': logs[i-1][3]
                }

        else:
            if data['username'] != username:
                conn.close()
                return json.dumps({"status": 3, "data": "NULL"})

            cursor.execute("SELECT * FROM logs WHERE username= ?", (data['username'],))
            logs = cursor.fetchall()

            for i in range(1, len(logs)+1):
                res['data'][i] = {
                    'event': logs[i-1][1],
                    'user': logs[i-1][2],
                    'filename': logs[i-1][3]
                }
        conn.close()
        return json.dumps(res), 200
    except:
        conn.close()
        return json.dumps({"status": 2, "data": "NULL"})


@app.route('/clear', methods=['GET'])
def clear():
    create_db()
    return json.dumps({"status": 1, "message": "Database cleared"}), 200


@app.route('/get', methods=['GET'])
def get():
    filename = request.args.get('filename')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''SELECT COUNT(id) FROM logs 
            WHERE filename = ? AND event_type IN ("document_creation", "document_edit")
            ORDER BY id DESC''', (filename,))
    total_mod = cursor.fetchone()[0]
    cursor.execute('''SELECT username FROM logs 
            WHERE filename = ? AND event_type IN ("document_creation", "document_edit")
            ORDER BY id DESC''', (filename,))
    last_mod = cursor.fetchone()[0]
    conn.close()
    return json.dumps({'total_mod': total_mod, 'last_mod': last_mod})

