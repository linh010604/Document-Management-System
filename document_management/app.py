import sqlite3
import os
import json
import requests
from flask import Flask, request
import base64

app = Flask(__name__)
db_name = "documents.db"
sql_file = "documents.sql"
db_flag = False

USER_SERVICE_URL = "http://micro1:5000/document"
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


@app.route('/create_document', methods=(['POST']))
def create_document():
    groups = request.form.get('groups')
    filename = request.form.get('filename')
    body = request.form.get('body')
    jwt_token = request.headers.get('Authorization', '').split(' ')[-1]

    conn = get_db()
    cursor = conn.cursor()

    try:
        encoded_header, encoded_payload, received_signature = jwt_token.split('.')
        payload = json.loads(base64.urlsafe_b64decode(encoded_payload + '==').decode('utf-8'))
        username = payload['username']

        PARAMS = {'jwt_token': jwt_token}

        r = requests.post(url=USER_SERVICE_URL, data=PARAMS)
        data = r.json()
        user_id = None

        if data:
            user_id = int(data["user_id"])
        else:
            conn.close()
            return json.dumps({"status": 2})

        cursor.execute("SELECT * FROM documents WHERE filename = ?", (filename,))

        check = cursor.fetchone()
        if check:
            cursor.execute("DELETE FROM documents WHERE filename = ?", (filename,))
            conn.commit()

        cursor.execute('''
                    INSERT INTO documents (filename, body, owner_id, groups)
                    VALUES (?, ?, ?, ?)
                ''', (filename, body, user_id, json.dumps(groups)))
        conn.commit()

        LOGPARAM = {"event_type": "document_creation", "username": username, "filename": filename}
        r = requests.post(url=LOGGING_SERVICE_URL, data=LOGPARAM)
        conn.close()
        return json.dumps({"status": 1})

    except:
        conn.close()
        return json.dumps({"status": 2})


@app.route('/edit_document', methods=['POST'])
def edit_document():
    filename = request.form.get('filename')
    body = request.form.get('body')
    jwt_token = request.headers.get('Authorization', '').split(' ')[-1]

    conn = get_db()
    cursor = conn.cursor()

    try:
        encoded_header, encoded_payload, received_signature = jwt_token.split('.')
        payload = json.loads(base64.urlsafe_b64decode(encoded_payload + '==').decode('utf-8'))
        username = payload['username']

        PARAMS = {'jwt_token': jwt_token}

        r = requests.post(url=USER_SERVICE_URL, data=PARAMS)
        data = r.json()
        user_id = None
        if data:
            user_id = int(data["user_id"])
        else:
            conn.close()
            return json.dumps({"status": 2})

        cursor.execute('SELECT groups FROM documents WHERE filename = ?', (filename,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return json.dumps({"status": 3})
        groups = json.loads(row[0])
        groups = json.loads(groups)

        user_group = data['groups']
        if user_group not in groups.values():
            return json.dumps({"status": 3})

        # Append to document body
        cursor.execute('''
            UPDATE documents
            SET body = body || ?
            WHERE filename = ?
        ''', (body, filename))
        conn.commit()

        LOGPARAM = {"event_type": "document_edit", "username": username, "filename": filename}
        r = requests.post(url=LOGGING_SERVICE_URL, data=LOGPARAM)

        conn.close()
        return json.dumps({"status": 1})
    except:
        conn.close()
        return json.dumps({"status": 2})

@app.route('/clear', methods=['GET'])
def clear():
    create_db()
    return json.dumps({"status": 1, "message": "Database cleared"}), 200

@app.route('/search', methods=['POST'])
def search():
    filename = request.form.get('filename')

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(''' SELECT * FROM documents WHERE filename = ?''', (filename, ))
    data = cursor.fetchone()
    conn.close()
    if data:
        return json.dumps({'filename': data[1], 'body': data[2], 'owner_id': data[3], 'groups': data[4]}), 200
    else:
        return json.dumps({})

