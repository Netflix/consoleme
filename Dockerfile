# Dockerfile should instantiate AWS Project with configurable plugins
FROM python:3.8
MAINTAINER Curtis Castrapel
COPY . /apps/consoleme
WORKDIR /apps/consoleme
ENV SETUPTOOLS_USE_DISTUTILS=stdlib
# Install dependencies
RUN curl -sL https://deb.nodesource.com/setup_10.x | bash
RUN apt-get clean
RUN apt-get update
RUN apt-get install build-essential libxml2-dev libxmlsec1-dev libxmlsec1-openssl musl-dev libcurl4-nss-dev python3-dev nodejs -y
RUN pip install -U setuptools pip cython
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements-test.txt
RUN pip install -e .
RUN pip install -e default_plugins
RUN pip install watchdog
# Required by watchdog
RUN pip install argh

# Install frontend
RUN npm install yarn -g
RUN yarn
# Run Webpack to generate legacy Frontend / React files
RUN ./node_modules/.bin/webpack

# Install SPA frontend
RUN yarn --cwd ui
