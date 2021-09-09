import json
from unittest.mock import patch

from tornado.testing import AsyncHTTPTestCase

from tests.conftest import MockBaseHandler


class TestAwsIamUsers(AsyncHTTPTestCase):
    def get_app(self):
        from consoleme.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    @patch(
        "consoleme.handlers.v2.aws_iam_users.UserDetailHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    def test_fetch_nonexistent_user(self):
        response = self.fetch("/api/v2/users/123456789012/test_nonexistent_user")
        self.assertEqual(response.code, 404)
        self.assertEqual(response.reason, "Not Found")
        body = json.loads(response.body)
        self.assertEqual(
            body,
            {
                "status": 404,
                "title": "Not Found",
                "message": "Unable to retrieve the specified user: 123456789012/test_nonexistent_user. ",
            },
        )

    @patch(
        "consoleme.handlers.v2.aws_iam_users.UserDetailHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    def test_fetch_user(self):
        response = self.fetch("/api/v2/users/123456789012/TestUser")
        self.assertEqual(response.code, 200)
        body = json.loads(response.body)
        body.pop("created_time")
        self.assertEqual(
            body,
            {
                "name": "TestUser",
                "account_id": "123456789012",
                "account_name": "default_account",
                "arn": "arn:aws:iam::123456789012:user/TestUser",
                "inline_policies": [
                    {
                        "PolicyName": "SomePolicy",
                        "PolicyDocument": {
                            "Statement": [
                                {"Effect": "Deny", "Action": "*", "Resource": "*"}
                            ],
                            "Version": "2012-10-17",
                        },
                    }
                ],
                "assume_role_policy_document": None,
                "cloudtrail_details": {
                    "error_url": "",
                    "errors": {"cloudtrail_errors": []},
                },
                "s3_details": {
                    "query_url": "",
                    "error_url": "",
                    "errors": {"s3_errors": []},
                },
                "apps": {"app_details": []},
                "managed_policies": [
                    {
                        "PolicyName": "policy-one",
                        "PolicyArn": "arn:aws:iam::123456789012:policy/policy-one",
                    }
                ],
                "permissions_boundary": {},
                "tags": [],
                "config_timeline_url": None,
                "templated": False,
                "template_link": None,
                "updated_time": None,
                "last_used_time": None,
                "description": None,
                "owner": None,
            },
        )

    @patch(
        "consoleme.handlers.v2.aws_iam_users.UserDetailHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    def test_delete_user_forbidden(self):
        import boto3

        from consoleme.config import config

        user_name = "test_delete_user_forbidden"
        iam = boto3.client("iam", **config.get("boto3.client_kwargs", {}))
        iam.create_user(UserName=user_name)
        response = self.fetch(
            f"/api/v2/users/123456789012/{user_name}", method="DELETE"
        )
        self.assertEqual(response.code, 403)
        body = json.loads(response.body)
        self.assertEqual(
            body,
            {
                "status": 403,
                "title": "Forbidden",
                "message": "User is unauthorized to delete an AWS IAM user",
            },
        )

    def test_delete_user_allowed(self):
        import boto3

        from consoleme.config import config

        headers = {
            config.get("auth.user_header_name"): "person@example.com",
            config.get(
                "auth.groups_header_name"
            ): "groupa,groupb,groupc,consoleme_admins@example.com",
        }
        user_name = "test_delete_user_allowed"
        iam = boto3.client("iam", **config.get("boto3.client_kwargs", {}))
        iam.create_user(UserName=user_name)
        response = self.fetch(
            f"/api/v2/users/123456789012/{user_name}", method="DELETE", headers=headers
        )
        self.assertEqual(response.code, 200)
        body = json.loads(response.body)
        self.assertEqual(
            body,
            {
                "status": "success",
                "message": "Successfully deleted AWS IAM user from account",
                "iam_user_name": user_name,
                "account": "123456789012",
            },
        )
