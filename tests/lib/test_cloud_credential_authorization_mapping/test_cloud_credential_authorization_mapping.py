import unittest


class TestCloudCredentialAuthorizationMapping(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        from consoleme.celery.celery_tasks import cache_roles_for_account
        from consoleme.celery.celery_tasks import cache_roles_across_accounts
        cache_roles_for_account("123456789012")
        cache_roles_across_accounts()

    def setUp(self):
        self.maxDiff = 10000

    async def test_retrieve_credential_authorization_mapping(self):
        pass

    async def test_determine_users_authorized_roles(self):
        pass

    async def test_generate_and_store_credential_authorization_mapping(self):
        from consoleme.lib.cloud_credential_authorization_mapping import (
            generate_and_store_credential_authorization_mapping,
        )
        from consoleme.lib.cloud_credential_authorization_mapping import (
            RoleAuthorizations,
        )

        mapping = await generate_and_store_credential_authorization_mapping()

        expected = {
            "group8": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber8"},
                authorized_roles_cli_only=set(),
            ),
            "group8@example.com": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber8"},
                authorized_roles_cli_only=set(),
            ),
            "group8-cli": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber8"
                },
            ),
            "group8-cli@example.com": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber8"
                },
            ),
            "group3": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber3"},
                authorized_roles_cli_only=set(),
            ),
            "group3@example.com": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber3"},
                authorized_roles_cli_only=set(),
            ),
            "group3-cli": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber3"
                },
            ),
            "group3-cli@example.com": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber3"
                },
            ),
            "group6": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber6"},
                authorized_roles_cli_only=set(),
            ),
            "group6@example.com": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber6"},
                authorized_roles_cli_only=set(),
            ),
            "group6-cli": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber6"
                },
            ),
            "group6-cli@example.com": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber6"
                },
            ),
            "group9": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber9"},
                authorized_roles_cli_only=set(),
            ),
            "group9@example.com": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber9"},
                authorized_roles_cli_only=set(),
            ),
            "group9-cli": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber9"
                },
            ),
            "group9-cli@example.com": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber9"
                },
            ),
            "group5": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber5"},
                authorized_roles_cli_only=set(),
            ),
            "group5@example.com": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber5"},
                authorized_roles_cli_only=set(),
            ),
            "group5-cli": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber5"
                },
            ),
            "group5-cli@example.com": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber5"
                },
            ),
            "group2": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber2"},
                authorized_roles_cli_only=set(),
            ),
            "group2@example.com": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber2"},
                authorized_roles_cli_only=set(),
            ),
            "group2-cli": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber2"
                },
            ),
            "group2-cli@example.com": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber2"
                },
            ),
            "group1": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber1"},
                authorized_roles_cli_only=set(),
            ),
            "group1@example.com": RoleAuthorizations(
                authorized_roles={
                    "arn:aws:iam::123456789012:role/RoleNumber1",
                    "arn:aws:iam::123456789012:role/rolename",
                },
                authorized_roles_cli_only={"arn:aws:iam::123456789012:role/rolename2"},
            ),
            "group1-cli": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber1"
                },
            ),
            "group1-cli@example.com": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber1"
                },
            ),
            "group7": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber7"},
                authorized_roles_cli_only=set(),
            ),
            "group7@example.com": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber7"},
                authorized_roles_cli_only=set(),
            ),
            "group7-cli": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber7"
                },
            ),
            "group7-cli@example.com": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber7"
                },
            ),
            "group4": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber4"},
                authorized_roles_cli_only=set(),
            ),
            "group4@example.com": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber4"},
                authorized_roles_cli_only=set(),
            ),
            "group4-cli": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber4"
                },
            ),
            "group4-cli@example.com": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber4"
                },
            ),
            "group0": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber0"},
                authorized_roles_cli_only=set(),
            ),
            "group0@example.com": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber0"},
                authorized_roles_cli_only=set(),
            ),
            "group0-cli": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber0"
                },
            ),
            "group0-cli@example.com": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber0"
                },
            ),
            "someuser@example.com": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/userrolename"},
                authorized_roles_cli_only=set(),
            ),
            "groupa@example.com": RoleAuthorizations(
                authorized_roles={
                    "arn:aws:iam::123456789012:role/roleA",
                    "arn:aws:iam::123456789012:role/roleB",
                },
                authorized_roles_cli_only=set(),
            ),
        }
        for k, v in expected.items():
            self.assertEqual(mapping.get(k), v)

    async def test_RoleTagAuthorizationMappingGenerator(self):
        from consoleme.lib.cloud_credential_authorization_mapping import (
            RoleTagAuthorizationMappingGenerator,
        )
        from consoleme.lib.cloud_credential_authorization_mapping import (
            RoleAuthorizations,
        )

        authorization_mapping = await RoleTagAuthorizationMappingGenerator().generate_credential_authorization_mapping(
            {}
        )

        expected = {
            "group8": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber8"},
                authorized_roles_cli_only=set(),
            ),
            "group8@example.com": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber8"},
                authorized_roles_cli_only=set(),
            ),
            "group8-cli": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber8"
                },
            ),
            "group8-cli@example.com": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber8"
                },
            ),
            "group1": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber1"},
                authorized_roles_cli_only=set(),
            ),
            "group1@example.com": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber1"},
                authorized_roles_cli_only=set(),
            ),
            "group1-cli": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber1"
                },
            ),
            "group1-cli@example.com": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber1"
                },
            ),
            "group0": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber0"},
                authorized_roles_cli_only=set(),
            ),
            "group0@example.com": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber0"},
                authorized_roles_cli_only=set(),
            ),
            "group0-cli": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber0"
                },
            ),
            "group0-cli@example.com": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber0"
                },
            ),
            "group5": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber5"},
                authorized_roles_cli_only=set(),
            ),
            "group5@example.com": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber5"},
                authorized_roles_cli_only=set(),
            ),
            "group5-cli": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber5"
                },
            ),
            "group5-cli@example.com": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber5"
                },
            ),
            "group6": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber6"},
                authorized_roles_cli_only=set(),
            ),
            "group6@example.com": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber6"},
                authorized_roles_cli_only=set(),
            ),
            "group6-cli": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber6"
                },
            ),
            "group6-cli@example.com": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber6"
                },
            ),
            "group7": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber7"},
                authorized_roles_cli_only=set(),
            ),
            "group7@example.com": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber7"},
                authorized_roles_cli_only=set(),
            ),
            "group7-cli": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber7"
                },
            ),
            "group7-cli@example.com": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber7"
                },
            ),
            "group4": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber4"},
                authorized_roles_cli_only=set(),
            ),
            "group4@example.com": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber4"},
                authorized_roles_cli_only=set(),
            ),
            "group4-cli": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber4"
                },
            ),
            "group4-cli@example.com": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber4"
                },
            ),
            "group2": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber2"},
                authorized_roles_cli_only=set(),
            ),
            "group2@example.com": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber2"},
                authorized_roles_cli_only=set(),
            ),
            "group2-cli": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber2"
                },
            ),
            "group2-cli@example.com": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber2"
                },
            ),
            "group3": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber3"},
                authorized_roles_cli_only=set(),
            ),
            "group3@example.com": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber3"},
                authorized_roles_cli_only=set(),
            ),
            "group3-cli": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber3"
                },
            ),
            "group3-cli@example.com": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber3"
                },
            ),
            "group9": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber9"},
                authorized_roles_cli_only=set(),
            ),
            "group9@example.com": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/RoleNumber9"},
                authorized_roles_cli_only=set(),
            ),
            "group9-cli": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber9"
                },
            ),
            "group9-cli@example.com": RoleAuthorizations(
                authorized_roles=set(),
                authorized_roles_cli_only={
                    "arn:aws:iam::123456789012:role/RoleNumber9"
                },
            ),
        }
        for k, v in expected.items():
            self.assertEqual(authorization_mapping.get(k), v)

    async def test_DynamicConfigAuthorizationMappingGenerator(self):
        from consoleme.lib.cloud_credential_authorization_mapping import (
            DynamicConfigAuthorizationMappingGenerator,
        )
        from consoleme.lib.cloud_credential_authorization_mapping import (
            RoleAuthorizations,
        )

        authorization_mapping = await DynamicConfigAuthorizationMappingGenerator().generate_credential_authorization_mapping(
            {}
        )

        expected = {
            "someuser@example.com": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/userrolename"},
                authorized_roles_cli_only=set(),
            ),
            "group1@example.com": RoleAuthorizations(
                authorized_roles={"arn:aws:iam::123456789012:role/rolename"},
                authorized_roles_cli_only={"arn:aws:iam::123456789012:role/rolename2"},
            ),
            "groupa@example.com": RoleAuthorizations(
                authorized_roles={
                    "arn:aws:iam::123456789012:role/roleB",
                    "arn:aws:iam::123456789012:role/roleA",
                },
                authorized_roles_cli_only=set(),
            ),
        }
        for k, v in expected.items():
            self.assertEqual(authorization_mapping.get(k), v)

    async def test_InternalPluginAuthorizationMappingGenerator(self):
        from consoleme.lib.cloud_credential_authorization_mapping import (
            InternalPluginAuthorizationMappingGenerator,
        )
        from consoleme.lib.cloud_credential_authorization_mapping import (
            RoleAuthorizations,
        )

        expected = {
            "groupa@example.com": RoleAuthorizations(
                authorized_roles={
                    "arn:aws:iam::123456789012:role/roleA",
                    "arn:aws:iam::123456789012:role/roleB",
                },
                authorized_roles_cli_only=set(),
            ),
        }
        authorization_mapping = await InternalPluginAuthorizationMappingGenerator().generate_credential_authorization_mapping(
            expected
        )
        for k, v in expected.items():
            self.assertEqual(authorization_mapping.get(k), v)

