from google.cloud import datastore 
import cirq
from flask import Flask
import time
import sys
import datetime
from cirq.contrib.qasm_import import circuit_from_qasm, QasmException
from cirq_multiplexer.multiplex import multiplex_onto_sycamore, get_error_qubits

def run_job(entity: 'datastore.Entity', handler, device, err_qubits) -> 'datastore.Entity':
    """ Run job on one of available handlers and update entity
    Arg: 
        entity: unfinished job key-able entity
    Returns: 
        entity with updated results or response message
    """

    # ensure only running unfinished jobs
    assert not entity['done']

    # mark entity as done TODO
    entity['done'] = True

    # parse circuit
    # This could be done in the verifier, and we could pickle load the circuit here
    #   but that may be limited by datastore's ability to save binary data
    try:
        circuit = circuit_from_qasm(entity['qasm'])
    except QasmException as e:
        entity['message'] = 'Exception observed while converting QASM string to circuit:\n' + str(e) + '\n' + \
                            'With QASM string:\n' + str(entity['qasm'])
        return entity

    # conditionally map circuit
    try:
        circuit, _ = next(multiplex_onto_sycamore([circuit], device, exclude_always=err_qubits))
    except Exception as e:
        entity['message'] = 'Exception observed while mapping circuit:\n' + str(e)
        return entity

    # time and run circuit
    start = time.time()
    try:
        result = handler.run(circuit, repetitions=int(entity['repetitions']))
    except Exception as e:
        entity['message'] = "Exception observed while  running circuit:\n"+ str(e)
        return entity
    elapsed = time.time() - start

    # update and return entity
    entity['results'] = str(result)
    entity['time'] = elapsed
    entity['processed_timestamp'] = datetime.datetime.utcnow()
    return entity

#def run(client: datastore.Client) -> str:
def run(processor_id) -> str:
    """ pull unfinished, verified jobs and run them
    Returns: 
        string message with number of jobs run
    """

    # Connect to datastore
    client = datastore.Client()

    # Initialize google cloud quantum engine
    engine = cirq.google.Engine(project_id=client.project)

    # get handler and device
    handler = engine.sampler(processor_id=processor_id, gate_set=cirq.google.SYC_GATESET)
    device = engine.get_processor(processor_id=processor_id).get_device([cirq.google.SYC_GATESET])

    # get current error qubits from recent calibration
    err_qubits = get_error_qubits(client.project, processor_id, 25)

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
            entity = run_job(entity, handler, device, err_qubits)
            client.put(entity)

    # return number of jobs run
    return 'Jobs run: '+str(len(keys))

if __name__ == '__main__':
    # processor id from argument
    PROCESSOR_ID = str(sys.argv[1])

    print(run(PROCESSOR_ID))
