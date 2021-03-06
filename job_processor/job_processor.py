from google.cloud import datastore 
import cirq
from flask import Flask
import time
import sys
import datetime
import os
from networkx import Graph
from itertools import combinations
from cirq.contrib.routing import route_circuit

def get_error_qubits(project_id, processor_id, threshold):

    # query for the latest calibration
    engine = cirq.google.Engine(project_id=project_id)
    processor = engine.get_processor(processor_id=processor_id)
    latest_calibration = processor.get_current_calibration()

    err_qubits = set()
    for metric_name in latest_calibration:
        for qubit_or_pair in latest_calibration[metric_name]:
            metric_value = latest_calibration[metric_name][qubit_or_pair]
            # find the qubits that have higher error probability(above the threshold)
            if metric_value[0] > threshold:
                # get all the qubits in the tuple from a metric key
                for q in qubit_or_pair:
                    err_qubits.add(q)
    return err_qubits

def naive_connectivity(gridqubits):
    # Workaround because I can't get connectivity directly from device object
    return Graph((q1,q2) for q1,q2 in combinations(gridqubits, 2) if q1.is_adjacent(q2))

def place_circuit(circuit, device, exclude_always):
    if exclude_always is None:
        exclude_always = set()
    else:
        exclude_always = set(exclude_always)

    try:
        return cirq.google.optimized_for_sycamore(circuit=circuit, new_device=device, optimizer_type='sycamore')
    except ValueError as e:
        pass

    # Workaround to work with route_circuit, which unnecessarily doesn't support multi-qubit measures
    def split_measure(measure_gate:'cirq.GateOperation') -> 'cirq.GateOperation':
        if not cirq.protocols.is_measurement(measure_gate):
            yield measure_gate
            return
        key = cirq.protocols.measurement_key(measure_gate)
        yield cirq.Moment([cirq.measure(qubit, key=key+'.'+str(qubit)) for qubit in measure_gate.qubits])
    circuit = cirq.Circuit(*map(split_measure, circuit.all_operations()))

    available_qubits = device.qubit_set() - exclude_always
    graph = naive_connectivity(available_qubits)

    circuit = route_circuit(circuit=circuit, device_graph=graph, algo_name='greedy').circuit
    circuit = cirq.google.optimized_for_sycamore(circuit=circuit, new_device=device, optimizer_type='sycamore')

    # Workaround because SerializableDevice is not json-able
    circuit = cirq.Circuit() + circuit

    device.validate_circuit(circuit)

    return circuit

def prepare_job(entity: 'datastore.Entity', device, err_qubits) -> 'datastore.Entity':
    """ Run job on one of available handlers and update entity
    Arg: 
        entity: unfinished job key-able entity
    Returns: 
        entity with updated results or response message
    """

    # ensure only running unfinished jobs
    assert not entity['done'] and not entity['sent']

    # parse circuit
    # This could be done in the verifier, and we could pickle load the circuit here
    #   but that may be limited by datastore's ability to save binary data
    try:
        circuit = cirq.read_json(json_text=entity['circuit'])
    except Exception as e:
        entity['message'] = 'Exception observed while converting JSON to circuit:\n' + str(type(e)) + str(e) + '\n' + \
                            'With JSON:\n' + str(entity['circuit'])
        entity['done'] = True
        return entity, None, None

    # conditionally map circuit
    try:
        #circuit, _ = next(multiplex_onto_sycamore([circuit], device, exclude_always=err_qubits))
        circuit = place_circuit(circuit, device, err_qubits)
    except Exception as e:
        entity['message'] = 'Exception observed while mapping circuit:\n' + str(type(e)) + str(e)
        entity['done'] = True
        return entity, None, None

    entity.exclude_from_indexes.add('mapped_circuit')
    entity['mapped_circuit'] = cirq.to_json(circuit)

    return entity, circuit, entity['repetitions']

def run_jobs(handler, circuits, repetitions):
    circuits = list(circuits)
    enginejob = handler._engine.run_batch(circuits, repetitions=max(repetitions), processor_ids=handler._processor_ids, gate_set=handler._gate_set)
    yield from ([enginejob.program_id, enginejob.job_id, i] for i in range(len(circuits)))

def finalize_job(entity, result_key):
    # update and return entity
    entity.exclude_from_indexes.add('results')
    entity['result_key'] = result_key
    entity['message'] = 'Success'
    entity['processed_timestamp'] = datetime.datetime.utcnow()
    entity['processed_version'] = os.environ.get('GAE_VERSION')
    entity['sent'] = True
    return entity

#def run(client: datastore.Client) -> str:
def run(project_id, processor_id) -> str:
    """ pull unfinished, verified jobs and run them
    Returns: 
        string message with number of jobs run
    """

    # Connect to datastore
    client = datastore.Client(project_id)

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
    query.add_filter("sent", "=", False)
    query.add_filter("verified", "=", True)

    while True:
        # get each job by key and run it in a transaction
        transaction = client.transaction()
        transaction.begin(timeout=600)

        prepared = [prepare_job(entity, device, err_qubits) for entity in query.fetch(limit=20)]
        if not prepared: break

        to_run, complete = [],[]
        for entity, circuit, repetitions in prepared:
            if circuit and repetitions:
                to_run.append((entity, circuit, repetitions))
            else:
                complete.append(entity)
        assert len(to_run) + len(complete) == len(prepared)

        if to_run:
            entities, circuits, repetitions = zip(*to_run)
            result_keys = run_jobs(handler, circuits, list(repetitions))
            complete.extend(map(finalize_job, entities, result_keys))

        #client.put_multi(complete)
        for entity in complete:
            transaction.put(entity)

        transaction.commit()

    # return number of jobs run
    return 'Jobs run: '+str(len(prepared))

if __name__ == '__main__':
    # processor id from argument
    PROJECT_ID = str(sys.argv[1])
    PROCESSOR_ID = str(sys.argv[2])

    print(run(PROJECT_ID, PROCESSOR_ID))
