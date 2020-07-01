import asyncio
import json
import os
import unittest
from datetime import datetime, timedelta

import boto3
import fakeredis
import pytest
from mock import MagicMock, Mock, patch
from mockredis import mock_strict_redis_client
from moto import mock_dynamodb2, mock_iam, mock_lambda, mock_sts
from tornado.concurrent import Future

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
                    "Sid": "",
                    "Effect": "Allow",
                    "Principal": {"AWS": "arn:aws:iam::123456789012:role/FakeRole"},
                    "Action": "sts:AssumeRole",
                }
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

fakeredis_server = fakeredis.FakeServer()


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
        self, restricted=False, compliance_restricted=False, get_groups_val=[]
    ):
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


@pytest.fixture
def aws_credentials():
    """Mocked AWS Credentials for moto."""
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"


@pytest.fixture(autouse=True)
def sts(aws_credentials):
    """Mocked STS Fixture."""
    with mock_sts():
        yield boto3.client("sts", region_name="us-east-1")


@pytest.fixture(autouse=True)
def iam(aws_credentials):
    """Mocked IAM Fixture."""
    with mock_iam():
        yield boto3.client("iam", region_name="us-east-1")


@pytest.fixture(autouse=True)
def dynamodb(aws_credentials):
    """Mocked DynamoDB Fixture."""
    with mock_dynamodb2():
        # Remove the config value for the DynamoDB Server
        from consoleme.config.config import CONFIG

        old_value = CONFIG.config.pop("dynamodb_server", None)

        yield boto3.client("dynamodb", region_name="us-east-1")

        # Reset the config value:
        CONFIG.config["dynamodb_server"] = old_value


@pytest.fixture
def aws_lambda(aws_credentials):
    """Mocked AWS Lambda Fixture."""
    with mock_lambda():
        yield boto3.client("lambda", region_name="us-east-1")


@pytest.fixture(scope="function")
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


@pytest.fixture(scope="function")
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


@pytest.fixture(scope="function")
def requests_table(dynamodb):
    # Create the table:
    dynamodb.create_table(
        TableName="consoleme_requests_global",
        AttributeDefinitions=[{"AttributeName": "request_id", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "request_id", "KeyType": "HASH"}],
        ProvisionedThroughput={"ReadCapacityUnits": 1000, "WriteCapacityUnits": 1000},
    )

    yield dynamodb


@pytest.fixture(scope="function")
def users_table(dynamodb):
    # Create the table:
    dynamodb.create_table(
        TableName="consoleme_users_global",
        AttributeDefinitions=[{"AttributeName": "username", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],
        ProvisionedThroughput={"ReadCapacityUnits": 1000, "WriteCapacityUnits": 1000},
    )

    yield dynamodb


@pytest.fixture(scope="function")
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


@pytest.fixture(scope="function")
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


@pytest.fixture
def iam_sync_roles(iam):
    statement_policy = json.dumps(
        {
            "Statement": [{"Effect": "Deny", "Action": "*", "Resource": "*"}],
            "Version": "2012-10-17",
        }
    )

    # Create the role that CloudAux will assume:
    iam.create_role(RoleName="ConsoleMe", AssumeRolePolicyDocument="{}")
    # Create a generic test instance profile
    iam.create_role(RoleName="TestInstanceProfile", AssumeRolePolicyDocument="{}")

    # Create a managed policy:
    policy_one = iam.create_policy(
        PolicyName="policy-one", PolicyDocument=statement_policy
    )["Policy"]["Arn"]
    policy_two = iam.create_policy(
        PolicyName="policy-two", PolicyDocument=statement_policy
    )["Policy"]["Arn"]

    # Create 50 IAM roles for syncing:
    for x in range(0, 10):
        iam.create_role(RoleName=f"RoleNumber{x}", AssumeRolePolicyDocument="{}")
        iam.put_role_policy(
            RoleName=f"RoleNumber{x}",
            PolicyName="SomePolicy",
            PolicyDocument=statement_policy,
        )
        iam.tag_role(
            RoleName=f"RoleNumber{x}", Tags=[{"Key": "Number", "Value": f"{x}"}]
        )
        iam.attach_role_policy(RoleName=f"RoleNumber{x}", PolicyArn=policy_one)
        iam.attach_role_policy(RoleName=f"RoleNumber{x}", PolicyArn=policy_two)

    # Create the dynamic user role:
    iam.create_role(RoleName="awsaccount_user", AssumeRolePolicyDocument="{}")
    iam.put_role_policy(
        RoleName="awsaccount_user",
        PolicyName="SomePolicy",
        PolicyDocument=statement_policy,
    )
    iam.attach_role_policy(RoleName="awsaccount_user", PolicyArn=policy_one)

    # Create another dynamic user role

    iam.create_role(RoleName="cm_someuser_N", AssumeRolePolicyDocument="{}")
    iam.put_role_policy(
        RoleName="cm_someuser_N",
        PolicyName="SomePolicy",
        PolicyDocument=statement_policy,
    )
    iam.attach_role_policy(RoleName="cm_someuser_N", PolicyArn=policy_one)

    yield iam


@pytest.fixture
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


class FakeRedis(fakeredis.FakeStrictRedis):
    def __init__(self, *args, **kwargs):
        super(FakeRedis, self).__init__(*args, **kwargs, server=fakeredis_server)


@pytest.fixture(autouse=True)
def redis(mocker):
    mocker.patch("redis.Redis", FakeRedis)
    mocker.patch("redis.StrictRedis", FakeRedis)
    return True


@pytest.fixture
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


@pytest.fixture
def mock_exception_stats():
    p = patch("consoleme.exceptions.exceptions.get_plugin_by_name")

    yield p.start()

    p.stop()


@pytest.fixture
def mock_celery_stats(mock_exception_stats):
    p = patch("consoleme.celery.celery_tasks.stats")

    yield p.start()

    p.stop()


@pytest.fixture
def mock_async_http_client():
    p_return_value = Mock()
    p_return_value.body = "{}"
    p = patch("tornado.httpclient.AsyncHTTPClient")

    p.return_value.fetch.return_value = create_future(p_return_value)

    yield p.start()

    p.stop()


@pytest.fixture
def user_role_lambda(aws_lambda):
    aws_lambda.create_function(
        FunctionName="UserRoleCreator",
        Runtime="python3.7",
        Role="arn:aws:iam::123456789012:role/UserRoleCreatorLambdaProfile",
        Handler="handler",
        Code={"ZipFile": "lolcode".encode()},
    )

    yield aws_lambda


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
