import json

import pytest
from cloudaux.orchestration.aws.iam.role import get_role
from mock import MagicMock, mock, patch
from mockredis import mock_strict_redis_client

from consoleme.exceptions.exceptions import (
    NoRoleTemplateException,
    UserRoleLambdaException,
)


@pytest.mark.asyncio
async def test_cloudaux_to_aws(iam, iam_sync_roles, dynamodb):
    from consoleme_internal.plugins.aws.aws import init

    aws = init()

    # Get the get_account_authorization version of RoleNumber0: (located at position 1 after ConsoleMe)
    account_authorization_role = iam.get_account_authorization_details(Filter=["Role"])[
        "RoleDetailList"
    ][1]

    # Get the cloudaux version:
    cloudaux_role = get_role({"Arn": account_authorization_role["Arn"]})

    # Convert it:
    await aws._cloudaux_to_aws(cloudaux_role)

    # Verify that it's all there:
    account_authorization_role_json = json.dumps(
        account_authorization_role,
        sort_keys=True,
        default=aws.dynamo._json_encode_timestamps,
    )
    del cloudaux_role["Description"]
    cloudaux_role_json = json.dumps(
        cloudaux_role, sort_keys=True, default=aws.dynamo._json_encode_timestamps
    )

    assert account_authorization_role_json == cloudaux_role_json


@pytest.mark.asyncio
async def test_fetch_role_template(retry, user_iam_role, dynamodb, sts, iam):
    from consoleme.config.config import CONFIG
    from consoleme_internal.plugins.aws.aws import init
    from consoleme.lib.dynamo import IAMRoleDynamoHandler

    dynamo = IAMRoleDynamoHandler()
    # Set the config value for the redis cache location
    old_value = CONFIG.config["aws"].pop("iamroles_redis_key", None)
    CONFIG.config["aws"]["iamroles_redis_key"] = "test_fetch_role_template_cache"

    aws = init()

    mock_red = mock_strict_redis_client()

    mock_aws_red = patch.object(aws, "red", mock_red)
    mock_aws_red.start()

    role_arn = "arn:aws:iam::123456789012:role/roleName"

    role_entry = {
        "arn": role_arn,
        "name": role_arn.split("/")[1],
        "accountId": role_arn.split(":")[4],
        "ttl": 300,
        "policy": "{}",
        "templated": False,
    }

    # DynamoDB
    dynamo.sync_iam_role_for_account(role_entry)

    # Clear out the existing cache from Redis:
    aws.red.delete("test_fetch_role_template_cache")

    # And again -- this time it's in Redis:
    result = await aws.fetch_iam_role("123456789012", role_arn)
    assert result
    assert json.dumps(result["policy"])

    # Validate that it's in Redis:
    assert aws.red.hlen("test_fetch_role_template_cache") == 1
    assert aws.red.hget("test_fetch_role_template_cache", result["arn"])

    # Clear out the existing cache from Redis:
    aws.red.delete("test_fetch_role_template_cache")

    # And if it can't be found at all?
    dynamodb.delete_item(
        TableName="consoleme_iamroles_global",
        Key={"arn": {"S": role_arn}, "accountId": {"S": "123456789012"}},
    )

    items = dynamodb.scan(TableName="consoleme_iamroles_global")["Items"]
    for item in items:
        assert not item.get("arn", {}).get("S") == role_arn

    assert not await aws.fetch_iam_role("123456789012", role_arn)

    # Reset the config values:
    if not old_value:
        del CONFIG.config["aws"]["iamroles_redis_key"]
    else:
        CONFIG.config["aws"]["iamroles_redis_key"] = old_value

    mock_aws_red.stop()


@pytest.mark.asyncio
async def test_fetch_role_template_from_aws(retry, iamrole_table, sts, iam_sync_roles):
    from consoleme.config.config import CONFIG
    from consoleme_internal.plugins.aws.aws import init

    # Set the config value for the redis cache location
    old_value = CONFIG.config["aws"].pop("iamroles_redis_key", None)
    CONFIG.config["aws"][
        "iamroles_redis_key"
    ] = "test_fetch_role_template_cache_from_aws"

    aws = init()
    mock_red = mock_strict_redis_client()

    mock_aws_red = patch.object(aws, "red", mock_red)
    mock_aws_red.start()

    role_arn = "arn:aws:iam::123456789012:role/RoleNumber0"

    # Clear out the existing cache from Redis:
    aws.red.delete("test_fetch_role_template_cache_from_aws")

    # Try to find the role that exists in DDB, but does not exist in Redis:
    result = await aws.fetch_iam_role("123456789012", role_arn)
    assert result
    assert json.dumps(result["policy"])

    # Validate that it's in Redis:
    assert aws.red.hlen("test_fetch_role_template_cache_from_aws") == 1
    assert json.loads(
        aws.red.hget("test_fetch_role_template_cache_from_aws", result["arn"])
    )

    # Validate that it's in DynamoDB:
    assert (
        aws.dynamo.fetch_iam_role(role_arn, "123456789012")["Item"]["arn"] == role_arn
    )

    # Clear out the existing cache from Redis:
    aws.red.delete("test_fetch_role_template_cache_from_aws")

    # Reset the config values:
    if not old_value:
        del CONFIG.config["aws"]["iamroles_redis_key"]
    else:
        CONFIG.config["aws"]["iamroles_redis_key"] = old_value
    mock_aws_red.stop()


def _make_aws_with_mocked_redis_accountdata():
    from consoleme_internal.plugins.aws import aws as aws_plugin

    aws = aws_plugin.init()

    aws_plugin.redis_get_sync = MagicMock(
        return_value=json.dumps(
            {"123456789012": ["awsaccount", "awsaccount@example.com"]}
        )
    )

    aws.red.hget = MagicMock(return_value=None)
    aws.red.hset = MagicMock(return_value=None)

    return aws


@pytest.mark.asyncio
async def test_call_user_lambda(
    retry, iam, iamrole_table, sts, iam_sync_roles, user_role_lambda
):
    import consoleme_internal.plugins.aws.aws

    # Set the configuration region to us-east-1:
    old_conf_region = consoleme_internal.plugins.aws.aws.config.region
    consoleme_internal.plugins.aws.aws.config.region = "us-east-1"

    aws = _make_aws_with_mocked_redis_accountdata()

    # Mock out the result from the lambda function:
    mock_return = {
        "success": True,
        "role_name": "cm-123456789012-111111111111111111111",
        "account_number": "123456789012",
    }
    mock_moto = mock.patch(
        "moto.awslambda.models.LambdaFunction.invoke",
        lambda *args, **kwargs: json.dumps(mock_return),
    )
    mock_moto.start()

    result = await aws.call_user_lambda(
        f'arn:aws:iam::123456789012:role/{"1" * 21}',
        "someuser@example.com",
        "123456789012",
    )

    assert (
        result == "arn:aws:iam::123456789012:role/cm-123456789012-111111111111111111111"
    )

    # Test if the Lambda gives us a bad response:
    mock_return["success"] = False
    with pytest.raises(UserRoleLambdaException):
        await aws.call_user_lambda(
            f'arn:aws:iam::123456789012:role/{"1" * 21}',
            "someuser@example.com",
            "123456789012",
        )

    # Test if it's MISSING the response:
    del mock_return["success"]
    with pytest.raises(UserRoleLambdaException):
        await aws.call_user_lambda(
            f'arn:aws:iam::123456789012:role/{"1" * 21}',
            "someuser@example.com",
            "123456789012",
        )

    mock_moto.stop()

    # Now test if the role itself doesn't exist:
    iam.detach_role_policy(
        RoleName="awsaccount_user",
        PolicyArn="arn:aws:iam::123456789012:policy/policy-one",
    )
    iam.delete_role_policy(RoleName="awsaccount_user", PolicyName="SomePolicy")
    iam.delete_role(RoleName="awsaccount_user")
    iamrole_table.delete_item(
        TableName="consoleme_iamroles_global",
        Key={
            "arn": {"S": "arn:aws:iam::123456789012:role/awsaccount_user"},
            "accountId": {"S": "123456789012"},
        },
    )

    with pytest.raises(NoRoleTemplateException):
        await aws.call_user_lambda(
            f'arn:aws:iam::123456789012:role/{"1" * 21}',
            "someuser@example.com",
            "123456789012",
        )

    # Cleanup:
    consoleme_internal.plugins.aws.aws.config.region = old_conf_region
