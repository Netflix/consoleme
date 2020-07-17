import ujson as json
from tornado.testing import AsyncHTTPTestCase

from consoleme.config import config


class TestRequestsHandler(AsyncHTTPTestCase):
    def get_app(self):
        from consoleme.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    def test_get(self):
        expected = {
            "status": 501,
            "title": "Not Implemented",
            "message": "Get requests",
        }
        headers = {
            config.get("auth.user_header_name"): "user@github.com",
            config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }
        response = self.fetch("/api/v2/requests", method="GET", headers=headers)
        self.assertEqual(response.code, 501)
        self.assertDictEqual(json.loads(response.body), expected)

    def test_post(self):
        expected = {
            "status": 501,
            "title": "Not Implemented",
            "message": "Create request",
        }
        headers = {
            config.get("auth.user_header_name"): "user@github.com",
            config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }
        response = self.fetch(
            "/api/v2/requests", method="POST", headers=headers, body="{}"
        )
        self.assertEqual(response.code, 501)
        self.assertDictEqual(json.loads(response.body), expected)


class TestRequestDetailHandler(AsyncHTTPTestCase):
    def get_app(self):
        from consoleme.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    def test_get(self):
        expected = {
            "status": 501,
            "title": "Not Implemented",
            "message": "Get request details",
        }
        headers = {
            config.get("auth.user_header_name"): "user@github.com",
            config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }
        response = self.fetch(
            "/api/v2/requests/16fd2706-8baf-433b-82eb-8c7fada847da",
            method="GET",
            headers=headers,
        )
        self.assertEqual(response.code, 501)
        self.assertDictEqual(json.loads(response.body), expected)

    def test_put(self):
        expected = {
            "status": 501,
            "title": "Not Implemented",
            "message": "Update request details",
        }
        headers = {
            config.get("auth.user_header_name"): "user@github.com",
            config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }
        response = self.fetch(
            "/api/v2/requests/16fd2706-8baf-433b-82eb-8c7fada847da",
            method="PUT",
            headers=headers,
            body="{}",
        )
        self.assertEqual(response.code, 501)
        self.assertDictEqual(json.loads(response.body), expected)
