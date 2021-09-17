import boto3
from botocore.exceptions import ClientError
from tenacity import Retrying, retry_if_exception_type, stop_after_attempt, wait_fixed

from consoleme.config import config

ddb = boto3.client(
    "dynamodb",
    endpoint_url=config.get(
        "dynamodb_server", config.get("boto3.client_kwargs.endpoint_url")
    ),
    region_name=config.region,
)

table_name = "consoleme_iamroles_global"
try:
    ddb.create_table(
        TableName=table_name,
        AttributeDefinitions=[
            {"AttributeName": "arn", "AttributeType": "S"},
            {"AttributeName": "accountId", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "arn", "KeyType": "HASH"},
            {"AttributeName": "accountId", "KeyType": "RANGE"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 100, "WriteCapacityUnits": 100},
        StreamSpecification={
            "StreamEnabled": True,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
    )

    try:
        for attempt in Retrying(
            stop=stop_after_attempt(3),
            wait=wait_fixed(3),
            retry=retry_if_exception_type(
                (
                    ddb.exceptions.ResourceNotFoundException,
                    ddb.exceptions.ResourceInUseException,
                )
            ),
        ):
            with attempt:
                ddb.update_time_to_live(
                    TableName=table_name,
                    TimeToLiveSpecification={"Enabled": True, "AttributeName": "ttl"},
                )
    except ClientError as e:
        if str(e) != (
            "An error occurred (ValidationException) when calling the UpdateTimeToLive operation: "
            "TimeToLive is already enabled"
        ):
            print(f"Unable to update TTL attribute on table {table_name}. Error: {e}.")

except ClientError as e:
    if str(e) != (
        "An error occurred (ResourceInUseException) when calling the CreateTable operation: "
        "Cannot create preexisting table"
    ):
        print(f"Unable to create table {table_name}. Error: {e}.")

table_name = "consoleme_config_global"
try:
    ddb.create_table(
        TableName="consoleme_config_global",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],  # Partition key
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 10, "WriteCapacityUnits": 10},
        StreamSpecification={
            "StreamEnabled": True,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
    )
except ClientError as e:
    if str(e) != (
        "An error occurred (ResourceInUseException) when calling the CreateTable operation: "
        "Cannot create preexisting table"
    ):
        print(f"Unable to create table {table_name}. Error: {e}.")

table_name = "consoleme_policy_requests"
try:
    ddb.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "request_id", "KeyType": "HASH"}],  # Partition key
        AttributeDefinitions=[
            {"AttributeName": "request_id", "AttributeType": "S"},
            {"AttributeName": "arn", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "arn-request_id-index",
                "KeySchema": [{"AttributeName": "arn", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 123,
                    "WriteCapacityUnits": 123,
                },
            }
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 10, "WriteCapacityUnits": 10},
        StreamSpecification={
            "StreamEnabled": True,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
    )
except ClientError as e:
    if str(e) != (
        "An error occurred (ResourceInUseException) when calling the CreateTable operation: "
        "Cannot create preexisting table"
    ):
        print(f"Unable to create table {table_name}. Error: {e}.")

table_name = "consoleme_resource_cache"
try:
    ddb.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "resourceId", "KeyType": "HASH"},
            {"AttributeName": "resourceType", "KeyType": "RANGE"},  # Sort key
        ],  # Partition key
        AttributeDefinitions=[
            {"AttributeName": "resourceId", "AttributeType": "S"},
            {"AttributeName": "resourceType", "AttributeType": "S"},
            {"AttributeName": "arn", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "arn-index",
                "KeySchema": [{"AttributeName": "arn", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 123,
                    "WriteCapacityUnits": 123,
                },
            }
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 10, "WriteCapacityUnits": 10},
        StreamSpecification={
            "StreamEnabled": True,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
    )
except ClientError as e:
    if str(e) != (
        "An error occurred (ResourceInUseException) when calling the CreateTable operation: "
        "Cannot create preexisting table"
    ):
        print(f"Unable to create table {table_name}. Error: {e}.")

table_name = "consoleme_cloudtrail"
try:
    ddb.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "arn", "KeyType": "HASH"},  # Partition key
            {"AttributeName": "request_id", "KeyType": "RANGE"},  # Sort key
        ],
        AttributeDefinitions=[
            {"AttributeName": "arn", "AttributeType": "S"},
            {"AttributeName": "request_id", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 10, "WriteCapacityUnits": 10},
        StreamSpecification={
            "StreamEnabled": True,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
    )
    try:
        for attempt in Retrying(
            stop=stop_after_attempt(3),
            wait=wait_fixed(3),
            retry=retry_if_exception_type(
                (
                    ddb.exceptions.ResourceNotFoundException,
                    ddb.exceptions.ResourceInUseException,
                )
            ),
        ):
            with attempt:
                ddb.update_time_to_live(
                    TableName=table_name,
                    TimeToLiveSpecification={"Enabled": True, "AttributeName": "ttl"},
                )
    except ClientError as e:
        if str(e) != (
            "An error occurred (ValidationException) when calling the UpdateTimeToLive operation: "
            "TimeToLive is already enabled"
        ):
            print(f"Unable to update TTL attribute on table {table_name}. Error: {e}.")
except ClientError as e:
    if str(e) != (
        "An error occurred (ResourceInUseException) when calling the CreateTable operation: "
        "Cannot create preexisting table"
    ):
        print(f"Unable to create table {table_name}. Error: {e}.")

try:
    table_name = "consoleme_users_global"
    ddb.create_table(
        TableName=table_name,
        KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],  # Partition key
        AttributeDefinitions=[{"AttributeName": "username", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
        StreamSpecification={
            "StreamEnabled": True,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
    )
except ClientError as e:
    if str(e) != (
        "An error occurred (ResourceInUseException) when calling the CreateTable operation: "
        "Cannot create preexisting table"
    ):
        print(f"Unable to create table {table_name}. Error: {e}.")


table_name = "consoleme_notifications"
try:
    ddb.create_table(
        TableName=table_name,
        AttributeDefinitions=[
            {"AttributeName": "predictable_id", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "predictable_id", "KeyType": "HASH"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 100, "WriteCapacityUnits": 100},
        StreamSpecification={
            "StreamEnabled": True,
            "StreamViewType": "NEW_AND_OLD_IMAGES",
        },
    )

except ClientError as e:
    if str(e) != (
        "An error occurred (ResourceInUseException) when calling the CreateTable operation: "
        "Cannot create preexisting table"
    ):
        print(f"Unable to create table {table_name}. Error: {e}.")
