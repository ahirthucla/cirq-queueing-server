from google.cloud import datastore 
import cirq
from flask import Flask
import time
import sys
import datetime
from cirq.contrib.qasm_import import circuit_from_qasm, QasmException
from cirq_multiplexer.multiplex import multiplex_onto_sycamore, get_error_qubits
import os

def prepare_job(entity: 'datastore.Entity', device, err_qubits) -> 'datastore.Entity':
    """ Run job on one of available handlers and update entity
    Arg: 
        entity: unfinished job key-able entity
    Returns: 
        entity with updated results or response message
    """

    # ensure only running unfinished jobs
    assert not entity['done']

    # mark entity as done
    entity['done'] = True

    # parse circuit
    # This could be done in the verifier, and we could pickle load the circuit here
    #   but that may be limited by datastore's ability to save binary data
    try:
        circuit = circuit_from_qasm(entity['qasm'])
    except QasmException as e:
        entity['message'] = 'Exception observed while converting QASM string to circuit:\n' + str(e) + '\n' + \
                            'With QASM string:\n' + str(entity['qasm'])
        return entity, None, None

    # conditionally map circuit
    try:
        circuit, _ = next(multiplex_onto_sycamore([circuit], device, exclude_always=err_qubits))
    except Exception as e:
        entity['message'] = 'Exception observed while mapping circuit:\n' + str(e)
        return entity, None, None

    entity.exclude_from_indexes.add('mapped_circuit')
    entity['mapped_circuit'] = circuit.to_qasm()

    return entity, circuit, entity['repetitions']

def run_jobs(handler, circuits, repetitions):
    for result in handler.run_batch(circuits, repetitions=repetitions):
        yield str(result[0])

def finalize_job(entity, result):
    # update and return entity
    entity.exclude_from_indexes.add('results')
    entity['results'] = str(result)
    entity['processed_timestamp'] = datetime.datetime.utcnow()
    entity['processed_version'] = os.environ.get('GAE_VERSION')
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
    err_qubits = get_error_qubits(client.project, processor_id, 35)

    # pull unfinished, verified job keys
    query = client.query(kind="job")
    query.add_filter("done", "=", False)
    query.add_filter("verified", "=", True)

    # get each job by key and run it in a transaction
    with client.transaction():
        prepared = [prepare_job(entity, device, err_qubits) for entity in query.fetch()]

        to_run, complete = [],[]
        for entity, circuit, repetitions in prepared:
            if circuit and repetitions:
                to_run.append((entity, circuit, repetitions))
            else:
                complete.append((entity, circuit, repetitions))
        assert len(to_run) + len(complete) == len(prepared)

        if to_run:
            entities, circuits, repetitions = zip(*to_run)
            results = run_jobs(handler, circuits, list(repetitions))
            complete.extend(map(finalize_job, entities, results))
        client.put_multi(complete)

    # return number of jobs run
    return 'Jobs run: '+str(len(prepared))

if __name__ == '__main__':
    # processor id from argument
    PROCESSOR_ID = str(sys.argv[1])

    print(run(PROCESSOR_ID))
