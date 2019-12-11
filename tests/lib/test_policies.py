import asyncio
import random

from mock import patch
from tornado.testing import AsyncTestCase

from consoleme.config import config
from consoleme.lib.policies import should_auto_approve_policy


class TestPoliciesLibrary(AsyncTestCase):
    @patch("consoleme.lib.policies.zelkova")
    def test_should_auto_approve_policy(self, mock_zelkova):
        requested_policies = [
            {
                "policy": """"{
                          "Statement": [
                            {
                              "Action": [
                                "s3:ListBucket",
                                "s3:ListBucketVersions",
                                "s3:GetObject",
                                "s3:GetObjectTagging",
                                "s3:GetObjectVersion",
                                "s3:GetObjectVersionTagging",
                                "s3:GetObjectAcl",
                                "s3:GetObjectVersionAcl"
                              ],
                              "Effect": "Allow",
                              "Resource": [
                                "arn:aws:s3:::approve_all_requests_to_this_bucket",
                                "arn:aws:s3:::approve_all_requests_to_this_bucket/abc/*",
                              ]
                            }
                          ]
                        }
                        """,
                "approving_probe": "test_s3",
                "expected_result": {"approved": True, "approving_probe": "test_s3"},
            },
            {
                "policy": """"{
                                  "Statement": [
                                    {
                                      "Action": [
                                        "s3:ListBucket",
                                        "s3:ListBucketVersions",
                                        "s3:GetObject",
                                        "s3:GetObjectTagging",
                                        "s3:GetObjectVersion",
                                        "s3:GetObjectVersionTagging",
                                        "s3:GetObjectAcl",
                                        "s3:GetObjectVersionAcl"
                                      ],
                                      "Effect": "Allow",
                                      "Resource": [
                                        "arn:aws:s3:::dont_approve_this_bucket",
                                        "arn:aws:s3:::dont_approve_this_bucket/*"
                                      ]
                                    }
                                  ]
                                }
                                """,
                "expected_result": False,
            },
            {
                "policy": """"{
                                          "Statement": [
                                            {
                                              "Action": [
                                                "sqs:*"
                                              ],
                                              "Effect": "Allow",
                                              "Resource": [
                                                "*"
                                              ]
                                            }
                                          ]
                                        }
                                        """,
                "expected_result": False,
            },
            {
                "description": "test_same_account_sqs_approval",
                "policy": """"{
                                "Statement": [
                                  {
                                    "Action": [
                                      "sqs:GetQueueAttributes",
                                      "sqs:GetQueueUrl",
                                      "sqs:SendMessage",
                                      "sqs:ReceiveMessage",
                                      "sqs:DeleteMessage",
                                      "sqs:SetQueueAttributes"
                                    ],
                                    "Effect": "Allow",
                                    "Resource": [
                                      "arn:aws:sqs:*:123456789012:fake_queue"
                                    ]
                                  }
                                ]
                              }
                                                """,
                "approving_probe": "test_same_account_sqs",
                "expected_result": {
                    "approved": True,
                    "approving_probe": "test_same_account_sqs",
                },
            },
        ]
        for policy in requested_policies:
            zelkova_returns = []

            random_comparison = random.choice(["INCOMPARABLE", "MORE_PERMISSIVE"])
            for probe in config.get(
                "dynamic_config.policy_request_autoapprove_probes.probes", []
            ):
                if probe.get("name") == policy.get("approving_probe"):
                    zelkova_returns.append(
                        {"Items": [{"Comparison": "LESS_PERMISSIVE"}]}
                    )
                else:
                    zelkova_returns.append(
                        {"Items": [{"Comparison": random_comparison}]}
                    )

            mock_zelkova.compare_policies.side_effect = zelkova_returns

            events = [
                {
                    "arn": "arn:aws:iam::123456789012:role/testrole",
                    "inline_policies": [
                        {
                            "action": "attach",
                            "policy_name": "policy_name",
                            "policy_document": policy["policy"],
                        }
                    ],
                }
            ]
            result = asyncio.get_event_loop().run_until_complete(
                should_auto_approve_policy(
                    events, "user@example.com", ["groupa@example.com"]
                )
            )
            self.assertEqual(policy["expected_result"], result)
