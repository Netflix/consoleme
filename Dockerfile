# Dockerfile should instantiate AWS Project with configurable plugins
FROM python:3.8
MAINTAINER Curtis Castrapel
WORKDIR /apps/consoleme
# NODE_OPTIONS meeded to increase memory size of Node for the `yarn build` step. The Monaco Editor
# appears to be the culprit requiring this.
ENV NODE_OPTIONS="--max-old-space-size=20000"
ENV SETUPTOOLS_USE_DISTUTILS=stdlib

# Install OS dependencies
RUN curl -sL https://deb.nodesource.com/setup_14.x | bash
RUN apt-get clean
RUN apt-get update
RUN apt-get install build-essential libxml2-dev libxmlsec1-dev libxmlsec1-openssl musl-dev libcurl4-nss-dev python3-dev nodejs -y

# Install python dependencies
COPY requirements.txt requirements-test.txt setup.py /apps/consoleme/
COPY default_plugins /apps/consoleme/default_plugins/

RUN pip install -U setuptools pip cython
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r requirements-test.txt
RUN pip install -e .
RUN pip install -e default_plugins
# Install watchdog. Used to automatically restart ConsoleMe in Docker, for development.
RUN pip install watchdog argh

# Install SPA frontend
COPY ui /apps/consoleme/ui/
RUN mkdir /apps/consoleme/consoleme
RUN npm install yarn -g
RUN yarn --cwd ui
RUN yarn --cwd ui build:prod

# Run ConsoleMe tornado server using configuration
COPY consoleme /apps/consoleme/consoleme/
CMD python scripts/retrieve_or_decode_configuration.py ; python /apps/consoleme/consoleme/__main__.py

EXPOSE 8081
