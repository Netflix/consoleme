import sys

import boto3
import ujson as json
from asgiref.sync import sync_to_async
from botocore.exceptions import ClientError

from consoleme.config import config
from consoleme.lib.plugins import get_plugin_by_name

stats = get_plugin_by_name(config.get("plugins.metrics", "default_metrics"))()
log = config.get_logger()


async def duo_mfa_user(username, message="ConsoleMe Authorization Request"):
    """Send a DUO mfa push request to user."""
    # Create session for the region deployed in.
    session = boto3.Session(region_name=config.region)

    # Create lambda client
    client = session.client("lambda")

    # Generate the payload for the event passed to the lambda function
    payload = {"username": username, "message_type": message}

    lambda_arn = config.get("duo.lambda_arn", None)

    log_data = {"function": f"{__name__}.{sys._getframe().f_code.co_name}"}

    if lambda_arn:
        try:
            # Invoke the Lambda Function that will send a DUO Push to the user
            response = await sync_to_async(client.invoke)(
                FunctionName=lambda_arn.format(config.region),
                InvocationType="RequestResponse",
                Payload=bytes(json.dumps(payload), "utf-8"),
            )

            stats.count("duo.mfa_request", tags={"user": username})
        except ClientError as e:
            log_data["error"] = e.response.get("Error", {}).get(
                "Message", "Unknown error in Duo Lambda invoke"
            )
            log.error(log_data, exc_info=True)
            # We had an error so we should deny this request
            return False

        log_data["message"] = "Duo MFA request sent to {}".format(username)

        log.info(log_data)

        # Decode and return the result
        return await decode_duo_response_from_lambda(response, username)


async def decode_duo_response_from_lambda(response, username):
    """Decode the response from the Duo lambda."""
    result = json.loads(response["Payload"].read().decode("utf-8"))
    if not result:
        return False
    if result.get("duo_auth", "") == "success":
        stats.count("duo.mfa_request.approve", tags={"user": username})
        return True
    stats.count("duo.mfa_request.deny", tags={"user": username})
    return False
