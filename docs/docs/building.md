## Building

# OS X

1. Setup prerequisites

   1. Set up Python 3.7.2+ (`brew install python@3.7`)
   1. Install Xcode and ensure the command-line tools are installed (`xcode-select --install`)
   1. `brew install pkgconfig`
   1. `brew install libxmlsec1`
   1. [Install Docker and Docker-Compose](https://github.com/Yelp/docker-compose/blob/master/docs/install.md)

1. Clone the ConsoleMe repo: `git clone git@github.com:Netflix/consoleme.git`

1. A local set of Redis and DynamoDB (local) instances need to be set up. This is provided as a Docker container.
   In a separate terminal window, start the local Redis and Dynamodb instances: `docker-compose up`.

1. Create the virtualenv and activate it using your preferred method.
   Here's the standard way: `python3.7 -m venv env && source env/bin/activate`

1. You will need to have AWS credentials for the installation to work (they need to be valid credentials for any
   account or user for the AWS SDK to communicate with the local DynamoDB container). Configure these in your
   ~/.aws/credentials file or as environment variables. [Instructions](https://docs.aws.amazon.com/cli/latest/topic/config-vars.html#credentials)

1. Install the default_plugins package within ConsoleMe if you
   have not developed custom internal plugins: `pip install -e default_plugins`

1. In repo root run `make install`.

1. Run ConsoleMe with the default configuration:
   `CONSOLEME_CONFIG_ENTRYPOINT=default_config CONFIG_LOCATION=docker/example_config_header_auth.yaml python consoleme/__main__.py`
   _ Note: ConsoleMe requires Python 3.6+. We recommend running on 3.7. If your virtualenv was installed under Python2.x
   this will blow up. You can usually fix this by uninstalling and reinstalling under python3.x by removing your existing
   virtualenv and creating a new one with Python 3: `python3.7 -m venv env`.
   _ When the `make install` command is running, it will install all the dependencies, and it will also run ConsoleMe
   Celery tasks to populate its Redis cache if necessary. This also updates the local DynamoDB instance, which persists
   data on disk. This command will need to be run anytime you want to update your local cache.

1. Configure your browser header injector ([Requestly](https://www.requestly.in/) is recommended) to inject
   user / group headers. Your group headers should contain a comma-separated list of google or AD groups.
   You can see which headers are being passed to ConsoleMe by visiting the `/myheaders` endpoint in ConsoleMe. \* Note: Make sure you have at least two groups in your list, otherwise every time you visit your local Consoleme
   Role page it will auto-login to the console with your one role.
