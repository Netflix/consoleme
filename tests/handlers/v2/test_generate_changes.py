import ujson as json
from mock import patch
from tornado.testing import AsyncHTTPTestCase

from tests.conftest import MockBaseHandler


class TestGenerateChangesHandler(AsyncHTTPTestCase):
    def get_app(self):
        from consoleme.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    def test_post_no_user(self):
        expected = b"No user detected. Check configuration."
        response = self.fetch("/api/v2/generate_changes", method="POST", body="abcd")
        self.assertEqual(response.code, 403)
        self.assertEqual(response.body, expected)

    @patch(
        "consoleme.handlers.v2.generate_changes.GenerateChangesHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    def test_post_invalid_requests(self):
        input_body = {"changes": [{"arn": "arn:aws:s3::123456789012:example_bucket"}]}
        response = self.fetch(
            "/api/v2/generate_changes", method="POST", body=json.dumps(input_body)
        )
        self.assertIn("Error validating input", str(response.body))
        self.assertEqual(response.code, 400)

        input_body["changes"][0][
            "resource"
        ] = "arn:aws:s3::12345678902:example_bucket_2"
        input_body["changes"][0]["generator_type"] = "fake"

        response = self.fetch(
            "/api/v2/generate_changes", method="POST", body=json.dumps(input_body)
        )
        self.assertIn("Error validating input", str(response.body))
        self.assertEqual(response.code, 400)

        input_body["changes"][0]["generator_type"] = "s3"
        input_body["changes"][0]["action_groups"] = ["get", "fakeaction"]

        response = self.fetch(
            "/api/v2/generate_changes", method="POST", body=json.dumps(input_body)
        )
        self.assertIn("Error validating input", str(response.body))
        self.assertEqual(response.code, 400)

    @patch(
        "consoleme.handlers.v2.generate_changes.GenerateChangesHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    def test_post_valid_request_generic(self):
        input_body = {
            "changes": [
                {
                    "user": "username@example.com",
                    "principal": {
                        "principal_type": "AwsResource",
                        "principal_arn": "arn:aws:iam::123456789012:role/roleName",
                    },
                    "generator_type": "s3",
                    "resource_arn": "arn:aws:s3:::123456789012-bucket",
                    "bucket_prefix": "/*",
                    "effect": "Allow",
                    "action_groups": ["get", "list"],
                },
                {
                    "user": "username@example.com",
                    "principal": {
                        "principal_type": "AwsResource",
                        "principal_arn": "arn:aws:iam::123456789012:role/roleName",
                    },
                    "generator_type": "s3",
                    "resource_arn": "arn:aws:s3:::bucket2",
                    "bucket_prefix": "/*",
                    "effect": "Allow",
                    "action_groups": ["list", "get"],
                },
                {
                    "user": "username@example.com",
                    "principal": {
                        "principal_type": "AwsResource",
                        "principal_arn": "arn:aws:iam::123456789012:role/roleName",
                    },
                    "generator_type": "crud_lookup",
                    "resource_arn": "*",
                    "effect": "Allow",
                    "service": "ssm",
                    "action_groups": ["list", "read"],
                },
            ]
        }

        response = self.fetch(
            "/api/v2/generate_changes", method="POST", body=json.dumps(input_body)
        )
        self.assertEqual(response.code, 200)
        result = json.loads(response.body)
        self.assertEqual(
            result["changes"][0]["principal"]["principal_arn"],
            input_body["changes"][0]["principal"]["principal_arn"],
        )
        self.assertEqual(
            len(result["changes"]),
            1,
        )

    @patch(
        "consoleme.handlers.v2.generate_changes.GenerateChangesHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    def test_post_valid_request_wildcard(self):
        input_body = {
            "changes": [
                {
                    "user": "username@example.com",
                    "principal": {
                        "principal_type": "AwsResource",
                        "principal_arn": "arn:aws:iam::123456789012:role/roleName",
                    },
                    "generator_type": "s3",
                    "resource_arn": "*",
                    "bucket_prefix": "folder_name/filename",
                    "effect": "Allow",
                    "action_groups": ["get", "list"],
                },
                {
                    "user": "username@example.com",
                    "principal": {
                        "principal_type": "AwsResource",
                        "principal_arn": "arn:aws:iam::123456789012:role/roleName",
                    },
                    "generator_type": "s3",
                    "resource_arn": "*",
                    "bucket_prefix": "folder_name/*",
                    "effect": "Allow",
                    "action_groups": ["list", "get"],
                },
                {
                    "user": "username@example.com",
                    "principal": {
                        "principal_type": "AwsResource",
                        "principal_arn": "arn:aws:iam::123456789012:role/roleName",
                    },
                    "generator_type": "crud_lookup",
                    "resource_arn": "*",
                    "effect": "Allow",
                    "service": "ssm",
                    "action_groups": ["list", "read"],
                },
            ]
        }

        response = self.fetch(
            "/api/v2/generate_changes", method="POST", body=json.dumps(input_body)
        )
        self.assertEqual(response.code, 200)
        result = json.loads(response.body)
        self.assertEqual(
            result["changes"][0]["principal"]["principal_arn"],
            input_body["changes"][0]["principal"]["principal_arn"],
        )

    @patch(
        "consoleme.handlers.v2.generate_changes.GenerateChangesHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    def test_post_valid_request_s3(self):
        input_body = {
            "changes": [
                {
                    "user": "username@example.com",
                    "principal": {
                        "principal_type": "AwsResource",
                        "principal_arn": "arn:aws:iam::123456789012:role/roleName",
                    },
                    "resource_arn": "arn:aws:s3::123456789012:examplebucket",
                    "bucket_prefix": "/*",
                    "generator_type": "s3",
                    "version": "abcd",
                    "asd": "sdf",
                    "action_groups": ["list", "delete"],
                }
            ]
        }
        response = self.fetch(
            "/api/v2/generate_changes", method="POST", body=json.dumps(input_body)
        )
        self.assertEqual(response.code, 200)
        result = json.loads(response.body)
        self.assertEqual(
            result["changes"][0]["principal"]["principal_arn"],
            "arn:aws:iam::123456789012:role/roleName",
        )

    @patch(
        "consoleme.handlers.v2.generate_changes.GenerateChangesHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    def test_post_valid_request_s3_combined_inline(self):
        input_body = {
            "changes": [
                {
                    "user": "username@example.com",
                    "principal": {
                        "principal_type": "AwsResource",
                        "principal_arn": "arn:aws:iam::123456789012:role/roleName",
                    },
                    "resource_arn": "arn:aws:s3::123456789012:examplebucket",
                    "bucket_prefix": "/*",
                    "generator_type": "s3",
                    "version": "abcd",
                    "asd": "sdf",
                    "action_groups": ["list", "delete"],
                },
                {
                    "principal": {
                        "principal_type": "AwsResource",
                        "principal_arn": "arn:aws:iam::123456789012:role/roleName",
                    },
                    "generator_type": "custom_iam",
                    "policy": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "IncludeAccounts": [
                                    "account_a",
                                    "account_b",
                                    "account_c",
                                ],
                                "Action": [
                                    "s3:GetObjectVersion",
                                    "s3:GetObject",
                                    "s3:GetObjectTagging",
                                    "s3:GetObjectAcl",
                                    "s3:ListBucket",
                                    "s3:GetObjectVersionAcl",
                                    "s3:ListBucketVersions",
                                    "s3:GetObjectVersionTagging",
                                ],
                                "Effect": "Allow",
                                "Resource": [
                                    "arn:aws:s3:::bucket2",
                                    "arn:aws:s3:::bucket2/*",
                                ],
                            }
                        ],
                    },
                },
            ]
        }
        response = self.fetch(
            "/api/v2/generate_changes", method="POST", body=json.dumps(input_body)
        )
        self.assertEqual(response.code, 200)
        result = json.loads(response.body)
        self.assertEqual(
            result["changes"][0]["principal"]["principal_arn"],
            "arn:aws:iam::123456789012:role/roleName",
        )
        policy = result["changes"][0]["policy"]["policy_document"]
        policy["Statement"][0].pop("Sid")
        policy["Statement"][1].pop("Sid")
        self.assertEqual(
            policy["Statement"][0],
            {
                "Action": [
                    "s3:deleteobject",
                    "s3:deleteobjecttagging",
                    "s3:deleteobjectversion",
                    "s3:deleteobjectversiontagging",
                    "s3:listbucket",
                    "s3:listbucketversions",
                ],
                "Effect": "Allow",
                "Resource": [
                    "arn:aws:s3:::arn:aws:s3::123456789012:examplebucket",
                    "arn:aws:s3:::arn:aws:s3::123456789012:examplebucket/*",
                ],
            },
        )

        self.assertEqual(
            policy["Statement"][1],
            {
                "Action": [
                    "s3:getobject",
                    "s3:getobjectacl",
                    "s3:getobjecttagging",
                    "s3:getobjectversion",
                    "s3:getobjectversionacl",
                    "s3:getobjectversiontagging",
                    "s3:listbucket",
                    "s3:listbucketversions",
                ],
                "Effect": "Allow",
                "IncludeAccounts": ["account_a", "account_b", "account_c"],
                "Resource": ["arn:aws:s3:::bucket2", "arn:aws:s3:::bucket2/*"],
            },
        )

    @patch(
        "consoleme.handlers.v2.generate_changes.GenerateChangesHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    @patch("consoleme.handlers.v2.generate_changes.ChangeGeneratorModelArray.parse_raw")
    def test_post_raises(self, mock_change_generator_model_array_parse_raw):
        mock_change_generator_model_array_parse_raw.side_effect = Exception(
            "Unknown Exception!"
        )
        input_body = {
            "changes": [
                {
                    "user": "username@example.com",
                    "principal": {
                        "principal_type": "AwsResource",
                        "principal_arn": "arn:aws:iam::123456789012:role/roleName",
                    },
                    "resource_arn": "arn:aws:s3::123456789012:examplebucket",
                    "bucket_prefix": "/*",
                    "generator_type": "s3",
                    "version": "abcd",
                    "asd": "sdf",
                    "action_groups": ["list", "delete"],
                }
            ]
        }
        response = self.fetch(
            "/api/v2/generate_changes", method="POST", body=json.dumps(input_body)
        )
        self.assertEqual(response.code, 500)
        self.assertIn("Error generating changes", str(response.body))

    @patch(
        "consoleme.handlers.v2.generate_changes.GenerateChangesHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    def test_post_valid_request_sns(self):
        input_body = {
            "changes": [
                {
                    "user": "username@example.com",
                    "principal": {
                        "principal_type": "AwsResource",
                        "principal_arn": "arn:aws:iam::123456789012:role/exampleRole",
                    },
                    "resource_arn": "arn:aws:sns:us-east-1:123456789012:exampletopic",
                    "generator_type": "sns",
                    "version": "abcd",
                    "asd": "sdf",
                    "action_groups": ["get_topic_attributes", "publish"],
                }
            ]
        }

        response = self.fetch(
            "/api/v2/generate_changes", method="POST", body=json.dumps(input_body)
        )
        self.assertEqual(response.code, 200)
        result = json.loads(response.body)
        self.assertEqual(
            result["changes"][0]["principal"]["principal_arn"],
            "arn:aws:iam::123456789012:role/exampleRole",
        )

    @patch(
        "consoleme.handlers.v2.generate_changes.GenerateChangesHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    def test_post_valid_request_sqs(self):
        input_body = {
            "changes": [
                {
                    "user": "username@example.com",
                    "principal": {
                        "principal_type": "AwsResource",
                        "principal_arn": "arn:aws:iam::123456789012:role/roleName",
                    },
                    "generator_type": "sqs",
                    "resource_arn": "arn:aws:sqs:us-east-1:123456789012:resourceName",
                    "effect": "Allow",
                    "action_groups": ["get_queue_attributes", "send_messages"],
                }
            ]
        }
        response = self.fetch(
            "/api/v2/generate_changes", method="POST", body=json.dumps(input_body)
        )
        self.assertEqual(response.code, 200)
        result = json.loads(response.body)
        self.assertEqual(
            result["changes"][0]["principal"]["principal_arn"],
            "arn:aws:iam::123456789012:role/roleName",
        )
