"""Docstring in public module."""

import os

import sys
import ujson as json
from mock import MagicMock, patch
from tornado.concurrent import Future
from tornado.testing import AsyncHTTPTestCase

from consoleme.config import config
from tests.conftest import MockBaseHandler, MOCK_ROLE, MockRedisHandler
from tests.conftest import create_future

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


class TestPoliciesHandler(AsyncHTTPTestCase):
    def get_app(self):
        from consoleme.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    @patch(
        "consoleme.handlers.policies.PolicyViewHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    def test_policies_pageload(self):
        response = self.fetch("/policies")
        self.assertEqual(response.code, 200)
        self.assertIn(b"All Policies", response.body)
        self.assertIn(b"Templated", response.body)


class TestPolicyEditHandler(AsyncHTTPTestCase):
    def get_app(self):
        from consoleme.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    @patch("consoleme.handlers.policies.aws.fetch_iam_role")
    @patch(
        "consoleme.handlers.policies.PolicyEditHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    @patch("consoleme.lib.aws.RedisHandler", mock_policy_redis)
    def test_policy_pageload(self, mock_fetch_iam_role):
        mock_fetch_iam_role_rv = Future()
        mock_fetch_iam_role_rv.set_result(MOCK_ROLE)
        mock_fetch_iam_role.return_value = mock_fetch_iam_role_rv
        headers = {
            config.get("auth.user_header_name"): "user@github.com",
            config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }
        response = self.fetch(
            "/policies/edit/123456789012/iamrole/FakeRole", headers=headers
        )
        self.assertEqual(response.code, 200)
        self.assertIn(b"Role arn:aws:iam::123456789012:role/FakeRole", response.body)
        self.assertIn(b"fake/file.json", response.body)
        self.assertIn(b"New Policy", response.body)
        self.assertIn(b"iam:GetAccountAuthorizationDetails", response.body)

    @patch(
        "consoleme.handlers.policies.PolicyEditHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    @patch("consoleme.handlers.policies.aws.fetch_iam_role")
    def test_policy_notfound(self, mock_fetch_iam_role):
        mock_fetch_iam_role_rv = Future()
        mock_fetch_iam_role_rv.set_result(None)
        mock_fetch_iam_role.return_value = mock_fetch_iam_role_rv
        headers = {
            config.get("auth.user_header_name"): "user@github.com",
            config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }
        response = self.fetch(
            "/policies/edit/123456789012/iamrole/FakeRole", headers=headers
        )
        self.assertEqual(response.code, 404)


class TestPolicyResourceEditHandler(AsyncHTTPTestCase):
    def get_app(self):
        from consoleme.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    @patch(
        "consoleme.handlers.policies.ResourcePolicyEditHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    @patch("consoleme.lib.aws.RedisHandler", mock_policy_redis)
    @patch("consoleme.handlers.base.auth")
    @patch("consoleme.lib.aws.get_bucket_policy")
    @patch("consoleme.lib.aws.get_bucket_tagging")
    def test_s3_policy_pageload(
        self, mock_get_bucket_tagging, mock_get_bucket_policy, mock_auth
    ):
        mock_get_bucket_policy.return_value = {
            "Policy": json.dumps(
                {
                    "Id": "Policy1562773327512",
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Sid": "Stmt1562773326182",
                            "Action": ["s3:GetObject", "s3:ListBucket"],
                            "Effect": "Allow",
                            "Resource": "arn:aws:s3:::bucketname",
                            "Principal": {
                                "AWS": ["arn:aws:iam::123456789012:role/FakeRole"]
                            },
                        }
                    ],
                }
            )
        }

        mock_get_bucket_tagging.return_value = {"TagSet": []}
        mock_auth.is_user_contractor.return_value = create_future(False)

        headers = {
            config.get("auth.user_header_name"): "user@github.com",
            config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }
        response = self.fetch(
            "/policies/edit/123456789012/s3/bucketname", headers=headers
        )
        self.assertEqual(response.code, 200)
        self.assertIn(b"arn:aws:iam::123456789012:role/FakeRole", response.body)
        self.assertIn(b"s3:GetObject", response.body)
        self.assertIn(b"Resource Policy Editor", response.body)

    @patch(
        "consoleme.handlers.policies.ResourcePolicyEditHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    @patch("consoleme.lib.aws.RedisHandler", mock_policy_redis)
    @patch("consoleme.handlers.base.auth")
    @patch("consoleme.lib.aws.get_queue_url")
    @patch("consoleme.lib.aws.get_queue_attributes")
    @patch("consoleme.lib.aws.list_queue_tags")
    def test_sqs_queue_pageload(
        self,
        mock_list_queue_tags,
        mock_get_queue_attributes,
        mock_get_queue_url,
        mock_auth,
    ):
        mock_list_queue_tags.return_value = []
        mock_get_queue_url.return_value = (
            "https://queue.amazonaws.com/123456789012/queuename"
        )
        mock_get_queue_attributes.return_value = {
            "Policy": {
                "Version": "2008-10-17",
                "Id": "arn:aws:sqs:us-east-1:123456789012:queuename/policyId",
                "Statement": [
                    {
                        "Sid": "testsid",
                        "Effect": "Allow",
                        "Principal": {"AWS": "*"},
                        "Action": "SQS:SendMessage",
                        "Resource": "arn:aws:sqs:us-east-1:123456789012:queuename/policyId",
                        "Condition": {
                            "StringEquals": {
                                "aws:SourceArn": "arn:aws:sns:us-west-2:123456789012:doesnotexist"
                            }
                        },
                    }
                ],
            },
            "QueueArn": "arn:aws:sqs:us-east-1:123456789012:queuename",
        }
        mock_auth.is_user_contractor.return_value = create_future(False)

        headers = {
            config.get("auth.user_header_name"): "user@github.com",
            config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }
        response = self.fetch(
            "/policies/edit/123456789012/sqs/us-east-1/queuename", headers=headers
        )
        self.assertEqual(response.code, 200)
        self.assertIn(b"arn:aws:sqs:us-east-1:123456789012:queuename", response.body)
        self.assertIn(b"SQS:SendMessage", response.body)
        self.assertIn(b"Resource Policy Editor", response.body)

    @patch(
        "consoleme.handlers.policies.ResourcePolicyEditHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    @patch("consoleme.lib.aws.RedisHandler", mock_policy_redis)
    @patch("consoleme.handlers.base.auth")
    @patch("consoleme.lib.aws.get_topic_attributes")
    @patch("consoleme.lib.aws.boto3_cached_conn")
    def test_sns_topic_pageload(
        self, mock_boto3_cached_conn, mock_get_topic_attributes, mock_auth
    ):
        mock_boto3_cached_conn.list_tags_for_resource.return_value = {"Tags": []}
        mock_get_topic_attributes.return_value = {
            "Policy": json.dumps(
                {
                    "Version": "2008-10-17",
                    "Id": "__default_policy_ID",
                    "Statement": [
                        {
                            "Sid": "__default_statement_ID",
                            "Effect": "Allow",
                            "Principal": {"AWS": "*"},
                            "Action": [
                                "SNS:GetTopicAttributes",
                                "SNS:SetTopicAttributes",
                                "SNS:AddPermission",
                                "SNS:RemovePermission",
                                "SNS:DeleteTopic",
                                "SNS:Subscribe",
                                "SNS:ListSubscriptionsByTopic",
                                "SNS:Publish",
                                "SNS:Receive",
                            ],
                            "Resource": "arn:aws:sns:us-east-1:123456789012:topicname",
                            "Condition": {
                                "StringEquals": {"AWS:SourceOwner": "123456789012"}
                            },
                        }
                    ],
                }
            ),
            "Owner": "123456789012",
            "SubscriptionsPending": "0",
            "TopicArn": "arn:aws:sns:us-east-1:123456789012:topicname",
            "EffectiveDeliveryPolicy": "fake",
            "SubscriptionsConfirmed": "1",
            "DisplayName": "",
            "SubscriptionsDeleted": "0",
        }
        mock_auth.is_user_contractor.return_value = create_future(False)

        headers = {
            config.get("auth.user_header_name"): "user@github.com",
            config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }
        response = self.fetch(
            "/policies/edit/123456789012/sns/us-east-1/topicname", headers=headers
        )
        self.assertEqual(response.code, 200)
        self.assertIn(b"arn:aws:sns:us-east-1:123456789012:topicname", response.body)
        self.assertIn(b"SNS:GetTopicAttributes", response.body)
        self.assertIn(b"Resource Policy Editor", response.body)

    @patch(
        "consoleme.handlers.policies.ResourcePolicyEditHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    @patch("consoleme.lib.aws.RedisHandler", mock_policy_redis)
    @patch("consoleme.handlers.base.auth")
    @patch("consoleme.lib.aws.get_bucket_policy")
    @patch("consoleme.lib.aws.get_bucket_tagging")
    @patch("consoleme.handlers.policies.can_manage_policy_requests")
    @patch("consoleme.lib.policies.boto3_cached_conn")
    def test_s3_update_policy(
        self,
        mock_boto3_cached_conn,
        mock_can_manage_policy_requests,
        mock_get_bucket_tagging,
        mock_get_bucket_policy,
        mock_auth,
    ):
        mock_can_manage_policy_requests.return_value = create_future(True)
        mock_get_bucket_policy.return_value = {
            "Policy": json.dumps(
                {
                    "Id": "Policy1562773327512",
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Sid": "Stmt1562773326182",
                            "Action": ["s3:GetObject", "s3:ListBucket"],
                            "Effect": "Allow",
                            "Resource": "arn:aws:s3:::bucketname",
                            "Principal": {
                                "AWS": ["arn:aws:iam::123456789012:role/FakeRole"]
                            },
                        }
                    ],
                }
            )
        }

        mock_get_bucket_tagging.return_value = {"TagSet": []}
        mock_auth.is_user_contractor.return_value = create_future(False)

        headers = {
            config.get("auth.user_header_name"): "user@github.com",
            config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }
        body = [
            {
                "type": "ResourcePolicy",
                "name": "Resource Policy",
                "value": '{"test": "value"}',
                "is_new": False,
            }
        ]

        response = self.fetch(
            "/policies/edit/123456789012/s3/bucketname",
            headers=headers,
            method="POST",
            body=json.dumps(body),
        )
        self.assertEqual(response.code, 200)
        self.assertIn(b'{"status": "success"}', response.body)

        body = [{"type": "update_tag", "name": "tag-test", "value": "test"}]

        response = self.fetch(
            "/policies/edit/123456789012/s3/bucketname",
            headers=headers,
            method="POST",
            body=json.dumps(body),
        )
        self.assertEqual(response.code, 200)
        self.assertIn(b'{"status": "success"}', response.body)

        body = [{"type": "delete_tag", "name": "tag-test"}]

        response = self.fetch(
            "/policies/edit/123456789012/s3/bucketname",
            headers=headers,
            method="POST",
            body=json.dumps(body),
        )
        self.assertEqual(response.code, 200)
        self.assertIn(b'{"status": "success"}', response.body)

    @patch(
        "consoleme.handlers.policies.ResourcePolicyEditHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    @patch("consoleme.lib.aws.RedisHandler", mock_policy_redis)
    @patch("consoleme.handlers.base.auth")
    @patch("consoleme.lib.aws.get_queue_url")
    @patch("consoleme.lib.aws.get_queue_attributes")
    @patch("consoleme.lib.aws.list_queue_tags")
    @patch("consoleme.handlers.policies.can_manage_policy_requests")
    @patch("consoleme.lib.policies.boto3_cached_conn")
    def test_sqs_update_policy(
        self,
        mock_boto3_cached_conn,
        mock_can_manage_policy_requests,
        mock_list_queue_tags,
        mock_get_queue_attributes,
        mock_get_queue_url,
        mock_auth,
    ):
        mock_can_manage_policy_requests.return_value = create_future(True)
        mock_list_queue_tags.return_value = []
        mock_get_queue_url.return_value = (
            "https://queue.amazonaws.com/123456789012/queuename"
        )
        mock_get_queue_attributes.return_value = {
            "Policy": {
                "Version": "2008-10-17",
                "Id": "arn:aws:sqs:us-east-1:123456789012:queuename/policyId",
                "Statement": [
                    {
                        "Sid": "testsid",
                        "Effect": "Allow",
                        "Principal": {"AWS": "*"},
                        "Action": "SQS:SendMessage",
                        "Resource": "arn:aws:sqs:us-east-1:123456789012:queuename/policyId",
                        "Condition": {
                            "StringEquals": {
                                "aws:SourceArn": "arn:aws:sns:us-west-2:123456789012:doesnotexist"
                            }
                        },
                    }
                ],
            },
            "QueueArn": "arn:aws:sqs:us-east-1:123456789012:queuename",
        }
        mock_auth.is_user_contractor.return_value = create_future(False)

        headers = {
            config.get("auth.user_header_name"): "user@github.com",
            config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }
        body = [
            {
                "type": "ResourcePolicy",
                "name": "Resource Policy",
                "value": '{"test":"policy"}',
                "is_new": False,
            }
        ]

        response = self.fetch(
            "/policies/edit/123456789012/sqs/queuename",
            headers=headers,
            method="POST",
            body=json.dumps(body),
        )
        self.assertEqual(response.code, 200)
        self.assertIn(b'{"status": "success"}', response.body)

        body = [{"type": "update_tag", "name": "tag-test", "value": "test"}]

        response = self.fetch(
            "/policies/edit/123456789012/sqs/queuename",
            headers=headers,
            method="POST",
            body=json.dumps(body),
        )
        self.assertEqual(response.code, 200)
        self.assertIn(b'{"status": "success"}', response.body)

        body = [{"type": "delete_tag", "name": "tag-test"}]

        response = self.fetch(
            "/policies/edit/123456789012/sqs/queuename",
            headers=headers,
            method="POST",
            body=json.dumps(body),
        )
        self.assertEqual(response.code, 200)
        self.assertIn(b'{"status": "success"}', response.body)

    @patch(
        "consoleme.handlers.policies.ResourcePolicyEditHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    @patch("consoleme.lib.aws.RedisHandler", mock_policy_redis)
    @patch("consoleme.handlers.base.auth")
    @patch("consoleme.lib.aws.get_topic_attributes")
    @patch("consoleme.handlers.policies.can_manage_policy_requests")
    @patch("consoleme.lib.aws.boto3_cached_conn")
    @patch("consoleme.lib.policies.boto3_cached_conn")
    def test_sns_update_policy(
        self,
        mock_boto3_cached_conn_p,
        mock_boto3_cached_conn,
        mock_can_manage_policy_requests,
        mock_get_topic_attributes,
        mock_auth,
    ):
        mock_can_manage_policy_requests.return_value = create_future(True)
        mock_boto3_cached_conn.list_tags_for_resource.return_value = {"Tags": []}
        mock_get_topic_attributes.return_value = {
            "Policy": json.dumps(
                {
                    "Version": "2008-10-17",
                    "Id": "__default_policy_ID",
                    "Statement": [
                        {
                            "Sid": "__default_statement_ID",
                            "Effect": "Allow",
                            "Principal": {"AWS": "*"},
                            "Action": [
                                "SNS:GetTopicAttributes",
                                "SNS:SetTopicAttributes",
                                "SNS:AddPermission",
                                "SNS:RemovePermission",
                                "SNS:DeleteTopic",
                                "SNS:Subscribe",
                                "SNS:ListSubscriptionsByTopic",
                                "SNS:Publish",
                                "SNS:Receive",
                            ],
                            "Resource": "arn:aws:sns:us-east-1:123456789012:topicname",
                            "Condition": {
                                "StringEquals": {"AWS:SourceOwner": "123456789012"}
                            },
                        }
                    ],
                }
            ),
            "Owner": "123456789012",
            "SubscriptionsPending": "0",
            "TopicArn": "arn:aws:sns:us-east-1:123456789012:topicname",
            "EffectiveDeliveryPolicy": "fake",
            "SubscriptionsConfirmed": "1",
            "DisplayName": "",
            "SubscriptionsDeleted": "0",
        }
        mock_auth.is_user_contractor.return_value = create_future(False)

        headers = {
            config.get("auth.user_header_name"): "user@github.com",
            config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }
        body = [
            {
                "type": "ResourcePolicy",
                "name": "Resource Policy",
                "value": '{"test":"policy"}',
                "is_new": False,
            }
        ]

        response = self.fetch(
            "/policies/edit/123456789012/sns/topicname",
            headers=headers,
            method="POST",
            body=json.dumps(body),
        )
        self.assertEqual(response.code, 200)
        self.assertIn(b'{"status": "success"}', response.body)

        body = [{"type": "update_tag", "name": "tag-test", "value": "test"}]

        response = self.fetch(
            "/policies/edit/123456789012/sns/topicname",
            headers=headers,
            method="POST",
            body=json.dumps(body),
        )
        self.assertEqual(response.code, 200)
        self.assertIn(b'{"status": "success"}', response.body)

        body = [{"type": "delete_tag", "name": "tag-test"}]

        response = self.fetch(
            "/policies/edit/123456789012/sns/topicname",
            headers=headers,
            method="POST",
            body=json.dumps(body),
        )
        self.assertEqual(response.code, 200)
        self.assertIn(b'{"status": "success"}', response.body)

    @patch(
        "consoleme.handlers.policies.ResourceTypeAheadHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    @patch("consoleme.lib.aws.RedisHandler", mock_policy_redis)
    @patch("consoleme.handlers.base.auth")
    @patch("consoleme.handlers.policies.redis_hgetall")
    def test_resource_typeahead(self, mock_redis_hgetall, mock_auth):
        headers = {
            config.get("auth.user_header_name"): "user@example.com",
            config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }

        # Invalid resource, no search string
        resource = "fake"
        response = self.fetch(
            f"/policies/typeahead?resource={resource}", headers=headers, method="GET"
        )
        self.assertEqual(response.code, 400)

        # Valid resource, no search string
        resource = "s3"
        response = self.fetch(
            f"/policies/typeahead?resource={resource}", headers=headers, method="GET"
        )
        self.assertEqual(response.code, 400)
        result = create_future({"123456789012": '["abucket1", "abucket2"]'})
        mock_redis_hgetall.return_value = result
        account_id = "123456789012"
        resource = "s3"
        search = "a"
        response = self.fetch(
            f"/policies/typeahead?resource={resource}&search={search}&account_id={account_id}",
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
