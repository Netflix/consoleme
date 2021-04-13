import time
import unittest

import boto3
import pytest
import ujson as json
from mock import patch
from pydantic import ValidationError

from consoleme.models import (
    Action,
    Action1,
    AssumeRolePolicyChangeModel,
    ChangeModelArray,
    Command,
    ExtendedRequestModel,
    ExtendedRoleModel,
    InlinePolicyChangeModel,
    ManagedPolicyChangeModel,
    PolicyRequestModificationRequestModel,
    PolicyRequestModificationResponseModel,
    RequestCreationResponse,
    RequestStatus,
    ResourcePolicyChangeModel,
    Status,
    UserModel,
)
from tests.conftest import create_future

existing_policy_name = "test_inline_policy_change5"
existing_policy_document = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": [
                "s3:ListBucket",
                "s3:ListBucketVersions",
                "s3:GetObject",
                "s3:GetObjectTagging",
                "s3:GetObjectVersion",
                "s3:GetObjectVersionTagging",
                "s3:GetObjectAcl",
                "s3:GetObjectVersionAcl",
            ],
            "Effect": "Allow",
            "Resource": ["arn:aws:s3:::test_bucket", "arn:aws:s3:::test_bucket/abc/*"],
            "Sid": "sid_test",
        }
    ],
}


async def get_extended_request_helper():
    inline_policy_change = {
        "principal_arn": "arn:aws:iam::123456789012:role/test",
        "change_type": "inline_policy",
        "resources": [],
        "version": 2.0,
        "status": "not_applied",
        "policy_name": "test_inline_policy_change",
        "id": "1234_0",
        "new": False,
        "action": "attach",
        "policy": {
            "version": None,
            "policy_document": {},
            "policy_sha256": "55d03ad7a2a447e6e883c520edcd8e5e3083c2f83fa1c390cee3f7dbedf28533",
        },
        "old_policy": None,
    }
    inline_policy_change_model = InlinePolicyChangeModel.parse_obj(inline_policy_change)

    extended_request = ExtendedRequestModel(
        id="1234",
        arn="arn:aws:iam::123456789012:role/test",
        timestamp=int(time.time()),
        justification="Test justification",
        requester_email="user@example.com",
        approvers=[],
        request_status="pending",
        changes=ChangeModelArray(changes=[inline_policy_change_model]),
        requester_info=UserModel(email="user@example.com"),
        comments=[],
    )
    return extended_request


class TestRequestsLibV2(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.maxDiff = None
        client = boto3.client("iam", region_name="us-east-1")
        role_name = "test"
        client.create_role(RoleName=role_name, AssumeRolePolicyDocument="{}")

    async def asyncTearDown(self):
        role_name = "test"
        from consoleme.lib.aws import delete_iam_role

        await delete_iam_role("123456789012", role_name, "consoleme-unit-test")

    async def test_validate_inline_policy_change(self):
        from consoleme.exceptions.exceptions import InvalidRequestParameter
        from consoleme.lib.v2.requests import validate_inline_policy_change

        role = ExtendedRoleModel(
            name="role_name",
            account_id="123456789012",
            account_name="friendly_name",
            arn="arn:aws:iam::123456789012:role/role_name",
            inline_policies=[],
            assume_role_policy_document={},
            managed_policies=[],
            tags=[],
        )

        inline_policy_change = {
            "principal_arn": "arn:aws:iam::123456789012:role/test",
            "change_type": "inline_policy",
            "resources": [],
            "version": 2.0,
            "status": "not_applied",
            "policy_name": "test_inline_policy_change",
            "new": False,
            "action": "attach",
            "policy": {
                "version": None,
                "policy_document": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": [
                                "s3:ListBucket",
                                "s3:ListBucketVersions",
                                "s3:GetObject",
                                "s3:GetObjectTagging",
                                "s3:GetObjectVersion",
                                "s3:GetObjectVersionTagging",
                                "s3:GetObjectAcl",
                                "s3:GetObjectVersionAcl",
                            ],
                            "Effect": "Allow",
                            "Resource": [
                                "arn:aws:s3:::test_bucket",
                                "arn:aws:s3:::test_bucket/abc/*",
                            ],
                            "Sid": "sid_test",
                        }
                    ],
                },
                "policy_sha256": "55d03ad7a2a447e6e883c520edcd8e5e3083c2f83fa1c390cee3f7dbedf28533",
            },
            "old_policy": None,
        }
        inline_policy_change_model = InlinePolicyChangeModel.parse_obj(
            inline_policy_change
        )

        # Attaching a new policy while claiming it's not new
        with pytest.raises(InvalidRequestParameter) as e:
            await validate_inline_policy_change(
                inline_policy_change_model, "user@example.com", role
            )
            self.assertIn(
                "Inline policy not seen but request claims change is not new", str(e)
            )

        # Trying to detach a new policy
        inline_policy_change_model.new = True
        inline_policy_change_model.action = Action.detach
        with pytest.raises(InvalidRequestParameter) as e:
            await validate_inline_policy_change(
                inline_policy_change_model, "user@example.com", role
            )
            self.assertIn("Can't detach an inline policy that is new.", str(e))

        # Trying to detach a non-existent policy
        inline_policy_change_model.new = False
        inline_policy_change_model.action = Action.detach
        with pytest.raises(InvalidRequestParameter) as e:
            await validate_inline_policy_change(
                inline_policy_change_model, "user@example.com", role
            )
            self.assertIn("Can't detach an inline policy that is not attached.", str(e))

        # Trying to attach a "new" policy that has the same name as an old policy -> Prevent accidental overwrites
        inline_policy_change_model.new = True
        inline_policy_change_model.action = Action.attach
        role.inline_policies = [{"PolicyName": inline_policy_change_model.policy_name}]
        with pytest.raises(InvalidRequestParameter) as e:
            await validate_inline_policy_change(
                inline_policy_change_model, "user@example.com", role
            )
            self.assertIn("Inline Policy with that name already exists.", str(e))

        # Trying to update an inline policy... without making any changes
        inline_policy_change_model.new = False
        inline_policy_change_model.action = Action.attach
        role.inline_policies = [
            {
                "PolicyName": inline_policy_change_model.policy_name,
                "PolicyDocument": inline_policy_change_model.policy.policy_document,
            }
        ]
        with pytest.raises(InvalidRequestParameter) as e:
            await validate_inline_policy_change(
                inline_policy_change_model, "user@example.com", role
            )
            self.assertIn(
                "No changes were found between the updated and existing policy.", str(e)
            )

        # Trying to update an inline policy with invalid characters
        inline_policy_change_model.action = Action.attach
        inline_policy_change_model.policy_name = "<>test_invalid_name"
        with pytest.raises(InvalidRequestParameter) as e:
            await validate_inline_policy_change(
                inline_policy_change_model, "user@example.com", role
            )
            self.assertIn("Invalid characters were detected in the policy.", str(e))

        # Now some tests that should pass validation

        # Updating an inline policy that exists
        inline_policy_change_model.new = False
        inline_policy_change_model.action = Action.attach
        inline_policy_change_model.policy_name = "test_inline_policy_change"
        role.inline_policies = [
            {"PolicyName": inline_policy_change_model.policy_name, "PolicyDocument": {}}
        ]
        await validate_inline_policy_change(
            inline_policy_change_model, "user@example.com", role
        )

        # Detaching an inline policy
        inline_policy_change_model.new = False
        inline_policy_change_model.action = Action.detach
        await validate_inline_policy_change(
            inline_policy_change_model, "user@example.com", role
        )

        # Adding a new inline policy
        inline_policy_change_model.new = True
        inline_policy_change_model.action = Action.attach
        inline_policy_change_model.policy_name = "test_inline_policy_change_2"
        await validate_inline_policy_change(
            inline_policy_change_model, "user@example.com", role
        )

    async def test_validate_managed_policy_change(self):
        from consoleme.exceptions.exceptions import InvalidRequestParameter
        from consoleme.lib.v2.requests import validate_managed_policy_change

        role = ExtendedRoleModel(
            name="role_name",
            account_id="123456789012",
            account_name="friendly_name",
            arn="arn:aws:iam::123456789012:role/role_name",
            inline_policies=[],
            assume_role_policy_document={},
            managed_policies=[],
            tags=[],
        )
        managed_policy_change = {
            "principal_arn": "arn:aws:iam::123456789012:role/role_name",
            "change_type": "managed_policy",
            "policy_name": "invalid<html>characters",
            "resources": [],
            "status": "not_applied",
            "action": "detach",
            "arn": "arn:aws:iam::123456789012:policy/TestManagedPolicy",
        }
        managed_policy_change_model = ManagedPolicyChangeModel.parse_obj(
            managed_policy_change
        )

        # Trying to update an managed policy with invalid characters
        with pytest.raises(InvalidRequestParameter) as e:
            await validate_managed_policy_change(
                managed_policy_change_model, "user@example.com", role
            )
            self.assertIn("Invalid characters were detected in the policy.", str(e))

        # Trying to detach a policy that is not attached
        managed_policy_change_model.action = Action1.detach
        with pytest.raises(InvalidRequestParameter) as e:
            await validate_managed_policy_change(
                managed_policy_change_model, "user@example.com", role
            )
            self.assertIn(
                f"{managed_policy_change_model.arn} is not attached to this role",
                str(e),
            )

        # Trying to attach a policy that is already attached
        role.managed_policies = [{"PolicyArn": managed_policy_change_model.arn}]
        managed_policy_change_model.action = Action1.attach
        with pytest.raises(InvalidRequestParameter) as e:
            await validate_managed_policy_change(
                managed_policy_change_model, "user@example.com", role
            )
            self.assertIn(
                f"{managed_policy_change_model.arn} already attached to this role",
                str(e),
            )

        # Valid tests

        # Attach a managed policy that is not attached
        managed_policy_change_model.arn = (
            "arn:aws:iam::123456789012:policy/TestManagedPolicy2"
        )
        managed_policy_change_model.action = Action1.attach
        await validate_managed_policy_change(
            managed_policy_change_model, "user@example.com", role
        )

        # Detach a managed policy that is attached to the role
        role.managed_policies = [{"PolicyArn": managed_policy_change_model.arn}]
        managed_policy_change_model.action = Action1.detach
        await validate_managed_policy_change(
            managed_policy_change_model, "user@example.com", role
        )

    async def test_validate_assume_role_policy_change(self):
        from consoleme.exceptions.exceptions import InvalidRequestParameter
        from consoleme.lib.v2.requests import validate_assume_role_policy_change

        role = ExtendedRoleModel(
            name="role_name",
            account_id="123456789012",
            account_name="friendly_name",
            arn="arn:aws:iam::123456789012:role/role_name",
            inline_policies=[],
            assume_role_policy_document={},
            managed_policies=[],
            tags=[],
        )
        assume_role_policy_change = {
            "principal_arn": "arn:aws:iam::123456789012:role/role_name",
            "change_type": "assume_role_policy",
            "resources": [],
            "status": "not_applied",
            "new": True,
            "policy": {
                "version": "<>>",
                "policy_document": {
                    "Statement": [
                        {
                            "Action": "sts:AssumeRole",
                            "Effect": "Allow",
                            "Principal": {
                                "AWS": "arn:aws:iam::123456789012:role/myProfile"
                            },
                            "Sid": "AllowMeToAssumePlease",
                        }
                    ],
                    "Version": "2012-10-17",
                },
                "policy_sha256": "55d03ad7a2a447e6e883c520edcd8e5e3083c2f83fa1c390cee3f7dbedf28533",
            },
            "old_policy": None,
        }
        assume_role_policy_change_model = AssumeRolePolicyChangeModel.parse_obj(
            assume_role_policy_change
        )

        # Trying to update an assume role policy with invalid characters
        with pytest.raises(InvalidRequestParameter) as e:
            await validate_assume_role_policy_change(
                assume_role_policy_change_model, "user@example.com", role
            )
            self.assertIn("Invalid characters were detected in the policy", str(e))

        assume_role_policy_change_model.policy.version = None

        # Updating the same assume role policy as current document
        role.assume_role_policy_document = (
            assume_role_policy_change_model.policy.policy_document
        )
        with pytest.raises(InvalidRequestParameter) as e:
            await validate_assume_role_policy_change(
                assume_role_policy_change_model, "user@example.com", role
            )
            self.assertIn(
                "No changes were found between the updated and existing assume role policy.",
                str(e),
            )

        # Valid test: updating assume role policy document with no invalid characters
        role.assume_role_policy_document = {}
        await validate_assume_role_policy_change(
            assume_role_policy_change_model, "user@example.com", role
        )

    async def test_generate_resource_policies(self):
        from consoleme.lib.redis import RedisHandler
        from consoleme.lib.v2.requests import generate_resource_policies

        # Redis is globally mocked. Let's store and retrieve a fake value
        red = RedisHandler().redis_sync()
        red.hmset(
            "AWSCONFIG_RESOURCE_CACHE",
            {
                "arn:aws:s3:::test_bucket": json.dumps({"accountId": "123456789013"}),
                "arn:aws:s3:::test_bucket_2": json.dumps({"accountId": "123456789013"}),
            },
        )

        inline_policy_change = {
            "principal_arn": "arn:aws:iam::123456789012:role/test",
            "change_type": "inline_policy",
            "resources": [
                {
                    "arn": "arn:aws:s3:::test_bucket",
                    "name": "test_bucket",
                    "account_id": "",
                    "region": "global",
                    "account_name": "",
                    "resource_type": "s3",
                },
                {
                    "arn": "arn:aws:s3:::test_bucket_2",
                    "name": "test_bucket_2",
                    "account_id": "",
                    "region": "global",
                    "account_name": "",
                    "resource_type": "s3",
                },
                {
                    "arn": "arn:aws:iam::123456789013:role/test_2",
                    "name": "test_2",
                    "account_id": "123456789013",
                    "region": "global",
                    "account_name": "",
                    "resource_type": "iam",
                },
                {
                    "arn": "arn:aws:iam::123456789012:role/test_3",
                    "name": "test_3",
                    "account_id": "123456789012",
                    "region": "global",
                    "account_name": "",
                    "resource_type": "iam",
                },
                {
                    "arn": "arn:aws:iam::123456789013:role/test_3",
                    "name": "test_3",
                    "account_id": "123456789013",
                    "region": "global",
                    "account_name": "",
                    "resource_type": "iam",
                },
            ],
            "version": 2.0,
            "status": "not_applied",
            "policy_name": "test_inline_policy_change",
            "new": False,
            "action": "attach",
            "policy": {
                "version": None,
                "policy_document": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": [
                                "s3:ListBucket",
                                "s3:ListBucketVersions",
                                "s3:GetObject",
                                "s3:GetObjectTagging",
                                "s3:GetObjectVersion",
                                "s3:GetObjectVersionTagging",
                                "s3:GetObjectAcl",
                                "s3:GetObjectVersionAcl",
                            ],
                            "Effect": "Allow",
                            "Resource": [
                                "arn:aws:s3:::test_bucket",
                                "arn:aws:s3:::test_bucket/abc/*",
                                "arn:aws:s3:::test_bucket_2",
                                "arn:aws:S3:::test_bucket_2/*",
                            ],
                            "Sid": "sid_test",
                        },
                        {
                            "Action": ["sts:AssumeRole", "sts:TagSession"],
                            "Effect": "Allow",
                            "Resource": ["arn:aws:iam::123456789013:role/test_2"],
                            "Sid": "assume_role_test_cross_account",
                        },
                        {
                            "Action": "sts:AssumeRole",
                            "Effect": "Allow",
                            "Resource": ["arn:aws:iam::123456789012:role/test_3"],
                            "Sid": "assume_role_test_same_account",
                        },
                        {
                            "Action": "sts:TagSession",
                            "Effect": "Allow",
                            "Resource": ["arn:aws:iam::123456789013:role/test_3"],
                            "Sid": "assume_role_test_cross_account_tag",
                        },
                    ],
                },
                "policy_sha256": "55d03ad7a2a447e6e883c520edcd8e5e3083c2f83fa1c390cee3f7dbedf28533",
            },
            "old_policy": None,
        }
        inline_policy_change_model = InlinePolicyChangeModel.parse_obj(
            inline_policy_change
        )

        managed_policy_change = {
            "principal_arn": "arn:aws:iam::123456789012:role/role_name",
            "change_type": "managed_policy",
            "policy_name": "invalid<html>characters",
            "resources": [],
            "status": "not_applied",
            "action": "detach",
            "arn": "arn:aws:iam::123456789012:policy/TestManagedPolicy",
        }
        managed_policy_change_model = ManagedPolicyChangeModel.parse_obj(
            managed_policy_change
        )

        request_changes = {
            "changes": [inline_policy_change_model, managed_policy_change_model]
        }
        extended_request = ExtendedRequestModel(
            id="1234",
            arn="arn:aws:iam::123456789012:role/test",
            timestamp=int(time.time()),
            justification="Test justification",
            requester_email="user@example.com",
            approvers=[],
            request_status="pending",
            changes=request_changes,
            requester_info=UserModel(email="user@example.com"),
            comments=[],
        )
        len_before_call = len(extended_request.changes.changes)
        number_of_resources = 4
        await generate_resource_policies(
            extended_request, extended_request.requester_email
        )

        self.assertEqual(
            len(extended_request.changes.changes), len_before_call + number_of_resources
        )
        self.assertEqual(
            inline_policy_change_model.policy,
            extended_request.changes.changes[0].policy,
        )
        self.assertEqual(
            len(inline_policy_change_model.resources),
            len(extended_request.changes.changes[0].resources),
        )
        self.assertIn(managed_policy_change_model, extended_request.changes.changes)

        seen_resource_one = False
        seen_resource_two = False
        seen_resource_three = False
        seen_resource_four = False
        for change in extended_request.changes.changes:
            if (
                change.change_type == "resource_policy"
                and change.arn == inline_policy_change_model.resources[0].arn
            ):
                seen_resource_one = True
                self.assertTrue(change.autogenerated)
            elif (
                change.change_type == "resource_policy"
                and change.arn == inline_policy_change_model.resources[1].arn
            ):
                seen_resource_two = True
                self.assertTrue(change.autogenerated)
            elif (
                change.change_type == "sts_resource_policy"
                and change.arn == inline_policy_change_model.resources[2].arn
            ):
                seen_resource_three = True
                self.assertTrue(change.autogenerated)
            elif (
                change.change_type == "sts_resource_policy"
                and change.arn == inline_policy_change_model.resources[4].arn
            ):
                seen_resource_four = True
                self.assertTrue(change.autogenerated)
            # Same account sts shouldn't be included
            if (
                change.change_type == "resource_policy"
                or change.change_type == "sts_resource_policy"
            ):
                self.assertNotEqual(
                    change.arn, inline_policy_change_model.resources[3].arn
                )

        self.assertTrue(seen_resource_one)
        self.assertTrue(seen_resource_two)
        self.assertTrue(seen_resource_three)
        self.assertTrue(seen_resource_four)
        red.delete("AWSCONFIG_RESOURCE_CACHE")

    async def test_apply_changes_to_role_inline_policy(self):
        from consoleme.lib.v2.requests import apply_changes_to_role

        inline_policy_change = {
            "principal_arn": "arn:aws:iam::123456789012:role/test",
            "change_type": "inline_policy",
            "resources": [],
            "version": 2.0,
            "status": "not_applied",
            "policy_name": "test_inline_policy_change",
            "new": True,
            "action": "detach",
            "policy": {
                "version": None,
                "policy_document": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": [
                                "s3:ListBucket",
                                "s3:ListBucketVersions",
                                "s3:GetObject",
                                "s3:GetObjectTagging",
                                "s3:GetObjectVersion",
                                "s3:GetObjectVersionTagging",
                                "s3:GetObjectAcl",
                                "s3:GetObjectVersionAcl",
                            ],
                            "Effect": "Allow",
                            "Resource": [
                                "arn:aws:s3:::test_bucket",
                                "arn:aws:s3:::test_bucket/abc/*",
                            ],
                            "Sid": "sid_test",
                        }
                    ],
                },
                "policy_sha256": "55d03ad7a2a447e6e883c520edcd8e5e3083c2f83fa1c390cee3f7dbedf28533",
            },
            "old_policy": None,
        }
        inline_policy_change_model = InlinePolicyChangeModel.parse_obj(
            inline_policy_change
        )

        extended_request = ExtendedRequestModel(
            id="1234",
            arn="arn:aws:iam::123456789012:role/test",
            timestamp=int(time.time()),
            justification="Test justification",
            requester_email="user@example.com",
            approvers=[],
            request_status="pending",
            changes=ChangeModelArray(changes=[inline_policy_change_model]),
            requester_info=UserModel(email="user@example.com"),
            comments=[],
        )

        response = RequestCreationResponse(
            errors=0,
            request_created=True,
            request_id=extended_request.id,
            action_results=[],
        )

        client = boto3.client("iam", region_name="us-east-1")
        role_name = "test"

        # Detaching inline policy that isn't attached -> error
        await apply_changes_to_role(
            extended_request, response, extended_request.requester_email
        )
        self.assertEqual(1, response.errors)
        self.assertIn(
            "Error occurred deleting inline policy",
            dict(response.action_results[0]).get("message"),
        )

        # Attaching inline policy -> no error
        response.action_results = []
        response.errors = 0
        inline_policy_change_model.action = Action.attach
        extended_request.changes = ChangeModelArray(
            changes=[inline_policy_change_model]
        )
        await apply_changes_to_role(
            extended_request, response, extended_request.requester_email
        )
        self.assertEqual(0, response.errors)
        self.assertIn(
            "Successfully applied inline policy",
            dict(response.action_results[0]).get("message", ""),
        )
        # Make sure it attached
        inline_policy = client.get_role_policy(
            RoleName=role_name, PolicyName=inline_policy_change_model.policy_name
        )
        self.assertEqual(
            inline_policy_change_model.policy_name, inline_policy.get("PolicyName")
        )
        self.assertEqual(
            inline_policy_change_model.policy.policy_document,
            inline_policy.get("PolicyDocument"),
        )

        # Updating the inline policy -> no error
        inline_policy_change_model.policy.policy_document.get("Statement")[0][
            "Effect"
        ] = "Deny"
        extended_request.changes = ChangeModelArray(
            changes=[inline_policy_change_model]
        )
        await apply_changes_to_role(
            extended_request, response, extended_request.requester_email
        )
        self.assertEqual(0, response.errors)
        self.assertIn(
            "Successfully applied inline policy",
            dict(response.action_results[0]).get("message", ""),
        )
        # Make sure it updated
        inline_policy = client.get_role_policy(
            RoleName=role_name, PolicyName=inline_policy_change_model.policy_name
        )
        self.assertEqual(
            inline_policy_change_model.policy_name, inline_policy.get("PolicyName")
        )
        self.assertEqual(
            inline_policy_change_model.policy.policy_document,
            inline_policy.get("PolicyDocument"),
        )

        # Detach the above attached inline policy -> no error, should be detached
        response.action_results = []
        response.errors = 0
        inline_policy_change_model.action = Action.detach
        extended_request.changes = ChangeModelArray(
            changes=[inline_policy_change_model]
        )
        await apply_changes_to_role(
            extended_request, response, extended_request.requester_email
        )
        self.assertEqual(0, response.errors)
        with pytest.raises(client.exceptions.NoSuchEntityException) as e:
            # check to make sure it's detached
            client.get_role_policy(
                RoleName=role_name, PolicyName=inline_policy_change_model.policy_name
            )
            self.assertIn("not attached to role", str(e))

    async def test_apply_changes_to_role_managed_policy(self):
        from consoleme.lib.v2.requests import apply_changes_to_role

        managed_policy_change = {
            "principal_arn": "arn:aws:iam::123456789012:role/role_name",
            "change_type": "managed_policy",
            "policy_name": "TestManagedPolicy",
            "resources": [],
            "status": "not_applied",
            "action": "detach",
            "arn": "arn:aws:iam::123456789012:policy/TestManagedPolicy",
        }
        managed_policy_change_model = ManagedPolicyChangeModel.parse_obj(
            managed_policy_change
        )

        extended_request = ExtendedRequestModel(
            id="1234",
            arn="arn:aws:iam::123456789012:role/test",
            timestamp=int(time.time()),
            justification="Test justification",
            requester_email="user@example.com",
            approvers=[],
            request_status="pending",
            changes=ChangeModelArray(changes=[managed_policy_change]),
            requester_info=UserModel(email="user@example.com"),
            comments=[],
        )

        response = RequestCreationResponse(
            errors=0,
            request_created=True,
            request_id=extended_request.id,
            action_results=[],
        )

        client = boto3.client("iam", region_name="us-east-1")
        role_name = "test"

        # Detaching a managed policy that's not attached
        await apply_changes_to_role(
            extended_request, response, extended_request.requester_email
        )
        self.assertEqual(1, response.errors)
        self.assertIn(
            "Error occurred detaching managed policy",
            dict(response.action_results[0]).get("message"),
        )

        # Trying to attach a managed policy that doesn't exist
        response.action_results = []
        response.errors = 0
        managed_policy_change_model.action = Action1.attach
        extended_request.changes = ChangeModelArray(
            changes=[managed_policy_change_model]
        )
        await apply_changes_to_role(
            extended_request, response, extended_request.requester_email
        )
        self.assertEqual(1, response.errors)
        self.assertIn(
            "Error occurred attaching managed policy",
            dict(response.action_results[0]).get("message"),
        )

        managed_policy_sample = {
            "Version": "2012-10-17",
            "Statement": [
                {"Effect": "Allow", "Action": ["s3:Get*", "s3:List*"], "Resource": "*"}
            ],
        }

        client.create_policy(
            PolicyName=managed_policy_change["policy_name"],
            PolicyDocument=json.dumps(managed_policy_sample),
        )

        # Attaching a managed policy that exists -> no errors
        response.action_results = []
        response.errors = 0
        await apply_changes_to_role(
            extended_request, response, extended_request.requester_email
        )
        self.assertEqual(0, response.errors)
        # Make sure it attached
        role_attached_policies = client.list_attached_role_policies(RoleName=role_name)
        self.assertEqual(len(role_attached_policies.get("AttachedPolicies")), 1)
        self.assertEqual(
            role_attached_policies.get("AttachedPolicies")[0].get("PolicyArn"),
            managed_policy_change_model.arn,
        )

        # Detaching the managed policy -> no errors
        response.action_results = []
        response.errors = 0
        managed_policy_change_model.action = Action1.detach
        extended_request.changes = ChangeModelArray(
            changes=[managed_policy_change_model]
        )
        await apply_changes_to_role(
            extended_request, response, extended_request.requester_email
        )
        self.assertEqual(0, response.errors)
        # Make sure it detached
        role_attached_policies = client.list_attached_role_policies(RoleName=role_name)
        self.assertEqual(len(role_attached_policies.get("AttachedPolicies")), 0)

    async def test_apply_changes_to_role_assume_role_policy(self):
        from consoleme.lib.v2.requests import apply_changes_to_role

        assume_role_policy_change = {
            "principal_arn": "arn:aws:iam::123456789012:role/role_name",
            "change_type": "assume_role_policy",
            "resources": [],
            "status": "not_applied",
            "new": True,
            "policy": {
                "version": "<>>",
                "policy_document": {
                    "Statement": [
                        {
                            "Action": "sts:AssumeRole",
                            "Effect": "Allow",
                            "Principal": {
                                "AWS": "arn:aws:iam::123456789012:role/myProfile"
                            },
                            "Sid": "AllowMeToAssumePlease",
                        }
                    ],
                    "Version": "2012-10-17",
                },
                "policy_sha256": "55d03ad7a2a447e6e883c520edcd8e5e3083c2f83fa1c390cee3f7dbedf28533",
            },
            "old_policy": None,
        }
        assume_role_policy_change_model = AssumeRolePolicyChangeModel.parse_obj(
            assume_role_policy_change
        )

        extended_request = ExtendedRequestModel(
            id="1234",
            arn="arn:aws:iam::123456789012:role/test",
            timestamp=int(time.time()),
            justification="Test justification",
            requester_email="user@example.com",
            approvers=[],
            request_status="pending",
            changes=ChangeModelArray(changes=[assume_role_policy_change_model]),
            requester_info=UserModel(email="user@example.com"),
            comments=[],
        )

        response = RequestCreationResponse(
            errors=0,
            request_created=True,
            request_id=extended_request.id,
            action_results=[],
        )

        client = boto3.client("iam", region_name="us-east-1")
        role_name = "test"

        # Attach the assume role policy document -> no errors
        await apply_changes_to_role(
            extended_request, response, extended_request.requester_email
        )
        self.assertEqual(0, response.errors)
        # Make sure it attached
        role_details = client.get_role(RoleName=role_name)
        self.assertDictEqual(
            role_details.get("Role").get("AssumeRolePolicyDocument"),
            assume_role_policy_change_model.policy.policy_document,
        )

    async def test_apply_changes_to_role_unsupported_change(self):
        from consoleme.lib.v2.requests import apply_changes_to_role

        resource_policy_change = {
            "principal_arn": "arn:aws:iam::123456789012:role/test",
            "change_type": "resource_policy",
            "resources": [
                {
                    "arn": "arn:aws:iam::123456789012:role/test",
                    "name": "test",
                    "account_id": "311271679914",
                    "resource_type": "iam",
                }
            ],
            "version": 2,
            "status": "not_applied",
            "arn": "arn:aws:s3:::test_bucket",
            "autogenerated": False,
            "policy": {
                "policy_document": {"Version": "2012-10-17", "Statement": []},
                "policy_sha256": "8f907b489532ad56fb7c52f3acc89b27680ed51296bf03984ce78d2b7b96076a",
            },
        }
        resource_policy_change_model = ResourcePolicyChangeModel.parse_obj(
            resource_policy_change
        )

        extended_request = ExtendedRequestModel(
            id="1234",
            arn="arn:aws:iam::123456789012:role/test",
            timestamp=int(time.time()),
            justification="Test justification",
            requester_email="user@example.com",
            approvers=[],
            request_status="pending",
            changes=ChangeModelArray(changes=[resource_policy_change_model]),
            requester_info=UserModel(email="user@example.com"),
            comments=[],
        )

        response = RequestCreationResponse(
            errors=0,
            request_created=True,
            request_id=extended_request.id,
            action_results=[],
        )

        # Not supported change -> Error
        await apply_changes_to_role(
            extended_request, response, extended_request.requester_email
        )
        self.assertEqual(1, response.errors)
        self.assertIn("Error occurred", dict(response.action_results[0]).get("message"))
        self.assertIn("not supported", dict(response.action_results[0]).get("message"))

    async def test_apply_specific_change_to_role(self):
        from consoleme.lib.v2.requests import apply_changes_to_role

        assume_role_policy_change = {
            "principal_arn": "arn:aws:iam::123456789012:role/role_name",
            "change_type": "assume_role_policy",
            "resources": [],
            "status": "not_applied",
            "new": True,
            "id": "12345",
            "policy": {
                "version": "2.0",
                "policy_document": {
                    "Statement": [
                        {
                            "Action": "sts:AssumeRole",
                            "Effect": "Allow",
                            "Principal": {
                                "AWS": "arn:aws:iam::123456789012:role/myProfile"
                            },
                            "Sid": "AllowMeToAssumePlease",
                        }
                    ],
                    "Version": "2012-10-17",
                },
                "policy_sha256": "55d03ad7a2a447e6e883c520edcd8e5e3083c2f83fa1c390cee3f7dbedf28533",
            },
            "old_policy": None,
        }
        assume_role_policy_change_model = AssumeRolePolicyChangeModel.parse_obj(
            assume_role_policy_change
        )

        extended_request = ExtendedRequestModel(
            id="1234",
            arn="arn:aws:iam::123456789012:role/test",
            timestamp=int(time.time()),
            justification="Test justification",
            requester_email="user@example.com",
            approvers=[],
            request_status="pending",
            changes=ChangeModelArray(changes=[assume_role_policy_change_model]),
            requester_info=UserModel(email="user@example.com"),
            comments=[],
        )

        response = RequestCreationResponse(
            errors=0,
            request_created=True,
            request_id=extended_request.id,
            action_results=[],
        )

        client = boto3.client("iam", region_name="us-east-1")
        role_name = "test"
        client.update_assume_role_policy(
            RoleName=role_name,
            PolicyDocument=json.dumps(
                {
                    "Statement": [
                        {
                            "Action": "sts:AssumeRole",
                            "Effect": "Allow",
                            "Principal": {
                                "AWS": "arn:aws:iam::123456789012:role/myProfile"
                            },
                            "Sid": "AllowMeToAssumePlease",
                        }
                    ],
                    "Version": "2012-10-17",
                },
                escape_forward_slashes=False,
            ),
        )
        # Specify ID different from change -> No changes should happen
        await apply_changes_to_role(
            extended_request, response, extended_request.requester_email, "1234"
        )
        self.assertEqual(0, response.errors)
        self.assertEqual(0, len(response.action_results))
        # Make sure the change didn't occur
        role_details = client.get_role(RoleName=role_name)
        self.assertDictEqual(
            role_details.get("Role").get("AssumeRolePolicyDocument"),
            {
                "Statement": [
                    {
                        "Action": "sts:AssumeRole",
                        "Effect": "Allow",
                        "Principal": {
                            "AWS": "arn:aws:iam::123456789012:role/myProfile"
                        },
                        "Sid": "AllowMeToAssumePlease",
                    }
                ],
                "Version": "2012-10-17",
            },
        )

        # Specify ID same as change -> Change should happen
        await apply_changes_to_role(
            extended_request,
            response,
            extended_request.requester_email,
            assume_role_policy_change_model.id,
        )
        self.assertEqual(0, response.errors)
        self.assertEqual(1, len(response.action_results))
        # Make sure the change occurred
        role_details = client.get_role(RoleName=role_name)
        self.assertDictEqual(
            role_details.get("Role").get("AssumeRolePolicyDocument"),
            assume_role_policy_change_model.policy.policy_document,
        )

    async def test_populate_old_policies(self):
        from consoleme.lib.v2.requests import populate_old_policies

        client = boto3.client("iam", region_name="us-east-1")
        client.put_role_policy(
            RoleName="test",
            PolicyName=existing_policy_name,
            PolicyDocument=json.dumps(
                existing_policy_document, escape_forward_slashes=False
            ),
        )

        inline_policy_change = {
            "principal_arn": "arn:aws:iam::123456789012:role/test",
            "change_type": "inline_policy",
            "resources": [],
            "version": 2.0,
            "status": "applied",
            "policy_name": existing_policy_name,
            "new": False,
            "action": "attach",
            "policy": {
                "version": None,
                "policy_document": {},
                "policy_sha256": "55d03ad7a2a447e6e883c520edcd8e5e3083c2f83fa1c390cee3f7dbedf28533",
            },
            "old_policy": None,
        }
        inline_policy_change_model = InlinePolicyChangeModel.parse_obj(
            inline_policy_change
        )

        extended_request = ExtendedRequestModel(
            id="1234",
            arn="arn:aws:iam::123456789012:role/test",
            timestamp=int(time.time()),
            justification="Test justification",
            requester_email="user@example.com",
            approvers=[],
            request_status="pending",
            changes=ChangeModelArray(changes=[inline_policy_change_model]),
            requester_info=UserModel(email="user@example.com"),
            comments=[],
        )

        # role = ExtendedRoleModel(
        #     name="role_name",
        #     account_id="123456789012",
        #     account_name="friendly_name",
        #     arn="arn:aws:iam::123456789012:role/role_name",
        #     inline_policies=[
        #         {
        #             "PolicyName": inline_policy_change_model.policy_name,
        #             "PolicyDocument": existing_policy_document,
        #         }
        #     ],
        #     assume_role_policy_document={},
        #     managed_policies=[],
        #     tags=[],
        # )

        # assert before calling this function that old policy is None
        self.assertEqual(None, extended_request.changes.changes[0].old_policy)

        extended_request = await populate_old_policies(
            extended_request, extended_request.requester_email
        )

        # assert after calling this function that old policy is None, we shouldn't modify changes that are already
        # applied
        self.assertEqual(None, extended_request.changes.changes[0].old_policy)

        extended_request.changes.changes[0].status = Status.not_applied
        # assert before calling this function that old policy is None
        self.assertEqual(None, extended_request.changes.changes[0].old_policy)

        extended_request = await populate_old_policies(
            extended_request, extended_request.requester_email
        )

        # assert after calling the function that the old policies populated properly
        self.assertDictEqual(
            existing_policy_document,
            extended_request.changes.changes[0].old_policy.policy_document,
        )

    async def test_apply_resource_policy_change_unsupported(self):
        from consoleme.lib.v2.requests import apply_resource_policy_change

        resource_policy_change = {
            "principal_arn": "arn:aws:iam::123456789012:role/test",
            "change_type": "resource_policy",
            "id": "1234",
            "source_change_id": "5678",
            "resources": [
                {
                    "arn": "arn:aws:iam::123456789012:role/test",
                    "name": "test",
                    "account_id": "311271679914",
                    "resource_type": "iam",
                }
            ],
            "version": 2,
            "status": "not_applied",
            "arn": "arn:aws:unsupported::123456789012:test_not_supported",
            "autogenerated": False,
            "policy": {
                "policy_document": {"Version": "2012-10-17", "Statement": []},
                "policy_sha256": "8f907b489532ad56fb7c52f3acc89b27680ed51296bf03984ce78d2b7b96076a",
            },
        }
        resource_policy_change_model = ResourcePolicyChangeModel.parse_obj(
            resource_policy_change
        )

        extended_request = ExtendedRequestModel(
            id="1234",
            arn="arn:aws:iam::123456789012:role/test",
            timestamp=int(time.time()),
            justification="Test justification",
            requester_email="user@example.com",
            approvers=[],
            request_status="pending",
            changes=ChangeModelArray(changes=[resource_policy_change_model]),
            requester_info=UserModel(email="user@example.com"),
            comments=[],
        )

        response = PolicyRequestModificationResponseModel(errors=0, action_results=[])

        # Not supported change -> Error
        response = await apply_resource_policy_change(
            extended_request,
            resource_policy_change_model,
            response,
            extended_request.requester_email,
        )

        self.assertEqual(1, response.errors)
        self.assertIn(
            "Cannot apply change", dict(response.action_results[0]).get("message")
        )
        self.assertIn("not supported", dict(response.action_results[0]).get("message"))

    async def test_apply_resource_policy_change_iam(self):
        from consoleme.lib.v2.requests import apply_resource_policy_change

        resource_policy_change = {
            "principal_arn": "arn:aws:iam::123456789012:role/test",
            "change_type": "sts_resource_policy",
            "id": "1234",
            "source_change_id": "5678",
            "supported": True,
            "resources": [
                {
                    "arn": "arn:aws:iam::123456789012:role/test",
                    "name": "test",
                    "account_id": "123456789012",
                    "resource_type": "iam",
                }
            ],
            "version": 2,
            "status": "not_applied",
            "arn": "arn:aws:iam::123456789012:role/test_2",
            "autogenerated": False,
            "policy": {
                "policy_document": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": ["sts:AssumeRole", "sts:TagSession"],
                            "Effect": "Allow",
                            "Principal": {
                                "AWS": ["arn:aws:iam::123456789012:role/test"]
                            },
                        }
                    ],
                },
                "policy_sha256": "8f907b489532ad56fb7c52f3acc89b27680ed51296bf03984ce78d2b7b96076a",
            },
        }
        resource_policy_change_model = ResourcePolicyChangeModel.parse_obj(
            resource_policy_change
        )

        extended_request = ExtendedRequestModel(
            id="1234",
            arn="arn:aws:iam::123456789012:role/test",
            timestamp=int(time.time()),
            justification="Test justification",
            requester_email="user@example.com",
            approvers=[],
            request_status="pending",
            changes=ChangeModelArray(changes=[resource_policy_change_model]),
            requester_info=UserModel(email="user@example.com"),
            comments=[],
        )

        response = PolicyRequestModificationResponseModel(errors=0, action_results=[])

        # Role doesn't exist -> applying policy -> error
        response = await apply_resource_policy_change(
            extended_request,
            resource_policy_change_model,
            response,
            extended_request.requester_email,
        )

        self.assertEqual(1, response.errors)
        self.assertIn("Error", dict(response.action_results[0]).get("message"))
        self.assertIn("NoSuchEntity", dict(response.action_results[0]).get("message"))
        self.assertEqual(Status.not_applied, resource_policy_change_model.status)

        client = boto3.client("iam", region_name="us-east-1")
        role_name = "test_2"
        client.create_role(RoleName=role_name, AssumeRolePolicyDocument="{}")
        response.errors = 0
        response.action_results = []

        # No error
        response = await apply_resource_policy_change(
            extended_request,
            resource_policy_change_model,
            response,
            extended_request.requester_email,
        )
        self.assertEqual(0, response.errors)
        # Make sure it attached
        role_details = client.get_role(RoleName=role_name)
        self.assertDictEqual(
            role_details.get("Role").get("AssumeRolePolicyDocument"),
            resource_policy_change_model.policy.policy_document,
        )

        # Ensure the request got updated
        self.assertEqual(Status.applied, resource_policy_change_model.status)

    async def test_apply_resource_policy_change_s3(self):
        from consoleme.lib.v2.requests import apply_resource_policy_change

        resource_policy_change = {
            "principal_arn": "arn:aws:iam::123456789012:role/test",
            "change_type": "resource_policy",
            "id": "1234",
            "source_change_id": "5678",
            "supported": True,
            "resources": [
                {
                    "arn": "arn:aws:iam::123456789012:role/test",
                    "name": "test",
                    "account_id": "311271679914",
                    "resource_type": "iam",
                }
            ],
            "version": 2,
            "status": "not_applied",
            "arn": "arn:aws:s3::123456789012:test_bucket",
            "autogenerated": False,
            "policy": {
                "policy_document": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": [
                                "s3:ListBucket",
                                "s3:ListBucketVersions",
                                "s3:GetObject",
                                "s3:GetObjectTagging",
                                "s3:GetObjectVersion",
                                "s3:GetObjectVersionTagging",
                                "s3:GetObjectAcl",
                                "s3:GetObjectVersionAcl",
                            ],
                            "Effect": "Allow",
                            "Resource": ["arn:aws:iam::123456789012:role/test"],
                            "Sid": "sid_test",
                        }
                    ],
                },
                "policy_sha256": "8f907b489532ad56fb7c52f3acc89b27680ed51296bf03984ce78d2b7b96076a",
            },
        }
        resource_policy_change_model = ResourcePolicyChangeModel.parse_obj(
            resource_policy_change
        )

        extended_request = ExtendedRequestModel(
            id="1234",
            arn="arn:aws:iam::123456789012:role/test",
            timestamp=int(time.time()),
            justification="Test justification",
            requester_email="user@example.com",
            approvers=[],
            request_status="pending",
            changes=ChangeModelArray(changes=[resource_policy_change_model]),
            requester_info=UserModel(email="user@example.com"),
            comments=[],
        )

        response = PolicyRequestModificationResponseModel(errors=0, action_results=[])

        # Bucket doesn't exist -> applying policy -> error
        response = await apply_resource_policy_change(
            extended_request,
            resource_policy_change_model,
            response,
            extended_request.requester_email,
        )

        self.assertEqual(1, response.errors)
        self.assertIn("Error", dict(response.action_results[0]).get("message"))
        self.assertIn("NoSuchBucket", dict(response.action_results[0]).get("message"))

        conn = boto3.resource("s3", region_name="us-east-1")
        conn.create_bucket(Bucket="test_bucket")
        response.errors = 0
        response.action_results = []
        # No error
        response = await apply_resource_policy_change(
            extended_request,
            resource_policy_change_model,
            response,
            extended_request.requester_email,
        )

        self.assertEqual(0, response.errors)
        # Check to make sure bucket policy got updated
        bucket_policy = conn.BucketPolicy("test_bucket")
        self.assertDictEqual(
            json.loads(bucket_policy.policy),
            resource_policy_change_model.policy.policy_document,
        )

    async def test_apply_resource_policy_change_sqs(self):
        from consoleme.lib.v2.requests import apply_resource_policy_change

        resource_policy_change = {
            "principal_arn": "arn:aws:iam::123456789012:role/test",
            "change_type": "resource_policy",
            "id": "1234",
            "source_change_id": "5678",
            "supported": True,
            "resources": [
                {
                    "arn": "arn:aws:iam::123456789012:role/test",
                    "name": "test",
                    "account_id": "311271679914",
                    "resource_type": "iam",
                }
            ],
            "version": 2,
            "status": "not_applied",
            "arn": "arn:aws:sqs:us-east-1:123456789012:test_sqs",
            "autogenerated": False,
            "policy": {
                "policy_document": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": ["sqs: *"],
                            "Effect": "Allow",
                            "Resource": ["arn:aws:iam::123456789012:role/test"],
                            "Sid": "sid_test",
                        }
                    ],
                },
                "policy_sha256": "8f907b489532ad56fb7c52f3acc89b27680ed51296bf03984ce78d2b7b96076a",
            },
        }
        resource_policy_change_model = ResourcePolicyChangeModel.parse_obj(
            resource_policy_change
        )

        extended_request = ExtendedRequestModel(
            id="1234",
            arn="arn:aws:iam::123456789012:role/test",
            timestamp=int(time.time()),
            justification="Test justification",
            requester_email="user@example.com",
            approvers=[],
            request_status="pending",
            changes=ChangeModelArray(changes=[resource_policy_change_model]),
            requester_info=UserModel(email="user@example.com"),
            comments=[],
        )

        response = PolicyRequestModificationResponseModel(errors=0, action_results=[])

        # SQS doesn't exist -> applying SQS policy -> error
        response = await apply_resource_policy_change(
            extended_request,
            resource_policy_change_model,
            response,
            extended_request.requester_email,
        )

        self.assertEqual(1, response.errors)
        self.assertIn("Error", dict(response.action_results[0]).get("message"))
        self.assertIn(
            "NonExistentQueue", dict(response.action_results[0]).get("message")
        )

        client = boto3.client("sqs", region_name="us-east-1")
        client.create_queue(QueueName="test_sqs")
        response.errors = 0
        response.action_results = []
        # No error
        response = await apply_resource_policy_change(
            extended_request,
            resource_policy_change_model,
            response,
            extended_request.requester_email,
        )

        self.assertEqual(0, response.errors)
        # Check to make sure queue attribute
        queue_url = client.get_queue_url(QueueName="test_sqs")
        attributes = client.get_queue_attributes(
            QueueUrl=queue_url.get("QueueUrl"), AttributeNames=["All"]
        )
        self.assertDictEqual(
            json.loads(attributes.get("Attributes").get("Policy")),
            resource_policy_change_model.policy.policy_document,
        )

    async def test_apply_resource_policy_change_sns(self):
        from consoleme.lib.v2.requests import apply_resource_policy_change

        resource_policy_change = {
            "principal_arn": "arn:aws:iam::123456789012:role/test",
            "change_type": "resource_policy",
            "id": "1234",
            "source_change_id": "5678",
            "supported": True,
            "resources": [
                {
                    "arn": "arn:aws:iam::123456789012:role/test",
                    "name": "test",
                    "account_id": "311271679914",
                    "resource_type": "iam",
                }
            ],
            "version": 2,
            "status": "not_applied",
            "arn": "arn:aws:sns:us-east-1:123456789012:test_sns",
            "autogenerated": False,
            "policy": {
                "policy_document": {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Action": ["sns: *"],
                            "Effect": "Allow",
                            "Resource": ["arn:aws:iam::123456789012:role/test"],
                            "Sid": "sid_test",
                        }
                    ],
                },
                "policy_sha256": "8f907b489532ad56fb7c52f3acc89b27680ed51296bf03984ce78d2b7b96076a",
            },
        }
        resource_policy_change_model = ResourcePolicyChangeModel.parse_obj(
            resource_policy_change
        )

        extended_request = ExtendedRequestModel(
            id="1234",
            arn="arn:aws:iam::123456789012:role/test",
            timestamp=int(time.time()),
            justification="Test justification",
            requester_email="user@example.com",
            approvers=[],
            request_status="pending",
            changes=ChangeModelArray(changes=[resource_policy_change_model]),
            requester_info=UserModel(email="user@example.com"),
            comments=[],
        )

        response = PolicyRequestModificationResponseModel(errors=0, action_results=[])

        # SNS doesn't exist -> applying SNS policy -> error
        response = await apply_resource_policy_change(
            extended_request,
            resource_policy_change_model,
            response,
            extended_request.requester_email,
        )

        self.assertEqual(1, response.errors)
        self.assertIn("Error", dict(response.action_results[0]).get("message"))
        self.assertIn("NotFound", dict(response.action_results[0]).get("message"))

        client = boto3.client("sns", region_name="us-east-1")
        client.create_topic(Name="test_sns")
        response.errors = 0
        response.action_results = []
        # No error
        response = await apply_resource_policy_change(
            extended_request,
            resource_policy_change_model,
            response,
            extended_request.requester_email,
        )

        self.assertEqual(0, response.errors)
        # Check to make sure sns attribute
        attributes = client.get_topic_attributes(
            TopicArn=resource_policy_change_model.arn
        )
        self.assertDictEqual(
            json.loads(attributes.get("Attributes").get("Policy")),
            resource_policy_change_model.policy.policy_document,
        )

    @patch("consoleme.lib.v2.requests.send_communications_new_comment")
    @patch("consoleme.lib.dynamo.UserDynamoHandler.write_policy_request_v2")
    async def test_parse_and_apply_policy_request_modification_add_comment(
        self, mock_dynamo_write, mock_send_comment
    ):
        from consoleme.lib.v2.requests import (
            parse_and_apply_policy_request_modification,
        )

        extended_request = await get_extended_request_helper()
        input_body = {"modification_model": {"command": "add_comment"}}

        policy_request_model = PolicyRequestModificationRequestModel.parse_obj(
            input_body
        )
        last_updated = extended_request.timestamp
        mock_dynamo_write.return_value = create_future(None)
        mock_send_comment.return_value = create_future(None)
        # Trying to set an empty comment
        with pytest.raises(ValidationError) as e:
            await parse_and_apply_policy_request_modification(
                extended_request,
                policy_request_model,
                "user2@example.com",
                [],
                last_updated,
            )
            self.assertIn("validation error", str(e))

        input_body["modification_model"]["comment_text"] = "Sample comment"
        policy_request_model = PolicyRequestModificationRequestModel.parse_obj(
            input_body
        )
        response = await parse_and_apply_policy_request_modification(
            extended_request,
            policy_request_model,
            "user2@example.com",
            [],
            last_updated,
        )
        self.assertEqual(0, response.errors)
        # Make sure comment got added to the request
        self.assertEqual(1, len(extended_request.comments))
        comment = extended_request.comments[0]
        self.assertEqual(comment.user_email, "user2@example.com")
        self.assertEqual(comment.text, "Sample comment")

    @patch("consoleme.lib.dynamo.UserDynamoHandler.write_policy_request_v2")
    async def test_parse_and_apply_policy_request_modification_update_change(
        self, mock_dynamo_write
    ):
        from consoleme.lib.v2.requests import (
            parse_and_apply_policy_request_modification,
        )

        extended_request = await get_extended_request_helper()
        updated_policy_doc = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": ["s3:*"],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::test_bucket",
                        "arn:aws:s3:::test_bucket/abc/*",
                    ],
                    "Sid": "sid_test",
                }
            ],
        }
        input_body = {
            "modification_model": {
                "command": "update_change",
                "change_id": extended_request.changes.changes[0].id + "non-existent",
                "policy_document": updated_policy_doc,
            }
        }
        policy_request_model = PolicyRequestModificationRequestModel.parse_obj(
            input_body
        )
        last_updated = extended_request.timestamp
        mock_dynamo_write.return_value = create_future(None)

        # Trying to update while not being authorized
        from consoleme.exceptions.exceptions import Unauthorized

        with pytest.raises(Unauthorized) as e:
            await parse_and_apply_policy_request_modification(
                extended_request,
                policy_request_model,
                "user2@example.com",
                [],
                last_updated,
            )
            self.assertIn("Unauthorized", str(e))

        # Trying to update a non-existent change
        from consoleme.exceptions.exceptions import NoMatchingRequest

        with pytest.raises(NoMatchingRequest) as e:
            await parse_and_apply_policy_request_modification(
                extended_request,
                policy_request_model,
                "user@example.com",
                [],
                last_updated,
            )
            self.assertIn("Unable to find", str(e))

        # Valid change to be updated
        policy_request_model.modification_model.change_id = (
            extended_request.changes.changes[0].id
        )
        response = await parse_and_apply_policy_request_modification(
            extended_request, policy_request_model, "user@example.com", [], last_updated
        )
        self.assertEqual(0, response.errors)
        # Make sure change got updated in the request
        self.assertDictEqual(
            extended_request.changes.changes[0].policy.policy_document,
            updated_policy_doc,
        )

    @patch("consoleme.lib.v2.requests.aws.fetch_iam_role")
    @patch("consoleme.lib.v2.requests.populate_old_policies")
    @patch("consoleme.lib.dynamo.UserDynamoHandler.write_policy_request_v2")
    @patch("consoleme.lib.v2.requests.can_admin_policies")
    async def test_parse_and_apply_policy_request_modification_apply_change(
        self,
        can_admin_policies,
        mock_dynamo_write,
        mock_populate_old_policies,
        mock_fetch_iam_role,
    ):
        from consoleme.exceptions.exceptions import NoMatchingRequest, Unauthorized
        from consoleme.lib.v2.requests import (
            parse_and_apply_policy_request_modification,
        )

        extended_request = await get_extended_request_helper()
        updated_policy_doc = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": ["s3:*"],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::test_bucket",
                        "arn:aws:s3:::test_bucket/abc/*",
                    ],
                    "Sid": "sid_test",
                }
            ],
        }
        input_body = {
            "modification_model": {
                "command": "apply_change",
                "change_id": extended_request.changes.changes[0].id + "non-existent",
                "policy_document": updated_policy_doc,
            }
        }
        policy_request_model = PolicyRequestModificationRequestModel.parse_obj(
            input_body
        )
        last_updated = extended_request.timestamp
        mock_dynamo_write.return_value = create_future(None)
        mock_populate_old_policies.return_value = create_future(extended_request)
        mock_fetch_iam_role.return_value = create_future(None)
        can_admin_policies.return_value = False
        client = boto3.client("iam", region_name="us-east-1")
        role_name = "test"

        # Trying to apply while not being authorized
        with pytest.raises(Unauthorized) as e:
            await parse_and_apply_policy_request_modification(
                extended_request,
                policy_request_model,
                "user@example.com",
                [],
                last_updated,
            )
            self.assertIn("Unauthorized", str(e))

        can_admin_policies.return_value = True
        # Trying to apply a non-existent change
        with pytest.raises(NoMatchingRequest) as e:
            await parse_and_apply_policy_request_modification(
                extended_request,
                policy_request_model,
                "consoleme_admins@example.com",
                [],
                last_updated,
            )
            self.assertIn("Unable to find", str(e))

        # Valid change to be applied
        policy_request_model.modification_model.change_id = (
            extended_request.changes.changes[0].id
        )
        response = await parse_and_apply_policy_request_modification(
            extended_request,
            policy_request_model,
            "user@example.com",
            [],
            last_updated,
            approval_probe_approved=True,
        )
        self.assertEqual(0, response.errors)
        # Make sure change got updated in the request
        self.assertDictEqual(
            extended_request.changes.changes[0].policy.policy_document,
            updated_policy_doc,
        )
        self.assertEqual(extended_request.changes.changes[0].status, Status.applied)
        # Make sure this change got applied
        inline_policy = client.get_role_policy(
            RoleName=role_name,
            PolicyName=extended_request.changes.changes[0].policy_name,
        )
        self.assertEqual(
            extended_request.changes.changes[0].policy_name,
            inline_policy.get("PolicyName"),
        )
        self.assertDictEqual(
            extended_request.changes.changes[0].policy.policy_document,
            inline_policy.get("PolicyDocument"),
        )

    @patch("consoleme.lib.v2.requests.send_communications_policy_change_request_v2")
    @patch("consoleme.lib.dynamo.UserDynamoHandler.write_policy_request_v2")
    async def test_parse_and_apply_policy_request_modification_cancel_request(
        self, mock_dynamo_write, mock_send_email
    ):
        from consoleme.exceptions.exceptions import (
            InvalidRequestParameter,
            Unauthorized,
        )
        from consoleme.lib.v2.requests import (
            parse_and_apply_policy_request_modification,
        )

        extended_request = await get_extended_request_helper()

        input_body = {"modification_model": {"command": "cancel_request"}}
        policy_request_model = PolicyRequestModificationRequestModel.parse_obj(
            input_body
        )
        last_updated = extended_request.timestamp
        mock_dynamo_write.return_value = create_future(None)
        mock_send_email.return_value = create_future(None)
        # Trying to cancel while not being authorized
        with pytest.raises(Unauthorized) as e:
            await parse_and_apply_policy_request_modification(
                extended_request,
                policy_request_model,
                "user2@example.com",
                [],
                last_updated,
            )
            self.assertIn("Unauthorized", str(e))

        extended_request.changes.changes[0].status = Status.applied
        # Trying to cancel while at least one change is applied
        res = await parse_and_apply_policy_request_modification(
            extended_request,
            policy_request_model,
            "user@example.com",
            [],
            last_updated,
        )
        self.assertIn(
            res.action_results[0].message,
            "Request cannot be cancelled because at least one change has been applied already. "
            "Please apply or cancel the other changes.",
        )
        extended_request.changes.changes[0].status = Status.not_applied

        # Trying to cancel an approved request
        extended_request.request_status = RequestStatus.approved
        with pytest.raises(InvalidRequestParameter) as e:
            await parse_and_apply_policy_request_modification(
                extended_request,
                policy_request_model,
                "user@example.com",
                [],
                last_updated,
            )
            self.assertIn("cannot be cancelled", str(e))

        # Cancelling valid request
        extended_request.request_status = RequestStatus.pending
        response = await parse_and_apply_policy_request_modification(
            extended_request, policy_request_model, "user@example.com", [], last_updated
        )
        self.assertEqual(0, response.errors)
        # Make sure request got cancelled
        self.assertEqual(RequestStatus.cancelled, extended_request.request_status)

    @patch("consoleme.lib.v2.requests.send_communications_policy_change_request_v2")
    @patch("consoleme.lib.v2.requests.can_move_back_to_pending_v2")
    @patch("consoleme.lib.dynamo.UserDynamoHandler.write_policy_request_v2")
    async def test_parse_and_apply_policy_request_modification_reject_and_move_back_to_pending_request(
        self, mock_dynamo_write, mock_move_back_to_pending, mock_send_email
    ):
        from consoleme.exceptions.exceptions import (
            InvalidRequestParameter,
            Unauthorized,
        )
        from consoleme.lib.v2.requests import (
            parse_and_apply_policy_request_modification,
        )

        extended_request = await get_extended_request_helper()

        input_body = {"modification_model": {"command": "reject_request"}}
        policy_request_model = PolicyRequestModificationRequestModel.parse_obj(
            input_body
        )
        last_updated = int(extended_request.timestamp.timestamp())
        mock_dynamo_write.return_value = create_future(None)
        mock_send_email.return_value = create_future(None)
        # Trying to reject while not being authorized
        with pytest.raises(Unauthorized) as e:
            await parse_and_apply_policy_request_modification(
                extended_request,
                policy_request_model,
                "user2@example.com",
                [],
                last_updated,
            )
            self.assertIn("Unauthorized", str(e))
        extended_request.changes.changes[0].status = Status.applied
        # Trying to reject while at least one change is applied
        res = await parse_and_apply_policy_request_modification(
            extended_request,
            policy_request_model,
            "consoleme_admins@example.com",
            [],
            last_updated,
        )
        self.assertEqual(
            res.action_results[0].message,
            "Request cannot be rejected because at least one change has been applied already. "
            "Please apply or cancel the other changes.",
        )
        extended_request.changes.changes[0].status = Status.not_applied

        # Trying to cancel an approved request
        extended_request.request_status = RequestStatus.approved
        with pytest.raises(InvalidRequestParameter) as e:
            await parse_and_apply_policy_request_modification(
                extended_request,
                policy_request_model,
                "consoleme_admins@example.com",
                [],
                last_updated,
            )
            self.assertIn("cannot be rejected", str(e))

        # Rejecting valid request
        extended_request.request_status = RequestStatus.pending
        response = await parse_and_apply_policy_request_modification(
            extended_request,
            policy_request_model,
            "consoleme_admins@example.com",
            [],
            last_updated,
        )
        self.assertEqual(0, response.errors)
        # Make sure request got rejected
        self.assertEqual(RequestStatus.rejected, extended_request.request_status)

        policy_request_model.modification_model.command = Command.move_back_to_pending
        mock_move_back_to_pending.return_value = create_future(False)
        # Trying to move back to pending request - not authorized
        with pytest.raises(Unauthorized) as e:
            await parse_and_apply_policy_request_modification(
                extended_request,
                policy_request_model,
                "user2@example.com",
                [],
                last_updated,
            )
            self.assertIn("Cannot move this request back to pending", str(e))

        mock_move_back_to_pending.return_value = create_future(True)
        # Trying to move back to pending request - authorized
        response = await parse_and_apply_policy_request_modification(
            extended_request,
            policy_request_model,
            "consoleme_admins@example.com",
            [],
            last_updated,
        )
        self.assertEqual(0, response.errors)
        # Make sure request got moved back
        self.assertEqual(RequestStatus.pending, extended_request.request_status)

    @patch("consoleme.lib.v2.requests.send_communications_policy_change_request_v2")
    @patch("consoleme.lib.v2.requests.aws.fetch_iam_role")
    @patch("consoleme.lib.v2.requests.populate_old_policies")
    @patch("consoleme.lib.dynamo.UserDynamoHandler.write_policy_request_v2")
    @patch("consoleme.lib.v2.requests.can_admin_policies")
    @patch("consoleme.lib.v2.requests.can_update_cancel_requests_v2")
    async def test_parse_and_apply_policy_request_modification_approve_request(
        self,
        mock_can_update_cancel_requests_v2,
        can_admin_policies,
        mock_dynamo_write,
        mock_populate_old_policies,
        mock_fetch_iam_role,
        mock_send_email,
    ):
        from asgiref.sync import sync_to_async
        from cloudaux.aws.sts import boto3_cached_conn

        from consoleme.exceptions.exceptions import Unauthorized
        from consoleme.lib.redis import RedisHandler
        from consoleme.lib.v2.requests import (
            parse_and_apply_policy_request_modification,
        )

        # Redis is globally mocked. Let's store and retrieve a fake value
        red = RedisHandler().redis_sync()
        red.hmset(
            "AWSCONFIG_RESOURCE_CACHE",
            {
                "arn:aws:s3:::test_bucket": json.dumps({"accountId": "123456789013"}),
                "arn:aws:s3:::test_bucket_2": json.dumps({"accountId": "123456789013"}),
            },
        )

        s3_client = await sync_to_async(boto3_cached_conn)(
            "s3",
            service_type="client",
            future_expiration_minutes=15,
            account_number="123456789013",
            region="us-east-1",
            session_name="ConsoleMe_UnitTest",
            arn_partition="aws",
        )
        s3_client.create_bucket(Bucket="test_bucket")

        extended_request = await get_extended_request_helper()
        resource_policy_change = {
            "principal_arn": "arn:aws:iam::123456789012:role/test",
            "change_type": "resource_policy",
            "resources": [
                {
                    "arn": "arn:aws:iam::123456789012:role/test",
                    "name": "test",
                    "account_id": "311271679914",
                    "resource_type": "iam",
                }
            ],
            "id": "123456",
            "version": 2,
            "status": "not_applied",
            "arn": "arn:aws:s3:::test_bucket",
            "autogenerated": False,
            "supported": True,
            "policy": {
                "policy_document": {"Version": "2012-10-17", "Statement": []},
                "policy_sha256": "8f907b489532ad56fb7c52f3acc89b27680ed51296bf03984ce78d2b7b96076a",
            },
        }
        resource_policy_change_model = ResourcePolicyChangeModel.parse_obj(
            resource_policy_change
        )
        extended_request.changes.changes.append(resource_policy_change_model)
        updated_policy_doc = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Action": ["s3:*"],
                    "Effect": "Allow",
                    "Resource": [
                        "arn:aws:s3:::test_bucket",
                        "arn:aws:s3:::test_bucket/abc/*",
                    ],
                    "Sid": "sid_test",
                }
            ],
        }
        input_body = {
            "modification_model": {
                "command": "update_change",
                "change_id": extended_request.changes.changes[0].id,
                "policy_document": updated_policy_doc,
            }
        }
        policy_request_model = PolicyRequestModificationRequestModel.parse_obj(
            input_body
        )
        last_updated = extended_request.timestamp
        mock_dynamo_write.return_value = create_future(None)
        mock_populate_old_policies.return_value = create_future(extended_request)
        mock_fetch_iam_role.return_value = create_future(None)
        mock_can_update_cancel_requests_v2.return_value = create_future(False)
        can_admin_policies.return_value = False
        mock_send_email.return_value = create_future(None)
        client = boto3.client("iam", region_name="us-east-1")
        role_name = "test"

        # Trying to approve while not being authorized
        with pytest.raises(Unauthorized) as e:
            await parse_and_apply_policy_request_modification(
                extended_request,
                policy_request_model,
                "user2@example.com",
                [],
                last_updated,
            )
            self.assertIn("Unauthorized", str(e))

        can_admin_policies.return_value = True
        mock_can_update_cancel_requests_v2.return_value = create_future(True)

        # Authorized person updating the change
        response = await parse_and_apply_policy_request_modification(
            extended_request,
            policy_request_model,
            "consoleme_admins@example.com",
            [],
            last_updated,
        )

        # 0 errors for approving the request, which doesn't apply any resource policy changes
        self.assertEqual(0, response.errors)
        # Make sure inline policy change got updated in the request
        self.assertDictEqual(
            extended_request.changes.changes[0].policy.policy_document,
            updated_policy_doc,
        )
        self.assertEqual(extended_request.changes.changes[0].status, Status.not_applied)
        # Apply the change
        input_body = {
            "modification_model": {
                "command": "apply_change",
                "change_id": extended_request.changes.changes[0].id,
            }
        }
        policy_request_model = PolicyRequestModificationRequestModel.parse_obj(
            input_body
        )

        await parse_and_apply_policy_request_modification(
            extended_request,
            policy_request_model,
            "consoleme_admins@example.com",
            [],
            last_updated,
        )

        self.assertEqual(extended_request.changes.changes[0].status, Status.applied)

        # Make sure this change got applied
        inline_policy = client.get_role_policy(
            RoleName=role_name,
            PolicyName=extended_request.changes.changes[0].policy_name,
        )
        self.assertEqual(
            extended_request.changes.changes[0].policy_name,
            inline_policy.get("PolicyName"),
        )
        self.assertDictEqual(
            extended_request.changes.changes[0].policy.policy_document,
            inline_policy.get("PolicyDocument"),
        )
        # Inline policy has been applied. Request should still be pending because
        # there's still a resource policy in the request
        self.assertEqual(RequestStatus.pending, extended_request.request_status)
        # Make sure resource policy change is still not applied
        self.assertEqual(extended_request.changes.changes[1].status, Status.not_applied)

        # Try to apply resource policy change. This should not work
        input_body = {
            "modification_model": {
                "command": "apply_change",
                "change_id": extended_request.changes.changes[1].id,
            }
        }
        policy_request_model = PolicyRequestModificationRequestModel.parse_obj(
            input_body
        )

        response = await parse_and_apply_policy_request_modification(
            extended_request,
            policy_request_model,
            "consoleme_admins@example.com",
            [],
            last_updated,
        )

        self.assertEqual(response.action_results[0].status, "success")
        self.assertEqual(
            response.action_results[0].message,
            "Successfully updated resource policy for arn:aws:s3:::test_bucket",
        )
        red.delete("AWSCONFIG_RESOURCE_CACHE")
        s3_client.delete_bucket(Bucket="test_bucket")
