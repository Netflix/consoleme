import tornado
from tornado.testing import AsyncTestCase

from consoleme.models import (
    AwsResourcePrincipalModel,
    InlinePolicyChangeModel,
    ResourceModel,
)


class TestChangeRequestLib(AsyncTestCase):
    @tornado.testing.gen_test
    async def test_generate_policy_sid(self):
        from consoleme.lib.change_request import _generate_policy_sid

        random_sid = await _generate_policy_sid("username@example.com")
        self.assertRegex(random_sid, "^cmusername\d{10}[a-z]{4}$")  # noqa

    @tornado.testing.gen_test
    async def test_generate_policy_name(self):
        from consoleme.lib.change_request import generate_policy_name

        random_sid = await generate_policy_name(None, "username@example.com")
        self.assertRegex(random_sid, "^cm_username_\d{10}_[a-z]{4}$")  # noqa
        explicit = await generate_policy_name("blah", "username@example.com")
        self.assertRegex(explicit, "blah")

    @tornado.testing.gen_test
    async def test_generate_inline_policy_model_from_statements(self):
        from copy import deepcopy

        from consoleme.lib.change_request import (
            _generate_inline_policy_model_from_statements,
        )

        original_statements = [
            {
                "Action": [
                    "s3:GetObject",
                    "s3:GetObjectTagging",
                    "s3:GetObjectVersionTagging",
                    "s3:GetObjectAcl",
                    "s3:GetObjectVersion",
                    "s3:ListBucketVersions",
                    "s3:ListBucket",
                    "s3:GetObjectVersionAcl",
                ],
                "Effect": "Allow",
                "Resource": [
                    "arn:aws:s3:::123456789012-bucket",
                    "arn:aws:s3:::123456789012-bucket/*",
                    "arn:aws:s3:::bucket2",
                    "arn:aws:s3:::bucket2/*",
                ],
            },
            {
                "Action": [
                    "sqs:GetQueueAttributes",
                    "sqs:SendMessage",
                    "sqs:GetQueueUrl",
                ],
                "Effect": "Allow",
                "Resource": ["arn:aws:sqs:us-east-1:123456789012:resourceName"],
            },
            {
                "Action": ["sns:Publish"],
                "Effect": "Allow",
                "Resource": ["arn:aws:sns:us-east-1:123456789012:resourceName"],
            },
            {
                "Action": [
                    "sns:GetTopicAttributes",
                    "sns:Publish",
                    "sns:GetEndpointAttributes",
                ],
                "Effect": "Allow",
                "Resource": ["*", "arn:aws:sns:us-east-1:123456789012:resourceName2"],
            },
        ]
        statements = deepcopy(original_statements)

        result = await _generate_inline_policy_model_from_statements(statements)
        for entry in ["Action", "Effect", "Resource"]:  # Disregard Sid here
            stripped_result = sorted(
                [
                    statement.pop(entry)
                    for statement in result.policy_document["Statement"]
                ]
            )
            stripped_comparison = sorted(
                [statement.pop(entry) for statement in original_statements]
            )
            self.assertEqual(stripped_result, stripped_comparison)

    @tornado.testing.gen_test
    async def test_generate_policy_statement(self):
        from consoleme.lib.change_request import _generate_policy_statement

        actions = ["iam:List*"]
        resources = ["arn:aws:iam::123456789012:role/resource1"]
        effect = "Allow"
        condition = {
            "StringEquals": {
                "iam:PermissionsBoundary": [
                    "arn:aws:iam::123456789012:policy/PermBoundarya"
                ]
            }
        }
        result = await _generate_policy_statement(actions, resources, effect, condition)
        self.assertEqual(actions, result["Action"])
        self.assertEqual(effect, result["Effect"])
        self.assertEqual(resources, result["Resource"])
        self.assertEqual(condition, result["Condition"])

    @tornado.testing.gen_test
    async def test_generate_inline_policy_change_model(self):
        from consoleme.lib.change_request import _generate_inline_policy_change_model

        is_new = True
        policy_name = None
        principal = AwsResourcePrincipalModel(
            principal_arn="arn:aws:iam::123456789012:role/roleName",
            principal_type="AwsResource",
        )
        resources = [
            ResourceModel(
                arn="arn:aws:s3:::123456789012-bucket",
                name="123456789012-bucket",
                account_id="",
                region="global",
                account_name="",
                policy_sha256=None,
                policy=None,
                owner=None,
                approvers=None,
                resource_type="s3",
                last_updated=None,
            ),
            ResourceModel(
                arn="arn:aws:s3:::bucket",
                name="bucket",
                account_id="",
                region="global",
                account_name="",
                policy_sha256=None,
                policy=None,
                owner=None,
                approvers=None,
                resource_type="s3",
                last_updated=None,
            ),
            ResourceModel(
                arn="arn:aws:sqs:us-east-1:123456789012:resourceName",
                name="resourceName",
                account_id="123456789012",
                region="us-east-1",
                account_name="",
                policy_sha256=None,
                policy=None,
                owner=None,
                approvers=None,
                resource_type="sqs",
                last_updated=None,
            ),
            ResourceModel(
                arn="arn:aws:sns:us-east-1:123456789012:resourceName",
                name="resourceName",
                account_id="123456789012",
                region="us-east-1",
                account_name="",
                policy_sha256=None,
                policy=None,
                owner=None,
                approvers=None,
                resource_type="sns",
                last_updated=None,
            ),
            ResourceModel(
                arn="arn:aws:sns:us-east-1:123456789012:resourceName2",
                name="resourceName2",
                account_id="123456789012",
                region="us-east-1",
                account_name="",
                policy_sha256=None,
                policy=None,
                owner=None,
                approvers=None,
                resource_type="sns",
                last_updated=None,
            ),
        ]
        statements = [
            {
                "Action": [
                    "s3:GetObject",
                    "s3:GetObjectTagging",
                    "s3:GetObjectVersionTagging",
                    "s3:GetObjectAcl",
                    "s3:GetObjectVersion",
                    "s3:ListBucketVersions",
                    "s3:ListBucket",
                    "s3:GetObjectVersionAcl",
                ],
                "Effect": "Allow",
                "Resource": [
                    "arn:aws:s3:::123456789012-bucket",
                    "arn:aws:s3:::123456789012-bucket/*",
                    "arn:aws:s3:::bucket",
                    "arn:aws:s3:::bucket/*",
                ],
                "Sid": "cmusername1592515689hnwb",
            },
            {
                "Action": [
                    "sqs:GetQueueAttributes",
                    "sqs:SendMessage",
                    "sqs:GetQueueUrl",
                ],
                "Effect": "Allow",
                "Resource": ["arn:aws:sqs:us-east-1:123456789012:resourceName"],
                "Sid": "cmusername1592515689dzbd",
            },
            {
                "Action": ["sns:Publish"],
                "Effect": "Allow",
                "Resource": ["arn:aws:sns:us-east-1:123456789012:resourceName"],
                "Sid": "cmusername1592515689kbra",
            },
            {
                "Action": [
                    "sns:GetTopicAttributes",
                    "sns:Publish",
                    "sns:GetEndpointAttributes",
                ],
                "Effect": "Allow",
                "Resource": ["*", "arn:aws:sns:us-east-1:123456789012:resourceName2"],
                "Sid": "cmusername1592515689aasy",
            },
        ]
        user = "username@example.com"
        result = await _generate_inline_policy_change_model(
            principal, resources, statements, user, is_new, policy_name
        )
        self.assertIsInstance(result, InlinePolicyChangeModel)
