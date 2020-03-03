# Dockerfile should instantiate AWS Project with configurable plugins
FROM python:3.7
MAINTAINER Curtis Castrapel
COPY . /apps/consoleme
WORKDIR /apps/consoleme
RUN apt update
RUN apt install build-essential libxml2-dev libxmlsec1-dev libxmlsec1-openssl musl-dev -y
RUN pip install -U setuptools pip cython
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements-test.txt
RUN pip install -e .
RUN pip install -e default_plugins
RUN pip install watchdog
# Required by watchdog
RUN pip install argh