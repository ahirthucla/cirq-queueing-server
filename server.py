from typing import Dict, Iterable, Union
from flask import Flask, request
from google.cloud import datastore
import datetime
from job_processor.job_processor import run as run_jobs
from job_verifier.job_verifier import verify_all

# Connect to datastore
client = datastore.Client()

# Initialize flask
app = Flask(__name__)

# available fields and their defaults. None if the field is required
fields = {'qasm':None, 'email':None, 'repetitions':None, 'student_id':None, 'note':'Your Note Here'}

PROCESSOR_ID = 'PID'

def store_job(data: Dict[str,str], client: datastore.Client) -> int:
    """ Stores job datastore 
    Args: 
        data: dict of HTML fields
        client: datastore client to save to
    Returns: 
        key that job was stored with
    """
    
    # initialize entity
    key = client.key('job')
    entity = datastore.Entity(key=key)

    # fill entity fields
    for field, default in fields.items():
        value = data.get(field)
        entity[field] = value if value else default

    entity['submission_timestamp'] = datetime.datetime.utcnow()
    entity['verified'] = False
    entity['done'] = False

    # store entity
    client.put(entity)

    # return entity key
    return entity.key

# TODO need type hint help on this one 
def fetch_by_job(job_ids: Iterable[int], client: datastore.Client) -> Dict[int, Dict]:
    """ Fetches jobs from datastore by job id
    Arg: 
        job_ids: Iterable of job identifiers
        client: datastore client for retrieving from
    Returns: 
        dict of job result dictionaries, by job id
    """

    # collect job id keys
    keys = [client.key('job', int(job_id)) for job_id in job_ids]

    # query for all entities simultaneously
    entities = client.get_multi(keys)

    # index entities by their identifier, turn into json-able dict, and return
    results = {entity.id: dict(entity.items()) for entity in entities}
    return results

def fetch_by_student(student_ids: Iterable[int], client: datastore.Client) -> Dict[int, Dict]:
    """ Fetches jobs from datastore by student id
    Arg: 
        student_ids: Iterable of student identifiers
        client: datastore client for retrieving from
    Returns: 
        dict of job result dictionaries, by student id
    """

    # results dict, by student id
    results = {}
    for student_id in student_ids:
        # build query
        query = client.query(kind="job")
        query.add_filter("student_id", "=", int(student_id))
        # query for entities
        entities = query.fetch()
        results[student_id] = {entity.id: dict(entity.items()) for entity in entities}
    
    return results


@app.route('/lookup', methods=['GET'])
def lookup() -> Dict[int, Dict]:
    """ Looks up job result(s) in datastore from request job_id(s) in HTML payload
    Returns: 
       generator of response messages, including job results or error messages
    """

    # check that request has args attached
    if request.args:
        # check that either 'job_id' or 'student_id' is one of the args
        if not {'job_id', 'student_id'}.intersection(request.args):
            return "Request GET should contain 'job_id' or 'student_id' argument fields"

        response = {}
        # yield jobs by job id
        try: 
            if 'job_id' in request.args: 
                response['Jobs by job_id'] = fetch_by_job(request.args.getlist('job_id'), client)
        except Exception as e:
            return "Exception:" + str(e)

        # yield jobs by student id
        try:
            if 'student_id' in request.args:
                response['Jobs by student_id'] = fetch_by_student(request.args.getlist('student_id'), client)
        except Exception as e:
            return "Exception:" + str(e)

        return response

    else: 
        return "Please GET with a 'job_id' argument field"

@app.route('/send', methods=['GET', 'POST'])
def send() -> str:
    """ Checks HTML payload for correct fields and stores job
    Returns: 
        string response message
    """

    failure_string = 'Please POST a json object containing the following fields:\n' + \
                    ', '.join(str(field) + ('(optional)' if default else '') for field,default in fields.items())

    # check that request is of type POST and has a json attached
    if request.method == 'POST' and request.json:
        # check that json has required fields
        required_fields = {field for field,default in fields.items() if not default}
        if any(x not in request.json for x in required_fields):
            return failure_string

        # store job from json
        job_id = store_job(request.json, client).id

        # return job id
        return "Job Stored with ID: " + str(job_id)
    else: 
        return failure_string

@app.route('/verify', methods=['GET'])
def verify():
    print(request.headers)
    #if not request.headers.get('HTTP_X_APPENGINE_CRON'):
    #  return 'Not Authorized'
    return verify_all(PROCESSOR_ID)

@app.route('/run', methods=['GET'])
def run(): 
    #if not request.headers.get('HTTP_X_APPENGINE_CRON'):
    #  return 'Not Authorized'
    return run_jobs(PROCESSOR_ID)

@app.route('/')
def root() -> str:
    """ Default root page
    Returns: 
        string response message
    """

    return "Use /send or /lookup"


if __name__ == '__main__':
    # run as local server for testing
    app.run(host='127.0.0.1', port=8080, debug=True)
