"""Docstring in public module."""
import json
import os
import urllib

import boto3
import pytest
import sys
from mock import patch
from mockredis import mock_strict_redis_client
from tornado.testing import AsyncHTTPTestCase

from consoleme.config import config

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(APP_ROOT, ".."))

red = mock_strict_redis_client()


class TestIndexHandler(AsyncHTTPTestCase):
    def get_app(self):
        from consoleme.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    def test_index_no_user(self):
        response = self.fetch("/")
        self.assertIn(b"No user detected. Check configuration", response.body)

    def test_index_pageload(self):
        headers = {
            config.get("auth.user_header_name"): "user@github.com",
            config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }

        response = self.fetch("/", headers=headers)
        self.assertEqual(response.code, 200)
        self.assertIn(b"static/js/bundle.js", response.body)


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
        from consoleme.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    def test_post_creds(self):
        mock_moto = patch(
            "moto.awslambda.models.LambdaFunction.invoke",
            lambda *args, **kwargs: json.dumps(self.mock_moto_lambda),
        )
        mock_moto.start()

        headers = {
            config.get("auth.user_header_name"): "someuser@example.com",
            config.get("auth.groups_header_name"): ("group1@example.com"),
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
        self.assertIn(
            "https://signin.aws.amazon.com/federation?Action=login&Issuer=YourCompany&Destination=https%3A%2F%2Fus-east-1.console.aws.amazon.com&SigninToken=",
            result.headers["Location"],
            "Should contain AWS login URI",
        )

        body["role"] = f"arn:aws:iam::123456789012:role/userrolename"

        result = self.fetch(
            "/",
            headers=headers,
            method="POST",
            body=urllib.parse.urlencode(body),
            follow_redirects=False,
        )

        self.assertEqual(result.code, 302)
        self.assertIn(
            "https://signin.aws.amazon.com/federation?Action=login&Issuer=YourCompany&Destination=https%3A%2F%2Fus-east-1.console.aws.amazon.com&SigninToken=",
            result.headers["Location"],
            "Should contain AWS login URI",
        )

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
