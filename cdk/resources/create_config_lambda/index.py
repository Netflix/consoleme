import os
import re
import logging
import boto3
import cfnresponse
import yaml

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client("s3")


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if value is None:
        raise ValueError(f"Missing required env var: {name}")
    return value


def _validate_account_id(account_id: str) -> str:
    if not re.fullmatch(r"\d{12}", account_id):
        raise ValueError(f"Invalid AWS account ID: {account_id}")
    return account_id


def _build_spoke_accounts_mapping():
    primary_account = _validate_account_id(_require_env("ACCOUNT_NUMBER"))

    mapping = {
        primary_account: [f"account_{primary_account}"]
    }

    spoke_accounts_raw = os.getenv("SPOKE_ACCOUNTS", "").strip()
    if spoke_accounts_raw:
        for acc in spoke_accounts_raw.split(","):
            acc = acc.strip()
            if not acc:
                continue
            acc = _validate_account_id(acc)
            mapping[acc] = [f"account_{acc}"]

    return mapping


def handler(event, context):
    request_type = event.get("RequestType")

    if request_type in ("Create", "Update"):
        return on_create(event, context)
    if request_type == "Delete":
        return on_delete(event, context)

    raise Exception(f"Invalid request type: {request_type}")


def on_create(event, context):
    try:
        with open("config.yaml", "r", encoding="utf-8") as f:
            template = f.read()

        spoke_accounts_objects_dict = _build_spoke_accounts_mapping()


        spoke_accounts_objects_list_yaml = yaml.safe_dump(
            {"account_ids_to_name": spoke_accounts_objects_dict},
            default_flow_style=False,
            sort_keys=False,
        ).rstrip()

        replacements = {
            "{issuer}": _require_env("ISSUER"),
            "{oidc_metadata_url}": _require_env("OIDC_METADATA_URL"),
            "{redis_host}": _require_env("REDIS_HOST"),
            "{aws_region}": _require_env("AWS_REGION"),
            "{ses_identity_arn}": _require_env("SES_IDENTITY_ARN"),
            "{support_chat_url}": _require_env("SUPPORT_CHAT_URL"),
            "{application_admin}": _require_env("APPLICATION_ADMIN"),
            "{account_number}": _require_env("ACCOUNT_NUMBER"),
            "{config_secret_name}": _require_env("CONFIG_SECRET_NAME"),
            "{spoke_accounts_objects_list_yaml}": spoke_accounts_objects_list_yaml,
        }

        config_yaml = template
        for key, value in replacements.items():
            config_yaml = config_yaml.replace(key, value)

        bucket_name = _require_env("DEPLOYMENT_BUCKET")

        result = s3_client.put_object(
            Bucket=bucket_name,
            Key="config.yaml",
            Body=config_yaml.encode("utf-8"),
            ServerSideEncryption="aws:kms",  # safe even if bucket enforces SSE
        )

        cfnresponse.send(event, context, cfnresponse.SUCCESS, result)

    except Exception as ex:
        logger.exception("Create/Update failed")
        cfnresponse.send(event, context, cfnresponse.FAILED, "Internal error")


def on_delete(event, context):
    try:
        bucket_name = _require_env("DEPLOYMENT_BUCKET")

        result = s3_client.delete_object(
            Bucket=bucket_name,
            Key="config.yaml",
        )

        cfnresponse.send(event, context, cfnresponse.SUCCESS, result)

    except Exception as ex:
        logger.exception("Delete failed")
        cfnresponse.send(event, context, cfnresponse.FAILED, "Internal error")
