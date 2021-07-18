import os

import boto3
import cfnresponse
import yaml

spoke_accounts_objects_dict = {}
spoke_accounts_objects_dict[os.getenv("ACCOUNT_NUMBER")] = [
    "account_" + os.getenv("ACCOUNT_NUMBER")
]
spoke_accounts_list = os.getenv("SPOKE_ACCOUNTS").split(",")

for account_id in spoke_accounts_list:
    spoke_accounts_objects_dict[str(account_id)] = ["account_" + account_id]

spoke_accounts_objects_list_yaml = yaml.dump(
    {"account_ids_to_name": spoke_accounts_objects_dict},
    explicit_start=False,
    default_flow_style=False,
    default_style="'",
)

s3_client = boto3.client("s3")


def handler(event, context):
    request_type = event["RequestType"]

    if request_type == "Create":
        return on_create(event, context)
    if request_type == "Update":
        return on_create(event, context)
    if request_type == "Delete":
        return on_delete(event, context)

    raise Exception("Invalid request type: %s" % request_type)


def on_create(event, context):
    with open("config.yaml") as f:
        config_yaml = f.read()

    config_yaml = config_yaml.format(
        issuer=os.getenv("ISSUER"),
        oidc_metadata_url=os.getenv("OIDC_METADATA_URL"),
        redis_host=os.getenv("REDIS_HOST"),
        aws_region=os.getenv("AWS_REGION"),
        ses_identity_arn=os.getenv("SES_IDENTITY_ARN"),
        support_chat_url=os.getenv("SUPPORT_CHAT_URL"),
        application_admin=os.getenv("APPLICATION_ADMIN"),
        account_number=os.getenv("ACCOUNT_NUMBER"),
        spoke_accounts_objects_list_yaml=spoke_accounts_objects_list_yaml,
        config_secret_name=os.getenv("CONFIG_SECRET_NAME"),
    )
    encoded_config = config_yaml.encode("utf-8")

    bucket_name = os.getenv("DEPLOYMENT_BUCKET")
    file_name = "config.yaml"
    s3_path = file_name

    try:
        result = s3_client.put_object(
            Bucket=bucket_name, Key=s3_path, Body=encoded_config
        )
        cfnresponse.send(event, context, cfnresponse.SUCCESS, result)
    except Exception as ex:
        cfnresponse.send(event, context, cfnresponse.FAILED, str(ex))


def on_delete(event, context):
    bucket_name = os.getenv("DEPLOYMENT_BUCKET")
    file_name = "config.yaml"
    s3_path = file_name

    try:
        result = s3_client.delete_object(Bucket=bucket_name, Key=s3_path)
        cfnresponse.send(event, context, cfnresponse.SUCCESS, result)
    except Exception as ex:
        cfnresponse.send(event, context, cfnresponse.FAILED, str(ex))
