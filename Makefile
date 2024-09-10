SHELL:=/bin/bash
project := consoleme

flake8 := flake8
pytest := PYTHONDONTWRITEBYTECODE=1 py.test --tb short \
	--cov-config .coveragerc --cov $(project) \
	--async-test-timeout=1 --timeout=30 tests

html_report := --cov-report html
test_args := --cov-report term-missing

.DEFAULT_GOAL := test-lint

# Set CONSOLEME_CONFIG_ENTRYPOINT make variable to CONSOLEME_CONFIG_ENTRYPOINT env variable, or "default_config"
CONSOLEME_CONFIG_ENTRYPOINT := $(or ${CONSOLEME_CONFIG_ENTRYPOINT},${CONSOLEME_CONFIG_ENTRYPOINT},default_config)
.PHONY: env_install
env_install:
	pip install wheel -r requirements.txt -r requirements-test.txt
	pip install -e .

.PHONY: build_ui
build_ui:
	yarn --cwd ui
	yarn --cwd ui build:prod

.PHONY: install
install: clean env_install build_ui bootstrap

.PHONY: docker_volume
docker_volume:
	if docker volume create dynamodb-data; then \
		echo "Created persistent docker volume for dynamodb."; \
	else \
		echo "Unable to configure persistent Dynamo directory. Docker must be installed on this host or container."; \
	fi

.PHONY: bootstrap
bootstrap: docker_volume dynamo redis

.PHONY: dynamo
dynamo:
	@echo "--> Configuring Dynamo (Make sure local dynamo is enabled on port 8000)"
	python scripts/initialize_dynamodb_oss.py

.PHONY: redis
redis:
	@echo "--> Configuring Redis"
	python scripts/initialize_redis_oss.py

.PHONY: test
test: clean
	ASYNC_TEST_TIMEOUT=60 CONFIG_LOCATION=example_config/example_config_test.yaml $(pytest)

.PHONY: bandit
bandit: clean
	bandit --ini tox.ini -r consoleme

.PHONY: testhtml
testhtml: clean
	ASYNC_TEST_TIMEOUT=60 CONSOLEME_CONFIG_ENTRYPOINT=$(CONSOLEME_CONFIG_ENTRYPOINT) CONFIG_LOCATION=example_config/example_config_test.yaml $(pytest) $(html_report) && open htmlcov/index.html

.PHONY: clean
clean:
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info
	rm -f celerybeat-schedule.db
	rm -f celerybeat-schedule
	rm -rf consoleme.tar.gz
	rm -rf ui/.npmrc ui/.yarnrc
	find $(project) tests -name "*.pyc" -delete
	find . -name '*.pyc' -delete
	find . -name '*.pyo' -delete
	find . -name '*.egg-link' -delete

.PHONY: lint
lint:
	$(flake8) $(project) setup.py test

.PHONY: test-lint
test-lint: test lint

.PHONY: docs
docs:
	$(MAKE) -C docs html

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
	@echo "--> Updating Python requirements"
	pip install --upgrade pip
	pip install --upgrade pip-tools
	pip install --upgrade setuptools
	pip-compile --output-file requirements.txt requirements.in -U --no-emit-index-url
	pip-compile --output-file requirements-test.txt requirements-test.in requirements.txt -U --no-emit-index-url
	pip-compile --output-file requirements-docs.txt requirements-docs.in -U --no-emit-index-url
	@echo "--> Done updating Python requirements"
	@echo "--> Installing new dependencies"
	pip install -e .
	pip install -r requirements-test.txt
	pip install -r requirements-docs.txt
	@echo "--> Done installing new dependencies"

consoleme.tar.gz: clean
	# Tar contents of the current directory
	touch consoleme.tar.gz
	tar --exclude='consoleme.tar.gz' --exclude='build*' --exclude='.tox/*' --exclude='env*' --exclude-from='.gitignore' --exclude='venv*' --exclude='node_modules*' --exclude='terraform/*' --exclude='.git/*' --exclude='.run/*' --exclude='debian*' --exclude='staging*' -czf consoleme.tar.gz .

.PHONY: create_ami
create_ami: consoleme.tar.gz packer clean

.PHONY: packer
packer:
ifdef CONFIG_LOCATION
	@echo "--> Using configuration at $(CONFIG_LOCATION)"
	export CONFIG_LOCATION=$(CONFIG_LOCATION)
endif
ifdef CONSOLEME_CONFIG_ENTRYPOINT
	@echo "--> Using configuration entrypoint at at $(CONSOLEME_CONFIG_ENTRYPOINT)"
	export CONSOLEME_CONFIG_ENTRYPOINT=$(CONSOLEME_CONFIG_ENTRYPOINT)
endif
	# Call Packer to build AMI
	packer build --debug -var 'app_archive=consoleme.tar.gz' packer/create_consoleme_ami.json

.PHONY: packer_ubuntu_oss
packer_ubuntu_oss: ubuntu_redis env_install

.PHONY: ubuntu_redis
ubuntu_redis:
ifdef CONFIG_LOCATION
	@echo "--> Using configuration at $(CONFIG_LOCATION)"
	export CONFIG_LOCATION=$(CONFIG_LOCATION)
endif
ifdef CONSOLEME_CONFIG_ENTRYPOINT
	@echo "--> Using configuration entrypoint at at $(CONSOLEME_CONFIG_ENTRYPOINT)"
	export CONSOLEME_CONFIG_ENTRYPOINT=$(CONSOLEME_CONFIG_ENTRYPOINT)
endif
	sudo apt-get install -y redis-server
	sudo systemctl enable redis-server.service
	sudo systemctl restart redis-server.service
