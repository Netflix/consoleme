import json

from mock import patch
from mockredis import mock_strict_redis_client

from consoleme.config import config
from consoleme.lib.plugins import get_plugin_by_name
from tests.conftest import AioTestCase
from tests.conftest import MockRedisHandler

group_mapping = get_plugin_by_name(config.get("plugins.group_mapping"))()


class TestGroupMappingPlugin(AioTestCase):
    async def setUp(self):
        self.gp = group_mapping

    async def test_get_eligible_roles(self):
        mock_atlas = patch(
            "consoleme_internal.plugins.metrics.metrics.Redis", mock_strict_redis_client
        )
        mock_atlas.start()
        groups = {
            # awssg:
            "111111111111": "awsrole-someaccount-111111111111@example.com",
            "222222222222": "awsrole-someaccount-222222222222@example.com",
            # cm only:
            "333333333333": "cm-333333333333@example.com",
            "444444444444": "cm-444444444444@example.com",
            # Should not create the following:
            "555555555555": "555555555555@example.com",
            "666666666666": "cm-666666666666@example.net",
            "777777777777": "cm-777777777777@example.com",
            "888888888888": "cm-user-role-onboarding@example.com",
            "999999999999": "awsrole-someaccount_user-888888888888@example.com",
            "000000000000": "awsrole-someaccount_poweruser-000000000000@example.com",
        }

        import consoleme_internal.plugins.group_mapping.group_mapping

        with patch.object(
            consoleme_internal.plugins.group_mapping.group_mapping, "RedisHandler"
        ) as mock_redis_handler:
            mock_redis_handler.return_value = MockRedisHandler(
                return_value='{"111111111111": true, "222222222222": true, "333333333333": true, "444444444444": true}'
            )
            roles = await self.gp.get_eligible_roles(
                "someuser@example.com", list(groups.values()), user_role="cm_someuser_N"
            )

        # Mixture between awssg and cm groups:

        self.assertEqual(len(roles), 4)
        self.assertIn("arn:aws:iam::111111111111:role/someaccount", roles)
        self.assertIn("arn:aws:iam::222222222222:role/someaccount", roles)
        self.assertIn("arn:aws:iam::000000000000:role/someaccount_poweruser", roles)
        self.assertIn("arn:aws:iam::888888888888:role/cm_someuser_N", roles)

        # Need to test if a user as the classic role -- AND the dynamic role:
        roles = await self.gp.get_eligible_roles(
            "someuser@example.com",
            [
                "awsrole-someaccount_user-888888888888@example.com",
                "awsrole-someaccount_poweruser-888888888888@example.com",
                "cm-user-role-onboarding@example.com",
            ],
            user_role="cm_someuser_N",
        )
        self.assertEqual(len(roles), 2)
        mock_atlas.stop()

    async def test_get_account_mappings(self):
        """Test the logic for getting account mappings (name -> ID, and ID -> names)"""
        with patch(
            "consoleme_internal.plugins.aws.aws.redis_get_sync"
        ) as mock_redis_handler:
            mock_redis_handler.return_value = json.dumps(
                {"111111111111": ["awsaccount", "awsaccount@example.com"]}
            )

            account_mappings = await self.gp.get_account_mappings()

        self.assertIsInstance(account_mappings["names_to_ids"], dict)
        self.assertIsInstance(account_mappings["ids_to_names"], dict)

        for name in ["awsaccount", "awsaccount@example.com"]:
            self.assertEqual(account_mappings["names_to_ids"][name], "111111111111")
            self.assertIn(name, account_mappings["ids_to_names"]["111111111111"])
