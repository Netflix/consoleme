import ujson as json
from mock import patch
from tornado.testing import AsyncHTTPTestCase

from tests.conftest import MockBaseHandler


class TestTypeAheadHandler(AsyncHTTPTestCase):
    def get_app(self):
        from consoleme.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    @patch(
        "consoleme.handlers.v2.typeahead.ResourceTypeAheadHandlerV2.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    def test_typeahead_get(self):
        from consoleme.config import config

        headers = {
            config.get("auth.user_header_name"): "user@github.com",
            config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }
        from consoleme.lib.redis import RedisHandler

        red = RedisHandler().redis_sync()
        red.hmset(
            "AWSCONFIG_RESOURCE_CACHE",
            {
                "arn:aws:ec2:us-west-2:123456789013:security-group/12345": "{}",
                "arn:aws:sqs:us-east-1:123456789012:rolequeue": "{}",
                "arn:aws:sns:us-east-1:123456789012:roletopic": "{}",
                "arn:aws:iam::123456789012:role/role": "{}",
            },
        )
        # Return all the things
        response = self.fetch(
            "/api/v2/typeahead/resources", method="GET", headers=headers
        )
        self.assertEqual(response.code, 200)
        responseJSON = json.loads(response.body)

        self.assertEqual(len(responseJSON), 4)
        # Filter for a specific query
        response = self.fetch(
            "/api/v2/typeahead/resources?typeahead=role", method="GET", headers=headers
        )
        self.assertEqual(response.code, 200)
        responseJSON = json.loads(response.body)
        self.assertEqual(len(responseJSON), 3)

        # Filter for a specific limit
        response = self.fetch(
            "/api/v2/typeahead/resources?typeahead=role&limit=1",
            method="GET",
            headers=headers,
        )
        self.assertEqual(response.code, 200)
        responseJSON = json.loads(response.body)
        self.assertEqual(len(responseJSON), 1)

        # Filter for a specific account
        response = self.fetch(
            "/api/v2/typeahead/resources?account_id=123456789013",
            method="GET",
            headers=headers,
        )
        self.assertEqual(response.code, 200)
        responseJSON = json.loads(response.body)
        self.assertEqual(len(responseJSON), 1)

        # Filter for a specific resource type
        response = self.fetch(
            "/api/v2/typeahead/resources?resource_type=sqs",
            method="GET",
            headers=headers,
        )
        self.assertEqual(response.code, 200)
        responseJSON = json.loads(response.body)
        self.assertEqual(len(responseJSON), 1)

        # filter for region
        response = self.fetch(
            "/api/v2/typeahead/resources?region=us-east-1",
            method="GET",
            headers=headers,
        )
        self.assertEqual(response.code, 200)
        responseJSON = json.loads(response.body)
        self.assertEqual(len(responseJSON), 2)

        # multifilter
        response = self.fetch(
            "/api/v2/typeahead/resources?region=us-east-1&account_id=123456789012&typeahead=role&limit=5",
            method="GET",
            headers=headers,
        )
        self.assertEqual(response.code, 200)
        responseJSON = json.loads(response.body)
        self.assertEqual(len(responseJSON), 2)
