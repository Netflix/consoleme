"""Docstring in public module."""
import json
import os
import sys
import time
import urllib
import uuid

import boto3
import pytest
from mock import patch, MagicMock
from mockredis import mock_strict_redis_client
from tornado.concurrent import Future
from tornado.testing import AsyncHTTPTestCase

from consoleme.config import config
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.routes import make_app
from tests.conftest import mock_accountdata_redis

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(APP_ROOT, ".."))

auth = get_plugin_by_name(config.get("plugins.auth"))()

Group = auth.Group
User = auth.User
ExtendedAttribute = auth.ExtendedAttribute

red = mock_strict_redis_client()


class TestIndexHandler(AsyncHTTPTestCase):
    def get_app(self):
        return make_app(jwt_validator=lambda x: {})

    def test_index_no_user(self):
        response = self.fetch("/")
        self.assertIn(b"No user detected. Check configuration", response.body)

    @patch("consoleme.handlers.base.RedisHandler")
    @patch("consoleme_internal.plugins.group_mapping.group_mapping.RedisHandler")
    def test_index_pageload(self, mock_gm_redis_handler, mock_redis_handler):
        red.set("SWAG_SETTINGS_ID_TO_NAMEv2", '{"12345": ["accountname"]}')
        mock_redis = Future()
        mock_redis.set_result(red)
        mock_redis_handler.return_value.redis.return_value = mock_redis
        mock_gm_redis_handler.return_value.redis.return_value = mock_redis
        headers = {
            "Oidc_claim_sub": "user@github.com",
            "Oidc_claim_googlegroups": "groupa,groupb,groupc",
            "Oidc_claim_userid": "1" * 21,
        }

        response = self.fetch("/", headers=headers)
        self.assertEqual(response.code, 200)
        self.assertIn(b"reset_aws_auth_cookie", response.body)


@pytest.mark.usefixtures(
    "retry", "user_role_lambda", "iam_sync_roles", "sts", "iamrole_table"
)
class TestIndexPostHandler(AsyncHTTPTestCase):
    def __init__(self, *args, **kwargs):
        AsyncHTTPTestCase.__init__(self, *args, **kwargs)

        self.test_groups = [
            "awsrole-awsaccount_user-123456789012@example.com",
            "cm-123456789012@example.com",
        ]
        self.mocks = []
        self.current_redis_roles = None
        self.old_redis_accountdata = None
        self.current_redis_accountdata = None
        self.redis = None
        self.mock_moto_lambda = None
        self.aws_return_string = None

    def get_app(self):
        return make_app(jwt_validator=lambda x: {})

    def setUp(self):
        from consoleme.config.config import CONFIG
        from consoleme_internal.plugins.aws.aws import init

        # Make fake Redis data (for IAM) -- for this, we replacing the `aws` object with our own::
        mocked_aws = init()
        self.current_redis_roles = f"test_post_dynamic_roles_{uuid.uuid4()}"
        mocked_aws.redis_key = self.current_redis_roles

        # Make fake Account data:
        self.old_red_accountdata = CONFIG.config["swag"].pop("redis_id_name_key", None)
        self.current_redis_accountdata = f"test_post_dynamic_roles_swag_{uuid.uuid4()}"
        CONFIG.config["swag"]["redis_id_name_key"] = self.current_redis_accountdata

        mock_swag = json.dumps(
            {"123456789012": ["awsaccount", "awsaccount@example.com"]}
        )

        self.redis = red

        # Delete the old values:
        self.redis.delete(self.current_redis_accountdata)
        self.redis.delete(self.current_redis_roles)

        self.redis.set(self.current_redis_accountdata, mock_swag)

        user = User(
            userName="someuser@example.com",
            domain="example.com",
            name={"fullName": "Some User"},
            updated={"onDate": str(int(round(time.time() * 1000)))},
            status="Enabled",
            userId="1" * 21,
            passed_background_check=True,
        )

        async def mock_get_user_info(*args, **kwargs):
            return user

        async def mock_get_group_membership(*args, **kwargs):
            return self.test_groups

        self.aws_return_string = aws_return_string = (
            "https://us-east-1.signin.aws.amazon.com/oauth?SignatureVersion=4&X-Amz-Algorithm"
            "=AWS4-HMAC-SHA256&X-Amz-Credential=ACCESS-KEY-ID..."
        )

        class MockAWSReturn:
            async def json(self, *args, **kwargs):
                return {"SigninToken": aws_return_string}

            def prepare(self):
                mocked_obj = MagicMock()
                mocked_obj.url = aws_return_string
                return mocked_obj

        def aws_request_mock(*args, **kwargs):
            return MockAWSReturn()

        async def async_request_mock(*args, **kwargs):
            return MockAWSReturn()

        self.mocks = [
            patch("consoleme.handlers.index.aws", mocked_aws),
            patch(
                "consoleme_internal.plugins.auth.auth.Auth.get_user_info",
                mock_get_user_info,
            ),
            patch(
                "consoleme_internal.plugins.auth.auth.Auth.get_group_memberships",
                mock_get_group_membership,
            ),
            patch(
                "consoleme_internal.plugins.aws.aws.requests_sync.Request",
                aws_request_mock,
            ),
            patch("consoleme_internal.plugins.aws.aws.redis_get_sync", self.redis.get),
            patch.object(mocked_aws, "red", mock_strict_redis_client()),
        ]

        for m in self.mocks:
            m.start()

        self.mock_moto_lambda = {
            "success": True,
            "role_name": "cm-123456789012-111111111111111111111",
            "account_number": "123456789012",
        }

        super().setUp()

    def tearDown(self):
        from consoleme.config.config import CONFIG

        # Delete the old values:
        self.redis.delete(self.current_redis_accountdata)
        self.redis.delete(self.current_redis_roles)

        for m in self.mocks:
            m.stop()

        if self.old_red_accountdata:
            CONFIG.config["swag"]["redis_id_name_key"] = self.old_red_accountdata
        else:
            del CONFIG.config["swag"]["redis_id_name_key"]

        super().tearDown()

    @patch("consoleme.handlers.base.RedisHandler", mock_accountdata_redis)
    @patch(
        "consoleme_internal.plugins.group_mapping.group_mapping.RedisHandler",
        mock_accountdata_redis,
    )
    def test_post_creds(self):
        mock_moto = patch(
            "moto.awslambda.models.LambdaFunction.invoke",
            lambda *args, **kwargs: json.dumps(self.mock_moto_lambda),
        )
        mock_moto.start()

        mock_get_user_attribute_value = Future()
        mock_get_user_attribute_value.set_result(
            ExtendedAttribute(attributeValue="cm_someuser_N")
        )
        mock_get_or_create_user_role_name = patch(
            "consoleme_internal.plugins.auth.auth.Auth.get_user_attribute",
            return_value=mock_get_user_attribute_value,
        )
        mock_get_or_create_user_role_name.start()

        headers = {
            "Oidc_claim_sub": "someuser@example.com",
            "Oidc_claim_googlegroups": (
                "cm-user-role-onboarding@example.com,awsrole-rolename2-123456789012@example.com,"
                "awsrole-rolename-123456789012@example.com"
            ),
            "Oidc_claim_userid": "1" * 21,
        }

        body = {
            "role": f"arn:aws:iam::123456789012:role/rolename",
            "region": "us-east-1",
            "_xsrf": "hay there!",
        }

        result = self.fetch(
            "/",
            headers=headers,
            method="POST",
            body=urllib.parse.urlencode(body),
            follow_redirects=False,
        )

        self.assertEqual(result.code, 302)
        self.assertEqual(result.headers["Location"], self.aws_return_string)

        # With an issue launching the lambda:
        self.mock_moto_lambda["success"] = False
        result = self.fetch(
            "/api/v1/get_credentials",
            method="POST",
            headers=headers,
            body=json.dumps(body),
        )
        self.assertEqual(result.code, 403)
        mock_moto.stop()

        # And with a static role:
        body["role"] = "arn:aws:iam::123456789012:role/rolename2"
        result = self.fetch(
            "/",
            headers=headers,
            method="POST",
            body=urllib.parse.urlencode(body),
            follow_redirects=False,
        )

        self.assertEqual(result.code, 302)
        self.assertEqual(result.headers["Location"], self.aws_return_string)

        # And an account that doesn't exist:
        body["role"] = "arn:aws:iam::222222222222:role/rolename"
        result = self.fetch(
            "/",
            headers=headers,
            method="POST",
            body=urllib.parse.urlencode(body),
            follow_redirects=False,
        )
        self.assertEqual(result.code, 403)

        # Now test if the role itself doesn't exist:
        self.redis.delete(self.current_redis_roles)
        iam = boto3.client("iam")
        iamrole_table = boto3.client("dynamodb", region_name="us-east-1")
        iam.detach_role_policy(
            RoleName="awsaccount_user",
            PolicyArn="arn:aws:iam::123456789012:policy/policy-one",
        )
        iam.delete_role_policy(RoleName="awsaccount_user", PolicyName="SomePolicy")
        iam.delete_role(RoleName="awsaccount_user")
        iamrole_table.delete_item(
            TableName="consoleme_iamroles_global",
            Key={
                "arn": {"S": "arn:aws:iam::123456789012:role/awsaccount_user"},
                "accountId": {"S": "123456789012"},
            },
        )
        body["role"] = f"arn:aws:iam::123456789012:role/cm_someuser_N"
        result = self.fetch(
            "/",
            headers=headers,
            method="POST",
            body=urllib.parse.urlencode(body),
            follow_redirects=False,
        )
        self.assertEqual(result.code, 403)
        mock_get_or_create_user_role_name.stop()
