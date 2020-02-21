from datetime import datetime, timedelta
from unittest import TestCase

import pytz
from mock import patch

from consoleme.lib.aws import (
    apply_managed_policy_to_role,
    is_role_instance_profile,
    role_has_managed_policy,
    role_has_tag,
    role_newer_than_x_days,
)

ROLE = {
    "Arn": "arn:aws:iam::123456789012:role/TestInstanceProfile",
    "RoleName": "TestInstanceProfile",
    "CreateDate": datetime.now(tz=pytz.utc) - timedelta(days=5),
    "AttachedManagedPolicies": [{"PolicyName": "Policy1"}, {"PolicyName": "Policy2"}],
    "Tags": [{"Key": "tag1", "Value": "value1"}],
}


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

    @patch("consoleme.lib.aws.boto3_cached_conn")
    def test_apply_managed_policy_to_role(self, mock_boto3_cached_conn):
        apply_managed_policy_to_role(ROLE, "test", "session")
        mock_boto3_cached_conn.assert_called_with(
            "iam",
            account_number="123456789012",
            assume_role="ConsoleMe",
            session_name="session",
        )
        mock_boto3_cached_conn().attach_role_policy.assert_called_with(
            RoleName=ROLE.get("RoleName"),
            PolicyArn="arn:aws:iam::123456789012:policy/test",
        )
