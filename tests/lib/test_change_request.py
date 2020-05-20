from unittest import TestCase

import ujson as json

from consoleme.lib.change_request import generate_iam_policy
from consoleme.lib.change_request import generate_s3_change
from consoleme.models import ChangeType
from consoleme.models import S3ChangeGeneratorModel


class TestChangeRequestLib(TestCase):
    def test_generate_iam_policy(self):
        resources = ["arn:aws:s3:::foo", "arn:aws:s3:::foo/bar/*"]
        actions = ["s3:ListObjects", "s3:GetObject", "s3:GetObject"]
        result = generate_iam_policy(resources, actions)
        self.assertEqual(
            result.policy_sha256,
            "0315b4f93ae5c8007038c7f16c909081eb951bca5f206576424179b8e56834d0",
        )
        policy_json = json.loads(result.policy_document)
        statement = policy_json["Statement"][0]
        self.assertListEqual(statement["Action"], ["s3:GetObject", "s3:ListObjects"])
        self.assertListEqual(
            statement["Resource"], ["arn:aws:s3:::foo", "arn:aws:s3:::foo/bar/*"],
        )
        self.assertEqual(statement["Effect"], "Allow")
        self.assertEqual(statement["Sid"], "")

    def test_generate_s3_change(self):
        test_change_input = {
            "arn": "arn:aws:iam::123456789012:role/hey",
            "generator_type": "s3",
            "resource": "arn:aws:s3:::foo",
            "bucket_name": "foo",
            "bucket_prefix": "/*",
            "action_groups": ["list", "get"],
        }

        test_change = S3ChangeGeneratorModel(**test_change_input)
        result = generate_s3_change(test_change)
        self.assertEqual(result.change_type, ChangeType.inline_policy)
        self.assertEqual(
            result.policy.policy_sha256,
            "75a9789293f685c34a882277c944a0db785e7d02e489625e1ccbcb429def4b92",
        )

        test_change_input["bucket_prefix"] = "/foo/*"
        test_change = S3ChangeGeneratorModel(**test_change_input)
        result = generate_s3_change(test_change)
        self.assertNotEqual(
            result.policy.policy_sha256,
            "75a9789293f685c34a882277c944a0db785e7d02e489625e1ccbcb429def4b92",
        )
