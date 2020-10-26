# Local Development

ConsoleMe requires Python 3.7 or above. Crude installation instructions are below. This documentation is in dire need of improvement.

#### MacOS

```text
# Install Python, Yarn, libxmlsec1, and other dependencies
brew install python@3.8 yarn pkgconfig libxmlsec1

# XCode Command-Line Tools
xcode-select --install
```

#### Linux

Ubuntu disco/19.04+, Debian buster/10+

```text
# Additional dependencies
apt-get install build-essential libxml2-dev libxmlsec1 libxmlsec1-dev libxmlsec1-openssl musl-dev libcurl4-nss-dev python3-dev -y
```

**Clone the ConsoleMe repo**

Clone ConsoleMe locally in a directory of your choosing:

```text
git clone git@github.com:Netflix/consoleme.git ; cd consoleme
```

**Start Redis and DynamoDB containers**

A local set of Redis and DynamoDB \(local\) instances need to be set up. These are provided as Docker containers. In a separate terminal window, start the local redis and dynamodb instances:

```text
docker-compose -f docker-compose-dependencies.yaml up -d
```

**Get access to administrative credentials on your account**

For an initial setup, we advise making an IAM user with sufficient privileges to allow ConsoleMe to sync your IAM roles, S3 buckets, SQS queues, SNS topics, and AWS Config data. Sections below outline the required permissions. See [this page](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html) for configuring your user credentials. Note: After you have ConsoleMe set up, you should no longer need IAM user credentials. Please set a reminder to delete these when you're done with them.

**Make a virtual environment and run the installation script**

In repo root run `make install`. You may also want to install the default plugins if you have not developed internal plugins: `pip install -e default_plugins`

```text
# Make a Python 3.8 Virtual Environment using your preferred method. Here's a standard way of doing it:
python3 -m venv env

# Activate virtualenv
. env/bin/activate

make install
# The `make install` step runs the following commands, and attempts to create local dynamo tables:
#
# pip install -r requirements.txt -r requirements-test.txt -e default_plugins -e .
# yarn
# node_modules/webpack/bin/webpack.js --progress
# python scripts/initialize_dynamodb_oss.py
# python scripts/initialize_redis_oss.py
```

> You will need to have AWS credentials for the installation to work \(they need to be valid credentials for any account or user for the AWS SDK to communicate with the local DynamoDB container\).

**Run ConsoleMe with the default configuration**

```text
# Run ConsoleMe
python consoleme/__main__.py
```

> ConsoleMe requires Python 3.7+. If your virtualenv was installed under Python2.x this will blow up. You can usually fix this by uninstalling and reinstalling under python3.x by removing your existing virtualenv and creating a new one with Python 3: `python3 -m venv env`. When the `make install` command is running, it will install all the dependencies, and it will also run ConsoleMe Celery tasks to populate its Redis cache if necessary. This also updates the local DynamoDB instance, which persists data on disk. This command will need to be run anytime you want to update your local cache.

#### Configure your browser

You can either use the `example_config/example_config_development.yaml` as your configuration to override the user you are authenticated as for development, or you can Configure a header injector such as [Requestly](https://www.requestly.in/) to inject user / group headers. By default, the header names are in your configuration file. In our example configurations, they are specified in `example_config_base.yaml` under the `auth.user_header_name` and `auth.groups_header_name` keys. The user header should be an email address, i.e. `you@example.com`. The groups header should be a list of comma-separated groups that you are a member of, i.e. `group1@example.com,group2@example.com,groupx@example.com`. You can see which headers are being passed to ConsoleMe by visiting the [`/myheaders` endpoint](http://localhost:8081/myheaders) in ConsoleMe.

> Make sure you have at least two groups in your list, otherwise every time you visit your local consoleme Role page it will auto-login to the console with your one role.

#### Browse to ConsoleMe

You should now be able to access the ConsoleMe web UI at [http://localhost:8081](http://localhost:8081/). Success! 🎉

