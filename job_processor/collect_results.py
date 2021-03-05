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

def fill_result(entity, engine):
    program_id, job_id, index = entity['result_key']
    enginejob = engine.get_program(program_id).get_job(job_id)
    if enginejob.status() != 'Success': return entity
    entity['result'] = enginejob.batched_results()[index][0].measurements.to_json()
    entity['done'] = True
    return entity

def collect_results(project_id, processor_id) -> str:

    # Connect to datastore
    client = datastore.Client(project_id)

    # Initialize google cloud quantum engine
    engine = cirq.google.Engine(project_id=client.project)

    # pull unfinished, verified job keys
    query = client.query(kind="job")
    query.add_filter("done", "=", False)
    query.add_filter("sent", "=", True)
    query.keys_only()

    for i, key in enumerate(query.fetch()):
        with client.transaction():
            entity = client.get(key)
            entity = fill_result(entity, engine)
            client.put(entity)

    # return number of jobs run
    return 'Results updated: '+str(i+1)

if __name__ == '__main__':
    # processor id from argument
    PROJECT_ID = str(sys.argv[1])
    PROCESSOR_ID = str(sys.argv[2])

    print(collect_results(PROJECT_ID, PROCESSOR_ID))
