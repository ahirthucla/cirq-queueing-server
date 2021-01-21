from google.cloud import datastore
import cirq
from cirq.contrib.qasm_import import circuit_from_qasm, QasmException

client = datastore.Client()

#engine = cirq.google.Engine(project_id='PROJECT_ID')
#handler = engine.sampler(processor_id='PROCESSOR_ID', gate_set=cg.SYC_GATESET)

handler = cirq.Simulator()

def run_job(entity):
    if entity['done']:
        assert 'results' in entity
        return entity

    try:
        circuit = circuit_from_qasm(entity['qasm'])
    except QasmException as e:
        result = 'Error converting QASM string to circuit:\n' +\
                            'Exception Observed:\n'+\
                            str(e)+'\n'+\
                            'With QASM string:\n'+\
                            str(entity['qasm'])
        entity['done'] = True
        entity['results'] = result
        return entity
    
    try:
        result = handler.run(circuit, repetitions=int(entity['shots']))
        result = str(result)
    except Exception as e:
        result = "Error running circuit:\n"+\
                 "Exception Observed:\n"+\
                 str(e)

    entity['done'] = True
    entity['results'] = result
    return entity

def run():
    query = client.query(kind="job")
    query.keys_only()
    query.add_filter("done", "=", False)
    keys = list(query.fetch())
    for key in keys:
        with client.transaction():
            entity = client.get(key.key)
            entity = run_job(entity)
            client.put(entity)
    return len(keys)

if __name__ == '__main__':
    run()
