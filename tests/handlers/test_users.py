"""Docstring in public module."""

import os
import sys
import jwt

import ujson as json
from tornado.escape import json_decode
from mock import MagicMock, patch
from mockredis import mock_strict_redis_client
from tornado.concurrent import Future
from tornado.ioloop import IOLoop
from tornado.testing import AsyncHTTPTestCase
from consoleme.lib.auth import mk_jwt_validator

from consoleme.routes import make_app
from tests.conftest import MockAuth, MockBaseHandler

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(APP_ROOT, ".."))

fake_user = {
    "userName": "test@example.com",
    "domain": "example.com",
    "name": {"fullName": "Test User"},
    "status": "active",
}

fake_groups = ["groupfizzygoblin", "group7glarb"]


# monkey patch MagicMock
async def async_magic():
    pass


MagicMock.__await__ = lambda x: async_magic().__await__()


class TestUsersHandler(AsyncHTTPTestCase):
    def get_app(self):
        return make_app(jwt_validator=lambda x: {})

    def get_new_ioloop(self):
        return IOLoop.instance()

    @patch(
        "consoleme.handlers.users.UsersHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    @patch("consoleme.handlers.base.RedisHandler")
    def test_users_pageload(self, mock_redis_handler):
        mock_redis = Future()
        mock_redis.set_result(mock_strict_redis_client())
        mock_redis_handler.return_value.redis.return_value = mock_redis
        headers = {
            "Oidc_claim_sub": "user@github.com",
            "Oidc_claim_googlegroups": "groupa,groupb,groupc",
        }

        response = self.fetch("/accessui/users", headers=headers)
        self.assertEqual(response.code, 200)
        self.assertIn(
            b"<th>Full Name</th>\n<th>Username</th>\n<th>Status</th>", response.body
        )

    def test_users_page_redirect(self):
        from consoleme.config.config import CONFIG

        old_value = CONFIG.config["dynamic_config"]["accessui"].pop("deprecate", None)
        CONFIG.config["dynamic_config"]["accessui"]["deprecate"] = True

        headers = {
            "Oidc_claim_sub": "user@github.com",
            "Oidc_claim_googlegroups": "groupa,groupb,groupc",
        }

        base_url = CONFIG.config.get("accessui_url")

        response = self.fetch(
            "/accessui/users", headers=headers, follow_redirects=False
        )
        self.assertEqual(response.code, 301)
        self.assertEqual(response.headers["Location"], f"{base_url}/users")

        # Reset the config values:
        if not old_value:
            del CONFIG.config["dynamic_config"]["accessui"]["deprecate"]
        else:
            CONFIG.config["dynamic_config"]["accessui"]["deprecate"] = old_value

    @patch(
        "consoleme.handlers.users.UserHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    @patch("consoleme.handlers.base.RedisHandler")
    @patch("consoleme.handlers.users.auth")
    def test_user_pageload(self, mock_auth, mock_redis_handler):
        get_user_info = Future()
        get_user_info.set_result(fake_user)

        get_group_memberships = Future()
        get_group_memberships.set_result(fake_groups)

        mock_auth.get_user_info.return_value = get_user_info
        mock_auth.get_group_memberships.return_value = get_group_memberships

        mock_redis = Future()
        mock_redis.set_result(mock_strict_redis_client())
        mock_redis_handler.return_value.redis.return_value = mock_redis
        headers = {
            "Oidc_claim_sub": "user@github.com",
            "Oidc_claim_googlegroups": "groupa,groupb,groupc",
        }

        response = self.fetch("/accessui/user/test@example.com", headers=headers)
        self.assertEqual(response.code, 200)
        self.assertIn(b"groupfizzygoblin", response.body)

    def test_user_page_redirect(self):
        from consoleme.config.config import CONFIG

        old_value = CONFIG.config["dynamic_config"]["accessui"].pop("deprecate", None)
        CONFIG.config["dynamic_config"]["accessui"]["deprecate"] = True

        headers = {
            "Oidc_claim_sub": "user@github.com",
            "Oidc_claim_googlegroups": "groupa,groupb,groupc",
        }

        base_url = CONFIG.config.get("accessui_url")

        response = self.fetch(
            "/accessui/user/test@example.com", headers=headers, follow_redirects=False
        )
        self.assertEqual(response.code, 301)
        self.assertEqual(
            response.headers["Location"], f"{base_url}/users/test@example.com"
        )

        # Reset the config values:
        if not old_value:
            del CONFIG.config["dynamic_config"]["accessui"]["deprecate"]
        else:
            CONFIG.config["dynamic_config"]["accessui"]["deprecate"] = old_value

    @patch(
        "consoleme.handlers.users.UserHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    @patch("consoleme.handlers.base.RedisHandler")
    @patch("consoleme.handlers.users.auth")
    @patch("consoleme.lib.google.can_modify_members", return_value=False)
    @patch("consoleme.lib.google.auth", MockAuth())
    def test_user_add_remove_group(
        self, mock_modify_members, mock_auth, mock_redis_handler
    ):
        get_user_info = Future()
        get_user_info.set_result(fake_user)

        get_group_memberships = Future()
        get_group_memberships.set_result(fake_groups)

        mock_auth.get_user_info.return_value = get_user_info
        mock_auth.get_group_memberships.return_value = get_group_memberships

        mock_redis = Future()
        mock_redis.set_result(mock_strict_redis_client())
        mock_redis_handler.return_value.redis.return_value = mock_redis

        headers = {
            "content-type": "application/json",
            "Oidc_claim_sub": "user@github.com",
            "Oidc_claim_googlegroups": "groupa,groupb,groupc",
        }

        data = [
            {"name": "add_groups", "value": "test@example.com"},
            {"name": "remove_groups", "value": ""},
        ]

        response = self.fetch(
            "/accessui/user/test@example.com",
            headers=headers,
            method="POST",
            body=json.dumps(data),
        )
        self.assertEqual(response.code, 200)
        self.assertIn(
            b"You are unable to add members to this group. Maybe it is restricted",
            response.body,
        )

        data = [
            {"name": "add_groups", "value": ""},
            {"name": "remove_groups", "value": "test@example.com"},
        ]

        response = self.fetch(
            "/accessui/user/test@example.com",
            headers=headers,
            method="POST",
            body=json.dumps(data),
        )
        self.assertEqual(response.code, 200)
        self.assertIn(b"There was at least one problem.", response.body)


TEST_SECRET = "SECRET"
TEST_GROUPS = ["group%d" % x for x in range(5)]
TEST_PAYLOAD = {"email": "user@github.com", "google_groups": TEST_GROUPS}
TEST_ALG = "HS256"
jwt_validator = mk_jwt_validator(TEST_SECRET, {"alg": {"enum": [TEST_ALG]}}, {})

tkn = jwt.encode(TEST_PAYLOAD, TEST_SECRET, algorithm=TEST_ALG)
tkn = tkn.decode("utf-8")
headers = {"Authorization": "Bearer %s" % tkn}


def create_future(ret_val=None):
    future = Future()
    future.set_result(ret_val)
    return future


class TestJSONBulkUserMembershipHandler(AsyncHTTPTestCase):
    def get_app(self):
        return make_app(jwt_validator=jwt_validator)

    @patch("consoleme.handlers.users.api_add_user_to_group_or_raise")
    def test_bulk_add(self, mock_api_add_user_to_group_or_raise):
        groups = ["stooges@example.com", "bald@example.com", "film@example.com"]
        member_name = "curly@example.com"

        def side_effect(group_name, member_name, actor):
            if group_name == groups[0]:
                return create_future("ADDED")
            if group_name == groups[1]:
                return create_future("REQUESTED")
            if group_name == groups[2]:
                future = Future()
                future.set_exception(Exception("foobar"))
                return future

        mock_api_add_user_to_group_or_raise.side_effect = side_effect

        response = self.fetch(
            f"/api/v1/users/{member_name}/memberships",
            headers=headers,
            method="POST",
            body=b'["stooges@example.com", "bald@example.com", "film@example.com"]',
        )

        body = json_decode(response.body)
        self.assertEqual(response.code, 200)

        self.assertEqual(body[0]["success"], True)
        self.assertEqual(body[0]["status"], "ADDED")
        self.assertEqual(body[0]["group"], groups[0])

        self.assertEqual(body[1]["success"], True)
        self.assertEqual(body[1]["status"], "REQUESTED")
        self.assertEqual(body[1]["group"], groups[1])

        self.assertEqual(body[2]["success"], False)
        self.assertEqual(body[2]["status"], "FAILED")
        self.assertEqual(body[2]["message"], "foobar")
        self.assertEqual(body[2]["group"], groups[2])
