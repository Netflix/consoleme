import tornado
from tornado.testing import AsyncTestCase

from consoleme.lib.change_request import (
    _generate_inline_policy_change_model,
    _generate_inline_policy_model_from_statements,
    _generate_policy_name,
    _generate_policy_sid,
)
from consoleme.models import InlinePolicyChangeModel, ResourceModel


class TestChangeRequestLib(AsyncTestCase):
    @tornado.testing.gen_test
    async def test_generate_policy_sid(self):
        random_sid = await _generate_policy_sid("username@example.com")
        self.assertRegex(random_sid, "^cmusername\d{10}[a-z]{4}$")

    @tornado.testing.gen_test
    async def test_generate_policy_name(self):
        random_sid = await _generate_policy_name(None, "username@example.com")
        self.assertRegex(random_sid, "^cm_username_\d{10}_[a-z]{4}$")
        explicit = await _generate_policy_name("blah", "username@example.com")
        self.assertRegex(explicit, "blah")

    @tornado.testing.gen_test
    async def test_generate_inline_policy_model_from_statements(self):
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
                    "arn:aws:s3:::bucket2",
                    "arn:aws:s3:::bucket2/*",
                ],
                "Sid": "cmusername1592515223nlop",
            },
            {
                "Action": [
                    "sqs:GetQueueAttributes",
                    "sqs:SendMessage",
                    "sqs:GetQueueUrl",
                ],
                "Effect": "Allow",
                "Resource": ["arn:aws:sqs:us-east-1:123456789012:resourceName"],
                "Sid": "cmusername1592515223flbj",
            },
            {
                "Action": ["sns:Publish"],
                "Effect": "Allow",
                "Resource": ["arn:aws:sns:us-east-1:123456789012:resourceName"],
                "Sid": "cmusername1592515223ehod",
            },
            {
                "Action": [
                    "sns:GetTopicAttributes",
                    "sns:Publish",
                    "sns:GetEndpointAttributes",
                ],
                "Effect": "Allow",
                "Resource": ["*", "arn:aws:sns:us-east-1:123456789012:resourceName2"],
                "Sid": "cmusername1592515223wesf",
            },
        ]

        result = await _generate_inline_policy_model_from_statements(statements)
        self.assertEqual(
            result.policy_sha256,
            "66da747c9166ee73295054eae957627b437c969f61bd69e9a98963accd8e30bf",
        )

    @tornado.testing.gen_test
    async def test_generate_inline_policy_change_model(self):
        is_new = True
        policy_name = None
        principal_arn = "arn:aws:iam::123456789012:role/roleName"
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
            principal_arn, resources, statements, user, is_new, policy_name
        )
        self.assertIsInstance(result, InlinePolicyChangeModel)
