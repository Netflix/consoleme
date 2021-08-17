import ujson as json
from asgiref.sync import async_to_sync
from mock import Mock, patch
from tornado.testing import AsyncHTTPTestCase

from consoleme.lib.self_service.models import (
    SelfServiceTypeaheadModel,
    SelfServiceTypeaheadModelArray,
)
from consoleme.models import AwsResourcePrincipalModel
from tests.conftest import MockBaseHandler, create_future


class TestTypeAheadHandler(AsyncHTTPTestCase):
    def get_app(self):
        from consoleme.routes import make_app

        return make_app(jwt_validator=lambda x: {})

    def setUp(self):
        super(TestTypeAheadHandler, self).setUp()

    @patch(
        "consoleme.handlers.v2.typeahead.ResourceTypeAheadHandlerV2.authorization_flow",
        MockBaseHandler.authorization_flow,
    )
    def test_typeahead_get(self):
        from consoleme.config import config

        headers = {
            config.get("auth.user_header_name"): "user@github.com",
            config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }
        from consoleme.lib.redis import RedisHandler

        red = RedisHandler().redis_sync()
        red.hmset(
            "AWSCONFIG_RESOURCE_CACHE",
            {
                "arn:aws:ec2:us-west-2:123456789013:security-group/12345": "{}",
                "arn:aws:sqs:us-east-1:123456789012:rolequeue": "{}",
                "arn:aws:sns:us-east-1:123456789012:roletopic": "{}",
                "arn:aws:iam::123456789012:role/role": "{}",
            },
        )
        # Return all the things
        response = self.fetch(
            "/api/v2/typeahead/resources", method="GET", headers=headers
        )
        self.assertEqual(response.code, 200)
        responseJSON = json.loads(response.body)

        self.assertEqual(len(responseJSON), 4)
        # Filter for a specific query
        response = self.fetch(
            "/api/v2/typeahead/resources?typeahead=role", method="GET", headers=headers
        )
        self.assertEqual(response.code, 200)
        responseJSON = json.loads(response.body)
        self.assertEqual(len(responseJSON), 3)

        # Filter for a specific limit
        response = self.fetch(
            "/api/v2/typeahead/resources?typeahead=role&limit=1",
            method="GET",
            headers=headers,
        )
        self.assertEqual(response.code, 200)
        responseJSON = json.loads(response.body)
        self.assertEqual(len(responseJSON), 1)

        # Filter for a specific account
        response = self.fetch(
            "/api/v2/typeahead/resources?account_id=123456789013",
            method="GET",
            headers=headers,
        )
        self.assertEqual(response.code, 200)
        responseJSON = json.loads(response.body)
        self.assertEqual(len(responseJSON), 1)

        # Filter for a specific resource type
        response = self.fetch(
            "/api/v2/typeahead/resources?resource_type=sqs",
            method="GET",
            headers=headers,
        )
        self.assertEqual(response.code, 200)
        responseJSON = json.loads(response.body)
        self.assertEqual(len(responseJSON), 1)

        # filter for region
        response = self.fetch(
            "/api/v2/typeahead/resources?region=us-east-1",
            method="GET",
            headers=headers,
        )
        self.assertEqual(response.code, 200)
        responseJSON = json.loads(response.body)
        self.assertEqual(len(responseJSON), 2)

        # multifilter
        response = self.fetch(
            "/api/v2/typeahead/resources?region=us-east-1&account_id=123456789012&typeahead=role&limit=5",
            method="GET",
            headers=headers,
        )
        self.assertEqual(response.code, 200)
        responseJSON = json.loads(response.body)
        self.assertEqual(len(responseJSON), 2)

    def test_cache_self_service_template_and_typeahead(self):
        from consoleme.lib.templated_resources import (
            TemplatedFileModelArray,
            TemplateFile,
        )

        mock_template_file_model_array = TemplatedFileModelArray(
            templated_resources=[
                TemplateFile(
                    name="fake_test_template_1",
                    repository_name="fake_repo",
                    owner="fake_owner",
                    include_accounts=["fake_account_1"],
                    exclude_accounts=None,
                    number_of_accounts=1,
                    resource="path/to/file.yaml",
                    file_path="path/to/file.yaml",
                    web_path="http://github.example.com/fake_repo/browse/master/path/to/file.yaml",
                    resource_type="iam_role",
                    template_language="honeybee",
                )
            ]
        )

        mock_template_typeahead_model = SelfServiceTypeaheadModel(
            details_endpoint="/api/v2/templated_resource/fake_repo/path/to/file.yaml",
            display_text="fake_test_template_1",
            icon="users",
            number_of_affected_resources=1,
            principal={
                "principal_type": "HoneybeeAwsResourceTemplate",
                "repository_name": "fake_repo",
                "resource_identifier": "path/to/file.yaml",
                "resource_url": "http://github.example.com/fake_repo/browse/master/path/to/file.yaml",
            },
        )

        patch_cache_resource_templates_for_repository = patch(
            "consoleme.lib.templated_resources.cache_resource_templates_for_repository",
            Mock(return_value=create_future(mock_template_file_model_array)),
        )

        # Cache resource templates, but let's not go down the rabbit hole of trying to mock a Git repo
        patch_cache_resource_templates_for_repository.start()
        from consoleme.lib.templated_resources import cache_resource_templates

        result = async_to_sync(cache_resource_templates)()
        patch_cache_resource_templates_for_repository.stop()
        self.assertEqual(result, mock_template_file_model_array)

        # Retrieve cached resource templates and ensure it is correct
        from consoleme.lib.templated_resources import retrieve_cached_resource_templates

        result = async_to_sync(retrieve_cached_resource_templates)()
        self.assertEqual(result, mock_template_file_model_array)

        # Cache and verify Self Service Typeahead
        from consoleme.lib.self_service.typeahead import cache_self_service_typeahead

        result = async_to_sync(cache_self_service_typeahead)()
        self.assertIsInstance(result, SelfServiceTypeaheadModelArray)
        self.assertGreater(len(result.typeahead_entries), 15)
        expected_entry = SelfServiceTypeaheadModel(
            account="default_account",
            details_endpoint="/api/v2/roles/123456789012/RoleNumber5",
            display_text="RoleNumber5",
            icon="user",
            number_of_affected_resources=1,
            principal=AwsResourcePrincipalModel(
                principal_type="AwsResource",
                principal_arn="arn:aws:iam::123456789012:role/RoleNumber5",
            ),
        )
        # Pre-existing role is in results
        self.assertIn(expected_entry, result.typeahead_entries)
        # HB template is in results
        self.assertIn(mock_template_typeahead_model, result.typeahead_entries)

        # Now let's mock the web requests
        from consoleme.config import config

        headers = {
            config.get("auth.user_header_name"): "user@github.com",
            config.get("auth.groups_header_name"): "groupa,groupb,groupc",
        }

        response = self.fetch(
            "/api/v2/templated_resource/fake_repo/path/to/file.yaml",
            method="GET",
            headers=headers,
        )
        self.assertEqual(response.code, 200)
        response_body = json.loads(response.body)
        self.assertEqual(
            response_body,
            {
                "name": "fake_test_template_1",
                "owner": "fake_owner",
                "include_accounts": ["fake_account_1"],
                "exclude_accounts": None,
                "number_of_accounts": 1,
                "resource": "path/to/file.yaml",
                "resource_type": "iam_role",
                "repository_name": "fake_repo",
                "template_language": "honeybee",
                "web_path": "http://github.example.com/fake_repo/browse/master/path/to/file.yaml",
                "file_path": "path/to/file.yaml",
                "content": None,
            },
        )
