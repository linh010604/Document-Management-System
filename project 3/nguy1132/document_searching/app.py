import base64
import hashlib
import sqlite3
import os
import json
import requests
from flask import Flask, request

app = Flask(__name__)

DOCUMENT_SERVICE_URL = 'http://micro2:5001/search'
LOGGING_SERVICE_URL = "http://micro4:5003/success"
USER_SERVICE_URL = "http://micro1:5000/document"


@app.route('/search', methods=['GET'])
def search():
    filename = request.args.get('filename')
    jwt_token = request.headers.get('Authorization', '').split(' ')[-1]

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
            return json.dumps({"status": 2, "data": "NULL"})

        DOCPARAMS = {'filename': filename}
        r = requests.post(url=DOCUMENT_SERVICE_URL, data=DOCPARAMS)
        doc_data = r.json()
        groups = json.loads(doc_data['groups'])
        groups = json.loads(groups)

        if data['groups'] not in groups.values():
            return json.dumps({"status": 3, 'data': "NULL"})

        PARAMS = {'user_id': doc_data['owner_id']}
        URL = "http://micro1:5000/get_user"
        r = requests.post(url=URL, data=PARAMS)
        owner_data = r.json()
        owner = owner_data['username']

        file_hash = hashlib.sha256(doc_data['body'].encode()).hexdigest()

        PARAMS = {'filename': filename}
        URL = "http://micro4:5003/get"
        r = requests.get(url=URL, params=PARAMS)
        mod = r.json()
        last_mod = mod['last_mod']
        total_mod = mod['total_mod']

        LOGPARAM = {"event_type": "document_search", "username": username, "filename": filename}
        r = requests.post(url=LOGGING_SERVICE_URL, data=LOGPARAM)

        return json.dumps({'status': 1,
                           'data': {
                               'filename': filename,
                               'owner': owner,
                               'last_mod': last_mod,
                               'total_mod': total_mod,
                               'hash': file_hash
                           }})

    except:
        return json.dumps({"status": 2, 'data': 'NULL'})

@app.route('/clear', methods=['GET'])
def clear():
    return json.dumps({"status": 1, "message": "No local database to clear"}), 200

