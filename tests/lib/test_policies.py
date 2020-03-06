import asyncio
from unittest import TestCase

from mock import MagicMock, patch

from consoleme.lib.policies import get_actions_for_resource, get_resources_from_events
from tests.conftest import create_future

mock_s3_bucket_redis = MagicMock(
    return_value=create_future({"123456789012": ["foobar", "bazbang"]})
)


class TestPoliciesLib(TestCase):
    def test_get_actions_for_resource(self):
        test_cases = [
            {
                "arn": "arn:aws:s3:::foobar",
                "statement": {
                    "Action": [
                        "s3:PutObject",
                        "s3:GetObject",
                        "ec2:DescribeInstances",
                    ],
                    "Resource": ["arn:aws:s3:::foobar", "arn:aws:s3:::foobar/*"],
                    "Effect": "Allow",
                },
                "expected": ["s3:PutObject", "s3:GetObject"],
                "description": "Statement with list Action and Resource",
            },
            {
                "arn": "arn:aws:s3:::foobar",
                "statement": {
                    "Action": "s3:PutObject",
                    "Resource": "arn:aws:s3:::foobar",
                    "Effect": "Allow",
                },
                "expected": ["s3:PutObject"],
                "description": "Statement with non-list Action and Resource",
            },
        ]

        for tc in test_cases:
            result = get_actions_for_resource(tc["arn"], tc["statement"])
            self.assertListEqual(tc["expected"], result, tc["description"])

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
                                    "Effect": "Allow",
                                },
                                {
                                    "Action": "s3:PutObject",
                                    "Resource": "arn:aws:s3:::bazbang",
                                    "Effect": "Allow",
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
            "bazbang": {
                "actions": ["s3:PutObject"],
                "arns": ["arn:aws:s3:::bazbang"],
                "account": "123456789012",
                "type": "s3",
                "region": "",
            },
        }
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(get_resources_from_events(policy_changes))
        self.assertDictEqual(expected, result)
