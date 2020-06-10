import boto3
import ujson as json
from mock import patch
from moto import mock_iam
from tornado.testing import AsyncHTTPTestCase

from consoleme.config import config
from tests.conftest import MockBaseHandler, create_future


class TestRolesHandler(AsyncHTTPTestCase):
    def get_app(self):
        from consoleme.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    def test_get(self):
        headers = {
            config.get("auth.user_header_name"): "user@github.com",
            config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }
        response = self.fetch("/api/v2/roles", method="GET", headers=headers)
        self.assertEqual(response.code, 200)
        responseJSON = json.loads(response.body)
        self.assertIn("_xsrf", responseJSON)
        self.assertIn("eligible_roles", responseJSON)
        self.assertEqual(0, len(responseJSON["eligible_roles"]))


class TestAccountRolesHandler(AsyncHTTPTestCase):
    def get_app(self):
        from consoleme.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    def test_get(self):
        expected = {
            "status": 501,
            "title": "Not Implemented",
            "message": "Get roles by account",
        }
        headers = {
            config.get("auth.user_header_name"): "user@github.com",
            config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }
        response = self.fetch(
            "/api/v2/roles/012345678901", method="GET", headers=headers
        )
        self.assertEqual(response.code, 501)
        self.assertDictEqual(json.loads(response.body), expected)


class TestRoleDetailHandler(AsyncHTTPTestCase):
    def get_app(self):
        from consoleme.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    def test_get(self):
        expected = {
            "status": 501,
            "title": "Not Implemented",
            "message": "Get role details",
        }
        headers = {
            config.get("auth.user_header_name"): "user@github.com",
            config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }
        response = self.fetch(
            "/api/v2/roles/012345678901/fake_account_admin",
            method="GET",
            headers=headers,
        )
        self.assertEqual(response.code, 501)
        self.assertDictEqual(json.loads(response.body), expected)

    def test_put(self):
        expected = {
            "status": 501,
            "title": "Not Implemented",
            "message": "Update role details",
        }
        headers = {
            config.get("auth.user_header_name"): "user@github.com",
            config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }
        response = self.fetch(
            "/api/v2/roles/012345678901/fake_account_admin",
            method="PUT",
            headers=headers,
            body="{}",
        )
        self.assertEqual(response.code, 501)
        self.assertDictEqual(json.loads(response.body), expected)

    @patch("consoleme.handlers.v2.roles.RoleDetailHandler.authorization_flow")
    def test_post_no_user(self, mock_auth):
        mock_auth.return_value = create_future(None)
        expected = {
            "status": 403,
            "title": "Forbidden",
            "message": "No user detected",
        }
        response = self.fetch(
            "/api/v2/roles/012345678901/fake_account_admin", method="DELETE",
        )
        self.assertEqual(response.code, 403)
        self.assertDictEqual(json.loads(response.body), expected)

    @patch(
        "consoleme.handlers.v2.roles.RoleDetailHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    def test_post_unauthorized_user(self):
        expected = {
            "status": 403,
            "title": "Forbidden",
            "message": "User is unauthorized to delete a role",
        }
        response = self.fetch(
            "/api/v2/roles/012345678901/fake_account_admin", method="DELETE",
        )
        self.assertEqual(response.code, 403)
        self.assertDictEqual(json.loads(response.body), expected)

    @patch(
        "consoleme.handlers.v2.roles.RoleDetailHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    @patch("consoleme.handlers.v2.roles.can_delete_roles")
    def test_post_authorized_user_invalid_role(self, mock_can_delete_roles):
        expected = {
            "status": 500,
            "title": "Internal Server Error",
            "message": "Error occurred deleting role: An error occurred (NoSuchEntity) when calling the GetRole "
            "operation: Role fake_account_admin not found",
        }
        mock_can_delete_roles.return_value = create_future(True)
        response = self.fetch(
            "/api/v2/roles/012345678901/fake_account_admin", method="DELETE",
        )
        self.assertEqual(response.code, 500)
        self.assertDictEqual(json.loads(response.body), expected)

    @patch(
        "consoleme.handlers.v2.roles.RoleDetailHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    @patch("consoleme.handlers.v2.roles.can_delete_roles")
    @mock_iam
    def test_post_authorized_user_valid_role(self, mock_can_delete_roles):
        client = boto3.client("iam", region_name="us-east-1")
        role_name = "fake_account_admin"
        account_id = "012345678901"
        client.create_role(RoleName=role_name, AssumeRolePolicyDocument="{}")
        expected = {
            "status": "success",
            "message": "Successfully deleted role from account",
            "role": role_name,
            "account": account_id,
        }

        mock_can_delete_roles.return_value = create_future(True)

        response = self.fetch(
            f"/api/v2/roles/{account_id}/{role_name}", method="DELETE",
        )
        self.assertEqual(response.code, 200)
        self.assertDictEqual(json.loads(response.body), expected)
