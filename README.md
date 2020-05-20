# ConsoleMe

ConsoleMe makes it easier to manage multiple AWS accounts. It is designed to consolidate tooling for the most common use cases around requesting access, self-service IAM,
AWS credentials, and logging into the AWS console. ConsoleMe improves user experience and insights around
console login and access requests. It offers a web interface where users can search and login to the AWS IAM roles
they have access to, and it saves previously selected roles for quicker access. It also provides a mechanism for users
to request access to Google groups. Google groups may have attributes defining who the owners and approvers of the group
are. If these are appropriately set, ConsoleMe will e-mail approvers when a request is made to a group that they own.

Editing IAM policies across multiple accounts is possible for administrators. End-users have the ability to write or
edit inline policies, and submit these to administrators to be approved and committed.

## Quick Start

Check out our Quick start guide

## Build and Run Instructions

### Prerequisites

#### MacOS

```bash
# Install Python
brew install python@3.7

# XCode Command-Line Tools
xcode-select --install

# Additional dependencies
brew install pkgconfig libxmlsec1
```

#### Linux

TODO: Needs testing

Ubuntu disco/19.04+, Debian buster/10+

```bash
# Additional dependencies
apt-get install libxmlsec1
```

### Clone the ConsoleMe repo

```bash
git clone git@github.com:Netflix-Skunkworks/consoleme.git
```

### Run dependencies

A local set of Redis and DynamoDB (local) instances need to be set up. These are provided as Docker containers. In a separate terminal window, start the local redis and dynamodb instances:

```bash
docker-compose -f docker-compose-dependencies.yaml up
```

### Run install

In repo root run `make install`. You may also want to install the default plugins if you have not developed internal plugins: `pip install -e default_plugins`

```bash
make install
```

> You will need to have AWS credentials for the installation to work (they need to be valid credentials for any
account or user for the AWS SDK to communicate with the local DynamoDB container).

### Run ConsoleMe with the default configuration

```bash
# Activate virtualenv created by `make install`
. env/bin/activate

# [Optional] Install default plugins
pip install -e default_plugins

# Run ConsoleMe
CONFIG_LOCATION=docker/example_config_header_auth.yaml python consoleme/__main__.py
```

> ConsoleMe requires Python 3.7+. If your virtualenv was installed under Python2.x
this will blow up. You can usually fix this by uninstalling and reinstalling under python3.x by removing your existing
virtualenv and creating a new one with Python 3: `python3 -m venv env`.
When the `make install` command is running, it will install all the dependencies, and it will also run ConsoleMe
Celery tasks to populate its Redis cache if necessary. This also updates the local DynamoDB instance, which persists
data on disk. This command will need to be run anytime you want to update your local cache.

### Configure your browser

Configure a header injector ([Requestly](https://www.requestly.in/) is recommended) to inject user / group headers. Your group
headers should contain a comma-separated list of google groups. You can see which headers are being passed to ConsoleMe
by visiting the `/myheaders` endpoint in ConsoleMe.

> Make sure you have at least two groups in your list, otherwise every time you visit your local consoleme Role page it will auto-login to the console with your one role.

### Browse to ConsoleMe

You should now be able to access the ConsoleMe web UI at http://localhost:8081. Success! 🎉

## Development

### Docker development

ConsoleMe can be developed solely within a docker container. Using the following command, the container will automatically be built and run. Your AWS secrets from ~/.aws/credentials will be placed on volumes in the container.

```bash
docker-compose -f docker-compose.yaml -f docker-compose-dependencies.yaml up
```

### Local DynamoDB

Running `docker-compose -f docker-compose-dependencies.yaml up` in the root directory will enable local dynamodb and local redis. To install a web interface
to assist with managing local dynamodb, install dynamodb-admin with:

```bash
npm install dynamodb-admin -g

# You need to tell dynamodb-admin which port dynamodb-local is running on when running dynamodb-admin
DYNAMO_ENDPOINT=http://localhost:8005 dynamodb-admin
```

### Update Dependencies

To update the `pip` Python dependencies, run this command:

```bash
make up-reqs
```

> If you're using Python 3.8 and trying to run this command on Mac, you may need to run
`PKG_CONFIG_PATH="/usr/local/opt/libxml2/lib/pkgconfig" make up-reqs` which forces pkgconfig to use
brew's xmlsec instead of the MacOS xmlsec (Details: https://github.com/mehcode/python-xmlsec/issues/111)

### Releases and Versioning

ConsoleMe uses [setupmeta](https://github.com/zsimic/setupmeta) for versioning, utilizing the [`devcommit` strategy](https://github.com/zsimic/setupmeta/blob/master/docs/versioning.rst#devcommit). This project adheres to [SemVer standards](https://semver.org/#summary) for major, minor, and patch versions. `setupmeta` diverges from SemVer slightly for development versions.

When you're ready to release **patch** changes on `master`:

```bash
python setup.py version --bump minor --commit --push
```

When you're ready to release **minor** changes on `master`:

```bash
python setup.py version --bump minor --commit --push
```

When you're ready to release **major** changes on `master` (rare, reserved for breaking changes):

```bash
python setup.py version --bump major --commit --push
```

### Running async functions

To run an async python function syncronously in a shell for testing:

```python
import asyncio
asyncio.get_event_loop().run_until_complete(<function>)
```


### PyCharm Unit Testing

To run tests in PyCharm, the clearly superior Python development environment, you need to update your Debug
configuration to include the following environment variables to assist with debugging:

- `CONFIG_LOCATION=/location/to/your/test.yaml` (Required)
- `ASYNC_TEST_TIMEOUT=9999999` (Optional for debugging the RESTful code)

Run `make test` or `make testhtml` to run unit tests

> Recommended: Run with the `Additional Arguments` set to `-n 4` to add some concurrency to the unit test execution.

### SAML

We're using the wonderful `kristophjunge/test-saml-idp` docker container to demonstrate an example SAML flow through ConsoleMe performed locally. The SimpleSaml configuration is not secure, and you should not use this in any sort of production environment. this is purely used as a demonstration of SAML auth within ConsoleMe.

The configuration for the SAML exists in `docker-compose-simplesaml.yaml` You can start the IDP locally with the following command ran from your `consoleme` directory:

`docker-compose -f docker-compose-saml.yaml up`

You will need to browse to the [Simplesaml metadata url](http://localhost:8080/simplesaml/saml2/idp/metadata.php?output=xml) and copy the x509 certificate
for the IDP (The first one), and replace the x509cert value specified in `docker/saml_example/settings.json`.


You can start ConsoleMe and point it to this IDP with the following command:

`CONFIG_LOCATION=docker/example_config_saml.yaml python consoleme/__main__.py`

The configuration in `docker-compose-saml.yaml` specifies the expected service provider Acs location (`http://localhost:8081/saml/acs`) and the entity ID it expects to receive ('http://localhost:8081').

A simple configuration for SimpleSaml users exists at `docker/simplesamlphp/authsources.php`. It specifies an example user (consoleme_user:consoleme_user), and an admin user (consoleme_admin:consoleme_admin).

ConsoleMe's configuration (`docker/example_config_saml.yaml`) specifies the following configuration:

`get_user_by_saml_settings.saml_path`: Location of SAML settings used by the OneLoginSaml2 library
	- You'll need to configure the entity ID, IdP Binding urls, and ACS urls in this file

`get_user_by_saml_settings.jwt`: After the user has authenticated, ConsoleMe will give them a jwt valid for the time specified in this configuration, along with the jwt attribute names for the user's email and groups.

`get_user_by_saml_settings.attributes`: Specifies the attributes that we expect to see in the SAML response, including the user's username, groups, and e-mail address

### Local development with Docker (PyCharm specific instructions)  # TODO: Docs with screenshots

It is possible to use Docker `docker-compose-test.yaml` to run ConsoleMe and its dependencies locally
in Docker with the default plugin set. Configure a new Docker Python interpreter to run __main__.py with your
working directory set to `/apps/consoleme` (on the container). This flow was tested on Windows 10.

### Generating Models from Swagger Spec

When changes are made to the Swagger spec, models may need to be regenerated using [datamodel-code-generator](https://github.com/koxudaxi/datamodel-code-generator).

```bash
pip install datamodel-code-generator
datamodel-codegen --input swagger.yaml --output consoleme/models/models.py
```

## Generate an AMI to deploy ConsoleMe to EC2

To generate an AMI, retrieve sufficiently privileged credentials locally and run `make create_ami`.
