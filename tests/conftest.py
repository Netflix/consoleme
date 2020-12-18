import asyncio
import json
import os
import random
import unittest
from datetime import datetime, timedelta

import boto3
import pytest
import redislite
from mock import MagicMock, Mock, patch
from mockredis import mock_strict_redis_client
from moto import (
    mock_config,
    mock_dynamodb2,
    mock_iam,
    mock_s3,
    mock_ses,
    mock_sns,
    mock_sqs,
    mock_sts,
)
from tornado.concurrent import Future

# This must be set before loading ConsoleMe's configuration

os.environ["CONFIG_LOCATION"] = "example_config/example_config_test.yaml"
from consoleme.config import config  # noqa: E402

MOCK_ROLE = {
    "arn": "arn:aws:iam::123456789012:role/FakeRole",
    "name": "FakeRole",
    "accountId": "123456789012",
    "ttl": 1557325374,
    "policy": {
        "Path": "/",
        "RoleId": "ABCDEFG",
        "Arn": "arn:aws:iam::123456789012:role/FakeRole",
        "CreateDate": "2019-01-15T22:55:53Z",
        "AssumeRolePolicyDocument": {
            "Version": "2008-10-17",
            "Statement": [
                {
                    "Sid": "2",
                    "Effect": "Allow",
                    "Principal": {"AWS": "arn:aws:iam::123456789012:role/FakeRole"},
                    "Action": "sts:AssumeRole",
                },
                {
                    "Sid": "1",
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": "arn:aws:iam::123456789012:role/ConsoleMeInstanceProfile"
                    },
                    "Action": "sts:AssumeRole",
                },
            ],
        },
        "Tags": [],
        "AttachedManagedPolicies": [
            {
                "PolicyName": "test1-Example.com",
                "PolicyArn": "arn:aws:iam::123456789012:policy/testPolicy",
            }
        ],
        "InstanceProfileList": [],
        "RolePolicyList": [
            {
                "PolicyName": "iam",
                "PolicyDocument": {
                    "Statement": [
                        {
                            "Action": [
                                "iam:GetAccountAuthorizationDetails",
                                "iam:GetRole",
                                "iam:GetRolePolicy",
                                "iam:ListInstanceProfiles",
                                "iam:ListInstanceProfilesForRole",
                                "iam:ListRolePolicies",
                                "iam:ListRoles",
                                "iam:ListAttachedRolePolicies",
                                "iam:ListRoleTags",
                                "s3:listallmybuckets",
                                "sqs:ListQueues",
                                "sqs:getqueueattributes",
                                "sns:ListTopics",
                            ],
                            "Effect": "Allow",
                            "Resource": ["*"],
                            "Sid": "iam",
                        }
                    ],
                    "Version": "2012-10-17",
                },
            }
        ],
    },
    "templated": "fake/file.json",
}

MOCK_REDIS_DB_PATH = "/tmp/consoleme_unit_test.rdb"
if os.path.exists(MOCK_REDIS_DB_PATH):
    os.remove(MOCK_REDIS_DB_PATH)
if os.path.exists(f"{MOCK_REDIS_DB_PATH}.settings"):
    os.remove(f"{MOCK_REDIS_DB_PATH}.settings")

all_roles = None


class AioTestCase(unittest.TestCase):

    # noinspection PyPep8Naming
    def __init__(self, methodName="runTest", loop=None):
        self.loop = loop or asyncio.get_event_loop()
        self._function_cache = {}
        super(AioTestCase, self).__init__(methodName=methodName)

    def coroutine_function_decorator(self, func):
        def wrapper(*args, **kw):
            return self.loop.run_until_complete(func(*args, **kw))

        return wrapper

    def __getattribute__(self, item):
        attr = object.__getattribute__(self, item)
        if asyncio.iscoroutinefunction(attr):
            if item not in self._function_cache:
                self._function_cache[item] = self.coroutine_function_decorator(attr)
            return self._function_cache[item]
        return attr


class MockBaseHandler:
    async def authorization_flow(
        self, user=None, console_only=True, refresh_cache=False
    ):
        self.user = "test@domain.com"
        self.ip = "1.2.3.4"
        self.groups = ["group1", "group2"]
        self.contractor = False
        self.red = mock_strict_redis_client()


class MockBaseMtlsHandler:
    async def authorization_flow_user(self):
        self.request_uuid = 1234
        self.ip = "1.2.3.4"
        self.requester = {"type": "user"}

    async def authorization_flow_app(self):
        self.request_uuid = 1234
        self.ip = "1.2.3.4"
        self.requester = {"type": "application", "name": "fakeapp"}


class MockAuth:
    def __init__(
        self, restricted=False, compliance_restricted=False, get_groups_val=None
    ):
        if get_groups_val is None:
            get_groups_val = []
        self.restricted = restricted
        self.compliance_restricted = compliance_restricted
        self.get_groups_val = get_groups_val

    async def get_groups(self, *kvargs):
        return self.get_groups_val


class MockRedis:
    def __init__(self, return_value=None):
        self.return_value = return_value

    def get(self, tag):
        print(f"MockRedis GET called with argument {tag}")
        return self.return_value

    def setex(self, *args):
        print(f"MockRedis SETEX called with args {args}")

    def hgetall(self, *args):
        print(f"MockRedis HGETALL called with args {args}")
        return self.return_value


class MockRedisHandler:
    def __init__(self, return_value=None):
        self.return_value = return_value

    async def redis(self):
        redis_client = MockRedis(return_value=self.return_value)
        return redis_client


mock_accountdata_redis = MagicMock(
    return_value=MockRedisHandler(
        return_value=json.dumps(
            {"123456789012": ["awsaccount", "awsaccount@example.com"]}
        )
    )
)


class AWSHelper:
    async def random_account_id(self):
        return str(random.randrange(100000000000, 999999999999))


@pytest.fixture(scope="session")
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"


@pytest.fixture(autouse=True, scope="session")
def sts(aws_credentials):
    """Mocked STS Fixture."""
    with mock_sts():
        yield boto3.client("sts", region_name="us-east-1")


@pytest.fixture(autouse=True, scope="session")
def iam(aws_credentials):
    """Mocked IAM Fixture."""
    with mock_iam():
        yield boto3.client("iam", region_name="us-east-1")


@pytest.fixture(autouse=True, scope="session")
def aws_config(aws_credentials):
    """Mocked Config Fixture."""
    with mock_config():
        yield boto3.client("config", region_name="us-east-1")


@pytest.fixture(autouse=True, scope="session")
def s3(aws_credentials):
    """Mocked S3 Fixture."""
    with mock_s3():
        yield boto3.client("s3", region_name="us-east-1")


@pytest.fixture(autouse=True, scope="session")
def ses(aws_credentials):
    """Mocked SES Fixture."""
    with mock_ses():
        client = boto3.client("ses", region_name="us-east-1")
        client.verify_email_address(EmailAddress="consoleme_test@example.com")
        yield client


@pytest.fixture(autouse=True, scope="session")
def sqs(aws_credentials):
    """Mocked SQS Fixture."""
    with mock_sqs():
        yield boto3.client("sqs", region_name="us-east-1")


@pytest.fixture(autouse=True, scope="session")
def sns(aws_credentials):
    """Mocked S3 Fixture."""
    with mock_sns():
        yield boto3.client("sns", region_name="us-east-1")


@pytest.fixture(autouse=True, scope="session")
def create_default_resources(s3, iam, redis, iam_sync_roles, iamrole_table):
    from asgiref.sync import async_to_sync

    from consoleme.lib.cache import store_json_results_in_redis_and_s3

    global all_roles
    buckets = [config.get("cache_roles_across_accounts.all_roles_combined.s3.bucket")]
    for bucket in buckets:
        s3.create_bucket(Bucket=bucket)

    if all_roles:
        async_to_sync(store_json_results_in_redis_and_s3)(
            all_roles,
            s3_bucket=config.get(
                "cache_roles_across_accounts.all_roles_combined.s3.bucket"
            ),
            s3_key=config.get("cache_roles_across_accounts.all_roles_combined.s3.file"),
        )
        return
    from consoleme.celery.celery_tasks import cache_roles_for_account
    from consoleme.lib.account_indexers import get_account_id_to_name_mapping
    from consoleme.lib.redis import RedisHandler

    red = RedisHandler().redis_sync()

    accounts_d = async_to_sync(get_account_id_to_name_mapping)()
    for account_id in accounts_d.keys():
        cache_roles_for_account(account_id)

    cache_key = config.get("aws.iamroles_redis_key", "IAM_ROLE_CACHE")
    all_roles = red.hgetall(cache_key)
    async_to_sync(store_json_results_in_redis_and_s3)(
        all_roles,
        s3_bucket=config.get(
            "cache_roles_across_accounts.all_roles_combined.s3.bucket"
        ),
        s3_key=config.get("cache_roles_across_accounts.all_roles_combined.s3.file"),
    )


@pytest.fixture(autouse=True, scope="session")
def dynamodb(aws_credentials):
    """Mocked DynamoDB Fixture."""
    with mock_dynamodb2():
        # Remove the config value for the DynamoDB Server
        from consoleme.config.config import CONFIG

        old_value = CONFIG.config.pop("dynamodb_server", None)

        yield boto3.client("dynamodb", region_name="us-east-1")

        # Reset the config value:
        CONFIG.config["dynamodb_server"] = old_value


@pytest.fixture(autouse=True, scope="session")
def retry():
    """Mock the retry library so that it doesn't retry."""

    class MockRetry:
        def __init__(self, *args, **kwargs):
            pass

        def call(self, f, *args, **kwargs):
            return f(*args, **kwargs)

    patch_retry = patch("retrying.Retrying", MockRetry)
    yield patch_retry.start()

    patch_retry.stop()


@pytest.fixture(autouse=True, scope="session")
def iamrole_table(dynamodb):
    # Create the table:
    dynamodb.create_table(
        TableName="consoleme_iamroles_global",
        AttributeDefinitions=[
            {"AttributeName": "arn", "AttributeType": "S"},
            {"AttributeName": "accountId", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "arn", "KeyType": "HASH"},
            {"AttributeName": "accountId", "KeyType": "RANGE"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1000, "WriteCapacityUnits": 1000},
    )

    # Apply a TTL:
    dynamodb.update_time_to_live(
        TableName="consoleme_iamroles_global",
        TimeToLiveSpecification={"Enabled": True, "AttributeName": "ttl"},
    )

    yield dynamodb


@pytest.fixture(autouse=True, scope="session")
def policy_requests_table(dynamodb):
    # Create the table:
    dynamodb.create_table(
        TableName="consoleme_policy_requests",
        KeySchema=[{"AttributeName": "request_id", "KeyType": "HASH"}],  # Partition key
        AttributeDefinitions=[
            {"AttributeName": "request_id", "AttributeType": "S"},
            {"AttributeName": "arn", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "arn-request_id-index",
                "KeySchema": [{"AttributeName": "arn", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 123,
                    "WriteCapacityUnits": 123,
                },
            }
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 10, "WriteCapacityUnits": 10},
    )

    yield dynamodb


@pytest.fixture(autouse=True, scope="session")
def requests_table(dynamodb):
    # Create the table:
    dynamodb.create_table(
        TableName="consoleme_requests_global",
        AttributeDefinitions=[{"AttributeName": "request_id", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "request_id", "KeyType": "HASH"}],
        ProvisionedThroughput={"ReadCapacityUnits": 1000, "WriteCapacityUnits": 1000},
    )

    yield dynamodb


@pytest.fixture(autouse=True, scope="session")
def users_table(dynamodb):
    # Create the table:
    dynamodb.create_table(
        TableName="consoleme_users_global",
        AttributeDefinitions=[{"AttributeName": "username", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],
        ProvisionedThroughput={"ReadCapacityUnits": 1000, "WriteCapacityUnits": 1000},
    )

    yield dynamodb


@pytest.fixture(autouse=True, scope="session")
def dummy_requests_data(requests_table):
    user = {
        "request_id": {"S": "abc-def-ghi"},
        "aws:rep:deleting": {"BOOL": False},
        "aws:rep:updateregion": {"S": "us-west-2"},
        "aws:rep:updatetime": {"N": "1547848006"},
        "group": {"S": "test_group"},
        "justification": {"S": "some reason"},
        "last_updated": {"N": "1245678901"},
        "request_time": {"N": "1234567890"},
        "status": {"S": "pending"},
        "updated_by": {"S": "somebody@somewhere.org"},
        "username": {"S": "test@user.xyz"},
        "reviewer_commnets": {"S": "All the access!"},
    }
    from consoleme.lib.dynamo import BaseDynamoHandler

    requests_table.put_item(
        TableName="consoleme_requests_global",
        Item=BaseDynamoHandler()._data_to_dynamo_replace(user),
    )

    yield requests_table


@pytest.fixture(autouse=True, scope="session")
def dummy_users_data(users_table):
    user = {
        "username": {"S": "test@user.xyz"},
        "aws:rep:deleting": {"BOOL": False},
        "aws:rep:updateregion": {"S": "us-west-2"},
        "last_udpated": {"N": "1547848006"},
        "requests": {"L": [{"S": "abc-def-ghi"}]},
    }
    from consoleme.lib.dynamo import BaseDynamoHandler

    users_table.put_item(
        TableName="consoleme_users_global",
        Item=BaseDynamoHandler()._data_to_dynamo_replace(user),
    )

    yield users_table


@pytest.fixture(autouse=True, scope="session")
def iam_sync_roles(iam):
    statement_policy = json.dumps(
        {
            "Statement": [{"Effect": "Deny", "Action": "*", "Resource": "*"}],
            "Version": "2012-10-17",
        }
    )

    assume_role_policy = json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": "arn:aws:iam::123456789012:role/ConsoleMeInstanceProfile"
                    },
                    "Action": "sts:AssumeRole",
                }
            ],
        }
    )

    # Create the role that CloudAux will assume:
    iam.create_role(RoleName="ConsoleMe", AssumeRolePolicyDocument=assume_role_policy)
    # Create a generic test instance profile
    iam.create_role(
        RoleName="TestInstanceProfile", AssumeRolePolicyDocument=assume_role_policy
    )

    # Create a managed policy:
    policy_one = iam.create_policy(
        PolicyName="policy-one", PolicyDocument=statement_policy
    )["Policy"]["Arn"]
    policy_two = iam.create_policy(
        PolicyName="policy-two", PolicyDocument=statement_policy
    )["Policy"]["Arn"]

    # Create 50 IAM roles for syncing:
    for x in range(0, 10):
        iam.create_role(
            RoleName=f"RoleNumber{x}", AssumeRolePolicyDocument=assume_role_policy
        )
        iam.put_role_policy(
            RoleName=f"RoleNumber{x}",
            PolicyName="SomePolicy",
            PolicyDocument=statement_policy,
        )
        iam.tag_role(
            RoleName=f"RoleNumber{x}",
            Tags=[
                {"Key": "Number", "Value": f"{x}"},
                {"Key": "authorized_groups", "Value": f"group{x}:group{x}@example.com"},
                {
                    "Key": "authorized_groups_cli_only",
                    "Value": f"group{x}-cli:group{x}-cli@example.com",
                },
            ],
        )
        iam.attach_role_policy(RoleName=f"RoleNumber{x}", PolicyArn=policy_one)
        iam.attach_role_policy(RoleName=f"RoleNumber{x}", PolicyArn=policy_two)

    # Create the dynamic user role:
    iam.create_role(
        RoleName="awsaccount_user", AssumeRolePolicyDocument=assume_role_policy
    )
    iam.put_role_policy(
        RoleName="awsaccount_user",
        PolicyName="SomePolicy",
        PolicyDocument=statement_policy,
    )
    iam.attach_role_policy(RoleName="awsaccount_user", PolicyArn=policy_one)

    # Create another dynamic user role

    iam.create_role(
        RoleName="cm_someuser_N", AssumeRolePolicyDocument=assume_role_policy
    )
    iam.put_role_policy(
        RoleName="cm_someuser_N",
        PolicyName="SomePolicy",
        PolicyDocument=statement_policy,
    )
    iam.attach_role_policy(RoleName="cm_someuser_N", PolicyArn=policy_one)

    iam.create_role(RoleName="rolename", AssumeRolePolicyDocument=assume_role_policy)
    iam.attach_role_policy(RoleName="rolename", PolicyArn=policy_one)

    yield iam


@pytest.fixture(autouse=True, scope="session")
def www_user():
    return json.loads(
        """{
        "Path": "/",
        "RoleName": "rolename",
        "RoleId": "AROAI5FHPGAEE6FRM5Q2Y",
        "Arn": "arn:aws:iam::123456789012:role/rolename",
        "CreateDate": "2017-10-06T22:07:23Z",
        "AssumeRolePolicyDocument": {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "",
                    "Effect": "Allow",
                    "Principal": {
                        "Federated": "arn:aws:iam::123456789012:saml-provider/saml"
                    },
                    "Action": "sts:AssumeRoleWithSAML",
                    "Condition": {
                        "StringEquals": {
                            "SAML:aud": "https://signin.aws.amazon.com/saml"
                        }
                    }
                },
                {
                    "Effect": "Allow",
                    "Principal": {
                        "AWS": "arn:aws:iam::123456789012:role/consoleme"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        },
        "InstanceProfileList": [],
        "RolePolicyList": [
            {
                "PolicyName": "user",
                "PolicyDocument": {
                    "Statement": [
                        {
                            "Action": [
                                "ec2:Describe*",
                                "lambda:Describe*",
                                "sns:List*",
                                "sqs:List*"
                            ],
                            "Effect": "Allow",
                            "Resource": [
                                "*"
                            ]
                        },
                        {
                            "Action": [
                                "iam:List*"
                            ],
                            "Effect": "Allow",
                            "Resource": [
                                "*"
                            ]
                        }
                    ],
                    "Version": "2012-10-17"
                }
            }
        ],
        "AttachedManagedPolicies": [
            {
                "PolicyName": "Abc",
                "PolicyArn": "arn:aws:iam::123456789012:policy/Abc"
            },
            {
                "PolicyName": "Encrypt",
                "PolicyArn": "arn:aws:iam::123456789012:policy/Encrypt"
            },
            {
                "PolicyName": "ReadOnlyAccess",
                "PolicyArn": "arn:aws:iam::aws:policy/ReadOnlyAccess"
            },
            {
                "PolicyName": "Tag",
                "PolicyArn": "arn:aws:iam::123456789012:policy/Tag"
            }
        ],
        "Tags": []
    }"""
    )


class FakeRedis(redislite.StrictRedis):
    def __init__(self, *args, **kwargs):
        if kwargs.get("connection_pool"):
            del kwargs["connection_pool"]
        super(FakeRedis, self).__init__(
            MOCK_REDIS_DB_PATH, *args, **kwargs, decode_responses=True
        )


@pytest.fixture(autouse=True, scope="session")
def redis(session_mocker):
    session_mocker.patch("redis.Redis", FakeRedis)
    session_mocker.patch("redis.StrictRedis", FakeRedis)
    session_mocker.patch("consoleme.lib.redis.redis.StrictRedis", FakeRedis)
    session_mocker.patch("consoleme.lib.redis.redis.Redis", FakeRedis)
    session_mocker.patch(
        "consoleme.lib.redis.RedisHandler.redis_sync", return_value=FakeRedis()
    )
    session_mocker.patch(
        "consoleme.lib.redis.RedisHandler.redis", return_value=FakeRedis()
    )
    return True


@pytest.fixture(scope="session")
def user_iam_role(iamrole_table, www_user):
    from consoleme.lib.dynamo import IAMRoleDynamoHandler

    ddb = IAMRoleDynamoHandler()
    role_entry = {
        "arn": www_user.pop("Arn"),
        "name": www_user.pop("RoleName"),
        "accountId": "123456789012",
        "ttl": int((datetime.utcnow() + timedelta(hours=36)).timestamp()),
        "policy": ddb.convert_role_to_json(www_user),
    }
    ddb.sync_iam_role_for_account(role_entry)


@pytest.fixture(autouse=True, scope="session")
def mock_exception_stats():
    p = patch("consoleme.exceptions.exceptions.get_plugin_by_name")

    yield p.start()

    p.stop()


@pytest.fixture(autouse=True, scope="session")
def mock_celery_stats(mock_exception_stats):
    p = patch("consoleme.celery.celery_tasks.stats")

    yield p.start()

    p.stop()


@pytest.fixture(scope="session")
def mock_async_http_client():
    p_return_value = Mock()
    p_return_value.body = "{}"
    p = patch("tornado.httpclient.AsyncHTTPClient")

    p.return_value.fetch.return_value = create_future(p_return_value)

    yield p.start()

    p.stop()


@pytest.fixture(autouse=True, scope="session")
def populate_caches(
    redis,
    user_iam_role,
    iam_sync_roles,
    dummy_users_data,
    dummy_requests_data,
    policy_requests_table,
    iamrole_table,
    create_default_resources,
    s3,
    sns,
    sqs,
    iam,
    www_user,
):
    from asgiref.sync import async_to_sync

    from consoleme.celery import celery_tasks as celery
    from consoleme.lib.account_indexers import get_account_id_to_name_mapping
    from consoleme_default_plugins.plugins.celery_tasks import (
        celery_tasks as default_celery_tasks,
    )

    celery.cache_cloud_account_mapping()
    accounts_d = async_to_sync(get_account_id_to_name_mapping)()
    default_celery_tasks.cache_application_information()

    for account_id in accounts_d.keys():
        celery.cache_roles_for_account(account_id)
        celery.cache_s3_buckets_for_account(account_id)
        celery.cache_sns_topics_for_account(account_id)
        celery.cache_sqs_queues_for_account(account_id)
        celery.cache_managed_policies_for_account(account_id)
        # celery.cache_resources_from_aws_config_for_account(account_id) # No select_resource_config in moto yet
    celery.cache_policies_table_details()
    celery.cache_policy_requests()
    celery.cache_credential_authorization_mapping()


class MockAioHttpResponse:
    status = 200
    responses = []

    @classmethod
    async def json(cls):
        try:
            return cls.responses.pop(0)
        except Exception:  # noqa
            return []


class MockAioHttpRequest:
    @classmethod
    async def get(cls, *args, **kwargs):
        return MockAioHttpResponse()

    @classmethod
    async def post(cls, *args, **kwargs):
        return MockAioHttpResponse()


def create_future(ret_val=None):
    future = Future()
    future.set_result(ret_val)
    return future
