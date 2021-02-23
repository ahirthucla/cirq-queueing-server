from typing import TYPE_CHECKING, cast
from google.cloud import datastore
import cirq
from cirq.contrib.qasm_import import circuit_from_qasm, QasmException
import time
import cirq.google as cg
import datetime
import sys
import os

if TYPE_CHECKING:
    from google.cloud.datastore import Entity

def verify_job(entity: 'Entity', max_qubits: int = 16, max_ops: int = 120, max_reps: int = 100) -> 'Entity':
    """ Verify that a job satisfies max count constraints, passes a manual check, and is valid for the device
    Args: 
        entity: unfinished, unverified job 
        max_qubits: maximum number of qubits a circuit can use
        max_ops: maximum number of operations in circuit
        max_reps: maximum number of times circuit can be run
    Returns: 
        updated entity, either verified or with error response message
    """

    # ensure only correct jobs are being pulled
    assert not entity['done'] and not entity['verified']

    # record verification timestamp
    entity['verified_timestamp'] = datetime.datetime.utcnow()
    entity['verified_version'] = os.environ.get('GAE_VERSION')
    entity.exclude_from_indexes.add('message')

    # parse circuit from qasm, checking for illegal qasm circuit
    try:
        circuit = circuit_from_qasm(entity['qasm'])
    except QasmException as e:
        message = 'Error converting QASM string to circuit:\n' +\
                            'Exception Observed:\n'+\
                            str(e)+'\n'+\
                            'With QASM string:\n'+\
                            str(entity['qasm'])
        entity['verified'] = False
        entity['message'] = message
        return entity
    
    # check for too many qubits
    message = ''
    qubit_count = sum(1 for _ in circuit.all_qubits())
    if qubit_count > max_qubits: 
        message += 'Circuit uses too many qubits: ' + str(qubit_count) + '>' + str(max_qubits) + '\n'

    # check for too many operations
    op_count = sum(1 for _ in circuit.all_operations())
    if op_count > max_ops: 
        message += 'Circuit has too many operations: ' + str(op_count) + '>' + str(max_ops) + '\n'

    # check for too many repetitions
    rep_count = int(entity['repetitions'])
    if rep_count > max_reps:
        message += 'Circuit is repeated too many times: ' + str(rep_count) + '>' + str(max_reps) + '\n'

    # save error message and exit
    if message:
        entity['verified'] = False
        entity['message'] = message
        return entity

    # update and return valid circuit
    entity['verified'] = True
    entity['message'] = 'Validated'
    return entity

def verify_all(processor_id: str) -> str:
    """ pull unfinished, unverified jobs and verifies them
    Arg: 
        processor_id: string name of processor to verify against
    Returns: 
        string message with number of jobs verified
    """

    # Connect to datastore
    client = datastore.Client()

    # pull unfinished, unverified job keys
    query = client.query(kind="job")
    query.keys_only()
    query.add_filter("done", "=", False)
    query.add_filter("verified", "=", False)
    keys = list(query.fetch())

    # get each job by key and verify it in a transaction
    for key in keys:
        with client.transaction():
            entity = client.get(key.key)
            entity = verify_job(entity)
            client.put(entity)

    # return number of jobs verified
    return 'Jobs verified: '+str(len(keys))

if __name__ == '__main__':
    # pull processor name from arguments
    processor_id = str(sys.argv[1])

    # runs verifier and prints number of jobs verified
    print(verify_all(processor_id))
