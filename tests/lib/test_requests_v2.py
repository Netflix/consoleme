import time

import boto3
import pytest
import tornado
import ujson as json
from mock import patch
from moto import mock_iam
from tornado.testing import AsyncTestCase

from consoleme.exceptions.exceptions import InvalidRequestParameter
from consoleme.models import (
    Action,
    Action1,
    AssumeRolePolicyChangeModel,
    ChangeModelArray,
    ChangeType,
    ExtendedRequestModel,
    ExtendedRoleModel,
    InlinePolicyChangeModel,
    ManagedPolicyChangeModel,
    RequestCreationResponse,
    ResourcePolicyChangeModel,
    UserModel,
)
from tests.conftest import AWSHelper


class TestRequestsLibV2(AsyncTestCase):
    @tornado.testing.gen_test
    async def test_validate_inline_policy_change(self):
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

    @tornado.testing.gen_test
    async def test_validate_managed_policy_change(self):
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
        managed_policy_change_model.policy_name = "TestManagedPolicy"
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

    @tornado.testing.gen_test
    async def test_validate_assume_role_policy_change(self):
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

    @patch(
        "consoleme.lib.v2.requests.get_resource_account", AWSHelper.random_account_id,
    )
    @tornado.testing.gen_test
    async def test_generate_resource_policies(self):
        from consoleme.lib.v2.requests import generate_resource_policies

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
        number_of_resources = 2
        await generate_resource_policies(
            extended_request, extended_request.requester_email
        )

        self.assertEqual(
            len(extended_request.changes.changes), len_before_call + number_of_resources
        )
        self.assertIn(inline_policy_change_model, extended_request.changes.changes)
        self.assertIn(managed_policy_change_model, extended_request.changes.changes)

        seen_resource_one = False
        seen_resource_two = False
        for change in extended_request.changes.changes:
            if (
                change.change_type == ChangeType.resource_policy
                and change.arn == inline_policy_change_model.resources[0].arn
            ):
                seen_resource_one = True
                self.assertTrue(change.autogenerated)
            if (
                change.change_type == ChangeType.resource_policy
                and change.arn == inline_policy_change_model.resources[0].arn
            ):
                seen_resource_two = True
                self.assertTrue(change.autogenerated)

        self.assertTrue(seen_resource_one)
        self.assertTrue(seen_resource_two)

    @mock_iam
    @tornado.testing.gen_test
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
        client.create_role(RoleName=role_name, AssumeRolePolicyDocument="{}")

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

    @mock_iam
    @tornado.testing.gen_test
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
        client.create_role(RoleName=role_name, AssumeRolePolicyDocument="{}")

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
            PolicyName=managed_policy_change_model.policy_name,
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
        role_attached_policies = client.list_attached_role_policies(RoleName=role_name,)
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
        role_attached_policies = client.list_attached_role_policies(RoleName=role_name,)
        self.assertEqual(len(role_attached_policies.get("AttachedPolicies")), 0)

    @mock_iam
    @tornado.testing.gen_test
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
        client.create_role(RoleName=role_name, AssumeRolePolicyDocument="{}")

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

    @tornado.testing.gen_test
    async def test_apply_changes_to_role_unsupport_change(self):
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
