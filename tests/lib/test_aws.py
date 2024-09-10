import asyncio
import copy
import time
from datetime import datetime, timedelta
from unittest import TestCase, mock

import boto3
import pytest
import pytz
import ujson as json
from mock import patch

ROLE = {
    "Arn": "arn:aws:iam::123456789012:role/TestInstanceProfile",
    "RoleName": "TestInstanceProfile",
    "CreateDate": datetime.now(tz=pytz.utc) - timedelta(days=5),
    "AttachedManagedPolicies": [{"PolicyName": "Policy1"}, {"PolicyName": "Policy2"}],
    "Tags": [{"Key": "tag1", "Value": "value1"}],
}


class TestAwsLib(TestCase):
    def test_is_role_instance_profile(self):
        from consoleme.lib.aws import is_role_instance_profile

        self.assertTrue(is_role_instance_profile(ROLE))

    def test_is_role_instance_profile_false(self):
        from consoleme.lib.aws import is_role_instance_profile

        role = {"RoleName": "Test"}
        self.assertFalse(is_role_instance_profile(role))

    def test_role_newer_than_x_days(self):
        from consoleme.lib.aws import role_newer_than_x_days

        self.assertTrue(role_newer_than_x_days(ROLE, 30))

    def test_role_newer_than_x_days_false(self):
        from consoleme.lib.aws import role_newer_than_x_days

        self.assertFalse(role_newer_than_x_days(ROLE, 1))

    def test_role_has_managed_policy(self):
        from consoleme.lib.aws import role_has_managed_policy

        self.assertTrue(role_has_managed_policy(ROLE, "Policy1"))

    def test_role_has_managed_policy_false(self):
        from consoleme.lib.aws import role_has_managed_policy

        self.assertFalse(role_has_managed_policy(ROLE, "Policy3"))

    def test_role_has_tag(self):
        from consoleme.lib.aws import role_has_tag

        self.assertTrue(role_has_tag(ROLE, "tag1"))
        self.assertTrue(role_has_tag(ROLE, "tag1", "value1"))

    def test_role_has_tag_false(self):
        from consoleme.lib.aws import role_has_tag

        self.assertFalse(role_has_tag(ROLE, "tag2"))
        self.assertFalse(role_has_tag(ROLE, "tag2", "value1"))
        self.assertFalse(role_has_tag(ROLE, "tag1", "value2"))

    def test_apply_managed_policy_to_role(self):
        from consoleme.lib.aws import apply_managed_policy_to_role

        apply_managed_policy_to_role(ROLE, "policy-one", "session")

    @patch("consoleme.lib.aws.redis_hget")
    def test_get_resource_account(self, mock_aws_config_resources_redis):
        from consoleme.lib.aws import get_resource_account

        mock_aws_config_resources_redis.return_value = None
        test_cases = [
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

        aws_config_resources_test_case = {
            "arn": "arn:aws:s3:::foobar",
            "expected": "123456789012",
            "description": "internal S3 bucket",
        }
        aws_config_resources_test_case_redis_result = {"accountId": "123456789012"}
        mock_aws_config_resources_redis.return_value = json.dumps(
            aws_config_resources_test_case_redis_result
        )

        result = loop.run_until_complete(
            get_resource_account(aws_config_resources_test_case["arn"])
        )
        self.assertEqual(
            aws_config_resources_test_case["expected"],
            result,
            f"Test case failed: " f"{aws_config_resources_test_case['description']}",
        )

    def test_is_member_of_ou(self):
        from consoleme.lib.aws import _is_member_of_ou

        loop = asyncio.get_event_loop()
        fake_org = {
            "Id": "r",
            "Children": [
                {
                    "Id": "a",
                    "Type": "ORGANIZATIONAL_UNIT",
                    "Children": [
                        {
                            "Id": "b",
                            "Type": "ORGANIZATIONAL_UNIT",
                            "Children": [{"Id": "100", "Type": "ACCOUNT"}],
                        }
                    ],
                },
            ],
        }

        # Account ID in nested OU
        result, ous = loop.run_until_complete(_is_member_of_ou("100", fake_org))
        self.assertTrue(result)
        self.assertEqual(ous, {"b", "a", "r"})

        # OU ID in OU structure
        result, ous = loop.run_until_complete(_is_member_of_ou("b", fake_org))
        self.assertTrue(result)
        self.assertEqual(ous, {"a", "r"})

        # ID not in OU structure
        result, ous = loop.run_until_complete(_is_member_of_ou("101", fake_org))
        self.assertFalse(result)
        self.assertEqual(ous, set())

    def test_scp_targets_account_or_ou(self):
        from consoleme.lib.aws import _scp_targets_account_or_ou
        from consoleme.models import (
            ServiceControlPolicyDetailsModel,
            ServiceControlPolicyModel,
            ServiceControlPolicyTargetModel,
        )

        loop = asyncio.get_event_loop()
        blank_scp_details = ServiceControlPolicyDetailsModel(
            id="",
            arn="",
            name="",
            description="",
            aws_managed=False,
            content="",
        )

        # SCP targets account directly
        scp_targets = [
            ServiceControlPolicyTargetModel(
                target_id="100", arn="", name="", type="ACCOUNT"
            )
        ]
        fake_scp = ServiceControlPolicyModel(
            targets=scp_targets, policy=blank_scp_details
        )
        fake_ous = set()
        result = loop.run_until_complete(
            _scp_targets_account_or_ou(fake_scp, "100", fake_ous)
        )
        self.assertTrue(result)

        # SCP targets OU of which account is a member
        scp_targets = [
            ServiceControlPolicyTargetModel(
                target_id="abc123", arn="", name="", type="ORGANIZATIONAL_UNIT"
            )
        ]
        fake_scp = ServiceControlPolicyModel(
            targets=scp_targets, policy=blank_scp_details
        )
        fake_ous = {"abc123", "def456"}
        result = loop.run_until_complete(
            _scp_targets_account_or_ou(fake_scp, "100", fake_ous)
        )
        self.assertTrue(result)

        # SCP doesn't target account
        scp_targets = [
            ServiceControlPolicyTargetModel(
                target_id="ghi789", arn="", name="", type="ORGANIZATIONAL_UNIT"
            )
        ]
        fake_scp = ServiceControlPolicyModel(
            targets=scp_targets, policy=blank_scp_details
        )
        fake_ous = {"abc123", "def456"}
        result = loop.run_until_complete(
            _scp_targets_account_or_ou(fake_scp, "100", fake_ous)
        )
        self.assertFalse(result)

    def test_fetch_managed_policy_details(self):
        from consoleme.config import config
        from consoleme.lib.aws import fetch_managed_policy_details

        loop = asyncio.get_event_loop()

        result = loop.run_until_complete(
            fetch_managed_policy_details("123456789012", "policy-one")
        )
        self.assertDictEqual(
            result["Policy"],
            {
                "Statement": [{"Effect": "Deny", "Action": "*", "Resource": "*"}],
                "Version": "2012-10-17",
            },
        )
        self.assertListEqual(result["TagSet"], [])

        with pytest.raises(Exception) as e:
            loop.run_until_complete(
                fetch_managed_policy_details("123456789012", "policy-non-existent")
            )

        self.assertIn("NoSuchEntity", str(e))

        # test paths
        client = boto3.client(
            "iam", region_name="us-east-1", **config.get("boto3.client_kwargs", {})
        )
        policy_name = "policy_with_paths"
        policy_path = "/testpath/testpath2/"
        client.create_policy(
            PolicyName=policy_name,
            Path=policy_path,
            PolicyDocument=json.dumps(result["Policy"]),
        )
        result = loop.run_until_complete(
            fetch_managed_policy_details(
                "123456789012", policy_name, path="testpath/testpath2"
            )
        )
        self.assertDictEqual(
            result["Policy"],
            {
                "Statement": [{"Effect": "Deny", "Action": "*", "Resource": "*"}],
                "Version": "2012-10-17",
            },
        )

    def test_allowed_to_sync_role(self):
        from consoleme.config.config import CONFIG
        from consoleme.lib.aws import allowed_to_sync_role

        old_config = copy.deepcopy(CONFIG.config)
        test_role_arn = "arn:aws:iam::111111111111:role/role-name-here-1"
        test_role_tags = [
            {"Key": "testtag", "Value": "testtagv"},
            {"Key": "testtag2", "Value": "testtag2v"},
        ]

        self.assertEqual(allowed_to_sync_role(test_role_arn, test_role_tags), True)

        # Allow - allowed_tags exists in role
        CONFIG.config = {
            **CONFIG.config,
            "roles": {
                "allowed_tags": {"testtag": "testtagv"},
            },
        }

        self.assertEqual(allowed_to_sync_role(test_role_arn, test_role_tags), True)

        # Reject, one of the tags doesn't exist on role
        CONFIG.config = {
            **CONFIG.config,
            "roles": {
                "allowed_tags": {"testtag": "testtagv", "testtagNOTEXIST": "testv"},
            },
        }

        self.assertEqual(allowed_to_sync_role(test_role_arn, test_role_tags), False)

        # Allow - Role has all allowed_tags, doesn't matter that allowed_arns doesn't have our role ARN
        CONFIG.config = {
            **CONFIG.config,
            "roles": {
                "allowed_tags": {"testtag": "testtagv"},
                "allowed_arns": ["arn:aws:iam::111111111111:role/some-other-role"],
            },
        }

        self.assertEqual(allowed_to_sync_role(test_role_arn, test_role_tags), True)

        # Allow - Role has all allowed_tags
        CONFIG.config = {
            **CONFIG.config,
            "roles": {
                "allowed_tags": {"testtag": "testtagv"},
                "allowed_arns": ["arn:aws:iam::111111111111:role/BADROLENAME"],
            },
        }

        self.assertEqual(allowed_to_sync_role(test_role_arn, test_role_tags), True)

        # Reject - No tag
        CONFIG.config = {
            **CONFIG.config,
            "roles": {
                "allowed_tags": {"a": "b"},
            },
        }

        self.assertEqual(allowed_to_sync_role(test_role_arn, test_role_tags), False)

        # Allow by ARN
        CONFIG.config = {
            **CONFIG.config,
            "roles": {
                "allowed_arns": ["arn:aws:iam::111111111111:role/role-name-here-1"]
            },
        }

        self.assertEqual(allowed_to_sync_role(test_role_arn, test_role_tags), True)

        # Allow - allowed_tag_keys exists in role
        CONFIG.config = {
            **CONFIG.config,
            "roles": {
                "allowed_tag_keys": ["testtag"],
            },
        }

        self.assertEqual(allowed_to_sync_role(test_role_arn, test_role_tags), True)

        # Reject - No tag key
        CONFIG.config = {
            **CONFIG.config,
            "roles": {
                "allowed_tag_keys": ["unknown"],
            },
        }

        self.assertEqual(allowed_to_sync_role(test_role_arn, test_role_tags), False)

        CONFIG.config = old_config

    def test_remove_temp_policies(self):
        from consoleme.lib.aws import remove_temp_policies

        iam_client = mock.Mock()
        current_dateint = datetime.today().strftime("%Y%m%d")
        past_dateint = (datetime.today() - timedelta(days=1)).strftime("%Y%m%d")
        future_dateint = (datetime.today() + timedelta(days=1)).strftime("%Y%m%d")
        current_time = int(time.time())

        # Should be deleted if date is current date
        policy_name = f"cm_delete-on_{current_dateint}_username_{current_time}"
        role = {
            "RoleName": "rolewithtemppolicy",
            "Arn": "arn:aws:iam::123456789012:role/rolewithtemppolicy",
            "RolePolicyList": [
                {
                    "PolicyName": policy_name,
                    "PolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Action": ["sts:assumerole"],
                                "Effect": "Allow",
                                "Resource": ["arn:aws:iam::*:role/123"],
                            }
                        ],
                    },
                }
            ],
        }
        result = remove_temp_policies(role, iam_client)
        self.assertTrue(result)
        iam_client.delete_role_policy.assert_called_with(
            RoleName="rolewithtemppolicy", PolicyName=policy_name
        )

        # Should be deleted if date is past date
        policy_name = f"cm_delete-on_{past_dateint}_username_{current_time}"
        role = {
            "RoleName": "rolewithtemppolicy",
            "Arn": "arn:aws:iam::123456789012:role/rolewithtemppolicy",
            "RolePolicyList": [
                {
                    "PolicyName": policy_name,
                    "PolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Action": ["sts:assumerole"],
                                "Effect": "Allow",
                                "Resource": ["arn:aws:iam::*:role/123"],
                            }
                        ],
                    },
                }
            ],
        }
        iam_client = mock.Mock()
        result = remove_temp_policies(role, iam_client)
        self.assertTrue(result)
        iam_client.delete_role_policy.assert_called_with(
            RoleName="rolewithtemppolicy", PolicyName=policy_name
        )

        # Should not be deleted if date is future date
        policy_name = f"cm_delete-on_{future_dateint}_username_{current_time}"
        role = {
            "RoleName": "rolewithtemppolicy",
            "Arn": "arn:aws:iam::123456789012:role/rolewithtemppolicy",
            "RolePolicyList": [
                {
                    "PolicyName": policy_name,
                    "PolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Action": ["sts:assumerole"],
                                "Effect": "Allow",
                                "Resource": ["arn:aws:iam::*:role/123"],
                            }
                        ],
                    },
                }
            ],
        }
        iam_client = mock.Mock()
        result = remove_temp_policies(role, iam_client)
        self.assertFalse(result)
        iam_client.delete_role_policy.assert_not_called()

        # Should not be deleted if date is invalid date
        policy_name = f"cm_delete-on_INVALID_username_{current_time}"
        role = {
            "RoleName": "rolewithtemppolicy",
            "Arn": "arn:aws:iam::123456789012:role/rolewithtemppolicy",
            "RolePolicyList": [
                {
                    "PolicyName": policy_name,
                    "PolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Action": ["sts:assumerole"],
                                "Effect": "Allow",
                                "Resource": ["arn:aws:iam::*:role/123"],
                            }
                        ],
                    },
                }
            ],
        }
        iam_client = mock.Mock()
        result = remove_temp_policies(role, iam_client)
        self.assertFalse(result)
        iam_client.delete_role_policy.assert_not_called()
