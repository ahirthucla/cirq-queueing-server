# Copyright 2018 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from flask import Flask, render_template, request
import job_processor

# [START gae_python38_datastore_store_and_fetch_times]
# [START gae_python3_datastore_store_and_fetch_times]
from google.cloud import datastore

client = datastore.Client()

# [END gae_python3_datastore_store_and_fetch_times]
# [END gae_python38_datastore_store_and_fetch_times]
app = Flask(__name__)


# [START gae_python38_datastore_store_and_fetch_times]
# [START gae_python3_datastore_store_and_fetch_times]
def store_job(dt):
    key = client.key('job')
    entity = datastore.Entity(key=key)

    for field in ['qasm', 'email', 'shots']:
        entity.update({field:str(dt[field])})
    entity.update({'done':False})

    client.put(entity)
    return entity.key.id

def fetch_results(dt):
    keys = [client.key('job', int(jid)) for jid in dt]
    entities = client.get_multi(keys)
    #results = query.fetch(limit=limit)
    results = {}
    for entity in entities:
        results[entity.id] = dict(entity.items())

    return results
# [END gae_python3_datastore_store_and_fetch_times]
# [END gae_python38_datastore_store_and_fetch_times]


# [START gae_python38_datastore_render_times]
# [START gae_python3_datastore_render_times]
@app.route('/lookup', methods=['GET'])
def lookup():
    if request.args:
        if 'jid' not in request.args:
            return "Request URL should contain 'jid' field"
        return fetch_results(request.args.getlist('jid'))
    else: 
        return "Please GET with a URL  'jid' field of a list of job identifiers"

@app.route('/send', methods=['GET', 'POST'])
def send():
    # Store the current access time in Datastore.
    if request.method == 'GET':
        return "Please POST a json object containing 'qasm', 'email', and 'shots' fields"
    if request.method == 'POST':
        if request.json:
            if any([x not in request.json for x in ['qasm', 'email', 'shots']]): 
                return "Request JSON should contain 'qasm', 'email', and 'shots' fields"

            jid = store_job(request.json)
            return "Job Stored with ID: " + str(jid)
        else: 
            return "Please POST a json object containing 'qasm', 'email', and 'shots' fields"

@app.route('/run')
def run_jobs():
    count = job_processor.run()
    return "Jobs run: " + str(count)

@app.route('/')
def root():
    return "Use /send or /lookup"

# [END gae_python3_datastore_render_times]
# [END gae_python38_datastore_render_times]


if __name__ == '__main__':
    # This is used when running locally only. When deploying to Google App
    # Engine, a webserver process such as Gunicorn will serve the app. This
    # can be configured by adding an `entrypoint` to app.yaml.

    # Flask's development server will automatically serve static files in
    # the "static" directory. See:
    # http://flask.pocoo.org/docs/1.0/quickstart/#static-files. Once deployed,
    # App Engine itself will serve those files as configured in app.yaml.
    app.run(host='127.0.0.1', port=8080, debug=True)
