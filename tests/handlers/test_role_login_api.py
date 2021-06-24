"""Docstring in public module."""
import os
import sys

import ujson as json
from tornado.testing import AsyncHTTPTestCase

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(APP_ROOT, ".."))


class TestRoleLoginApi(AsyncHTTPTestCase):
    def get_app(self):
        from consoleme.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    def test_role_api_fail(self):
        from consoleme.config import config

        headers = {
            config.get("auth.user_header_name"): "user@example.com",
            config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }

        response = self.fetch("/api/v2/role_login/role123", headers=headers)
        self.assertEqual(response.code, 404)
        self.assertEqual(
            json.loads(response.body),
            {
                "type": "error",
                "message": "You do not have any roles matching your search criteria. ",
            },
        )

    def test_role_api_fail_multiple_matching_roles(self):
        from consoleme.config import config

        headers = {
            config.get("auth.user_header_name"): "userwithmultipleroles@example.com",
            config.get("auth.groups_header_name"): "group9,group3",
        }

        response = self.fetch("/api/v2/role_login/role", headers=headers)
        self.assertEqual(response.code, 200)
        response_j = json.loads(response.body)
        self.assertEqual(
            response_j["message"],
            "You have more than one role matching your query. Please select one.",
        )
        self.assertEqual(response_j["reason"], "multiple_roles")
        self.assertEqual(response_j["type"], "redirect")
        self.assertIn("/?arn=role&warningMessage=", response_j["redirect_url"])

    def test_role_api_success(self):
        from consoleme.config import config

        headers = {
            config.get("auth.user_header_name"): "userwithrole@example.com",
            config.get("auth.groups_header_name"): "groupa@example.com",
        }

        response = self.fetch("/api/v2/role_login/roleA", headers=headers)
        self.assertEqual(response.code, 200)
        response_j = json.loads(response.body)
        self.assertEqual(response_j["type"], "redirect")
        self.assertEqual(response_j["reason"], "console_login")
        self.assertEqual(response_j["role"], "arn:aws:iam::123456789012:role/roleA")
        self.assertIn(
            "https://signin.aws.amazon.com/federation?Action=login&Issuer=YourCompany&Destination=https%3A%2F%2Fus-east-1.console.aws.amazon.com&SigninToken=",
            response_j["redirect_url"],
        )
