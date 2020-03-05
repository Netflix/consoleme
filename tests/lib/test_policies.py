import asyncio
from unittest import TestCase

from mock import MagicMock, patch

from consoleme.lib.policies import get_resources_from_events
from tests.conftest import create_future

mock_s3_bucket_redis = MagicMock(
    return_value=create_future({"123456789012": ["foobar", "bazbang"]})
)


class TestPoliciesLib(TestCase):
    def test_get_actions_for_resource(self):
        pass

    def test_get_formatted_policy_changes(self):
        pass

    @patch("consoleme.lib.aws.redis_hgetall", mock_s3_bucket_redis)
    def test_get_resources_from_events(self):
        policy_changes = [
            {
                "inline_policies": [
                    {
                        "policy_document": {
                            "Statement": [
                                {
                                    "Action": [
                                        "s3:PutObject",
                                        "s3:GetObject",
                                        "ec2:DescribeInstances",
                                    ],
                                    "Resource": [
                                        "arn:aws:s3:::foobar",
                                        "arn:aws:s3:::foobar/*",
                                    ],
                                },
                            ],
                        },
                    },
                ],
            },
        ]
        expected = {
            "foobar": {
                "actions": ["s3:PutObject", "s3:GetObject"],
                "arns": ["arn:aws:s3:::foobar", "arn:aws:s3:::foobar/*"],
                "account": "123456789012",
                "type": "s3",
                "region": "",
            },
        }
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(get_resources_from_events(policy_changes))
        self.assertDictEqual(expected, result)
