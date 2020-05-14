import ujson as json
from mock import patch
from tornado.testing import AsyncHTTPTestCase


class TestRequestsHandler(AsyncHTTPTestCase):
    def get_app(self):
        from consoleme.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    @patch(
        "consoleme.handlers.base.BaseJSONHandler.get_current_user",
        lambda x: {"email": "foo@bar.com"},
    )
    def test_get(self):
        headers = {"Authorization": "Bearer foo"}
        response = self.fetch("/api/v2/requests", method="GET", headers=headers)
        expected = {
            "status": 501,
            "title": "Not Implemented",
            "message": "Get requests",
        }
        self.assertEqual(response.code, 501)
        self.assertDictEqual(json.loads(response.body), expected)

    @patch(
        "consoleme.handlers.base.BaseJSONHandler.get_current_user",
        lambda x: {"email": "foo@bar.com"},
    )
    def test_post(self):
        headers = {"Authorization": "Bearer foo"}
        response = self.fetch(
            "/api/v2/requests", method="POST", headers=headers, body="{}"
        )
        expected = {
            "status": 501,
            "title": "Not Implemented",
            "message": "Create request",
        }
        self.assertEqual(response.code, 501)
        self.assertDictEqual(json.loads(response.body), expected)


class TestRequestDetailHandler(AsyncHTTPTestCase):
    def get_app(self):
        from consoleme.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    @patch(
        "consoleme.handlers.base.BaseJSONHandler.get_current_user",
        lambda x: {"email": "foo@bar.com"},
    )
    def test_get(self):
        headers = {"Authorization": "Bearer foo"}
        response = self.fetch(
            "/api/v2/requests/16fd2706-8baf-433b-82eb-8c7fada847da",
            method="GET",
            headers=headers,
        )
        expected = {
            "status": 501,
            "title": "Not Implemented",
            "message": "Get request details",
        }
        self.assertEqual(response.code, 501)
        self.assertDictEqual(json.loads(response.body), expected)

    @patch(
        "consoleme.handlers.base.BaseJSONHandler.get_current_user",
        lambda x: {"email": "foo@bar.com"},
    )
    def test_put(self):
        headers = {"Authorization": "Bearer foo"}
        response = self.fetch(
            "/api/v2/requests/16fd2706-8baf-433b-82eb-8c7fada847da",
            method="PUT",
            headers=headers,
            body="{}",
        )
        expected = {
            "status": 501,
            "title": "Not Implemented",
            "message": "Update request details",
        }

        self.assertEqual(response.code, 501)
        self.assertDictEqual(json.loads(response.body), expected)
