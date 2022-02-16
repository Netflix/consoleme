import sentry_sdk
import tornado.escape
import tornado.web
import ujson as json
from asgiref.sync import sync_to_async
from marshmallow import Schema, ValidationError, fields, validates_schema

from consoleme.config import config
from consoleme.exceptions.exceptions import CertTooOldException
from consoleme.handlers.base import BaseMtlsHandler
from consoleme.lib.account_indexers import get_cloud_account_model_array
from consoleme.lib.duo import duo_mfa_user
from consoleme.lib.plugins import get_plugin_by_name
from consoleme.models import Environment

stats = get_plugin_by_name(config.get("plugins.metrics", "default_metrics"))()
log = config.get_logger()
aws = get_plugin_by_name(config.get("plugins.aws", "default_aws"))()
internal_config = config.config_plugin
auth = get_plugin_by_name(config.get("plugins.auth", "default_auth"))()
group_mapping = get_plugin_by_name(
    config.get("plugins.group_mapping", "default_group_mapping")
)()
internal_policies = get_plugin_by_name(
    config.get("plugins.internal_policies", "default_policies")
)()


class CredentialsSchema(Schema):
    requested_role = fields.Str()
    user_role = fields.Boolean(default=False, missing=False)
    app_name = fields.Str()
    account = fields.Str()
    console_only = fields.Boolean(default=False, missing=False)
    no_ip_restrictions = fields.Boolean(default=False, missing=False)
    custom_ip_restrictions = fields.List(fields.Str(), required=False)

    @validates_schema
    def validate_minimum(self, data, *args, **kwargs):
        """Validate that the minimum fields are supplied."""
        if (
            not data.get("requested_role")
            and not data.get("user_role")
            and not data.get("app_name")
        ):
            raise ValidationError(
                "Must supply either a requested_role, or a user_role/account combo, or an app_name."
            )

        return data

    @validates_schema
    def validate_dynamic_role_request(self, data, *args, **kwargs):
        if data.get("user_role"):
            if data.get("requested_role"):
                raise ValidationError(
                    "Cannot specify both a requested_role and user_role."
                )

            if not data.get("account"):
                raise ValidationError("Must specify an account.")

        return data

    @validates_schema
    def validate_app_name_request(self, data, *args, **kwargs):
        """Validate that if an app name is provided, then a requested role / user role aren't specified"""
        if data.get("app_name"):
            if data.get("requested_role") or data.get("user_role"):
                raise ValidationError(
                    "Cannot specify requested_role/user_role and an app name."
                )

        return data


credentials_schema = CredentialsSchema()


class GetCredentialsHandler(BaseMtlsHandler):
    """Main consoleme api handler."""

    def check_xsrf_cookie(self):
        pass

    def initialize(self):
        self.user = None
        self.eligible_roles = []

    async def raise_if_certificate_too_old(self, role, log_data=None):
        log_data = {} if not log_data else log_data
        try:
            max_cert_age = await group_mapping.get_max_cert_age_for_role(role)
            max_cert_age_message = config.get(
                "errors.custom_max_cert_age_message", "Please refresh your certificate."
            )
        except Exception as e:
            sentry_sdk.capture_exception()
            log_data["error"] = e
            log_data[
                "message"
            ] = "Failed to get max MTLS certificate age. Returning default value of 1 day"
            max_cert_age = 1  # Default to one day expiration if we fail to get max certificate age info
        max_cert_age_seconds = max_cert_age * (24 * 60 * 60)  # Seconds in a day
        try:
            if self.current_cert_age > max_cert_age_seconds:
                raise CertTooOldException(
                    f"MTLS certificate is too old. The role you selected requires a max cert "
                    f"age of {max_cert_age} days. "
                    f"{max_cert_age_message}"
                )
        except CertTooOldException as e:
            log_data["message"] = "Unable to get credentials for user"
            log_data["eligible_roles"] = self.eligible_roles
            log.warning(log_data, exc_info=True)
            stats.count(
                "GetCredentialsHandler.post.exception",
                tags={"user": self.user, "requested_role": role, "authorized": False},
            )
            error = {
                "code": "905",
                "message": (
                    f"MTLS certificate is too old. {max_cert_age_message}. "
                    f"Max cert age for {role} is {max_cert_age} days."
                ),
                "requested_role": role,
                "exception": str(e),
                "request_id": self.request_uuid,
            }
            self.set_status(403)
            self.write(error)
            await self.finish()
            raise

    async def _get_the_requested_role(self, request: dict, log_data: dict) -> str:
        """Get the requested role to complete the credentials fetching."""
        if request.get("requested_role"):
            return request["requested_role"]
        elif request.get("app_name"):
            role_models = await internal_policies.get_roles_associated_with_app(
                request["app_name"]
            )
            if not role_models:
                stats.count(
                    "GetCredentialsHandler.post",
                    tags={
                        "user": self.user,
                        "user_role": False,
                        "app_name": request["app_name"],
                    },
                )
                log_data["message"] = "No matching roles for provided app name."
                log.warning(log_data)
                error = {
                    "code": "900",
                    "message": "No matching roles for provided app name.",
                    "request_id": self.request_uuid,
                }
                self.set_status(400)
                self.write(error)
                await self.finish()
                return ""

            account_ids = set()
            # If an account was passed into this function, we can use that
            if "account" in request:
                am = await group_mapping.get_account_mappings()
                if request["account"] in am["ids_to_names"].keys():
                    # Account ID was passed in directly
                    account_ids.add(request["account"])
                else:
                    # Might be a friendly name, have to check
                    if not am["names_to_ids"].get(request["account"]):
                        stats.count(
                            "GetCredentialsHandler.post.error",
                            tags={
                                "user": self.user,
                                "user_role": False,
                                "account": request["account"],
                            },
                        )
                        log_data["message"] = "Can't find the passed in account."
                        log.warning(log_data)
                        error = {
                            "code": "906",
                            "message": "No matching account for provided account.",
                            "request_id": self.request_uuid,
                        }
                        self.set_status(400)
                        self.write(error)
                        await self.finish()
                        return ""

                    account_ids.add(am["names_to_ids"][request["account"]])

            if not account_ids:
                # no account id was passed in, check to see if we can "smartly" determine the account.
                # Preference will be given to test accounts
                filtered_accounts = await get_cloud_account_model_array(
                    environment=Environment.test.value
                )
                # convert to set for O(1) lookup
                for account in filtered_accounts.accounts:
                    account_ids.add(account.id)

            potential_arns = []
            # for all roles associated with app, find the one that is also an account in potential account ids
            for role in role_models:
                if role.account_id in account_ids:
                    potential_arns.append(role.arn)

            if len(potential_arns) != 1:
                # if length isn't exactly 1, then it's an error either way (0 or more than 1)
                if len(potential_arns) == 0:
                    code = "900"
                    message = "No matching roles"
                else:
                    code = "901"
                    message = "More than one matching role"

                stats.count(
                    "GetCredentialsHandler.post.error",
                    tags={
                        "user": self.user,
                        "user_role": False,
                    },
                )
                log_data["message"] = message
                log.warning(log_data)
                error = {
                    "code": code,
                    "message": message,
                    "request_id": self.request_uuid,
                }
                self.set_status(400)
                self.write(error)
                await self.finish()
                return ""

            # if here, then success, we found exactly 1 ARN
            return potential_arns[0]

        else:
            # Check that the account exists:
            am = await group_mapping.get_account_mappings()

            # First, check if an account ID was passed in:
            if request["account"] in am["ids_to_names"].keys():
                account_id = request["account"]

            # If it was a "friendly" name, then get the account ID for it.
            else:
                # Was this a bogus name?
                if not am["names_to_ids"].get(request["account"]):
                    stats.count(
                        "GetCredentialsHandler.post",
                        tags={
                            "user": self.user,
                            "user_role": True,
                            "account": request["account"],
                        },
                    )
                    log_data["message"] = "Can't find the passed in account."
                    log.warning(log_data)
                    error = {
                        "code": "906",
                        "message": "No matching account.",
                        "account": request["account"],
                        "request_id": self.request_uuid,
                    }
                    self.set_status(400)
                    self.write(error)
                    await self.finish()
                    return ""

                account_id = am["names_to_ids"][request["account"]]

            # Shove the account ID into the request:
            request["account_id"] = account_id

            return f"arn:aws:iam::{account_id}:role/{self.user_role_name}"

    async def post(self):
        """/api/v1/get_credentials - Endpoint used to get credentials via mtls. Used by newt and weep.
        ---
        get:
            description: Credentials endpoint. Authenticates user via MTLS and returns requested credentials.
            responses:
                200:
                    description: Returns credentials or list of matching roles
                403:
                    description: No matching roles found, or user has failed authn/authz.
        """
        log_data = {
            "function": "GetCredentialsHandler.post",
            "user-agent": self.request.headers.get("User-Agent"),
            "request_id": self.request_uuid,
        }

        # Validate the input:
        data = tornado.escape.json_decode(self.request.body)
        try:
            request = await sync_to_async(credentials_schema.load)(data)
        except ValidationError as ve:
            stats.count(
                "GetCredentialsHandler.post",
                tags={"user": self.user, "validation_error": str(ve)},
            )

            log_data["validation_error"]: ve.messages
            log.error(log_data)

            error = {
                "code": "904",
                "message": f"Invalid JSON sent to the server:\n{json.dumps(ve.messages, indent=2)}",
                "request_id": self.request_uuid,
            }
            self.set_status(400)
            self.write(error)
            await self.finish()
            return
        requester_type = self.requester.get("type")

        if requester_type == "application":
            app_name = self.requester.get("name")
            await self.get_credentials_app_flow(
                app_name, self.requester, request, log_data
            )
        elif requester_type == "user":
            user_email = self.requester.get("email")
            await self.get_credentials_user_flow(user_email, request, log_data)
        else:
            raise tornado.web.HTTPError(403, "Unauthorized entity.")
        return

    async def get_credentials_app_flow(self, app_name, app, request, log_data):
        requested_role = request["requested_role"]
        log_data["requested_role"] = requested_role
        log_data["app"] = app_name
        log_data["message"] = "App is requesting role"
        log_data["custom_ip_restrictions"] = request.get("custom_ip_restrictions")
        log_data["request"] = json.dumps(request)
        log.debug(log_data)
        arn_parts = requested_role.split(":")
        if (
            len(arn_parts) != 6
            or arn_parts[0] != "arn"
            or arn_parts[1] != "aws"
            or arn_parts[2] != "iam"
        ):
            log_data["message"] = "Invalid Role ARN"
            log.warning(log_data)
            error = {
                "code": "899",
                "message": "Invalid Role ARN. Applications must pass the full role ARN when requesting credentials",
                "requested_role": requested_role,
            }
            self.set_status(403)
            self.write(error)
            await self.finish()
            return
        # Check if role is valid ARN
        authorized = await internal_config.is_context_authorized(app, requested_role)

        stats.count(
            "GetCredentialsHandler.post",
            tags={
                "user": app_name,
                "requested_role": requested_role,
                "authorized": authorized,
            },
        )

        if not authorized:
            log_data["message"] = "Unauthorized"
            log.warning(log_data)
            error = {
                "code": "900",
                "message": "Unauthorized",
                "requested_role": requested_role,
            }
            self.set_status(403)
            self.write(error)
            await self.finish()
            return

        credentials = await aws.get_credentials(
            app_name,
            requested_role,
            enforce_ip_restrictions=False,
            user_role=False,
            account_id=None,
            custom_ip_restrictions=request.get("custom_ip_restrictions"),
        )
        self.set_header("Content-Type", "application/json")
        credentials.pop("ResponseMetadata", None)
        credentials.pop("AssumedRoleUser", None)
        credentials.pop("PackedPolicySize", None)
        # Need to use ujson here because the credentials contain a datetime element
        self.write(json.dumps(credentials))
        await self.finish()
        return

    async def get_credentials_user_flow(self, user_email, request, log_data):
        log_data["user"] = user_email

        await self.authorization_flow(
            user=user_email, console_only=request["console_only"]
        )
        # Get the role to request:
        requested_role = await self._get_the_requested_role(request, log_data)
        if not requested_role:
            raise tornado.web.HTTPError(403, "No requested role detected.")
        log_data["requested_role"] = requested_role

        log_data["message"] = "User is requesting role"
        log.debug(log_data)
        matching_roles = await group_mapping.filter_eligible_roles(requested_role, self)

        log_data["matching_roles"] = matching_roles

        if len(matching_roles) == 0:
            stats.count(
                "GetCredentialsHandler.post",
                tags={"user": self.user, "requested_role": None, "authorized": False},
            )
            log_data["message"] = "No matching roles"
            log.warning(log_data)
            error = {
                "code": "900",
                "message": "No matching roles",
                "requested_role": requested_role,
                "request_id": self.request_uuid,
            }
            self.set_status(403)
            self.write(error)
            return
        if len(matching_roles) > 1:
            stats.count(
                "GetCredentialsHandler.post",
                tags={"user": self.user, "requested_role": None, "authorized": False},
            )
            log_data["message"] = "More than one matching role"
            log.warning(log_data)
            error = {
                "code": "901",
                "message": log_data["message"],
                "requested_role": requested_role,
                "matching roles": matching_roles,
                "request_id": self.request_uuid,
            }
            self.set_status(403)
            self.write(error)
            return
        if len(matching_roles) == 1:
            await self.raise_if_certificate_too_old(matching_roles[0], log_data)
            try:
                enforce_ip_restrictions = True
                if request["no_ip_restrictions"]:
                    # Duo prompt the user in order to get non IP-restricted credentials
                    mfa_success = await duo_mfa_user(
                        self.user.split("@")[0],
                        message="ConsoleMe Non-IP Restricted Credential Request",
                    )

                    if mfa_success:
                        enforce_ip_restrictions = False
                        stats.count(
                            "GetCredentialsHandler.post.no_ip_restriction.success",
                            tags={"user": self.user, "requested_role": requested_role},
                        )
                        log_data[
                            "message"
                        ] = "User requested non-IP-restricted credentials"
                        log.debug(log_data)
                    else:
                        # Log and emit a metric
                        log_data["message"] = "MFA Denied or Timeout"
                        log.warning(log_data)
                        stats.count(
                            "GetCredentialsHandler.post.no_ip_restriction.failure",
                            tags={"user": self.user, "requested_role": requested_role},
                        )
                        error = {
                            "code": "902",
                            "message": "MFA Not Successful",
                            "requested_role": requested_role,
                            "request_id": self.request_uuid,
                        }
                        self.set_status(403)
                        self.write(error)
                        await self.finish()
                        return

                log_data["enforce_ip_restrictions"] = enforce_ip_restrictions
                log_data["message"] = "Retrieving credentials"
                log.debug(log_data)

                # User-role logic:
                # User-role should come in as cm-[username or truncated username]_[N or NC]
                user_role = False
                account_id = None

                # User role must be in user's attributes
                if (
                    self.user_role_name
                    and matching_roles[0].split("role/")[1] == self.user_role_name
                ):
                    user_role = True
                    account_id = (
                        matching_roles[0].split("arn:aws:iam::")[1].split(":role")[0]
                    )

                credentials = await aws.get_credentials(
                    self.user,
                    matching_roles[0],
                    enforce_ip_restrictions=enforce_ip_restrictions,
                    user_role=user_role,
                    account_id=account_id,
                )
            except Exception as e:
                log_data["message"] = "Unable to get credentials for user"
                log_data["eligible_roles"] = self.eligible_roles
                log.error(log_data, exc_info=True)
                stats.count(
                    "GetCredentialsHandler.post.exception",
                    tags={
                        "user": self.user,
                        "requested_role": requested_role,
                        "authorized": False,
                    },
                )
                error = {
                    "code": "902",
                    "message": "Unable to get credentials.",
                    "requested_role": requested_role,
                    "matching_role": matching_roles[0],
                    "exception": str(e),
                    "request_id": self.request_uuid,
                }
                self.set_status(403)
                self.write(error)
                await self.finish()
                return
        if not credentials:
            log_data["message"] = "Unauthorized or invalid role"
            log.warning(log_data)
            stats.count(
                "GetCredentialsHandler.post.unauthorized",
                tags={
                    "user": self.user,
                    "requested_role": requested_role,
                    "authorized": False,
                },
            )
            error = {
                "code": "903",
                "message": "Requested role not found in eligible roles",
                "requested_role": requested_role,
                "eligible roles": self.eligible_roles,
                "request_id": self.request_uuid,
            }
            self.write(error)
            await self.finish()
            return
        else:
            log_data["message"] = "Success. Returning credentials"
            log.debug(log_data)
            stats.count(
                "GetCredentialsHandler.post.success",
                tags={
                    "user": self.user,
                    "requested_role": requested_role,
                    "authorized": True,
                },
            )
            credentials.pop("ResponseMetadata", None)
            credentials.pop("AssumedRoleUser", None)
            credentials.pop("PackedPolicySize", None)
            self.write(json.dumps(credentials))
            self.set_header("Content-Type", "application/json")
            await self.finish()
            return
