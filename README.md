A small server, job-verifier, and job-processor for quantum programs on Google's Sycamore device, using google cloud

To run locally:

git clone --recurse-submodules https://github.com/ahirthucla/cirq_queueing_server

pip install -r requirements.txt

pip install -e quantum_circuit_multiplexers

-change GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_PROCESSOR environment variables.

python server.py


To run on gcloud:

- change GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_PROCESSOR env variables in Dockerfile
gcloud app deploy server.yaml
