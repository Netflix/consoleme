import asyncio
from unittest import TestCase

import ujson as json
from mock import MagicMock, patch

from tests.conftest import create_future

mock_aws_config_resources_redis = MagicMock(
    return_value=create_future(json.dumps({"accountId": "123456789012"}))
)


class TestPoliciesLib(TestCase):
    def test_get_actions_for_resource(self):
        from consoleme.lib.policies import get_actions_for_resource

        test_cases = [
            {
                "arn": "arn:aws:s3:::foobar",
                "statement": {
                    "Action": ["s3:PutObject", "s3:GetObject", "ec2:DescribeInstances"],
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

    @patch("consoleme.lib.aws.redis_hget", mock_aws_config_resources_redis)
    def test_get_resources_from_events(self):
        from consoleme.lib.policies import get_resources_from_events

        policy_changes = [
            {
                "inline_policies": [
                    {
                        "policy_document": {
                            "Statement": [
                                # Most common structure, with an added non-s3 action.
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
                                # Make sure we properly handle non-list actions and resources.
                                {
                                    "Action": "s3:PutObject",
                                    "Resource": "arn:aws:s3:::bazbang",
                                    "Effect": "Allow",
                                },
                                # Wildcard actions should show up in results.
                                {
                                    "Action": "*",
                                    "Resource": "arn:aws:s3:::bangbar",
                                    "Effect": "Allow",
                                },
                                # Partial wildcard actions should show up in results.
                                {
                                    "Action": "s3:Get*",
                                    "Resource": "arn:aws:s3:::heewon",
                                    "Effect": "Allow",
                                },
                                # Wildcard resource ARN shouldn't show up in results.
                                {"Action": "*", "Resource": "*", "Effect": "Allow"},
                                # Wildcard resource name shouldn't show up in results.
                                {
                                    "Action": "s3:PutObject",
                                    "Resource": "arn:aws:s3:::*",
                                    "Effect": "Allow",
                                },
                            ]
                        }
                    }
                ]
            }
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
            "bangbar": {
                "actions": ["*"],
                "arns": ["arn:aws:s3:::bangbar"],
                "account": "123456789012",
                "type": "s3",
                "region": "",
            },
            "heewon": {
                "actions": ["s3:Get*"],
                "arns": ["arn:aws:s3:::heewon"],
                "account": "123456789012",
                "type": "s3",
                "region": "",
            },
        }
        self.maxDiff = None
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(get_resources_from_events(policy_changes))
        self.assertDictEqual(expected, result)
