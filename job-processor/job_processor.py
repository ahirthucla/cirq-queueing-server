from typing import TYPE_CHECKING
from google.cloud import datastore 
import cirq
from cirq.contrib.qasm_import import circuit_from_qasm, QasmException
from flask import Flask
import time
import cirq.google as cg
import sys

if TYPE_CHECKING: 
    from google.cloud.datastore import Entity

# Connect to datastore
client = datastore.Client()

# Initialize flask
app = Flask(__name__)

# processor id from argument
processor_id = str(sys.argv[1])

# Initialize google cloud quantum engine
engine = cirq.google.Engine(project_id=client.project)

# Initialize handlers for qsim and real hardware
qsim_handler = engine.sampler(processor_id='qsim', gate_set=cg.SYC_GATESET)
real_handler = engine.sampler(processor_id=processor_id, gate_set=cg.SYC_GATESET)

# Map 'method' strings to handlers
handlers = {'csim':cirq.Simulator(), 'qsim':qsim_handler, 'real': real_handler}

#TODO multiplexing job circuits, demultiplexing the results, storing in each job

#def run_job(entity: 'Entity', handlers: whatever) -> 'Entity':
def run_job(entity: 'Entity') -> 'Entity':
    """ Run job on one of available handlers and update entity
    Arg: 
        entity: unfinished job
    Returns: 
        entity with updated results or response message
    """

    # ensure only running unfinished jobs
    assert not entity['done']:

    # mark entity as done
    entity['done'] = True

    # parse circuit
    # This could be done in the verifier, and we could pickle load the circuit here
    #   but that may be limited by datastore's ability to save binary data
    try:
        circuit = circuit_from_qasm(entity['qasm'])
    except QasmException as e:
        entity['message'] = 'Error converting QASM string to circuit:\n' +\
                            'Exception Observed:\n' + str(e) + '\n' + \
                            'With QASM string:\n' + str(entity['qasm'])
        return entity
    
    # select handler based on 'method' type
    if 'method' in entity and entity['method'] in handlers:
        handler = handlers[entity['method']]
    else:
        handler = handlers['csim']

    # time and run circuit
    start = time.time()
    try:
        result = handler.run(circuit, repetitions=int(entity['shots']))
    except Exception as e:
        entity['message'] = "Error running circuit:\n"+\
                 "Exception Observed:\n" + str()
        return entity
    elapsed = time.time() - start

    # update and return entity
    entity['results'] = str(result)
    entity['time'] = elapsed
    return entity

@app.route('/run')
#def run(client: datastore.Client) -> str:
def run() -> str:
    """ pull unfinished, verified jobs and run them
    Returns: 
        string message with number of jobs run
    """

    # tentatively create handlers in here if this isn't going to be a server.

    # pull unfinished, verified job keys
    query = client.query(kind="job")
    query.keys_only()
    query.add_filter("done", "=", False)
    query.add_filter("verified", "=", True)
    keys = list(query.fetch())

    # get each job by key and run it in a transaction
    for key in keys:
        with client.transaction():
            entity = client.get(key.key)
            #entity = run_job(entity, handlers)
            entity = run_job(entity)
            client.put(entity)

    # return number of jobs run
    return 'Jobs run: '+str(len(keys))

if __name__ == '__main__':
    # tentatively initialize client here

    # run as local server for testing
    app.run(host='127.0.0.1', port=8080, debug=True)
