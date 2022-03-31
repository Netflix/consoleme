---
description: Provides instructions for getting ConsoleMe up and running locally.
---

# Local

ConsoleMe requires Python 3.8 or above. Install [**git**](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git), [**docker**](https://docs.docker.com/get-docker/), and [**docker-compose**](https://docs.docker.com/compose/install/) \_\*\*\_on your system, consider following [Docker's post-installation steps for Linux](https://docs.docker.com/engine/install/linux-postinstall/), then clone ConsoleMe locally in a directory of your choosing via HTTP or SSH:

## MacOS

```text
# Install Python, Yarn, libxmlsec1, and other dependencies
brew install python@3.8 yarn pkgconfig libxmlsec1

# XCode Command-Line Tools
xcode-select --install
```

## Linux

Ubuntu disco/19.04+, Debian buster/10+

```text
# Additional dependencies
sudo apt-get install build-essential libxml2-dev libxmlsec1 libxmlsec1-dev libxmlsec1-openssl musl-dev libcurl4-nss-dev python3-dev pkg-config -y
# Nodejs/Yarn (Frontend dependencies)
curl -sL https://deb.nodesource.com/setup_14.x | sudo bash
sudo apt-get install -y nodejs
sudo npm install yarn -g
```

**Clone the ConsoleMe repo**

Clone ConsoleMe locally in a directory of your choosing:

```text
# If you have a fork, you'll want to clone it instead
git clone https://github.com/Netflix/consoleme.git ; cd consoleme
# OR # 
git clone git@github.com:Netflix/consoleme.git ; cd consoleme
```

**Start Redis and DynamoDB containers**

A local set of Redis and DynamoDB \(local\) instances need to be set up. These are provided as Docker containers. In a separate terminal window, start the local Redis and dynamodb instances:

```text
docker-compose -f docker-compose-dependencies.yaml up -d
```

**Get access to administrative credentials on your account**

For an initial setup, we advise making an IAM user with sufficient privileges to allow ConsoleMe to sync your IAM roles, S3 buckets, SQS queues, SNS topics, and AWS Config data. Sections below outline the required permissions. See [this page](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html) for configuring your user credentials.

{% hint style="info" %}
After you have ConsoleMe set up, you should no longer need IAM user credentials. Please set a reminder to delete these when you're done with them.
{% endhint %}

**Make a virtual environment and run the installation script**

In repo root run `make install`. Ensure that you have valid AWS credentials so that ConsoleMe can cache your resources.

```text
# Make a Python 3.8 Virtual Environment using your preferred method. Here's a standard way of doing it:
python3 -m venv env
. env/bin/activate

# Ensure that you have valid AWS credentials before running `make install`
make install

# The `make install` step runs the following commands, and attempts to create local dynamo tables:
#
# pip install -r requirements.txt -r requirements-test.txt -e .
# yarn --cwd ui
# yarn --cwd ui build:prod
# python scripts/initialize_dynamodb_oss.py
# python scripts/initialize_redis_oss.py
```

**Run ConsoleMe's backend with the default configuration**

```text
# Run ConsoleMe
python consoleme/__main__.py
# You should be able to visit Consoleme's Web UI at http://localhost:8081
```

```text
# (Optional) Run ConsoleMe's UI through Yarn for local UI development
cd ui ; yarn start
# If you follow this step, you should be able to see the UI at http://localhost:3000
```

```text
# (Optional) Run Celery for local development
cd /home/service/consoleme ; celery -A consoleme.celery_tasks.celery_tasks worker -l DEBUG -B -E --concurrency=8
# If you follow this step, you should be able to see Celery is running
```

> ConsoleMe requires Python 3.8+. If your virtualenv was installed under Python2.x this will blow up. You can usually fix this by uninstalling and reinstalling under python3.x by removing your existing virtualenv and creating a new one with Python 3: `python3 -m venv env`. When the `make install` command is running, it will install all the dependencies, and it will also run ConsoleMe Celery tasks to populate its Redis cache if necessary. This also updates the local DynamoDB instance, which persists data on disk. This command will need to be run anytime you want to update your local cache. In a production environment, you'd be running Celery, which has scheduled tasks that would update your resource cache automatically.

For local, unauthenticated development, the default configuration \([`example_config/example_config_development.yaml`](https://github.com/Netflix/consoleme/blob/master/example_config/example_config_development.yaml) \) will override the user you are authenticated as for development.

## Browse to ConsoleMe

You should now be able to access the ConsoleMe web UI at [http://localhost:8081/](http://localhost:8081/) \(Or [http://localhost:3000](http://localhost:3000) if you ran `cd ui ; yarn start`\).

You'll notice that you're unable to access any IAM roles with the default configuration. You'll need to follow the guidance under [Role Credential Authorization](../configuration/role-credential-authorization/) to grant access to role credentials to your users and/or the groups they are members of.

## Create your Configuration

At this point, you'll want to configure ConsoleMe to suit your needs. Read up on [ConsoleMe’s yaml configuration.](../configuration/) ConsoleMe can be configured to [authenticate your users via SAML, OIDC, header authentication, or it can bypass authentication altogether](../configuration/authentication-and-authorization/). We have a script that can help you generate your ConsoleMe configuration. Read more about that in our [Configuration FAQ](../configuration/#configuring-consoleme-is-complicated-is-there-something-that-can-help-me-generate-a-configuration).

Then, set the `CONFIG_LOCATION` environment variable to the full path of your configuration file, or copy the configuration to one of the locations ConsoleMe will load from \(described [here](../configuration/#how-does-consoleme-determine-its-configuration)\).

