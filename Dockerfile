# Dockerfile should instantiate AWS Project with configurable plugins
FROM python:3.8-slim as python-builder

WORKDIR /apps/consoleme
ENV SETUPTOOLS_USE_DISTUTILS=stdlib

# Install dependencies
RUN apt-get clean && \
    apt-get update && \
    apt-get install build-essential pkg-config libxml2-dev libxmlsec1-dev libxmlsec1-openssl musl-dev libcurl4-nss-dev python3-dev nodejs -y && \
    pip install -U setuptools pip cython

RUN python -m venv /opt/venv
# Make sure we use the virtualenv:
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt /apps/consoleme
COPY requirements-test.txt /apps/consoleme

RUN pip install -r requirements.txt

COPY . /apps/consoleme
RUN pip install -e .
RUN pip install -e default_plugins

## UI
FROM node:14-slim as node-builder

# NODE_OPTIONS meeded to increase memory size of Node for the `yarn build` step. The Monaco Editor
# appears to be the culprit requiring this.
ENV NODE_OPTIONS="--max-old-space-size=20000"

WORKDIR /apps/consoleme/ui
RUN mkdir -p /apps/consoleme/consoleme/templates
ADD ui /apps/consoleme/ui

# Install SPA frontend
RUN yarn install && yarn build:prod

# Development container
FROM python-builder as development

RUN \
  apt-get install -yqq curl && \
  echo "deb https://deb.nodesource.com/node_14.x buster main" > /etc/apt/sources.list.d/nodesource.list && \
  curl https://deb.nodesource.com/gpgkey/nodesource.gpg.key | apt-key add - && \
  echo "deb https://dl.yarnpkg.com/debian/ stable main" > /etc/apt/sources.list.d/yarn.list && \
  curl https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add - && \
  apt-get update && \
  apt-get install -yqq nodejs yarn

RUN pip install -r requirements-test.txt
RUN pip install watchdog argh

COPY . /apps/consoleme
COPY --from=python-builder /opt/venv /opt/venv
COPY --from=node-builder /apps/consoleme/ui/node_modules /apps/consoleme/ui/node_modules
COPY --from=node-builder /apps/consoleme/consoleme/templates /apps/consoleme/consoleme/templates

ENV PATH="/opt/venv/bin:$PATH"
CMD python scripts/retrieve_or_decode_configuration.py ; python /apps/consoleme/consoleme/__main__.py

EXPOSE 8081

# Final container
FROM python:3.8-slim
LABEL org.opencontainers.image.authors="Curtis Castrapel"

WORKDIR /apps/consoleme

COPY . /apps/consoleme
COPY --from=python-builder /opt/venv /opt/venv
COPY --from=node-builder /apps/consoleme/consoleme/templates /apps/consoleme/consoleme/templates

ENV PATH="/opt/venv/bin:$PATH"
CMD python scripts/retrieve_or_decode_configuration.py ; python /apps/consoleme/consoleme/__main__.py

EXPOSE 8081
