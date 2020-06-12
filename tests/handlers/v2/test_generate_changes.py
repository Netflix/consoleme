import ujson as json
from mock import patch
from tornado.testing import AsyncHTTPTestCase

from consoleme.lib.change_request import (
    generate_generic_change,
    generate_s3_change,
    generate_sns_change,
    generate_sqs_change,
)
from consoleme.models import (
    GenericChangeGeneratorModel,
    S3ChangeGeneratorModel,
    SNSChangeGeneratorModel,
    SQSChangeGeneratorModel,
)
from tests.conftest import MockBaseHandler, create_future


class TestGenerateChangesHandler(AsyncHTTPTestCase):
    def get_app(self):
        from consoleme.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    @patch(
        "consoleme.handlers.v2.generate_changes.GenerateChangesHandler.authorization_flow"
    )
    def test_post_no_user(self, mock_auth):
        mock_auth.return_value = create_future(None)
        expected = {"status": 403, "title": "Forbidden", "message": "No user detected"}
        response = self.fetch("/api/v2/generate_changes", method="POST", body="abcd")
        self.assertEqual(response.code, 403)
        self.assertDictEqual(json.loads(response.body), expected)

    @patch(
        "consoleme.handlers.v2.generate_changes.GenerateChangesHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    def test_post_invalid_requests(self):
        input_body = {
            "arn": "arn:aws:s3::123456789012:example_bucket",
        }
        expected = {
            "status": 400,
            "title": "Bad Request",
            "message": "Error validating input: 2 validation errors for ChangeGeneratorModel\ngenerator_type\n  "
            "field required (type=value_error.missing)\nresource\n  "
            "field required (type=value_error.missing)",
        }
        response = self.fetch(
            "/api/v2/generate_changes", method="POST", body=json.dumps(input_body)
        )
        self.assertEqual(response.code, 400)
        self.assertDictEqual(json.loads(response.body), expected)

        input_body["resource"] = "arn:aws:s3::12345678902:example_bucket_2"
        input_body["generator_type"] = "fake"
        expected = {
            "status": 400,
            "title": "Bad Request",
            "message": "Error validating input: 1 validation error for ChangeGeneratorModel\ngenerator_type\n  value is"
            " not a valid enumeration member; permitted: 'generic', 's3', 'sqs', 'sns' "
            "(type=type_error.enum; enum_values=[<GeneratorType.generic: 'generic'>, <GeneratorType.s3: "
            "'s3'>, <GeneratorType.sqs: 'sqs'>, <GeneratorType.sns: 'sns'>])",
        }
        response = self.fetch(
            "/api/v2/generate_changes", method="POST", body=json.dumps(input_body)
        )
        self.assertEqual(response.code, 400)
        self.assertDictEqual(json.loads(response.body), expected)

        input_body["generator_type"] = "s3"
        input_body["action_groups"] = ["get", "fakeaction"]
        expected = {
            "status": 400,
            "title": "Bad Request",
            "message": "Error validating input: 1 validation error for S3ChangeGeneratorModel\naction_groups -> 1\n  "
            "value is not a valid enumeration member; permitted: 'list', 'get', 'put', 'delete' "
            "(type=type_error.enum; enum_values=[<ActionGroup.list: 'list'>, <ActionGroup.get: 'get'>, "
            "<ActionGroup.put: 'put'>, <ActionGroup.delete: 'delete'>])",
        }
        response = self.fetch(
            "/api/v2/generate_changes", method="POST", body=json.dumps(input_body)
        )
        self.assertEqual(response.code, 400)
        self.assertDictEqual(json.loads(response.body), expected)

    @patch(
        "consoleme.handlers.v2.generate_changes.GenerateChangesHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    def test_post_valid_request_generic(self):
        input_body = {
            "arn": "arn:aws:s3::123456789012:examplebucket",
            "resource": "arn:aws:s3::12345678902:examplebucketahhhh",
            "generator_type": "generic",
            "version": "abcd",
            "asd": "sdf",
            "access_level": ["read", "write"],
        }
        generic_cgm = GenericChangeGeneratorModel(**input_body)
        expected = generate_generic_change(generic_cgm)
        response = self.fetch(
            "/api/v2/generate_changes", method="POST", body=json.dumps(input_body)
        )
        self.assertEqual(response.code, 200)
        result = json.loads(response.body)
        self.assertEqual(
            result["policy"]["policy_sha256"], expected.policy.policy_sha256
        )
        self.assertEqual(
            result["policy"]["policy_document"], expected.policy.policy_document
        )

    @patch(
        "consoleme.handlers.v2.generate_changes.GenerateChangesHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    def test_post_valid_request_s3(self):
        input_body = {
            "arn": "arn:aws:s3::123456789012:examplebucket",
            "resource": "arn:aws:s3::12345678902:examplebucketahhhh",
            "generator_type": "s3",
            "version": "abcd",
            "asd": "sdf",
            "action_groups": ["list", "delete"],
        }
        s3_cgm = S3ChangeGeneratorModel(**input_body)
        expected = generate_s3_change(s3_cgm)
        response = self.fetch(
            "/api/v2/generate_changes", method="POST", body=json.dumps(input_body)
        )
        self.assertEqual(response.code, 200)
        result = json.loads(response.body)
        self.assertEqual(
            result["policy"]["policy_sha256"], expected.policy.policy_sha256
        )
        self.assertEqual(
            result["policy"]["policy_document"], expected.policy.policy_document
        )

    @patch(
        "consoleme.handlers.v2.generate_changes.GenerateChangesHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    def test_post_valid_request_sns(self):
        input_body = {
            "arn": "arn:aws:s3::123456789012:examplebucket",
            "resource": "arn:aws:s3::12345678902:examplebucketahhhh",
            "generator_type": "sns",
            "version": "abcd",
            "asd": "sdf",
            "action_groups": ["get_topic_attributes", "publish"],
        }
        sns_cgm = SNSChangeGeneratorModel(**input_body)
        expected = generate_sns_change(sns_cgm)
        response = self.fetch(
            "/api/v2/generate_changes", method="POST", body=json.dumps(input_body)
        )
        self.assertEqual(response.code, 200)
        result = json.loads(response.body)
        self.assertEqual(
            result["policy"]["policy_sha256"], expected.policy.policy_sha256
        )
        self.assertEqual(
            result["policy"]["policy_document"], expected.policy.policy_document
        )

    @patch(
        "consoleme.handlers.v2.generate_changes.GenerateChangesHandler.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    def test_post_valid_request_sqs(self):
        input_body = {
            "arn": "arn:aws:s3::123456789012:examplebucket",
            "resource": "arn:aws:s3::12345678902:examplebucketahhhh",
            "generator_type": "sqs",
            "version": "abcd",
            "asd": "sdf",
            "action_groups": ["get_queue_attributes", "delete_messages"],
        }
        sqs_cgm = SQSChangeGeneratorModel(**input_body)
        expected = generate_sqs_change(sqs_cgm)
        response = self.fetch(
            "/api/v2/generate_changes", method="POST", body=json.dumps(input_body)
        )
        self.assertEqual(response.code, 200)
        result = json.loads(response.body)
        self.assertEqual(
            result["policy"]["policy_sha256"], expected.policy.policy_sha256
        )
        self.assertEqual(
            result["policy"]["policy_document"], expected.policy.policy_document
        )
