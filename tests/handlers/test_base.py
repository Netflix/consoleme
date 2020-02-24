import json

import jwt
from tornado.testing import AsyncHTTPTestCase
from tornado.web import Application

from consoleme.lib.auth import mk_jwt_validator

TEST_SECRET = "SECRET"
TEST_ALG = ["HS256"]
TEST_VALIDATOR = mk_jwt_validator(TEST_SECRET, {"alg": {"enum": TEST_ALG}}, {})


class TestBaseJSONHandler(AsyncHTTPTestCase):
    def get_app(self):
        self.app = Application(self.get_handlers())
        return self.app

    def get_handlers(self):
        from consoleme.handlers.base import BaseJSONHandler

        class JSONHandlerExample(BaseJSONHandler):
            def __init__(self, *args, **kwargs):
                kwargs["jwt_validator"] = TEST_VALIDATOR
                super().__init__(*args, **kwargs)

            def get_app(self):
                self.app = Application(self.get_handlers(), **self.get_app_kwargs())
                return self.app

            def get(self):
                self.write("hello")

        return [("/", JSONHandlerExample)]

    def test_missing_auth_header(self):
        response = self.fetch("/")
        self.assertEqual(response.code, 401)

    def test_invalid_auth_header(self):
        response = self.fetch("/", headers={"Authorization": "foo"})
        self.assertEqual(response.code, 401)
        self.assertEqual(json.loads(response.body)["message"], "Invalid Token")

    def test_invalid_jwt(self):
        payload = {"foo": "bar"}
        tkn = jwt.encode(payload, "WRONG_SECRET", algorithm=TEST_ALG[0])
        response = self.fetch("/", headers={"Authorization": tkn})
        self.assertEqual(response.code, 401)
        self.assertEqual(
            json.loads(response.body)["message"], "Invalid Token Signature"
        )

    def test_valid_jwt(self):
        payload = {"email": "cnorris@example.com"}
        tkn = jwt.encode(payload, TEST_SECRET, algorithm=TEST_ALG[0])
        response = self.fetch("/", headers={"Authorization": tkn})
        self.assertEqual(response.code, 200)
        self.assertEqual(response.body, b"hello")
