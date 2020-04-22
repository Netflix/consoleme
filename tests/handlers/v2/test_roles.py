import ujson as json
from mock import patch
from tornado.testing import AsyncHTTPTestCase
from tornado.web import Application


class TestRolesHandler(AsyncHTTPTestCase):
    def get_app(self):
        from consoleme.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    @patch(
        "consoleme.handlers.v2.roles.RolesHandler.get_current_user",
        lambda x: {"email": "foo@bar.com"},
    )
    def test_get(self):
        headers = {"Authorization": "Bearer foo"}
        response = self.fetch("/api/v2/roles", method="GET", headers=headers)
        expected = {
            "status": 501,
            "title": "Not Implemented",
            "message": "Get roles",
        }
        self.assertEqual(response.code, 501)
        self.assertDictEqual(json.loads(response.body), expected)


class TestAccountRolesHandler(AsyncHTTPTestCase):
    def get_app(self):
        from consoleme.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    @patch(
        "consoleme.handlers.v2.roles.AccountRolesHandler.get_current_user",
        lambda x: {"email": "foo@bar.com"},
    )
    def test_get(self):
        headers = {"Authorization": "Bearer foo"}
        response = self.fetch(
            "/api/v2/roles/0123456789012", method="GET", headers=headers
        )
        expected = {
            "status": 501,
            "title": "Not Implemented",
            "message": "Get roles by account",
        }
        self.assertEqual(response.code, 501)
        self.assertDictEqual(response.json, expected)


class TestRoleDetailHandler(AsyncHTTPTestCase):
    def get_app(self):
        from consoleme.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    @patch(
        "consoleme.handlers.v2.roles.RoleDetailHandler.get_current_user",
        lambda x: {"email": "foo@bar.com"},
    )
    def test_get(self):
        headers = {"Authorization": "Bearer foo"}
        response = self.fetch(
            "/api/v2/roles/0123456789012/fake_account_admin",
            method="GET",
            headers=headers,
        )
        expected = {
            "status": 501,
            "title": "Not Implemented",
            "message": "Get role details",
        }
        self.assertEqual(response.code, 501)
        self.assertDictEqual(response.json, expected)

    @patch(
        "consoleme.handlers.v2.roles.RoleDetailHandler.get_current_user",
        lambda x: {"email": "foo@bar.com"},
    )
    def test_put(self):
        headers = {"Authorization": "Bearer foo"}
        response = self.fetch(
            "/api/v2/roles/0123456789012/fake_account_admin",
            method="PUT",
            headers=headers,
            body="{}",
        )
        expected = {
            "status": 501,
            "title": "Not Implemented",
            "message": "Update role details",
        }

        self.assertEqual(response.code, 501)
        self.assertDictEqual(response.json, expected)
