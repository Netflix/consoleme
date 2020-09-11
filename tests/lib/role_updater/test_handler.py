import json
import os

import boto3
import tornado
from asgiref.sync import async_to_sync
from moto import mock_iam, mock_sts
from tornado.testing import AsyncTestCase

from consoleme.lib.role_updater import handler

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


class TestHandler(AsyncTestCase):
    @tornado.testing.gen_test
    async def test_parse_account_id_from_arn(self):
        arn = "arn:aws:iam::123456789012:role/testrole"
        account_id = await handler.parse_account_id_from_arn(arn)
        self.assertEqual(account_id, "123456789012")

    @tornado.testing.gen_test
    async def test_parse_role_name_from_arn(self):
        arn = "arn:aws:iam::123456789012:role/testrole"
        role_name = await handler.parse_role_name_from_arn(arn)
        self.assertEqual(role_name, "testrole")

    @tornado.testing.gen_test
    async def test_parse_role_name_with_path_from_arn(self):
        arn = "arn:aws:iam::123456789012:role/path/testrole"
        role_name = await handler.parse_role_name_from_arn(arn)
        self.assertEqual(role_name, "testrole")

    def test_update_inline_policy_attach(self):
        client = boto3.client("iam", region_name="us-east-1")
        role_name = "role_name"
        client.create_role(RoleName=role_name, AssumeRolePolicyDocument="{}")
        policy = {
            "action": "attach",
            "policy_name": "PolicyName",
            "policy_document": policy_document,
        }
        async_to_sync(handler.update_inline_policy)(client, role_name, policy)

    def test_update_inline_policy_attach_then_detach(self):
        client = boto3.client("iam", region_name="us-east-1")
        role_name = "role_name"
        client.create_role(RoleName=role_name, AssumeRolePolicyDocument="{}")
        attach_policy = {
            "action": "attach",
            "policy_name": "PolicyName",
            "policy_document": policy_document,
        }
        async_to_sync(handler.update_inline_policy)(client, role_name, attach_policy)
        detach_policy = {
            "action": "detach",
            "policy_name": "PolicyName",
            "policy_document": policy_document,
        }
        async_to_sync(handler.update_inline_policy)(client, role_name, detach_policy)

    def test_update_managed_policy_attach(self):
        client = boto3.client("iam", region_name="us-east-1")
        role_name = "role_name"
        client.create_role(RoleName=role_name, AssumeRolePolicyDocument="{}")
        policy = {
            "action": "attach",
            "arn": "arn:aws:iam::aws:policy/AdministratorAccess",
        }
        async_to_sync(handler.update_managed_policy)(client, role_name, policy)

    def test_update_managed_policy_attach_then_detach(self):
        client = boto3.client("iam", region_name="us-east-1")
        role_name = "role_name"
        client.create_role(RoleName=role_name, AssumeRolePolicyDocument="{}")
        attach_policy = {
            "action": "attach",
            "arn": "arn:aws:iam::aws:policy/AdministratorAccess",
        }
        async_to_sync(handler.update_managed_policy)(client, role_name, attach_policy)
        detach_policy = {
            "action": "detach",
            "arn": "arn:aws:iam::aws:policy/AdministratorAccess",
        }
        async_to_sync(handler.update_managed_policy)(client, role_name, detach_policy)

    def test_update_assume_role_policy_document(self):
        client = boto3.client("iam", region_name="us-east-1")
        role_name = "role_name"
        client.create_role(RoleName=role_name, AssumeRolePolicyDocument="{}")
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
        async_to_sync(handler.update_assume_role_document)(client, role_name, policy)

    def test_add_tag(self):
        client = boto3.client("iam", region_name="us-east-1")
        role_name = "role_name"
        client.create_role(RoleName=role_name, AssumeRolePolicyDocument="{}")
        tag = {"action": "add", "key": "testkey", "value": "testvalue"}
        async_to_sync(handler.update_tags)(client, role_name, tag)

    def test_remove_tag(self):
        client = boto3.client("iam", region_name="us-east-1")
        role_name = "role_name"
        client.create_role(RoleName=role_name, AssumeRolePolicyDocument="{}")
        tag = {"action": "remove", "key": "testkey"}
        async_to_sync(handler.update_tags)(client, role_name, tag)

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
        client = boto3.client("iam", region_name="us-east-1")
        client.create_role(RoleName="ConsoleMe", AssumeRolePolicyDocument="{}")
        async_to_sync(handler.update_role)(event)

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
        client = boto3.client("iam", region_name="us-east-1")
        client.create_role(RoleName="ConsoleMe", AssumeRolePolicyDocument="{}")
        async_to_sync(handler.update_role)(event)
