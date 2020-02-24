"""Docstring in public module."""

import os
import sys

from consoleme.config import config

from tests.conftest import create_future
from mock import patch, Mock
from mockredis import mock_strict_redis_client
from tornado.concurrent import Future
from tornado.testing import AsyncHTTPTestCase

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(APP_ROOT, ".."))


class TestAutologinHandler(AsyncHTTPTestCase):
    def get_app(self):
        from consoleme.routes import make_app
        return make_app(jwt_validator=lambda x: {})

    def test_role_pageload(
        self
    ):
        red = mock_strict_redis_client()
        red.set("SWAG_SETTINGS_ID_TO_NAMEv2", '{"12345": ["accountname"]}')

        headers = {
            config.get("auth.user_header_name"): "user@example.com",
            config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }

        response = self.fetch("/role/role123", headers=headers)
        self.assertEqual(response.code, 200)
        self.assertIn(b"reset_aws_auth_cookie", response.body)
