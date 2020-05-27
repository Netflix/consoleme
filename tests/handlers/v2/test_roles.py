import ujson as json
from mock import patch
from tornado.testing import AsyncHTTPTestCase
from consoleme.config import config

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