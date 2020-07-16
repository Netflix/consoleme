import boto3
from botocore.exceptions import ClientError

from consoleme.config import config

ddb = boto3.client(
    "dynamodb", endpoint_url=config.get("dynamodb_server"), region_name="us-east-1"
)

response = ddb.list_tables()

try:
    ddb.create_table(
        TableName="consoleme_users_global",
        KeySchema=[{"AttributeName": "username", "KeyType": "HASH"}],  # Partition key
        AttributeDefinitions=[{"AttributeName": "username", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 10, "WriteCapacityUnits": 10},
    )
except ClientError as e:
    print(
        "Unable to create table consoleme_users_global. Most likely it already exists and you can ignore this message. Error: {}".format(
            e
        )
    )

try:
    ddb.create_table(
        TableName="consoleme_requests_global",
        KeySchema=[{"AttributeName": "request_id", "KeyType": "HASH"}],  # Partition key
        AttributeDefinitions=[{"AttributeName": "request_id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 10, "WriteCapacityUnits": 10},
    )
except ClientError as e:
    print(
        "Unable to create table consoleme_requests_global. Most likely it already exists and you can ignore this message. Error: {}".format(
            e
        )
    )

try:
    ddb.create_table(
        TableName="consoleme_audit_global",
        KeySchema=[
            {"AttributeName": "uuid", "KeyType": "HASH"},  # Partition key
            {"AttributeName": "group", "KeyType": "RANGE"},  # Sort key
        ],
        AttributeDefinitions=[
            {"AttributeName": "uuid", "AttributeType": "S"},
            {"AttributeName": "group", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 10, "WriteCapacityUnits": 10},
    )
except ClientError as e:
    print(
        "Unable to create table consoleme_audit_global. Most likely it already exists and you can ignore this message. Error: {}".format(
            e
        )
    )


try:
    ddb.create_table(
        TableName="consoleme_iamroles_global",
        AttributeDefinitions=[
            {"AttributeName": "arn", "AttributeType": "S"},
            {"AttributeName": "accountId", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "arn", "KeyType": "HASH"},
            {"AttributeName": "accountId", "KeyType": "RANGE"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 100, "WriteCapacityUnits": 100},
    )

    ddb.update_time_to_live(
        TableName="consoleme_iamroles_global",
        TimeToLiveSpecification={"Enabled": True, "AttributeName": "ttl"},
    )

except ClientError as e:
    print(
        "Unable to create table "
        f"consoleme_iamroles_global. Most likely it already exists and you can ignore this message. Error: {e}."
    )

try:
    ddb.create_table(
        TableName="consoleme_config_global",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],  # Partition key
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        ProvisionedThroughput={"ReadCapacityUnits": 10, "WriteCapacityUnits": 10},
    )
except ClientError as e:
    print(
        f"Unable to create table consoleme_config_global. Most likely it already exists and you can ignore this "
        f"message. Error: {e}"
    )

try:
    ddb.create_table(
        TableName="consoleme_policy_requests",
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
    )
except ClientError as e:
    print(
        f"Unable to create table consoleme_policy_requests  . Most likely it already exists and you can ignore this "
        f"message. Error: {e}"
    )

try:
    ddb.create_table(
        TableName="consoleme_resource_cache",
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
    )
except ClientError as e:
    print(
        f"Unable to create table consoleme_resource_cache  . Most likely it already exists and you can ignore this "
        f"message. Error: {e}"
    )
