"""Docstring in public module."""

import os
import sys

import jwt
from mock import patch, Mock
from mockredis import mock_strict_redis_client
from tornado.concurrent import Future
from tornado.testing import AsyncHTTPTestCase
from tornado.ioloop import IOLoop
from tornado.escape import json_decode

from consoleme.config import config
from consoleme.lib.auth import mk_jwt_validator
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.routes import make_app
from tests.conftest import MockAuth
from tests.conftest import MockBaseHandler

auth = get_plugin_by_name(config.get("plugins.auth"))()

Group = auth.Group
User = auth.User

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(APP_ROOT, ".."))


class TestRequestHandler(AsyncHTTPTestCase):
    def get_app(self):
        return make_app(jwt_validator=lambda x: {})

    def get_new_ioloop(self):
        return IOLoop.instance()

    @patch(
        "consoleme.handlers.request.RequestGroupHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    @patch("consoleme.handlers.request.auth", MockAuth())
    @patch("consoleme.handlers.base.RedisHandler")
    def test_requestgroup_pageload(self, mock_redis_handler):
        mock_redis_handler.return_value.redis.return_value = create_future(
            mock_strict_redis_client()
        )
        headers = {
            "Oidc_claim_sub": "user@github.com",
            "Oidc_claim_googlegroups": "groupa,groupb,groupc",
        }

        response = self.fetch(
            "/accessui/request_access/group_to_request@domain.com", headers=headers
        )
        self.assertEqual(response.code, 200)
        self.assertIn(
            b"Secondary Approvers: groupapprover1, groupapprover2", response.body
        )

    def test_requestgroup_page_redirect(self):
        from consoleme.config.config import CONFIG

        old_value = CONFIG.config["dynamic_config"]["accessui"].pop("deprecate", None)
        CONFIG.config["dynamic_config"]["accessui"]["deprecate"] = True

        headers = {
            "Oidc_claim_sub": "user@github.com",
            "Oidc_claim_googlegroups": "groupa,groupb,groupc",
        }

        base_url = CONFIG.config.get("accessui_url")

        response = self.fetch(
            "/accessui/request_access/group_to_request@domain.com",
            headers=headers,
            follow_redirects=False,
        )
        self.assertEqual(response.code, 301)
        self.assertEqual(
            response.headers["Location"],
            f"{base_url}/groups/group_to_request@domain.com",
        )

        # Reset the config values:
        if not old_value:
            del CONFIG.config["dynamic_config"]["accessui"]["deprecate"]
        else:
            CONFIG.config["dynamic_config"]["accessui"]["deprecate"] = old_value

    @patch(
        "consoleme.handlers.request.ShowManageablePendingRequests.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    @patch("consoleme.handlers.request.get_all_pending_requests")
    @patch("consoleme.handlers.base.RedisHandler")
    def test_show_pending(self, mock_redis_handler, mock_get_all_pending_requests):
        mock_get_all_pending_requests_value = Future()
        mock_get_all_pending_requests_value.set_result({})
        mock_get_all_pending_requests.return_value = mock_get_all_pending_requests_value

        mock_redis_handler.return_value.redis.return_value = create_future(
            mock_strict_redis_client()
        )
        headers = {
            "Oidc_claim_sub": "user@github.com",
            "Oidc_claim_googlegroups": "groupa,groupb,groupc",
        }

        response = self.fetch("/accessui/pending", headers=headers)
        self.assertEqual(response.code, 200)
        self.assertIn(b"All Pending Requests", response.body)

    @patch("consoleme_internal.plugins.auth.auth.AsyncHTTPClient")
    @patch("consoleme.lib.requests.UserDynamoHandler")
    def test_pending_page_redirect(self, dynamo_handler, mock_http_client):
        from consoleme.config.config import CONFIG

        dynamo_handler.return_value.get_all_requests.return_value = {}
        p_return_value = Mock()
        p_return_value.body = "{}"
        mock_http_client.return_value.fetch.return_value = create_future(p_return_value)

        old_value = CONFIG.config["dynamic_config"]["accessui"].pop("deprecate", None)
        CONFIG.config["dynamic_config"]["accessui"]["deprecate"] = False

        headers = {
            "Oidc_claim_sub": "user@github.com",
            "Oidc_claim_googlegroups": "groupa,groupb,groupc",
        }

        response = self.fetch(
            "/accessui/pending", headers=headers, follow_redirects=False
        )
        self.assertEqual(response.code, 200)

        # Reset the config values:
        if not old_value:
            del CONFIG.config["dynamic_config"]["accessui"]["deprecate"]
        else:
            CONFIG.config["dynamic_config"]["accessui"]["deprecate"] = old_value

    @patch(
        "consoleme.handlers.request.RequestGroupHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    @patch("consoleme.handlers.request.auth", MockAuth())
    @patch("consoleme.handlers.base.RedisHandler")
    def test_requestgroup_wrong_domain(self, mock_redis_handler):
        mock_redis_handler.return_value.redis.return_value = create_future(
            mock_strict_redis_client()
        )
        headers = {
            "Oidc_claim_sub": "user@github.com",
            "Oidc_claim_googlegroups": "groupa,groupb,groupc",
        }

        response = self.fetch(
            "/accessui/request_access/group_to_request@domain2.com", headers=headers
        )
        self.assertIn(
            b"You are unable to request access to group_to_request@domain2.com because the group's domain "
            b"is domain2.com and your domain is domain.com. This group is not configured to allow cross domain "
            b"users to request access to it yet. Please contact the owner of this group, or #nerds if this group "
            b"should be requestable by cross-domain users.",
            response.body,
        )

    @patch(
        "consoleme.handlers.request.RequestGroupHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    @patch("consoleme.handlers.request.auth", MockAuth(compliance_restricted=True))
    @patch("consoleme.handlers.base.RedisHandler")
    def test_requestgroup_compliance_restricted(self, mock_redis_handler):
        # Compliance groups can be requested now.
        mock_redis_handler.return_value.redis.return_value = create_future(
            mock_strict_redis_client()
        )
        headers = {
            "Oidc_claim_sub": "user@github.com",
            "Oidc_claim_googlegroups": "groupa,groupb,groupc",
        }

        response = self.fetch(
            "/accessui/request_access/group_to_request@domain.com", headers=headers
        )
        self.assertIn(b"Please enter your justification.", response.body)

    @patch(
        "consoleme.handlers.request.RequestGroupHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    @patch("consoleme.handlers.request.auth", MockAuth(restricted=True))
    @patch("consoleme.handlers.base.RedisHandler")
    def test_requestgroup_restricted(self, mock_redis_handler):
        mock_redis_handler.return_value.redis.return_value = create_future(
            mock_strict_redis_client()
        )
        headers = {
            "Oidc_claim_sub": "user@github.com",
            "Oidc_claim_googlegroups": "groupa,groupb,groupc",
            "Cookie": "bypass_accessui_deprecate=bypass_accessui_deprecate",
        }

        response = self.fetch(
            "/accessui/request_access/group_to_request@domain.com", headers=headers
        )
        self.assertIn(
            b"You are unable to request access to the group_to_request@domain.com group because this "
            b"group is marked as 'restricted'. This means that Consoleme will not be able to add users "
            b"to this group due to its sensitivity. Please contact #nerds to request access.",
            response.body,
        )


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


class TestJSONBaseRequestHandler(AsyncHTTPTestCase):
    def get_app(self):
        return make_app(jwt_validator=jwt_validator)

    @patch("consoleme.handlers.base.RedisHandler")
    @patch("consoleme.handlers.request.get_all_pending_requests_api")
    def test_requests(self, mock_get_all_pending_requests_api, mock_redis_handler):
        mock_get_all_pending_requests_api.return_value = create_future([])

        mock_redis_handler.return_value.redis.return_value = create_future(
            mock_strict_redis_client()
        )

        response = self.fetch("/api/v1/requests", headers=headers)
        self.assertEqual(response.code, 200)
        self.assertEqual(json_decode(response.body), [])

    @patch("consoleme.handlers.base.RedisHandler")
    def test_request_create_422(self, mock_redis_handler):
        mock_redis_handler.return_value.redis.return_value = create_future(
            mock_strict_redis_client()
        )

        request_body = b'{"group": "myGroup"}'
        response = self.fetch(
            f"/api/v1/requests", headers=headers, method="POST", body=request_body
        )
        body = json_decode(response.body)

        self.assertEqual(response.code, 422)
        self.assertEqual(
            body.get("message"),
            "A requested group and justification must be passed to this endpoint.",
        )

    @patch("consoleme.handlers.base.RedisHandler")
    @patch("consoleme.handlers.request.auth")
    @patch("consoleme.handlers.request.get_existing_pending_request")
    @patch("consoleme.handlers.request.can_user_request_group_based_on_domain")
    @patch("consoleme.handlers.request.does_group_require_bg_check")
    def test_request_create_403_in_group(
        self,
        mock_does_group_require_bg_check,
        mock_can_user_request_group_based_on_domain,
        mock_get_existing_pending_request,
        mock_auth,
        mock_redis_handler,
    ):
        mock_redis_handler.return_value.redis.return_value = create_future(
            mock_strict_redis_client()
        )

        mock_user = User(**{"passed_background_check": True})
        mock_user_groups = ["myGroup"]
        mock_existing_request = None
        mock_group_info = Group(
            **{"requestable": True, "restricted": False, "name": "myGroup"}
        )

        mock_auth.get_group_info.return_value = create_future(mock_group_info)
        mock_auth.get_user_info.return_value = create_future(mock_user)
        mock_auth.get_groups.return_value = create_future(mock_user_groups)
        mock_get_existing_pending_request.return_value = create_future(
            mock_existing_request
        )
        mock_can_user_request_group_based_on_domain.return_value = True
        mock_does_group_require_bg_check.return_value = False

        request_body = b'{"justification": "because", "group": "myGroup"}'
        response = self.fetch(
            f"/api/v1/requests", headers=headers, method="POST", body=request_body
        )
        body = json_decode(response.body)

        self.assertEqual(response.code, 403)
        self.assertEqual(
            body.get("message"),
            "You are already in this group and are unable to request access.",
        )

    @patch("consoleme.handlers.base.RedisHandler")
    @patch("consoleme.handlers.request.auth")
    @patch("consoleme.handlers.request.get_existing_pending_request")
    @patch("consoleme.handlers.request.can_user_request_group_based_on_domain")
    @patch("consoleme.handlers.request.does_group_require_bg_check")
    def test_request_create_403_existing_request(
        self,
        mock_does_group_require_bg_check,
        mock_can_user_request_group_based_on_domain,
        mock_get_existing_pending_request,
        mock_auth,
        mock_redis_handler,
    ):
        mock_redis_handler.return_value.redis.return_value = create_future(
            mock_strict_redis_client()
        )

        mock_user = User(**{"passed_background_check": True})
        mock_user_groups = []
        mock_existing_request = {"request_id": 123456}
        mock_group_info = Group(
            **{"requestable": True, "restricted": False, "name": "myGroup"}
        )

        mock_auth.get_group_info.return_value = create_future(mock_group_info)
        mock_auth.get_user_info.return_value = create_future(mock_user)
        mock_auth.get_groups.return_value = create_future(mock_user_groups)
        mock_get_existing_pending_request.return_value = create_future(
            mock_existing_request
        )
        mock_can_user_request_group_based_on_domain.return_value = True
        mock_does_group_require_bg_check.return_value = False

        request_body = b'{"justification": "because", "group": "myGroup"}'
        response = self.fetch(
            f"/api/v1/requests", headers=headers, method="POST", body=request_body
        )
        body = json_decode(response.body)

        self.assertEqual(response.code, 403)
        self.assertEqual(
            body.get("message"),
            f"You already have a pending or approved request for this group. Request id: "
            f"{mock_existing_request.get('request_id')}",
        )

    @patch("consoleme.handlers.base.RedisHandler")
    @patch("consoleme.handlers.request.auth")
    @patch("consoleme.handlers.request.get_existing_pending_request")
    @patch("consoleme.handlers.request.can_user_request_group_based_on_domain")
    @patch("consoleme.handlers.request.does_group_require_bg_check")
    def test_request_create_403_not_requestable(
        self,
        mock_does_group_require_bg_check,
        mock_can_user_request_group_based_on_domain,
        mock_get_existing_pending_request,
        mock_auth,
        mock_redis_handler,
    ):
        mock_redis_handler.return_value.redis.return_value = create_future(
            mock_strict_redis_client()
        )

        mock_user = User(**{"passed_background_check": True})
        mock_user_groups = []
        mock_existing_request = None
        mock_group_info = Group(
            **{"requestable": False, "restricted": False, "name": "myGroup"}
        )

        mock_auth.get_group_info.return_value = create_future(mock_group_info)
        mock_auth.get_user_info.return_value = create_future(mock_user)
        mock_auth.get_groups.return_value = create_future(mock_user_groups)
        mock_get_existing_pending_request.return_value = create_future(
            mock_existing_request
        )
        mock_can_user_request_group_based_on_domain.return_value = True
        mock_does_group_require_bg_check.return_value = False

        request_body = b'{"justification": "because", "group": "myGroup"}'
        response = self.fetch(
            f"/api/v1/requests", headers=headers, method="POST", body=request_body
        )
        body = json_decode(response.body)

        self.assertEqual(response.code, 403)
        self.assertEqual(body.get("message"), "This group is not requestable.")

    @patch("consoleme.handlers.base.RedisHandler")
    @patch("consoleme.handlers.request.auth")
    @patch("consoleme.handlers.request.get_existing_pending_request")
    @patch("consoleme.handlers.request.can_user_request_group_based_on_domain")
    @patch("consoleme.handlers.request.does_group_require_bg_check")
    def test_request_create_403_restricted(
        self,
        mock_does_group_require_bg_check,
        mock_can_user_request_group_based_on_domain,
        mock_get_existing_pending_request,
        mock_auth,
        mock_redis_handler,
    ):
        mock_redis_handler.return_value.redis.return_value = create_future(
            mock_strict_redis_client()
        )

        mock_user = User(**{"passed_background_check": True})
        mock_user_groups = []
        mock_existing_request = None
        mock_group_info = Group(
            **{"requestable": True, "restricted": True, "name": "myGroup"}
        )

        mock_auth.get_group_info.return_value = create_future(mock_group_info)
        mock_auth.get_user_info.return_value = create_future(mock_user)
        mock_auth.get_groups.return_value = create_future(mock_user_groups)
        mock_get_existing_pending_request.return_value = create_future(
            mock_existing_request
        )
        mock_can_user_request_group_based_on_domain.return_value = True
        mock_does_group_require_bg_check.return_value = False

        request_body = b'{"justification": "because", "group": "myGroup"}'
        response = self.fetch(
            f"/api/v1/requests", headers=headers, method="POST", body=request_body
        )
        body = json_decode(response.body)

        self.assertEqual(response.code, 403)
        self.assertEqual(body.get("message"), "This group is marked as 'restricted'.")

    @patch("consoleme.handlers.base.RedisHandler")
    @patch("consoleme.handlers.request.auth")
    @patch("consoleme.handlers.request.get_existing_pending_request")
    @patch("consoleme.handlers.request.can_user_request_group_based_on_domain")
    @patch("consoleme.handlers.request.does_group_require_bg_check")
    def test_request_create_403_cross_domain(
        self,
        mock_does_group_require_bg_check,
        mock_can_user_request_group_based_on_domain,
        mock_get_existing_pending_request,
        mock_auth,
        mock_redis_handler,
    ):
        mock_redis_handler.return_value.redis.return_value = create_future(
            mock_strict_redis_client()
        )

        mock_user = User(**{"passed_background_check": True})
        mock_user_groups = []
        mock_existing_request = None
        mock_group_info = Group(
            **{"requestable": True, "restricted": False, "name": "myGroup"}
        )

        mock_auth.get_group_info.return_value = create_future(mock_group_info)
        mock_auth.get_user_info.return_value = create_future(mock_user)
        mock_auth.get_groups.return_value = create_future(mock_user_groups)
        mock_get_existing_pending_request.return_value = create_future(
            mock_existing_request
        )
        mock_can_user_request_group_based_on_domain.return_value = False
        mock_does_group_require_bg_check.return_value = False

        request_body = b'{"justification": "because", "group": "myGroup"}'
        response = self.fetch(
            f"/api/v1/requests", headers=headers, method="POST", body=request_body
        )
        body = json_decode(response.body)

        self.assertEqual(response.code, 403)
        self.assertEqual(
            body.get("message"),
            "You are not in this group's domain and the group does not allow cross domain membership.",
        )

    @patch("consoleme.handlers.base.RedisHandler")
    @patch("consoleme.handlers.request.auth")
    @patch("consoleme.handlers.request.get_existing_pending_request")
    @patch("consoleme.handlers.request.can_user_request_group_based_on_domain")
    @patch("consoleme.handlers.request.does_group_require_bg_check")
    def test_request_create_403_bg_check(
        self,
        mock_does_group_require_bg_check,
        mock_can_user_request_group_based_on_domain,
        mock_get_existing_pending_request,
        mock_auth,
        mock_redis_handler,
    ):
        mock_redis_handler.return_value.redis.return_value = create_future(
            mock_strict_redis_client()
        )

        mock_user = User(**{"passed_background_check": False})
        mock_user_groups = []
        mock_existing_request = None
        mock_group_info = Group(
            **{"requestable": True, "restricted": False, "name": "myGroup"}
        )

        mock_auth.get_group_info.return_value = create_future(mock_group_info)
        mock_auth.get_user_info.return_value = create_future(mock_user)
        mock_auth.get_groups.return_value = create_future(mock_user_groups)
        mock_get_existing_pending_request.return_value = create_future(
            mock_existing_request
        )
        mock_can_user_request_group_based_on_domain.return_value = True
        mock_does_group_require_bg_check.return_value = True

        request_body = b'{"justification": "because", "group": "myGroup"}'
        response = self.fetch(
            f"/api/v1/requests", headers=headers, method="POST", body=request_body
        )
        body = json_decode(response.body)

        self.assertEqual(response.code, 403)
        self.assertEqual(
            body.get("message"),
            f"User {'user@github.com'} has not passed background check. Group {mock_group_info.name} "
            f"requires a background check. Please contact Nerds",
        )

    @patch("consoleme.handlers.base.RedisHandler")
    @patch("consoleme.handlers.request.auth")
    @patch("consoleme.handlers.request.get_existing_pending_request")
    @patch("consoleme.handlers.request.can_user_request_group_based_on_domain")
    @patch("consoleme.handlers.request.does_group_require_bg_check")
    @patch("consoleme.handlers.request.get_accessui_request_review_url")
    @patch("consoleme.handlers.request.send_request_created_to_user")
    @patch("consoleme.handlers.request.send_request_to_secondary_approvers")
    @patch("consoleme.handlers.request.add_user_to_group")
    @patch("consoleme.handlers.request.send_access_email_to_user")
    @patch("consoleme.lib.dynamo.UserDynamoHandler.add_request")
    def test_request_create_approved(
        self,
        mock_add_request,
        mock_send_access_email_to_user,
        mock_add_user_to_group,
        mock_send_request_to_secondary_approvers,
        mock_send_request_created_to_user,
        mock_get_accessui_request_review_url,
        mock_does_group_require_bg_check,
        mock_can_user_request_group_based_on_domain,
        mock_get_existing_pending_request,
        mock_auth,
        mock_redis_handler,
    ):
        mock_redis_handler.return_value.redis.return_value = create_future(
            mock_strict_redis_client()
        )

        mock_request = {"request_id": 123456}
        mock_user = User(**{"passed_background_check": True})
        mock_user_groups = []
        mock_existing_request = None
        mock_group_info = Group(
            **{"requestable": True, "restricted": False, "name": "myGroup"}
        )

        mock_auth.get_group_info.return_value = create_future(mock_group_info)
        mock_auth.get_user_info.return_value = create_future(mock_user)
        mock_auth.get_groups.return_value = create_future(mock_user_groups)
        mock_get_existing_pending_request.return_value = create_future(
            mock_existing_request
        )
        mock_can_user_request_group_based_on_domain.return_value = True
        mock_does_group_require_bg_check.return_value = False
        mock_add_request.return_value = mock_request
        mock_get_accessui_request_review_url.return_value = ""
        mock_send_access_email_to_user.return_value = create_future()
        mock_add_user_to_group.return_value = create_future()
        mock_send_request_to_secondary_approvers.return_value = create_future()
        mock_send_request_created_to_user.return_value = create_future()

        request_body = b'{"justification": "because", "group": "myGroup"}'
        response = self.fetch(
            f"/api/v1/requests", headers=headers, method="POST", body=request_body
        )
        body = json_decode(response.body)

        self.assertEqual(
            mock_send_request_created_to_user.call_count, 0, "pending email"
        )
        self.assertEqual(mock_add_user_to_group.call_count, 1, "add user to group")
        self.assertEqual(mock_send_access_email_to_user.call_count, 1, "success email")
        self.assertEqual(response.code, 200)
        self.assertEqual(body, mock_request)

    @patch("consoleme.handlers.base.RedisHandler")
    @patch("consoleme.handlers.request.auth")
    @patch("consoleme.handlers.request.get_existing_pending_request")
    @patch("consoleme.handlers.request.can_user_request_group_based_on_domain")
    @patch("consoleme.handlers.request.does_group_require_bg_check")
    @patch("consoleme.handlers.request.get_accessui_request_review_url")
    @patch("consoleme.handlers.request.send_request_created_to_user")
    @patch("consoleme.handlers.request.send_request_to_secondary_approvers")
    @patch("consoleme.handlers.request.add_user_to_group")
    @patch("consoleme.handlers.request.send_access_email_to_user")
    @patch("consoleme.lib.dynamo.UserDynamoHandler.add_request")
    def test_request_create_approved_is_approver(
        self,
        mock_add_request,
        mock_send_access_email_to_user,
        mock_add_user_to_group,
        mock_send_request_to_secondary_approvers,
        mock_send_request_created_to_user,
        mock_get_accessui_request_review_url,
        mock_does_group_require_bg_check,
        mock_can_user_request_group_based_on_domain,
        mock_get_existing_pending_request,
        mock_auth,
        mock_redis_handler,
    ):
        mock_redis_handler.return_value.redis.return_value = create_future(
            mock_strict_redis_client()
        )

        mock_request = {"request_id": 123456}
        mock_user = User(**{"passed_background_check": True})
        mock_user_groups = ["group1"]
        mock_existing_request = None
        mock_group_info = Group(
            **{
                "secondary_approvers": "group1",
                "requestable": True,
                "restricted": False,
                "name": "myGroup",
            }
        )

        mock_auth.get_group_info.return_value = create_future(mock_group_info)
        mock_auth.get_user_info.return_value = create_future(mock_user)
        mock_auth.get_groups.return_value = create_future(mock_user_groups)
        mock_get_existing_pending_request.return_value = create_future(
            mock_existing_request
        )
        mock_can_user_request_group_based_on_domain.return_value = True
        mock_does_group_require_bg_check.return_value = False
        mock_add_request.return_value = mock_request
        mock_get_accessui_request_review_url.return_value = ""
        mock_send_access_email_to_user.return_value = create_future()
        mock_add_user_to_group.return_value = create_future()
        mock_send_request_to_secondary_approvers.return_value = create_future()
        mock_send_request_created_to_user.return_value = create_future()

        request_body = b'{"justification": "because", "group": "myGroup"}'
        response = self.fetch(
            f"/api/v1/requests", headers=headers, method="POST", body=request_body
        )
        body = json_decode(response.body)

        self.assertEqual(
            mock_send_request_created_to_user.call_count, 0, "pending email"
        )
        self.assertEqual(mock_add_user_to_group.call_count, 1, "add user to group")
        self.assertEqual(mock_send_access_email_to_user.call_count, 1, "success email")
        self.assertEqual(response.code, 200)
        self.assertEqual(body, mock_request)

    @patch("consoleme.handlers.base.RedisHandler")
    @patch("consoleme.handlers.request.auth")
    @patch("consoleme.handlers.request.get_existing_pending_request")
    @patch("consoleme.handlers.request.can_user_request_group_based_on_domain")
    @patch("consoleme.handlers.request.does_group_require_bg_check")
    @patch("consoleme.handlers.request.get_accessui_request_review_url")
    @patch("consoleme.handlers.request.send_request_created_to_user")
    @patch("consoleme.handlers.request.send_request_to_secondary_approvers")
    @patch("consoleme.handlers.request.add_user_to_group")
    @patch("consoleme.handlers.request.send_access_email_to_user")
    @patch("consoleme.lib.dynamo.UserDynamoHandler.add_request")
    def test_request_create_pending(
        self,
        mock_add_request,
        mock_send_access_email_to_user,
        mock_add_user_to_group,
        mock_send_request_to_secondary_approvers,
        mock_send_request_created_to_user,
        mock_get_accessui_request_review_url,
        mock_does_group_require_bg_check,
        mock_can_user_request_group_based_on_domain,
        mock_get_existing_pending_request,
        mock_auth,
        mock_redis_handler,
    ):
        mock_redis_handler.return_value.redis.return_value = create_future(
            mock_strict_redis_client()
        )

        mock_request = {"request_id": 123456}
        mock_user = User(**{"passed_background_check": True})
        mock_user_groups = []
        mock_existing_request = None
        mock_group_info = Group(
            **{
                "requestable": True,
                "restricted": False,
                "name": "myGroup",
                "secondary_approvers": "group1",
            }
        )

        mock_auth.get_group_info.return_value = create_future(mock_group_info)
        mock_auth.get_user_info.return_value = create_future(mock_user)
        mock_auth.get_groups.return_value = create_future(mock_user_groups)
        mock_get_existing_pending_request.return_value = create_future(
            mock_existing_request
        )
        mock_can_user_request_group_based_on_domain.return_value = True
        mock_does_group_require_bg_check.return_value = False
        mock_add_request.return_value = mock_request
        mock_get_accessui_request_review_url.return_value = ""
        mock_send_access_email_to_user.return_value = create_future()
        mock_add_user_to_group.return_value = create_future()
        mock_send_request_to_secondary_approvers.return_value = create_future()
        mock_send_request_created_to_user.return_value = create_future()

        request_body = b'{"justification": "because", "group": "myGroup"}'
        response = self.fetch(
            f"/api/v1/requests", headers=headers, method="POST", body=request_body
        )
        body = json_decode(response.body)

        self.assertEqual(
            mock_send_request_created_to_user.call_count, 1, "pending email"
        )
        self.assertEqual(mock_add_user_to_group.call_count, 0, "add user to group")
        self.assertEqual(mock_send_access_email_to_user.call_count, 0, "success email")
        self.assertEqual(response.code, 200)
        self.assertEqual(body, mock_request)


class TestJSONUserRequestHandler(AsyncHTTPTestCase):
    def get_app(self):
        return make_app(jwt_validator=jwt_validator)

    @patch("consoleme.handlers.base.RedisHandler")
    @patch("consoleme.handlers.request.get_request_by_id")
    def test_requests_404(self, mock_get_request_by_id, mock_redis_handler):
        mock_get_request_by_id.return_value = create_future(None)

        mock_redis_handler.return_value.redis.return_value = create_future(
            mock_strict_redis_client()
        )

        request_id = 123456
        response = self.fetch(f"/api/v1/requests/{request_id}", headers=headers)
        body = json_decode(response.body)

        self.assertEqual(response.code, 404)
        self.assertEqual(body.get("message"), f"Request {request_id} not found.")

    @patch("consoleme.handlers.base.RedisHandler")
    @patch("consoleme.handlers.request.get_request_by_id")
    def test_requests_200(self, mock_get_request_by_id, mock_redis_handler):
        request = {"foo": "bar"}

        mock_get_request_by_id.return_value = create_future(request)
        mock_redis_handler.return_value.redis.return_value = create_future(
            mock_strict_redis_client()
        )

        request_id = 123456
        response = self.fetch(f"/api/v1/requests/{request_id}", headers=headers)
        body = json_decode(response.body)

        self.assertEqual(response.code, 200)
        self.assertEqual(body, request)

    @patch("consoleme.handlers.base.RedisHandler")
    @patch("consoleme.lib.dynamo.UserDynamoHandler.change_request_status_by_id")
    @patch("consoleme.handlers.request.auth")
    @patch("consoleme.handlers.request.get_request_by_id")
    @patch("consoleme.handlers.request.can_approve_reject_request")
    @patch("consoleme.handlers.request.can_cancel_request")
    @patch("consoleme.handlers.request.can_move_back_to_pending")
    @patch("consoleme.handlers.request.add_user_to_group")
    @patch("consoleme.handlers.request.remove_user_from_group")
    @patch("consoleme.handlers.request.get_accessui_request_review_url")
    @patch("consoleme.handlers.request.send_access_email_to_user")
    def test_request_approval(
        self,
        mock_send_access_email_to_user,
        mock_get_accessui_request_review_url,
        mock_remove_user_from_group,
        mock_add_user_to_group,
        mock_can_move_back_to_pending,
        mock_can_cancel_request,
        mock_can_approve_reject_request,
        mock_get_request_by_id,
        mock_auth,
        mock_change_request_status_by_id,
        mock_redis_handler,
    ):
        request = {
            "foo": "bar",
            "status": "pending",
            "username": "me",
            "group": "my-group",
        }
        mock_get_request_by_id.return_value = create_future(request)

        mock_change_request_status_by_id.return_value = request

        mock_redis_handler.return_value.redis.return_value = create_future(
            mock_strict_redis_client()
        )

        list_future = create_future(["group1", "user1"])
        mock_auth.get_groups.return_value = list_future
        mock_auth.get_secondary_approvers.return_value = list_future

        mock_remove_user_from_group.return_value = create_future(None)
        mock_add_user_to_group.return_value = create_future(None)
        mock_send_access_email_to_user.return_value = create_future(None)

        mock_get_accessui_request_review_url.return_value = ""
        mock_can_approve_reject_request.return_value = create_future(True)
        mock_can_cancel_request.return_value = create_future(True)
        mock_can_move_back_to_pending.return_value = create_future(True)

        request_id = 123456
        request_body = b'{"comment": "foobar","status": "cancelled"}'
        response = self.fetch(
            f"/api/v1/requests/{request_id}",
            headers=headers,
            method="PUT",
            body=request_body,
        )
        body = json_decode(response.body)

        self.assertEqual(response.code, 200)
        self.assertEqual(body, request)

    @patch("consoleme.handlers.base.RedisHandler")
    @patch("consoleme.lib.dynamo.UserDynamoHandler.change_request_status_by_id")
    @patch("consoleme.handlers.request.auth")
    @patch("consoleme.handlers.request.get_request_by_id")
    @patch("consoleme.handlers.request.can_approve_reject_request")
    @patch("consoleme.handlers.request.can_cancel_request")
    @patch("consoleme.handlers.request.can_move_back_to_pending")
    @patch("consoleme.handlers.request.add_user_to_group")
    @patch("consoleme.handlers.request.remove_user_from_group")
    @patch("consoleme.handlers.request.get_accessui_request_review_url")
    @patch("consoleme.handlers.request.send_access_email_to_user")
    def test_request_approval_422(
        self,
        mock_send_access_email_to_user,
        mock_get_accessui_request_review_url,
        mock_remove_user_from_group,
        mock_add_user_to_group,
        mock_can_move_back_to_pending,
        mock_can_cancel_request,
        mock_can_approve_reject_request,
        mock_get_request_by_id,
        mock_auth,
        mock_change_request_status_by_id,
        mock_redis_handler,
    ):
        request = {
            "foo": "bar",
            "status": "pending",
            "username": "me",
            "group": "my-group",
        }
        mock_get_request_by_id.return_value = create_future(request)

        mock_change_request_status_by_id.return_value = request

        mock_redis_handler.return_value.redis.return_value = create_future(
            mock_strict_redis_client()
        )

        list_future = create_future(["group1", "user1"])
        mock_auth.get_groups.return_value = list_future
        mock_auth.get_secondary_approvers.return_value = list_future

        mock_remove_user_from_group.return_value = create_future(None)
        mock_add_user_to_group.return_value = create_future(None)
        mock_send_access_email_to_user.return_value = create_future(None)

        mock_get_accessui_request_review_url.return_value = ""
        mock_can_approve_reject_request.return_value = create_future(True)
        mock_can_cancel_request.return_value = create_future(True)
        mock_can_move_back_to_pending.return_value = create_future(True)

        request_id = 123456
        request_body = b'{"comment": "foobar"}'
        response = self.fetch(
            f"/api/v1/requests/{request_id}",
            headers=headers,
            method="PUT",
            body=request_body,
        )
        body = json_decode(response.body)

        self.assertEqual(response.code, 422)
        self.assertEqual(body.get("message"), "Please pass a new status")

    @patch("consoleme.handlers.base.RedisHandler")
    @patch("consoleme.lib.dynamo.UserDynamoHandler.change_request_status_by_id")
    @patch("consoleme.handlers.request.auth")
    @patch("consoleme.handlers.request.get_request_by_id")
    @patch("consoleme.handlers.request.can_approve_reject_request")
    @patch("consoleme.handlers.request.can_cancel_request")
    @patch("consoleme.handlers.request.can_move_back_to_pending")
    @patch("consoleme.handlers.request.add_user_to_group")
    @patch("consoleme.handlers.request.remove_user_from_group")
    @patch("consoleme.handlers.request.get_accessui_request_review_url")
    @patch("consoleme.handlers.request.send_access_email_to_user")
    def test_request_approval_cannot_change(
        self,
        mock_send_access_email_to_user,
        mock_get_accessui_request_review_url,
        mock_remove_user_from_group,
        mock_add_user_to_group,
        mock_can_move_back_to_pending,
        mock_can_cancel_request,
        mock_can_approve_reject_request,
        mock_get_request_by_id,
        mock_auth,
        mock_change_request_status_by_id,
        mock_redis_handler,
    ):
        request = {
            "foo": "bar",
            "status": "pending",
            "username": "me",
            "group": "my-group",
        }
        mock_get_request_by_id.return_value = create_future(request)

        mock_change_request_status_by_id.return_value = request

        mock_redis_handler.return_value.redis.return_value = create_future(
            mock_strict_redis_client()
        )

        list_future = create_future(["group1", "user1"])
        mock_auth.get_groups.return_value = list_future
        mock_auth.get_secondary_approvers.return_value = list_future

        mock_remove_user_from_group.return_value = create_future(None)
        mock_add_user_to_group.return_value = create_future(None)
        mock_send_access_email_to_user.return_value = create_future(None)

        mock_get_accessui_request_review_url.return_value = ""
        mock_can_approve_reject_request.return_value = create_future(False)
        mock_can_cancel_request.return_value = create_future(False)
        mock_can_move_back_to_pending.return_value = create_future(False)

        request_id = 123456
        request_body = b'{"comment": "foobar","status": "approved"}'
        response = self.fetch(
            f"/api/v1/requests/{request_id}",
            headers=headers,
            method="PUT",
            body=request_body,
        )
        body = json_decode(response.body)

        self.assertEqual(response.code, 403)
        self.assertEqual(
            body.get("message"),
            "You are unauthorized to change the status on this request.",
        )

    @patch("consoleme.handlers.base.RedisHandler")
    @patch("consoleme.lib.dynamo.UserDynamoHandler.change_request_status_by_id")
    @patch("consoleme.handlers.request.auth")
    @patch("consoleme.handlers.request.get_request_by_id")
    @patch("consoleme.handlers.request.can_approve_reject_request")
    @patch("consoleme.handlers.request.can_cancel_request")
    @patch("consoleme.handlers.request.can_move_back_to_pending")
    @patch("consoleme.handlers.request.add_user_to_group")
    @patch("consoleme.handlers.request.remove_user_from_group")
    @patch("consoleme.handlers.request.get_accessui_request_review_url")
    @patch("consoleme.handlers.request.send_access_email_to_user")
    def test_request_approval_cannot_cancel(
        self,
        mock_send_access_email_to_user,
        mock_get_accessui_request_review_url,
        mock_remove_user_from_group,
        mock_add_user_to_group,
        mock_can_move_back_to_pending,
        mock_can_cancel_request,
        mock_can_approve_reject_request,
        mock_get_request_by_id,
        mock_auth,
        mock_change_request_status_by_id,
        mock_redis_handler,
    ):
        request = {
            "foo": "bar",
            "status": "pending",
            "username": "me",
            "group": "my-group",
        }
        mock_get_request_by_id.return_value = create_future(request)

        mock_change_request_status_by_id.return_value = request

        mock_redis_handler.return_value.redis.return_value = create_future(
            mock_strict_redis_client()
        )

        list_future = create_future(["group1", "user1"])
        mock_auth.get_groups.return_value = list_future
        mock_auth.get_secondary_approvers.return_value = list_future

        mock_remove_user_from_group.return_value = create_future(None)
        mock_add_user_to_group.return_value = create_future(None)
        mock_send_access_email_to_user.return_value = create_future(None)

        mock_get_accessui_request_review_url.return_value = ""
        mock_can_approve_reject_request.return_value = create_future(True)
        mock_can_cancel_request.return_value = create_future(False)
        mock_can_move_back_to_pending.return_value = create_future(True)

        request_id = 123456
        request_body = b'{"comment": "foobar","status": "cancelled"}'
        response = self.fetch(
            f"/api/v1/requests/{request_id}",
            headers=headers,
            method="PUT",
            body=request_body,
        )
        body = json_decode(response.body)

        self.assertEqual(response.code, 403)
        self.assertEqual(
            body.get("message"), "You are unauthorized to cancel this request."
        )

    @patch("consoleme.handlers.base.RedisHandler")
    @patch("consoleme.lib.dynamo.UserDynamoHandler.change_request_status_by_id")
    @patch("consoleme.handlers.request.auth")
    @patch("consoleme.handlers.request.get_request_by_id")
    @patch("consoleme.handlers.request.can_approve_reject_request")
    @patch("consoleme.handlers.request.can_cancel_request")
    @patch("consoleme.handlers.request.can_move_back_to_pending")
    @patch("consoleme.handlers.request.add_user_to_group")
    @patch("consoleme.handlers.request.remove_user_from_group")
    @patch("consoleme.handlers.request.get_accessui_request_review_url")
    @patch("consoleme.handlers.request.send_access_email_to_user")
    def test_request_approval_cannot_approve_reject(
        self,
        mock_send_access_email_to_user,
        mock_get_accessui_request_review_url,
        mock_remove_user_from_group,
        mock_add_user_to_group,
        mock_can_move_back_to_pending,
        mock_can_cancel_request,
        mock_can_approve_reject_request,
        mock_get_request_by_id,
        mock_auth,
        mock_change_request_status_by_id,
        mock_redis_handler,
    ):
        request = {
            "foo": "bar",
            "status": "pending",
            "username": "me",
            "group": "my-group",
        }
        mock_get_request_by_id.return_value = create_future(request)

        mock_change_request_status_by_id.return_value = request

        mock_redis_handler.return_value.redis.return_value = create_future(
            mock_strict_redis_client()
        )

        list_future = create_future(["group1", "user1"])
        mock_auth.get_groups.return_value = list_future
        mock_auth.get_secondary_approvers.return_value = list_future

        mock_remove_user_from_group.return_value = create_future(None)
        mock_add_user_to_group.return_value = create_future(None)
        mock_send_access_email_to_user.return_value = create_future(None)

        mock_get_accessui_request_review_url.return_value = ""
        mock_can_approve_reject_request.return_value = create_future(False)
        mock_can_cancel_request.return_value = create_future(True)
        mock_can_move_back_to_pending.return_value = create_future(True)

        request_id = 123456
        request_body = b'{"comment": "foobar","status": "approved"}'
        response = self.fetch(
            f"/api/v1/requests/{request_id}",
            headers=headers,
            method="PUT",
            body=request_body,
        )
        body = json_decode(response.body)

        self.assertEqual(response.code, 403)
        self.assertEqual(
            body.get("message"),
            "You are unauthorized to approve or reject this request.",
        )

    @patch("consoleme.handlers.base.RedisHandler")
    @patch("consoleme.lib.dynamo.UserDynamoHandler.change_request_status_by_id")
    @patch("consoleme.handlers.request.auth")
    @patch("consoleme.handlers.request.get_request_by_id")
    @patch("consoleme.handlers.request.can_approve_reject_request")
    @patch("consoleme.handlers.request.can_cancel_request")
    @patch("consoleme.handlers.request.can_move_back_to_pending")
    @patch("consoleme.handlers.request.add_user_to_group")
    @patch("consoleme.handlers.request.remove_user_from_group")
    @patch("consoleme.handlers.request.get_accessui_request_review_url")
    @patch("consoleme.handlers.request.send_access_email_to_user")
    def test_request_approval_cannot_make_pending(
        self,
        mock_send_access_email_to_user,
        mock_get_accessui_request_review_url,
        mock_remove_user_from_group,
        mock_add_user_to_group,
        mock_can_move_back_to_pending,
        mock_can_cancel_request,
        mock_can_approve_reject_request,
        mock_get_request_by_id,
        mock_auth,
        mock_change_request_status_by_id,
        mock_redis_handler,
    ):
        request = {
            "foo": "bar",
            "status": "approved",
            "username": "me",
            "group": "my-group",
        }
        mock_get_request_by_id.return_value = create_future(request)

        mock_change_request_status_by_id.return_value = request

        mock_redis_handler.return_value.redis.return_value = create_future(
            mock_strict_redis_client()
        )

        list_future = create_future(["group1", "user1"])
        mock_auth.get_groups.return_value = list_future
        mock_auth.get_secondary_approvers.return_value = list_future

        mock_remove_user_from_group.return_value = create_future(None)
        mock_add_user_to_group.return_value = create_future(None)
        mock_send_access_email_to_user.return_value = create_future(None)

        mock_get_accessui_request_review_url.return_value = ""
        mock_can_approve_reject_request.return_value = create_future(True)
        mock_can_cancel_request.return_value = create_future(True)
        mock_can_move_back_to_pending.return_value = create_future(False)

        request_id = 123456
        request_body = b'{"comment": "foobar","status": "pending"}'
        response = self.fetch(
            f"/api/v1/requests/{request_id}",
            headers=headers,
            method="PUT",
            body=request_body,
        )
        body = json_decode(response.body)

        self.assertEqual(response.code, 403)
        self.assertEqual(
            body.get("message"), "You are unauthorized to make this request pending."
        )
