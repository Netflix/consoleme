# FAQ

## How do I override one of ConsoleMe's web routes, or add new routes just for my internal implementation of ConsoleMe?

You can add new routes or override existing routes in your implementation of ConsoleMe through the use of an internal plugin. ConsoleMe provides a set of default plugins that serve as an example of how you should implement your internal plugins.

Included in the default\_plugins set is a list of [internal routes](https://github.com/Netflix/consoleme/blob/master/consoleme/default_plugins/consoleme/plugins/internal_routes/internal_routes.py) and an example [web handler](https://github.com/Netflix/consoleme/blob/master/consoleme/default_plugins/plugins/internal_routes/handlers/internal_demo_route.py#L9). The routes defined here will take precedence over ConsoleMe's [default routes](https://github.com/Netflix/consoleme/blob/master/consoleme/routes.py#L91).

## How can I generate an AMI for ConsoleMe so I can deploy it to EC2?

We provide an example flow to generating an AMI based on ConsoleMe's default configuration. This should serve as a reference for you to create your own AMI. Here are the general steps you'd need to follow to get this running today. We are looking for contributions to make this process smoother:

1. Install Packer with the guidance [here](https://learn.hashicorp.com/tutorials/packer/getting-started-install).
2. Retrieve AWS credentials locally \(Place them in your ~/.aws/credentials file under the default profile, or set them as environment variables\)
3. Place your custom configuration in a file called `consoleme.yaml` in your ConsoleMe directory
4. Run `make create_ami`from your ConsoleMe directory. This process will compress the current directory and create an Ubuntu AMI for ConsoleMe

## How do I generate models from the Swagger specification?

We use [datamodel-code-generator](https://github.com/koxudaxi/datamodel-code-generator) to generate Pydantic models for ConsoleMe.

If you make changes to [ConsoleMe's Swagger specification](https://github.com/Netflix/consoleme/blob/master/swagger.yaml), you'll need to re-generate the [Pydantic Models file ](https://github.com/Netflix/consoleme/blob/master/consoleme/models.py)with the following command:

```text
 datamodel-codegen --target-python-version 3.8 --base-class consoleme.lib.pydantic.BaseModel --input swagger.yaml --output consoleme/models.py
```

## How do I debug the unit tests?

To run tests in PyCharm, the clearly superior Python development environment, you need to update your Debug configuration to include the following environment variables to assist with debugging:

* `CONFIG_LOCATION=example_config/example_config_test.yaml` \(Required\)
* `ASYNC_TEST_TIMEOUT=3600` \(Optional for debugging the RESTful code without having to worry about timeouts\)

Run `make test` or `make testhtml` to run unit tests

## How do I release a new version of ConsoleMe

ConsoleMe uses [setupmeta](https://github.com/zsimic/setupmeta) for versioning, utilizing the [`devcommit` strategy](https://github.com/zsimic/setupmeta/blob/master/docs/versioning.rst#devcommit). This project adheres to [SemVer standards](https://semver.org/#summary) for major, minor, and patch versions. `setupmeta` diverges from SemVer slightly for development versions.

When you're ready to release **patch** changes on `master`:

```bash
python setup.py version --bump minor --commit --push
```

When you're ready to release **minor** changes on `master`:

```bash
python setup.py version --bump minor --commit --push
```

When you're ready to release **major** changes on `master` \(rare, reserved for breaking changes\):

```bash
python setup.py version --bump major --commit --push
```

## How do I update ConsoleMe's Python dependencies?

To update Python dependencies, run this command:

```bash
make up-reqs
```

> If you're using Python 3.8 and trying to run this command on Mac, you may need to run `PKG_CONFIG_PATH="/usr/local/opt/libxml2/lib/pkgconfig" make up-reqs` which forces pkgconfig to use brew's xmlsec instead of the MacOS xmlsec \(Details: [https://github.com/mehcode/python-xmlsec/issues/111](https://github.com/mehcode/python-xmlsec/issues/111)\)

If an updated package causes an incompatibility issue, please identify the issue, pin the older version in ConsoleMe's [requirements.in](https://github.com/Netflix/consoleme/blob/master/requirements.in) file, and add a comment identifying the issue you encountered.

## How can I run and debug my local DynamoDB container?

Running `docker-compose -f docker-compose-dependencies.yaml up` in the root directory will enable local dynamodb and local Redis.

To install a web interface to assist with managing local dynamodb, install dynamodb-admin with the following command, then visit [http://localhost:8001](http://localhost:8001) to view the contents of your local DynamoDB.

```bash
npm install dynamodb-admin -g

# You need to tell dynamodb-admin which port dynamodb-local is running on when running dynamodb-admin
DYNAMO_ENDPOINT=http://localhost:8005 dynamodb-admin
```

