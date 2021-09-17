import json
import os
import unittest

import boto3
from asgiref.sync import async_to_sync

os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_SECURITY_TOKEN"] = "testing"
os.environ["AWS_SESSION_TOKEN"] = "testing"

policy_document = json.dumps(
    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": ["s3:ListBucket"],
                "Effect": "Allow",
                "Resource": ["arn:aws:s3:::BUCKET_NAME"],
                "Sid": "s3readwrite",
            }
        ],
    }
)


class TestHandler(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        from consoleme.config import config
        from consoleme.lib.role_updater import handler

        self.handler = handler
        client = boto3.client(
            "iam", region_name="us-east-1", **config.get("boto3.client_kwargs", {})
        )
        role_name = "role_name"
        client.create_role(RoleName=role_name, AssumeRolePolicyDocument="{}")

    async def asyncTearDown(self):
        role_name = "role_name"
        from consoleme.lib.aws import delete_iam_role

        await delete_iam_role("123456789012", role_name, "consoleme-unit-test")

    async def test_parse_account_id_from_arn(self):
        arn = "arn:aws:iam::123456789012:role/testrole"
        account_id = await self.handler.parse_account_id_from_arn(arn)
        self.assertEqual(account_id, "123456789012")

    async def test_parse_role_name_from_arn(self):
        arn = "arn:aws:iam::123456789012:role/testrole"
        role_name = await self.handler.parse_role_name_from_arn(arn)
        self.assertEqual(role_name, "testrole")

    async def test_parse_role_name_with_path_from_arn(self):
        arn = "arn:aws:iam::123456789012:role/path/testrole"
        role_name = await self.handler.parse_role_name_from_arn(arn)
        self.assertEqual(role_name, "testrole")

    def test_update_inline_policy_attach(self):
        from consoleme.config import config

        client = boto3.client(
            "iam", region_name="us-east-1", **config.get("boto3.client_kwargs", {})
        )
        role_name = "role_name"

        policy = {
            "action": "attach",
            "policy_name": "PolicyName",
            "policy_document": policy_document,
        }
        async_to_sync(self.handler.update_inline_policy)(client, role_name, policy)

    def test_update_inline_policy_attach_then_detach(self):
        from consoleme.config import config

        client = boto3.client(
            "iam", region_name="us-east-1", **config.get("boto3.client_kwargs", {})
        )
        role_name = "role_name"
        attach_policy = {
            "action": "attach",
            "policy_name": "PolicyName",
            "policy_document": policy_document,
        }
        async_to_sync(self.handler.update_inline_policy)(
            client, role_name, attach_policy
        )
        detach_policy = {
            "action": "detach",
            "policy_name": "PolicyName",
            "policy_document": policy_document,
        }
        async_to_sync(self.handler.update_inline_policy)(
            client, role_name, detach_policy
        )

    def test_update_managed_policy_attach(self):
        from consoleme.config import config

        client = boto3.client(
            "iam", region_name="us-east-1", **config.get("boto3.client_kwargs", {})
        )
        role_name = "role_name"
        policy = {
            "action": "attach",
            "arn": "arn:aws:iam::aws:policy/AdministratorAccess",
        }
        async_to_sync(self.handler.update_managed_policy)(client, role_name, policy)

    def test_update_managed_policy_attach_then_detach(self):
        from consoleme.config import config

        client = boto3.client(
            "iam", region_name="us-east-1", **config.get("boto3.client_kwargs", {})
        )
        role_name = "role_name"
        attach_policy = {
            "action": "attach",
            "arn": "arn:aws:iam::aws:policy/AdministratorAccess",
        }
        async_to_sync(self.handler.update_managed_policy)(
            client, role_name, attach_policy
        )
        detach_policy = {
            "action": "detach",
            "arn": "arn:aws:iam::aws:policy/AdministratorAccess",
        }
        async_to_sync(self.handler.update_managed_policy)(
            client, role_name, detach_policy
        )

    def test_update_assume_role_policy_document(self):
        from consoleme.config import config

        client = boto3.client(
            "iam", region_name="us-east-1", **config.get("boto3.client_kwargs", {})
        )
        role_name = "role_name"
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": "arn:aws:iam::123456789012:role/testRole"},
                }
            ],
            "Action": "sts:AssumeRole",
        }
        async_to_sync(self.handler.update_assume_role_document)(
            client, role_name, policy
        )

    def test_add_tag(self):
        from consoleme.config import config

        client = boto3.client(
            "iam", region_name="us-east-1", **config.get("boto3.client_kwargs", {})
        )
        role_name = "role_name"
        tag = {"action": "add", "key": "testkey", "value": "testvalue"}
        async_to_sync(self.handler.update_tags)(client, role_name, tag)

    def test_remove_tag(self):
        from consoleme.config import config

        client = boto3.client(
            "iam", region_name="us-east-1", **config.get("boto3.client_kwargs", {})
        )
        role_name = "role_name"
        tag = {"action": "remove", "key": "testkey"}
        async_to_sync(self.handler.update_tags)(client, role_name, tag)

    def test_handler(self):
        event = [
            {
                "arn": "arn:aws:iam::123456789012:role/ConsoleMe",
                "inline_policies": [
                    {
                        "action": "attach",
                        "policyname": "test1",
                        "policy_document": '{"policy": "test"}',
                    },
                    {"action": "detach", "policyname": "test1"},
                ],
                "managed_policies": [
                    {
                        "action": "attach",
                        "arn": "arn:aws:iam::aws:policy/AdministratorAccess",
                    },
                    {
                        "action": "detach",
                        "arn": "arn:aws:iam::aws:policy/AdministratorAccess",
                    },
                ],
                "assume_role_policy_document": {
                    "action": "add",
                    "assume_role_policy_document": '{"policy": "test"}',
                },
                "tags": [{"action": "add", "key": "Key", "value": "Value"}],
            }
        ]
        async_to_sync(self.handler.update_role)(event)

    def test_handler_d(self):
        event = [
            {
                "arn": "arn:aws:iam::123456789012:role/ConsoleMe",
                "inline_policies": [
                    {
                        "action": "attach",
                        "policyname": "test1",
                        "policy_document": {"policy": "test"},
                    },
                    {"action": "detach", "policyname": "test1"},
                ],
                "managed_policies": [
                    {
                        "action": "attach",
                        "arn": "arn:aws:iam::aws:policy/AdministratorAccess",
                    },
                    {
                        "action": "detach",
                        "arn": "arn:aws:iam::aws:policy/AdministratorAccess",
                    },
                ],
                "assume_role_policy_document": {
                    "action": "add",
                    "assume_role_policy_document": {"policy": "test"},
                },
                "tags": [{"action": "add", "key": "Key", "value": "Value"}],
            }
        ]
        async_to_sync(self.handler.update_role)(event)
