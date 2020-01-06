"""Docstring in public module."""

import os
import sys

from tests.conftest import create_future
from mock import patch, Mock
from mockredis import mock_strict_redis_client
from tornado.concurrent import Future
from tornado.testing import AsyncHTTPTestCase

from consoleme.routes import make_app

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(APP_ROOT, ".."))


class TestAutologinHandler(AsyncHTTPTestCase):
    def get_app(self):
        return make_app(jwt_validator=lambda x: {})

    @patch("consoleme_internal.plugins.group_mapping.group_mapping.RedisHandler")
    @patch("consoleme.handlers.base.RedisHandler")
    @patch("consoleme_internal.plugins.auth.auth.AsyncHTTPClient")
    def test_role_pageload(
        self, async_http_client, mock_redis_handler, mock_gm_redis_handler
    ):
        group_return_value = Mock()
        group_return_value.body = "{}"
        async_http_client.return_value.fetch.return_value = create_future(
            group_return_value
        )
        red = mock_strict_redis_client()
        red.set("SWAG_SETTINGS_ID_TO_NAMEv2", '{"12345": ["accountname"]}')
        mock_redis = Future()
        mock_redis.set_result(red)
        mock_redis_handler.return_value.redis.return_value = mock_redis
        mock_gm_redis_handler.return_value.redis.return_value = mock_redis

        headers = {
            "Oidc_claim_sub": "user@github.com",
            "Oidc_claim_googlegroups": "groupa,groupb,groupc",
            "Oidc_claim_userid": "1" * 21,
        }

        response = self.fetch("/role/role123", headers=headers)
        self.assertEqual(response.code, 200)
        self.assertIn(b"reset_aws_auth_cookie", response.body)
