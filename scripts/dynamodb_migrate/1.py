# This migration script converts policy requests to V2 policy requests

import asyncio
import sys

from consoleme.lib.dynamo import UserDynamoHandler


async def migrate():
    # Get all policy requests
    # iterate through changes
    # if has principal_arn, convert
    dynamo = UserDynamoHandler("consoleme")
    requests = await dynamo.get_all_policy_requests(status=None)
    for request in requests:
        changes = (
            request.get("extended_request", {}).get("changes", {}).get("changes", [])
        )
        for change in changes:
            if not change.get("principal_arn"):
                continue
            change["principal"] = {
                "principal_arn": change["principal_arn"],
                "principal_type": "AwsResource",
            }
            change.pop("principal_arn")
    dynamo.parallel_write_table(dynamo.policy_requests_table, requests)


async def revert_migrate():
    # Get all policy requests
    # iterate through changes
    # if has principal, convert to principal_arn
    dynamo = UserDynamoHandler("consoleme")
    requests = await dynamo.get_all_policy_requests(status=None)
    print(requests)
    for request in requests:
        changes = (
            request.get("extended_request", {}).get("changes", {}).get("changes", [])
        )
        for change in changes:
            if not change.get("principal"):
                continue
            principal_arn = change["principal"].get("principal_arn")
            if not principal_arn:
                continue
            change["principal_arn"] = principal_arn
            change.pop("principal")
    dynamo.parallel_write_table(dynamo.policy_requests_table, requests)


if len(sys.argv) != 2 or sys.argv[1] not in ["migrate", "revert_migrate"]:
    raise Exception(
        "You must run this script with a single argument: `migrate`, or `revert_migrate`"
    )

if sys.argv[1] == "migrate":
    asyncio.run(migrate())
elif sys.argv[1] == "revert_migrate":
    asyncio.run(revert_migrate())
