"""Docstring in public module."""
import os
import sys

import ujson as json
from mock import MagicMock, patch
from tornado.testing import AsyncHTTPTestCase

from tests.conftest import MockBaseHandler, MockRedisHandler, create_future

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(APP_ROOT, ".."))

mock_policy_redis = MagicMock(
    return_value=MockRedisHandler(
        return_value={
            "123456789012": (
                '["arn:aws:iam:123456789012:policy/Policy1",'
                '"arn:aws:iam:123456789012:policy/Policy2"]'
            )
        }
    )
)


class TestPolicyResourceEditHandler(AsyncHTTPTestCase):
    def get_app(self):
        from consoleme.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    @patch(
        "consoleme.handlers.v1.policies.ResourceTypeAheadHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    @patch("consoleme.lib.aws.RedisHandler", mock_policy_redis)
    @patch("consoleme.handlers.base.auth")
    @patch("consoleme.handlers.v1.policies.retrieve_json_data_from_redis_or_s3")
    def test_resource_typeahead(
        self, mock_retrieve_json_data_from_redis_or_s3, mock_auth
    ):
        from consoleme.config import config

        mock_auth.validate_certificate.return_value = create_future(True)
        mock_auth.extract_user_from_certificate.return_value = create_future(
            {"name": "user@example.com", "type": "user"}
        )
        mock_auth.get_cert_age_seconds.return_value = create_future(100)
        headers = {
            config.get("auth.user_header_name"): "user@example.com",
            config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }

        # Invalid resource, no search string
        resource = "fake"
        response = self.fetch(
            f"/api/v1/policies/typeahead?resource={resource}",
            headers=headers,
            method="GET",
        )
        self.assertEqual(response.code, 400)

        # Valid resource, no search string
        resource = "s3"
        response = self.fetch(
            f"/api/v1/policies/typeahead?resource={resource}",
            headers=headers,
            method="GET",
        )
        self.assertEqual(response.code, 400)
        result = create_future({"123456789012": '["abucket1", "abucket2"]'})
        mock_retrieve_json_data_from_redis_or_s3.return_value = result
        account_id = "123456789012"
        resource = "s3"
        search = "a"
        response = self.fetch(
            f"/api/v1/policies/typeahead?resource={resource}&search={search}&account_id={account_id}",
            headers=headers,
            method="GET",
        )
        self.assertEqual(response.code, 200)
        self.assertIsInstance(json.loads(response.body), list)
        self.assertEqual(
            json.loads(response.body),
            [
                {"title": "abucket1", "account_id": "123456789012"},
                {"title": "abucket2", "account_id": "123456789012"},
            ],
        )
