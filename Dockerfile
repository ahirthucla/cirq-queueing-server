FROM gcr.io/google-appengine/python

# Create a virtualenv for dependencies. This isolates these packages from
# system-level packages.
# Use -p python3 or -p python3.7 to select python version. Default is version 2.
RUN virtualenv /env -p python3.7

# Setting these environment variables are the same as running
# source /env/bin/activate.
ENV VIRTUAL_ENV /env
ENV PATH /env/bin:$PATH
ENV GOOGLE_CLOUD_PROJECT your_project_id
ENV GOOGLE_CLOUD_PROCESSOR your_processor_id

# Add the application source code.
ADD . /app

# Run pip to install all dependencies into the virtualenv.
RUN pip install -r /app/requirements.txt
RUN pip install /app/quantum_circuit_multiplexers

# Run a WSGI server to serve the application. gunicorn must be declared as
# a dependency in requirements.txt.
CMD gunicorn -b :$PORT server:app
