import asyncio
from unittest import TestCase

import pytest
import pytz
from datetime import datetime, timedelta
from mock import MagicMock, patch

from consoleme.lib.aws import (
    apply_managed_policy_to_role,
    get_resource_account,
    is_role_instance_profile,
    role_has_managed_policy,
    role_has_tag,
    role_newer_than_x_days,
)
from tests.conftest import MockRedisHandler, create_future

ROLE = {
    "Arn": "arn:aws:iam::123456789012:role/TestInstanceProfile",
    "RoleName": "TestInstanceProfile",
    "CreateDate": datetime.now(tz=pytz.utc) - timedelta(days=5),
    "AttachedManagedPolicies": [{"PolicyName": "Policy1"}, {"PolicyName": "Policy2"}],
    "Tags": [{"Key": "tag1", "Value": "value1"}],
}


mock_s3_bucket_redis = MagicMock(
    return_value=create_future({"123456789012": ["foobar", "bazbang"]})
)


@pytest.mark.usefixtures("iam", "iam_sync_roles")
class TestAwsLib(TestCase):
    def test_is_role_instance_profile(self):
        self.assertTrue(is_role_instance_profile(ROLE))

    def test_is_role_instance_profile_false(self):
        role = {"RoleName": "Test"}
        self.assertFalse(is_role_instance_profile(role))

    def test_role_newer_than_x_days(self):
        self.assertTrue(role_newer_than_x_days(ROLE, 30))

    def test_role_newer_than_x_days_false(self):
        self.assertFalse(role_newer_than_x_days(ROLE, 1))

    def test_role_has_managed_policy(self):
        self.assertTrue(role_has_managed_policy(ROLE, "Policy1"))

    def test_role_has_managed_policy_false(self):
        self.assertFalse(role_has_managed_policy(ROLE, "Policy3"))

    def test_role_has_tag(self):
        self.assertTrue(role_has_tag(ROLE, "tag1"))
        self.assertTrue(role_has_tag(ROLE, "tag1", "value1"))

    def test_role_has_tag_false(self):
        self.assertFalse(role_has_tag(ROLE, "tag2"))
        self.assertFalse(role_has_tag(ROLE, "tag2", "value1"))
        self.assertFalse(role_has_tag(ROLE, "tag1", "value2"))

    def test_apply_managed_policy_to_role(self):
        apply_managed_policy_to_role(ROLE, "policy-one", "session")

    @patch("consoleme.lib.aws.redis_hgetall", mock_s3_bucket_redis)
    def test_get_resource_account(self):
        test_cases = [
            {
                "arn": "arn:aws:s3:::foobar",
                "expected": "123456789012",
                "description": "internal S3 bucket",
            },
            {
                "arn": "arn:aws:s3:::nope",
                "expected": "",
                "description": "external S3 bucket",
            },
            {
                "arn": "arn:aws:waddup:us-east-1:987654321000:cool-resource",
                "expected": "987654321000",
                "description": "arbitrary resource with account in ARN",
            },
            {
                "arn": "arn:aws:waddup:us-east-1::cool-resource",
                "expected": "",
                "description": "arbitrary resource without account in ARN",
            },
        ]
        loop = asyncio.get_event_loop()
        for tc in test_cases:
            result = loop.run_until_complete(get_resource_account(tc["arn"]))
            self.assertEqual(
                tc["expected"], result, f"Test case failed: {tc['description']}"
            )
