import ujson as json
from mock import patch
from tornado.testing import AsyncHTTPTestCase
from consoleme.config import config

class TestRequestsHandler(AsyncHTTPTestCase):
    def get_app(self):
        from consoleme.routes import make_app

        return make_app(jwt_validator=lambda x: {})
    
    def test_get(self):
        headers = {
            config.get("auth.user_header_name"): "user@github.com",
            config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }
        response = self.fetch("/api/v2/requests", method="GET", headers=headers)
        self.assertEqual(response.code, 200)
        self.assertIn(b"501: OK", response.body)

    def test_post(self):
        headers = {
            config.get("auth.user_header_name"): "user@github.com",
            config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }
        response = self.fetch( "/api/v2/requests", method="POST", headers=headers, body="{}")
        self.assertEqual(response.code, 200)
        self.assertIn(b"501: OK", response.body)


class TestRequestDetailHandler(AsyncHTTPTestCase):
    def get_app(self):
        from consoleme.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    def test_get(self):
        headers = {
            config.get("auth.user_header_name"): "user@github.com",
            config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }
        response = self.fetch(
            "/api/v2/requests/16fd2706-8baf-433b-82eb-8c7fada847da",
            method="GET",
            headers=headers,
        )
        self.assertEqual(response.code, 200)
        self.assertIn(b"501: OK", response.body)

    def test_put(self):
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
        self.assertEqual(response.code, 200)
        self.assertIn(b"501: OK", response.body)
