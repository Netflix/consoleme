"""Docstring in public module."""

import os
import sys

import jwt
import ujson as json
from mock import patch, Mock
from mockredis import mock_strict_redis_client
from tornado.concurrent import Future
from tornado.escape import json_decode
from tornado.testing import AsyncHTTPTestCase

from consoleme.config import config
from consoleme.exceptions.exceptions import (
    BackgroundCheckNotPassedException,
    BulkAddPrevented,
    DifferentUserGroupDomainException,
    NotAMemberException,
    UnableToModifyRestrictedGroupMembers,
)
from consoleme.lib.auth import mk_jwt_validator
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.routes import make_app
from tests.conftest import MockAuth, MockBaseHandler

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(APP_ROOT, ".."))

auth = get_plugin_by_name(config.get("plugins.auth"))()

Group = auth.Group


class TestGroupsHandler(AsyncHTTPTestCase):
    def get_app(self):
        return make_app()

    @patch(
        "consoleme.handlers.groups.GroupsHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    @patch("consoleme.handlers.base.RedisHandler")
    def test_groups_pageload(self, mock_redis_handler):
        mock_redis = Future()
        mock_redis.set_result(mock_strict_redis_client())
        mock_redis_handler.return_value.redis.return_value = mock_redis
        headers = {
            "Oidc_claim_sub": "user@github.com",
            "Oidc_claim_googlegroups": "groupa,groupb,groupc",
        }

        response = self.fetch("/accessui/groups", headers=headers)
        self.assertEqual(response.code, 200)
        self.assertIn(
            b"<th>Name</th>\n<th>Description</th>\n<th>Access</th>", response.body
        )

    def test_groups_page_redirect(self):
        from consoleme.config.config import CONFIG

        old_value = CONFIG.config["dynamic_config"]["accessui"].pop("deprecate", None)
        CONFIG.config["dynamic_config"]["accessui"]["deprecate"] = True

        headers = {
            "Oidc_claim_sub": "user@github.com",
            "Oidc_claim_googlegroups": "groupa,groupb,groupc",
        }

        base_url = CONFIG.config.get("accessui_url")

        response = self.fetch(
            "/accessui/groups", headers=headers, follow_redirects=False
        )
        self.assertEqual(response.code, 301)
        self.assertEqual(response.headers["Location"], f"{base_url}/groups")

        # Reset the config values:
        if not old_value:
            del CONFIG.config["dynamic_config"]["accessui"]["deprecate"]
        else:
            CONFIG.config["dynamic_config"]["accessui"]["deprecate"] = old_value

    @patch("consoleme_internal.plugins.auth.auth.AsyncHTTPClient")
    def test_group_page_redirect(self, async_http_client):
        from consoleme.config.config import CONFIG

        group_service_return_value = Mock()
        group_service_return_value.body = "{}"
        async_http_client.return_value.fetch.return_value = create_future(
            group_service_return_value
        )

        old_value = CONFIG.config["dynamic_config"]["accessui"].pop("deprecate", None)
        CONFIG.config["dynamic_config"]["accessui"]["deprecate"] = True

        headers = {
            "Oidc_claim_sub": "user@github.com",
            "Oidc_claim_googlegroups": "groupa,groupb,groupc",
        }

        base_url = CONFIG.config.get("accessui_url")

        response = self.fetch(
            "/accessui/group/mygroup@example.com",
            headers=headers,
            follow_redirects=False,
        )
        self.assertEqual(response.code, 301)
        self.assertEqual(
            response.headers["Location"], f"{base_url}/groups/mygroup@example.com"
        )

        # Reset the config values:
        if not old_value:
            del CONFIG.config["dynamic_config"]["accessui"]["deprecate"]
        else:
            CONFIG.config["dynamic_config"]["accessui"]["deprecate"] = old_value

    @patch(
        "consoleme.handlers.groups.GroupHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    @patch("consoleme.handlers.groups.auth", MockAuth())
    @patch("consoleme.handlers.base.RedisHandler")
    @patch("consoleme.handlers.groups.can_edit_attributes", return_value=True)
    def test_group_pageload(self, mock_can_edit_attributes, mock_redis_handler):
        mock_redis = Future()
        mock_redis.set_result(mock_strict_redis_client())
        mock_redis_handler.return_value.redis.return_value = mock_redis
        headers = {
            "Oidc_claim_sub": "user@github.com",
            "Oidc_claim_googlegroups": "groupa,groupb,groupc",
        }

        response = self.fetch("/accessui/group/groupname@test.com", headers=headers)
        self.assertEqual(response.code, 200)
        self.assertIn(
            '<input type="text" name="name" placeholder="Group Name" value="groupname@test.com" disabled>',
            response.body.decode("utf-8"),
        )
        self.assertIn(
            '<input type="text" name="friendlyName" placeholder="Friendly group Name"',
            response.body.decode("utf-8"),
        )
        self.assertIn(
            'href="http://127.0.0.1:8081/accessui/request_access/groupname@test.com">Link</a>',
            response.body.decode("utf-8"),
        )

    @patch(
        "consoleme.handlers.groups.GroupHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    @patch("consoleme.handlers.groups.auth", MockAuth())
    @patch("consoleme.handlers.base.RedisHandler")
    @patch("consoleme.handlers.groups.can_edit_attributes", return_value=True)
    @patch("consoleme.handlers.groups.can_modify_members", return_value=False)
    def test_group_compliance_cannot_add_remove_members(
        self, mock_can_modify_members, mock_can_edit_attributes, mock_redis_handler
    ):
        mock_redis = Future()
        mock_redis.set_result(mock_strict_redis_client())
        mock_redis_handler.return_value.redis.return_value = mock_redis
        headers = {
            "Oidc_claim_sub": "user@example.com",
            "Oidc_claim_googlegroups": "groupa,groupb,groupc",
        }

        response = self.fetch("/accessui/group/groupname@test.com", headers=headers)
        self.assertEqual(response.code, 200)
        self.assertIn(
            '<label>Add members</label>\n<textarea rows="2" name="add_members" placeholder="usera@example.com,userb@example.com"\ndisabled></textarea>',
            response.body.decode("utf-8"),
        )

    @patch(
        "consoleme.handlers.groups.GroupHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    @patch("consoleme.handlers.groups.auth", MockAuth())
    @patch("consoleme.handlers.base.RedisHandler")
    @patch("consoleme.handlers.groups.can_edit_attributes", return_value=True)
    @patch(
        "consoleme.handlers.groups.can_edit_sensitive_attributes", return_value=False
    )
    @patch("consoleme.handlers.groups.can_modify_members", return_value=True)
    def test_group_compliance_cannot_edit_sensitive_attributes(
        self,
        mock_can_modify_members,
        mock_can_edit_sensitive_attributes,
        mock_can_edit_attributes,
        mock_redis_handler,
    ):
        mock_redis = Future()
        mock_redis.set_result(mock_strict_redis_client())
        mock_redis_handler.return_value.redis.return_value = mock_redis
        headers = {
            "Oidc_claim_sub": "user@github.com",
            "Oidc_claim_googlegroups": "groupa,groupb,groupc",
        }

        response = self.fetch("/accessui/group/groupname@test.com", headers=headers)
        self.assertEqual(response.code, 200)
        self.assertIn(
            '<input type="checkbox" name="restricted" tabindex="0"\ndisabled\n"/>',
            response.body.decode("utf-8"),
        )
        self.assertIn(
            '<input type="checkbox" name="compliance_restricted" tabindex="0"\ndisabled\n"/>',
            response.body.decode("utf-8"),
        )
        self.assertIn(
            '<input type="text" name="secondary_approvers" placeholder="group1@example.com,group2@example.com"\nvalue="groupapprover1,groupapprover2"\n>\n</div>',
            response.body.decode("utf-8"),
        )
        self.assertIn(
            '<label>Add members</label>\n<textarea rows="2" name="add_members" placeholder="usera@example.com,userb@example.com"\n></textarea>',
            response.body.decode("utf-8"),
        )

    @patch(
        "consoleme.handlers.groups.GroupHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    @patch("consoleme.handlers.groups.auth", MockAuth())
    @patch("consoleme.handlers.base.RedisHandler")
    @patch("consoleme.handlers.groups.can_edit_attributes", return_value=True)
    @patch("consoleme.handlers.groups.can_modify_members", return_value=True)
    def test_group_add_remove_members(
        self, mock_can_modify_members, mock_can_edit_attributes, mock_redis_handler
    ):
        mock_redis = Future()
        mock_redis.set_result(mock_strict_redis_client())
        mock_redis_handler.return_value.redis.return_value = mock_redis

        headers = {
            "content-type": "application/json",
            "Oidc_claim_sub": "user@github.com",
            "Oidc_claim_googlegroups": "groupa,groupb,groupc",
        }

        data = [
            {"name": "add_members", "value": "testuser@group.com"},
            {"name": "remove_members", "value": ""},
        ]

        response = self.fetch(
            "/accessui/group/test@group.com",
            headers=headers,
            method="POST",
            body=json.dumps(data),
        )
        self.assertEqual(response.code, 200)
        self.assertIn(b"There was at least one problem.", response.body)

        data = [
            {"name": "add_members", "value": ""},
            {"name": "remove_members", "value": "testuser@group.com"},
        ]

        response = self.fetch(
            "/accessui/group/test@group.com",
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


class TestJSONGroupHandler(AsyncHTTPTestCase):
    def get_app(self):
        return make_app(jwt_validator=jwt_validator)

    @patch("consoleme.handlers.groups.auth")
    @patch("consoleme.handlers.groups.can_edit_attributes")
    @patch("consoleme.handlers.groups.can_edit_sensitive_attributes")
    @patch("consoleme.handlers.groups.is_sensitive_attr")
    def test_patch_no_data(
        self,
        mock_is_sensitive_attr,
        mock_can_edit_sensitive_attributes,
        mock_can_edit_attributes,
        mock_auth,
    ):
        group_info = {"restricted": False, "compliance_restricted": False}
        mock_auth.get_group_info.return_value = create_future(Group(**group_info))
        mock_auth.get_groups.return_value = create_future(list())
        mock_auth.put_group_attributes.return_value = create_future(None)
        mock_can_edit_attributes.return_value = True
        mock_can_edit_sensitive_attributes.return_value = True

        group_name = "group@example.com"
        request_body = b"{}"
        response = self.fetch(
            f"/api/v1/groups/{group_name}",
            headers=headers,
            method="PATCH",
            body=request_body,
        )

        self.assertEqual(response.code, 204)

    @patch("consoleme.handlers.groups.auth")
    @patch("consoleme.handlers.groups.can_edit_attributes")
    @patch("consoleme.handlers.groups.can_edit_sensitive_attributes")
    @patch("consoleme.handlers.groups.is_sensitive_attr")
    def test_patch_random_data(
        self,
        mock_is_sensitive_attr,
        mock_can_edit_sensitive_attributes,
        mock_can_edit_attributes,
        mock_auth,
    ):
        group_info = {"restricted": False, "compliance_restricted": False}
        mock_auth.get_group_info.return_value = create_future(Group(**group_info))
        mock_auth.get_groups.return_value = create_future(list())
        mock_auth.put_group_attributes.return_value = create_future(None)
        mock_can_edit_attributes.return_value = True
        mock_can_edit_sensitive_attributes.return_value = True

        group_name = "group@example.com"
        request_body = b'{"randomProp":"foobar"}'
        response = self.fetch(
            f"/api/v1/groups/{group_name}",
            headers=headers,
            method="PATCH",
            body=request_body,
        )

        self.assertEqual(response.code, 204)

    @patch("consoleme.handlers.groups.auth")
    @patch("consoleme.handlers.groups.can_edit_attributes")
    @patch("consoleme.handlers.groups.can_edit_sensitive_attributes")
    @patch("consoleme.handlers.groups.is_sensitive_attr")
    def test_patch_good_data(
        self,
        mock_is_sensitive_attr,
        mock_can_edit_sensitive_attributes,
        mock_can_edit_attributes,
        mock_auth,
    ):
        group_info = {"restricted": False, "compliance_restricted": False}
        mock_auth.get_group_info.return_value = create_future(Group(**group_info))
        mock_auth.get_groups.return_value = create_future(list())
        mock_auth.put_group_attributes.return_value = create_future(None)
        mock_can_edit_attributes.return_value = True
        mock_can_edit_sensitive_attributes.return_value = True

        group_name = "group@example.com"
        request_body = (
            b'{"restricted":"true", "secondary_approvers":"email@example.com"}'
        )
        response = self.fetch(
            f"/api/v1/groups/{group_name}",
            headers=headers,
            method="PATCH",
            body=request_body,
        )

        self.assertEqual(response.code, 204)

    @patch("consoleme.handlers.groups.auth")
    @patch("consoleme.handlers.groups.can_edit_attributes")
    @patch("consoleme.handlers.groups.can_edit_sensitive_attributes")
    @patch("consoleme.handlers.groups.is_sensitive_attr")
    def test_patch_404_no_group(
        self,
        mock_is_sensitive_attr,
        mock_can_edit_sensitive_attributes,
        mock_can_edit_attributes,
        mock_auth,
    ):
        mock_auth.get_group_info.side_effect = Exception
        mock_auth.get_groups.return_value = create_future(list())
        mock_auth.put_group_attributes.return_value = create_future(None)
        mock_can_edit_attributes.return_value = True
        mock_can_edit_sensitive_attributes.return_value = True

        group_name = "group@example.com"
        request_body = b'{"compliance_restricted":"true"}'
        response = self.fetch(
            f"/api/v1/groups/{group_name}",
            headers=headers,
            method="PATCH",
            body=request_body,
        )
        body = json_decode(response.body)

        self.assertEqual(response.code, 404)
        self.assertEqual(
            body.get("message"), f"Unable to retrieve the specified group: {group_name}"
        )

    @patch("consoleme.handlers.groups.auth")
    @patch("consoleme.handlers.groups.can_edit_attributes")
    @patch("consoleme.handlers.groups.can_edit_sensitive_attributes")
    @patch("consoleme.handlers.groups.is_sensitive_attr")
    def test_patch_403_no_edit(
        self,
        mock_is_sensitive_attr,
        mock_can_edit_sensitive_attributes,
        mock_can_edit_attributes,
        mock_auth,
    ):
        group_info = {"restricted": False, "compliance_restricted": False}
        mock_auth.get_group_info.return_value = create_future(Group(**group_info))
        mock_auth.get_groups.return_value = create_future(list())
        mock_auth.put_group_attributes.return_value = create_future(None)
        mock_can_edit_attributes.return_value = False
        mock_can_edit_sensitive_attributes.return_value = True

        group_name = "group@example.com"
        request_body = b'{"compliance_restricted":"true"}'
        response = self.fetch(
            f"/api/v1/groups/{group_name}",
            headers=headers,
            method="PATCH",
            body=request_body,
        )
        body = json_decode(response.body)

        self.assertEqual(response.code, 403)
        self.assertEqual(body.get("message"), "Unauthorized to edit this group.")

    @patch("consoleme.handlers.groups.auth")
    @patch("consoleme.handlers.groups.can_edit_attributes")
    @patch("consoleme.handlers.groups.can_edit_sensitive_attributes")
    @patch("consoleme.handlers.groups.is_sensitive_attr")
    def test_patch_400_invalid_email(
        self,
        mock_is_sensitive_attr,
        mock_can_edit_sensitive_attributes,
        mock_can_edit_attributes,
        mock_auth,
    ):
        group_info = {"restricted": False, "compliance_restricted": False}
        mock_auth.get_group_info.return_value = create_future(Group(**group_info))
        mock_auth.get_groups.return_value = create_future(list())
        mock_auth.put_group_attributes.return_value = create_future(None)
        mock_can_edit_attributes.return_value = True
        mock_can_edit_sensitive_attributes.return_value = True

        group_name = "group@example.com"
        request_body = b'{"secondary_approvers":"email@example.com,notAnEmail"}'
        response = self.fetch(
            f"/api/v1/groups/{group_name}",
            headers=headers,
            method="PATCH",
            body=request_body,
        )
        body = json_decode(response.body)

        self.assertEqual(response.code, 400)
        self.assertEqual(
            body.get("message"), "Invalid e-mail address entered: notAnEmail"
        )

    @patch("consoleme.handlers.groups.auth")
    @patch("consoleme.handlers.groups.can_edit_attributes")
    @patch("consoleme.handlers.groups.can_edit_sensitive_attributes")
    @patch("consoleme.handlers.groups.is_sensitive_attr")
    def test_patch_400_invalid_bool(
        self,
        mock_is_sensitive_attr,
        mock_can_edit_sensitive_attributes,
        mock_can_edit_attributes,
        mock_auth,
    ):
        group_info = {"restricted": False, "compliance_restricted": False}
        mock_auth.get_group_info.return_value = create_future(Group(**group_info))
        mock_auth.get_groups.return_value = create_future(list())
        mock_auth.put_group_attributes.return_value = create_future(None)
        mock_can_edit_attributes.return_value = True
        mock_can_edit_sensitive_attributes.return_value = True

        group_name = "group@example.com"
        request_body = b'{"restricted":"blah"}'
        response = self.fetch(
            f"/api/v1/groups/{group_name}",
            headers=headers,
            method="PATCH",
            body=request_body,
        )
        body = json_decode(response.body)

        self.assertEqual(response.code, 400)
        self.assertEqual(
            body.get("message"), "Invalid boolean value entered for restricted: blah"
        )

    @patch("consoleme.handlers.groups.auth")
    @patch("consoleme.handlers.groups.can_edit_attributes")
    @patch("consoleme.handlers.groups.can_edit_sensitive_attributes")
    @patch("consoleme.handlers.groups.is_sensitive_attr")
    def test_patch_403_restricted(
        self,
        mock_is_sensitive_attr,
        mock_can_edit_sensitive_attributes,
        mock_can_edit_attributes,
        mock_auth,
    ):
        group_info = {"restricted": True, "compliance_restricted": False}
        mock_auth.get_group_info.return_value = create_future(Group(**group_info))
        mock_auth.get_groups.return_value = create_future(list())
        mock_auth.put_group_attributes.return_value = create_future(None)
        mock_can_edit_attributes.return_value = True
        mock_can_edit_sensitive_attributes.return_value = False

        group_name = "group@example.com"
        request_body = b'{"compliance_restricted":"true"}'
        response = self.fetch(
            f"/api/v1/groups/{group_name}",
            headers=headers,
            method="PATCH",
            body=request_body,
        )
        body = json_decode(response.body)

        self.assertEqual(response.code, 403)
        self.assertEqual(
            body.get("message"),
            "You are not authorized to edit sensitive attribute: compliance_restricted",
        )

    @patch("consoleme.handlers.groups.auth")
    @patch("consoleme.handlers.groups.can_edit_attributes")
    @patch("consoleme.handlers.groups.can_edit_sensitive_attributes")
    @patch("consoleme.handlers.groups.is_sensitive_attr")
    def test_patch_403_compliance_restricted(
        self,
        mock_is_sensitive_attr,
        mock_can_edit_sensitive_attributes,
        mock_can_edit_attributes,
        mock_auth,
    ):
        group_info = {"restricted": False, "compliance_restricted": True}
        mock_auth.get_group_info.return_value = create_future(Group(**group_info))
        mock_auth.get_groups.return_value = create_future(list())
        mock_auth.put_group_attributes.return_value = create_future(None)
        mock_can_edit_attributes.return_value = True
        mock_can_edit_sensitive_attributes.return_value = False

        group_name = "group@example.com"
        request_body = b'{"compliance_restricted":"true"}'
        response = self.fetch(
            f"/api/v1/groups/{group_name}",
            headers=headers,
            method="PATCH",
            body=request_body,
        )
        body = json_decode(response.body)

        self.assertEqual(response.code, 403)
        self.assertEqual(
            body.get("message"),
            "You are not authorized to edit sensitive attribute: compliance_restricted",
        )


class TestJSONBulkGroupMemberHandler(AsyncHTTPTestCase):
    def get_app(self):
        return make_app(jwt_validator=jwt_validator)

    @patch("consoleme.handlers.groups.api_add_user_to_group_or_raise")
    def test_bulk_add(self, mock_api_add_user_to_group_or_raise):
        members = ["moe@example.com", "larry@example.com", "shemp@example.com"]
        group_name = "stooges@example.com"

        def side_effect(group_name, member_name, actor):
            if member_name == members[0]:
                return create_future("ADDED")
            if member_name == members[1]:
                return create_future("REQUESTED")
            if member_name == members[2]:
                future = Future()
                future.set_exception(Exception("foobar"))
                return future

        mock_api_add_user_to_group_or_raise.side_effect = side_effect

        response = self.fetch(
            f"/api/v1/groups/{group_name}/members",
            headers=headers,
            method="POST",
            body=b'["moe@example.com", "larry@example.com", "shemp@example.com"]',
        )

        body = json_decode(response.body)
        self.assertEqual(response.code, 200)

        self.assertEqual(body[0]["success"], True)
        self.assertEqual(body[0]["status"], "ADDED")
        self.assertEqual(body[0]["member"], members[0])

        self.assertEqual(body[1]["success"], True)
        self.assertEqual(body[1]["status"], "REQUESTED")
        self.assertEqual(body[1]["member"], members[1])

        self.assertEqual(body[2]["success"], False)
        self.assertEqual(body[2]["status"], "FAILED")
        self.assertEqual(body[2]["message"], "foobar")
        self.assertEqual(body[2]["member"], members[2])


class TestJSONGroupMemberHandler(AsyncHTTPTestCase):
    def get_app(self):
        return make_app(jwt_validator=jwt_validator)

    @patch("consoleme.handlers.groups.auth")
    @patch("consoleme.handlers.groups.can_modify_members")
    @patch("consoleme.handlers.groups.add_user_to_group")
    def test_add(self, mock_add_user_to_group, mock_can_modify_members, mock_auth):
        mock_auth.get_groups.return_value = create_future(list())
        mock_auth.get_group_info.return_value = create_future(Group())
        mock_can_modify_members.return_value = True
        mock_add_user_to_group.return_value = create_future(None)

        group_name = "group@example.com"
        member_name = "member@example.com"
        response = self.fetch(
            f"/api/v1/groups/{group_name}/members/{member_name}",
            headers=headers,
            method="POST",
            allow_nonstandard_methods=True,
        )

        self.assertEqual(response.code, 204)

    @patch("consoleme.handlers.groups.auth")
    @patch("consoleme.handlers.groups.can_modify_members")
    @patch("consoleme.handlers.groups.add_user_to_group")
    def test_add_404(self, mock_add_user_to_group, mock_can_modify_members, mock_auth):
        mock_auth.get_groups.return_value = create_future(list())
        mock_auth.get_group_info.side_effect = Exception
        mock_can_modify_members.return_value = True
        mock_add_user_to_group.return_value = create_future(None)

        group_name = "group@example.com"
        member_name = "member@example.com"
        response = self.fetch(
            f"/api/v1/groups/{group_name}/members/{member_name}",
            headers=headers,
            method="POST",
            allow_nonstandard_methods=True,
        )
        body = json_decode(response.body)

        self.assertEqual(response.code, 404)
        self.assertEqual(
            body.get("message"), "Unable to retrieve the specified group: "
        )

    @patch("consoleme.handlers.groups.auth")
    @patch("consoleme.handlers.groups.can_modify_members")
    @patch("consoleme.handlers.groups.add_user_to_group")
    def test_add_cannot_add(
        self, mock_add_user_to_group, mock_can_modify_members, mock_auth
    ):
        mock_auth.get_groups.return_value = create_future(list())
        mock_auth.get_group_info.return_value = create_future(Group())
        mock_can_modify_members.return_value = False
        mock_add_user_to_group.return_value = create_future(None)

        group_name = "group@example.com"
        member_name = "member@example.com"
        response = self.fetch(
            f"/api/v1/groups/{group_name}/members/{member_name}",
            headers=headers,
            method="POST",
            allow_nonstandard_methods=True,
        )
        body = json_decode(response.body)

        self.assertEqual(response.code, 403)
        self.assertEqual(
            body.get("message"), "Unauthorized to modify members of this group."
        )

    @patch("consoleme.handlers.groups.auth")
    @patch("consoleme.handlers.groups.can_modify_members")
    @patch("consoleme.handlers.groups.add_user_to_group")
    def test_add_no_bg_check(
        self, mock_add_user_to_group, mock_can_modify_members, mock_auth
    ):
        mock_auth.get_groups.return_value = create_future(list())
        mock_auth.get_group_info.return_value = create_future(Group())
        mock_can_modify_members.return_value = True
        mock_add_user_to_group.side_effect = BackgroundCheckNotPassedException

        group_name = "group@example.com"
        member_name = "member@example.com"
        response = self.fetch(
            f"/api/v1/groups/{group_name}/members/{member_name}",
            headers=headers,
            method="POST",
            allow_nonstandard_methods=True,
        )

        self.assertEqual(response.code, 403)

    @patch("consoleme.handlers.groups.auth")
    @patch("consoleme.handlers.groups.can_modify_members")
    @patch("consoleme.handlers.groups.add_user_to_group")
    def test_add_diff_domain(
        self, mock_add_user_to_group, mock_can_modify_members, mock_auth
    ):
        mock_auth.get_groups.return_value = create_future(list())
        mock_auth.get_group_info.return_value = create_future(Group())
        mock_can_modify_members.return_value = True
        mock_add_user_to_group.side_effect = DifferentUserGroupDomainException

        group_name = "group@example.com"
        member_name = "member@example.com"
        response = self.fetch(
            f"/api/v1/groups/{group_name}/members/{member_name}",
            headers=headers,
            method="POST",
            allow_nonstandard_methods=True,
        )

        self.assertEqual(response.code, 403)

    @patch("consoleme.handlers.groups.auth")
    @patch("consoleme.handlers.groups.can_modify_members")
    @patch("consoleme.handlers.groups.add_user_to_group")
    def test_add_restricted_group(
        self, mock_add_user_to_group, mock_can_modify_members, mock_auth
    ):
        mock_auth.get_groups.return_value = create_future(list())
        mock_auth.get_group_info.return_value = create_future(Group())
        mock_can_modify_members.return_value = True
        mock_add_user_to_group.side_effect = UnableToModifyRestrictedGroupMembers

        group_name = "group@example.com"
        member_name = "member@example.com"
        response = self.fetch(
            f"/api/v1/groups/{group_name}/members/{member_name}",
            headers=headers,
            method="POST",
            allow_nonstandard_methods=True,
        )

        self.assertEqual(response.code, 403)

    @patch("consoleme.handlers.groups.auth")
    @patch("consoleme.handlers.groups.can_modify_members")
    @patch("consoleme.handlers.groups.add_user_to_group")
    def test_add_no_bulk_add(
        self, mock_add_user_to_group, mock_can_modify_members, mock_auth
    ):
        mock_auth.get_groups.return_value = create_future(list())
        mock_auth.get_group_info.return_value = create_future(Group())
        mock_can_modify_members.return_value = True
        mock_add_user_to_group.side_effect = BulkAddPrevented

        group_name = "group@example.com"
        member_name = "member@example.com"
        response = self.fetch(
            f"/api/v1/groups/{group_name}/members/{member_name}",
            headers=headers,
            method="POST",
            allow_nonstandard_methods=True,
        )

        self.assertEqual(response.code, 403)

    @patch("consoleme.handlers.groups.remove_user_from_group")
    def test_removal(self, mock_remove_user_from_group):
        mock_remove_user_from_group.return_value = create_future(None)

        group_name = "group@example.com"
        member_name = "member@example.com"
        response = self.fetch(
            f"/api/v1/groups/{group_name}/members/{member_name}",
            headers=headers,
            method="DELETE",
        )

        self.assertEqual(response.code, 204)

    @patch("consoleme.handlers.groups.remove_user_from_group")
    def test_removal_already_removed(self, mock_remove_user_from_group):
        mock_remove_user_from_group.side_effect = NotAMemberException

        group_name = "group@example.com"
        member_name = "member@example.com"
        response = self.fetch(
            f"/api/v1/groups/{group_name}/members/{member_name}",
            headers=headers,
            method="DELETE",
        )

        self.assertEqual(response.code, 204)

    @patch("consoleme.handlers.groups.remove_user_from_group")
    def test_removal_403(self, mock_remove_user_from_group):
        mock_remove_user_from_group.side_effect = UnableToModifyRestrictedGroupMembers(
            "Given error message."
        )

        group_name = "group@example.com"
        member_name = "member@example.com"
        response = self.fetch(
            f"/api/v1/groups/{group_name}/members/{member_name}",
            headers=headers,
            method="DELETE",
        )
        body = json_decode(response.body)

        self.assertEqual(response.code, 403)
        self.assertEqual(body.get("message"), "Given error message.")
