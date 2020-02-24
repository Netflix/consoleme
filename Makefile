SHELL:=/bin/bash
project := consoleme

flake8 := flake8
pytest := PYTHONDONTWRITEBYTECODE=1 py.test --tb short \
	--cov-config .coveragerc --cov $(project) \
	--async-test-timeout=1 --timeout=30 tests

html_report := --cov-report html
test_args := --cov-report term-missing

.DEFAULT_GOAL := test-lint

env/bin/activate:
ifndef CONDA_SHLVL
	# If using Conda for environments, don't create a virtualenv
	virtualenv -p $(shell which python3) env
else
    VIRTUAL_ENV := $(shell which python3)
endif

prod_install:
env_install: env/bin/activate
	# Activate either the virtualenv in env/ or tell conda to activate
	. env/bin/activate || source activate consoleme;\
	pip install -r requirements.txt ;\
	pip install -r requirements-test.txt ;\
	python setup.py develop

.PHONY: install
install: clean
	make env_install
	make bootstrap

.PHONY: bootstrap
bootstrap:
	docker volume create dynamodb-data
	make dynamo
	make redis

.PHONY: dynamo
dynamo:
	@echo "--> Configuring Dynamo (Make sure local dynamo is enabled on port 8000)"
	. env/bin/activate || source activate consoleme;\
	python scripts/initialize_dynamodb_oss.py

.PHONY: redis
redis:
	@echo "--> Configuring Redis"
	. env/bin/activate || source activate consoleme;\
	python scripts/initialize_redis_oss.py

.PHONY: test
test: clean
ifndef VIRTUAL_ENV
	$(error Please activate virtualenv first)
endif
ifndef CONFIG_LOCATION
	CONFIG_LOCATION=../consoleme-deploy/root/etc/consoleme/config/test.yaml $(pytest)
else
	export CONFIG_LOCATION=$(CONFIG_LOCATION); $(pytest)
endif

.PHONY: bandit
bandit: clean
	bandit --ini tox.ini -r consoleme

.PHONY: testhtml
testhtml: clean
	. env/bin/activate || source activate consoleme;\
	CONFIG_LOCATION=../consoleme-deploy/root/etc/consoleme/config/test.yaml $(pytest) $(html_report) && open htmlcov/index.html

.PHONY: clean
clean:
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info
	rm -f celerybeat-schedule.db
	find $(project) tests -name "*.pyc" -delete
	find . -name '*.pyc' -delete
	find . -name '*.pyo' -delete
	find . -name '*.egg-link' -delete

.PHONY: lint
lint:
	. env/bin/activate || source activate consoleme;\
	$(flake8) $(project) setup.py test

.PHONY: test-lint
test-lint: test lint

.PHONY: docs
docs:
	make -C docs html

.PHONY: docsopen
docsopen: docs
	open docs/_build/html/index.html

.PHONY: deps
deps: requirements.txt requirements-docs.txt requirements-test.txt
	pip-sync requirements.txt requirements-docs.txt requirements-test.txt

requirements.txt: requirements.in
	pip-compile --no-index requirements.in
	# Workaround for https://github.com/nvie/pip-tools/issues/325
	sed -i .txt '/-e /c\ ' requirements.txt

requirements-docs.txt: requirements-docs.in
	pip-compile --no-index requirements-docs.in

up-reqs: clean
ifndef VIRTUAL_ENV
	$(error Please activate virtualenv first)
endif
	@echo "--> Updating Python requirements"
	pip install --upgrade pip
	pip install --upgrade pip-tools
	pip install --upgrade setuptools
	pip-compile --output-file requirements.txt requirements.in -U --no-index
	pip-compile --output-file requirements-test.txt requirements-test.in -U --no-index
	pip-compile --output-file requirements-docs.txt requirements-docs.in -U --no-index
	@echo "--> Done updating Python requirements"
	@echo "--> Installing new dependencies"
	pip install -e .
	pip install -r requirements-test.txt
	pip install -r requirements-docs.txt
	@echo "--> Done installing new dependencies"