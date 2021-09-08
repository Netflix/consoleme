"""Docstring in public module."""
import copy
import json
import os
import sys
from datetime import datetime, timedelta
from unittest import TestCase

APP_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(APP_ROOT, ".."))


class TestCelerySync(TestCase):
    def setUp(self):
        from consoleme.celery_tasks import celery_tasks as celery

        self.celery = celery

    def cache_iam_resources_for_account(self):
        from consoleme.config.config import CONFIG
        from consoleme.lib.dynamo import IAMRoleDynamoHandler
        from consoleme.lib.redis import RedisHandler

        red = RedisHandler().redis_sync()

        # Set the config value for the redis cache location
        old_config = copy.deepcopy(CONFIG.config)
        CONFIG.config = {
            **CONFIG.config,
            "aws": {
                **CONFIG.config.get("aws", {}),
                "iamroles_redis_key": "cache_iam_resources_for_account",
            },
            "cache_iam_resources_across_accounts": {
                "all_roles_combined": {
                    "s3": {
                        "file": "cache_iam_resources_for_account.json.gz",
                    }
                }
            },
        }

        # Clear out the existing cache from Redis:
        red.delete("cache_iam_resources_for_account")
        # Run it:
        self.celery.cache_iam_resources_for_account("123456789012")

        # Verify that everything is there:
        dynamo = IAMRoleDynamoHandler()

        results = dynamo.role_table.scan(TableName="consoleme_iamroles_global")

        remaining_roles = [
            "arn:aws:iam::123456789012:role/ConsoleMe",
            "arn:aws:iam::123456789012:role/cm_someuser_N",
            "arn:aws:iam::123456789012:role/awsaccount_user",
            "arn:aws:iam::123456789012:role/TestInstanceProfile",
            "arn:aws:iam::123456789012:role/rolename",
        ] + [f"arn:aws:iam::123456789012:role/RoleNumber{num}" for num in range(0, 10)]

        self.assertEqual(results["Count"], len(remaining_roles))
        self.assertEqual(results["Count"], red.hlen("cache_iam_resources_for_account"))

        for i in results["Items"]:
            remaining_roles.remove(i["arn"])
            self.assertEqual(i["accountId"], "123456789012")
            self.assertGreater(int(i["ttl"]), 0)
            self.assertIsNotNone(json.loads(i["policy"]))
            self.assertEqual(
                json.loads(red.hget("cache_iam_resources_for_account", i["arn"]))[
                    "policy"
                ],
                i["policy"],
            )

        # Should all be accounted for:
        self.assertEqual(remaining_roles, [])

        # We should have the same data in redis on all regions, this time coming from DDB
        old_conf_region = self.celery.config.region
        self.celery.config.region = "us-east-1"

        # Clear out the existing cache from Redis:
        red.delete("cache_iam_resources_for_account")

        # This should spin off extra fake celery tasks
        res = self.celery.cache_iam_resources_across_accounts()
        self.assertEqual(
            res,
            {
                "function": "consoleme.celery_tasks.celery_tasks.cache_iam_resources_across_accounts",
                "cache_key": "cache_iam_resources_for_account",
                "num_roles": 15,
                "num_accounts": 1,
            },
        )  # This should spin off extra fake celery tasks
        res = self.celery.cache_iam_resources_across_accounts()
        self.assertEqual(
            res,
            {
                "function": "consoleme.celery_tasks.celery_tasks.cache_iam_resources_across_accounts",
                "cache_key": "cache_iam_resources_for_account",
                "num_roles": 15,
                "num_accounts": 1,
            },
        )

        # Reset the config value:
        self.celery.config.region = old_conf_region
        CONFIG.config = old_config

    def test_clear_old_redis_iam_cache(self):
        from consoleme.config.config import CONFIG
        from consoleme.lib.redis import RedisHandler

        red = RedisHandler().redis_sync()

        self.celery.REDIS_IAM_COUNT = 3

        # Clear out the existing cache from Redis:
        red.delete("cache_iam_resources_for_account_expiration")

        # Set the config value for the redis cache location
        old_value = CONFIG.config["aws"].pop("iamroles_redis_key", None)
        CONFIG.config["aws"][
            "iamroles_redis_key"
        ] = "cache_iam_resources_for_account_expiration"

        # Add in some dummy IAM roles with a TTL that is more than 6 hours old:
        old_ttl = int((datetime.utcnow() - timedelta(hours=6, seconds=5)).timestamp())

        # 13 items / 3 = 5 iterations -- all of these roles should be cleaned up:
        for i in range(0, 13):
            role_entry = {
                "arn": f"arn:aws:iam::123456789012:role/RoleNumber{i}",
                "name": f"RoleNumber{i}",
                "accountId": "123456789012",
                "ttl": old_ttl,
                "policy": "{}",
            }
            self.celery._add_role_to_redis(
                "cache_iam_resources_for_account_expiration", role_entry
            )

        # Add a role with a current TTL -- this should not be cleaned up:
        role_entry = {
            "arn": "arn:aws:iam::123456789012:role/RoleNumber99",
            "name": "RoleNumber99",
            "accountId": "123456789012",
            "ttl": int(datetime.utcnow().timestamp()),
            "policy": "{}",
        }
        self.celery._add_role_to_redis(
            "cache_iam_resources_for_account_expiration", role_entry
        )

        # Nothing should happen if we are not in us-west-2:
        old_conf_region = self.celery.config.region
        self.celery.config.region = "us-east-1"

        self.celery.clear_old_redis_iam_cache()
        self.assertEqual(red.hlen("cache_iam_resources_for_account_expiration"), 14)

        # With the proper region:
        self.celery.config.region = "us-west-2"
        self.celery.clear_old_redis_iam_cache()

        # Verify:
        self.assertEqual(red.hlen("cache_iam_resources_for_account_expiration"), 1)
        self.assertIsNotNone(
            red.hget(
                "cache_iam_resources_for_account_expiration",
                "arn:aws:iam::123456789012:role/RoleNumber99",
            )
        )

        # Clear out the existing cache from Redis:
        red.delete("cache_iam_resources_for_account_expiration")

        # Reset the config values:
        self.celery.config.region = old_conf_region
        self.celery.REDIS_IAM_COUNT = 1000
        if not old_value:
            del CONFIG.config["aws"]["iamroles_redis_key"]
        else:
            CONFIG.config["aws"]["iamroles_redis_key"] = old_value

    def test_trigger_credential_mapping_refresh_from_role_changes(self):
        res = self.celery.trigger_credential_mapping_refresh_from_role_changes()
        self.assertEqual(
            res,
            {
                "function": "consoleme.celery_tasks.celery_tasks.trigger_credential_mapping_refresh_from_role_changes",
                "message": "Successfully checked role changes",
                "num_roles_changed": 2,
            },
        )

    def test_cache_cloudtrail_denies(self):
        res = self.celery.cache_cloudtrail_denies()
        self.assertEqual(
            res,
            {
                "function": "consoleme.celery_tasks.celery_tasks.cache_cloudtrail_denies",
                "message": "Successfully cached cloudtrail denies",
                "num_new_cloudtrail_denies": 1,
                "num_cloudtrail_denies": 1,
            },
        )
