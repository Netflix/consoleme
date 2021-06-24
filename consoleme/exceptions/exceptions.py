"""Custom exceptions."""
import tornado.web

from consoleme.config import config
from consoleme.lib.plugins import get_plugin_by_name

log = config.get_logger("consoleme")
stats = get_plugin_by_name(config.get("plugins.metrics", "default_metrics"))()


class BaseException(Exception):
    def __init__(self, msg: str = "") -> None:
        self.msg = msg
        log.error(msg)  # use your logging things here
        stats.count(
            "baseexception",
            tags={"exception": str(self.__class__.__name__), "msg": msg},
        )
        super().__init__(msg)

    def __str__(self):
        """Stringifies the message."""
        return self.msg


class WebAuthNError(tornado.web.HTTPError):
    """Authentication Error"""

    def __init__(self, **kwargs):
        kwargs["status_code"] = 401
        super().__init__(**kwargs)


class MissingDataException(BaseException):
    """MissingDataException."""

    def __init__(self, msg=""):
        stats.count("MissingDataException")
        super().__init__(msg)


class InvalidCertificateException(BaseException):
    """InvalidCertificateException."""

    def __init__(self, msg=""):
        stats.count("InvalidCertificateException")
        super().__init__(msg)


class MissingCertificateException(BaseException):
    """MissingCertificateException."""

    def __init__(self, msg=""):
        stats.count("MissingCertificateException")
        super().__init__(msg)


class NoUserException(BaseException):
    """NoUserException."""

    def __init__(self, msg=""):
        stats.count("NoUserException")
        super().__init__(msg)


class NoGroupsException(BaseException):
    """NoGroupsException."""

    def __init__(self, msg=""):
        stats.count("NoGroupsException")
        super().__init__(msg)


class PendingRequestAlreadyExists(BaseException):
    """Pending request already exists for user."""

    def __init__(self, msg=""):
        stats.count("PendingRequestAlreadyExists")
        super().__init__(msg)


class NoExistingRequest(BaseException):
    """No existing request exists for user."""

    def __init__(self, msg=""):
        stats.count("NoExistingRequest")
        super().__init__(msg)


class CertTooOldException(BaseException):
    """MTLS Certificate is too old, despite being valid."""

    def __init__(self, msg=""):
        stats.count("CertTooOldException")
        super().__init__(msg)


class NotAMemberException(BaseException):
    """User is not a member of a group they are being removed from."""

    def __init__(self, msg: str = "") -> None:
        stats.count("NotAMemberException")
        super().__init__(msg)


class NoCredentialSubjectException(BaseException):
    """Unable to find credential subject for domain."""

    def __init__(self, msg=""):
        stats.count("NoCredentialSubjectException")
        super().__init__(msg)


class BackgroundCheckNotPassedException(BaseException):
    """User does not have a background check where one is required."""

    def __init__(self, msg=""):
        stats.count("BackgroundCheckNotPassedException")
        super().__init__(msg)


class DifferentUserGroupDomainException(BaseException):
    """Users cannot be added to groups that are under different domains."""

    def __init__(self, msg=""):
        stats.count("DifferentUserGroupDomainException")
        super().__init__(msg)


class UserAlreadyAMemberOfGroupException(BaseException):
    """Unable to add a user to a group that they're already a member of."""

    def __init__(self, msg=""):
        stats.count("UserAlreadyAMemberOfGroupException")
        super().__init__(msg)


class UnableToModifyRestrictedGroupMembers(BaseException):
    """Unable to add/remove a user to a group that is marked as restricted."""

    def __init__(self, msg=""):
        stats.count("UnableToModifyRestrictedGroupMembers")
        super().__init__(msg)


class UnableToEditSensitiveAttributes(BaseException):
    """Unable edit sensitive attributes."""

    def __init__(self, msg=""):
        stats.count("UnableToEditSensitiveAttributes")
        super().__init__(msg)


class NoMatchingRequest(BaseException):
    """Cannot find a matching request"""

    def __init__(self, msg=""):
        stats.count("NoMatchingRequest")
        super().__init__(msg)


class BulkAddPrevented(BaseException):
    """Bulk adding user to group is prevented"""

    def __init__(self, msg=""):
        stats.count("BulkAddPrevented")
        super().__init__(msg)


class UnauthorizedToAccess(BaseException):
    """Unauthorized to access resource"""

    def __init__(self, msg=""):
        stats.count("UnauthorizedToViewPage")
        super().__init__(msg)


class NoRoleTemplateException(BaseException):
    """The IAM role template for the per-user role does not exist."""

    def __init__(self, msg=""):
        stats.count("NoRoleTemplate")
        super().__init__(msg)


class UserRoleLambdaException(BaseException):
    """The Lambda function to create IAM roles errored out for some reason."""

    def __init__(self, msg=""):
        stats.count("BadResponseFromUserRoleLambda")
        super().__init__(msg)


class PolicyUnchanged(BaseException):
    """Updated policy is identical to existing policy."""

    def __init__(self, msg=""):
        stats.count("PolicyUnchanged")
        super().__init__(msg)


class InvalidDomainError(BaseException):
    """Invalid domain"""

    def __init__(self, msg=""):
        stats.count("InvalidDomainError")
        super().__init__(msg)


class UnableToGenerateRoleName(BaseException):
    """Unable to generate role name within constraints (64 characters, up to 10 duplicate usernames handled"""

    def __init__(self, msg=""):
        stats.count("UnableToGenerateRoleName")
        super().__init__(msg)


class InvalidInvocationArgument(BaseException):
    """Function was invoked with an invalid argument."""

    def __init__(self, msg=""):
        stats.count("InvalidInvocationArgument")
        super().__init__(msg)


class UserRoleNotAssumableYet(BaseException):
    """Newly created user role is not assumable yet."""

    def __init__(self, msg=""):
        stats.count("UserRoleNotAssumableYet")
        super().__init__(msg)


class NoArnException(BaseException):
    """No ARN passed to endpoint."""

    def __init__(self, msg=""):
        stats.count("NoArnException")
        super().__init__(msg)


class MustBeFte(BaseException):
    """Only Full Time Employees are allowed"""

    def __init__(self, msg=""):
        stats.count("MustBeFte")
        super().__init__(msg)


class Unauthorized(BaseException):
    """Unauthorized"""

    def __init__(self, msg=""):
        stats.count("Unauthorized")
        super().__init__(msg)


class InvalidRequestParameter(BaseException):
    """Invalid Request Parameter passed to function"""

    def __init__(self, msg=""):
        stats.count("InvalidRequestParameter")
        super().__init__(msg)


class MissingRequestParameter(BaseException):
    """Missing Request Parameter passed to function"""

    def __init__(self, msg=""):
        stats.count("InvalidRequestParameter")
        super().__init__(msg)


class KriegerError(BaseException):
    """Krieger communication error"""

    def __init__(self, msg=""):
        stats.count("InvalidRequestParameter")
        super().__init__(msg)


class BaseWebpackLoaderException(BaseException):
    """
    Base exception for django-webpack-loader.
    """

    def __init__(self, msg=""):
        stats.count("BaseWebpackLoaderException")
        super().__init__(msg)


class WebpackError(BaseWebpackLoaderException):
    """
    General webpack loader error.
    """

    def __init__(self, msg=""):
        stats.count("WebpackLoaderBadStatsError")
        super().__init__(msg)


class WebpackLoaderBadStatsError(BaseWebpackLoaderException):
    """
    The stats file does not contain valid data.
    """

    def __init__(self, msg=""):
        stats.count("WebpackLoaderBadStatsError")
        super().__init__(msg)


class WebpackLoaderTimeoutError(BaseWebpackLoaderException):
    """
    The bundle took too long to compile.
    """

    def __init__(self, msg=""):
        stats.count("WebpackLoaderTimeoutError")
        super().__init__(msg)


class WebpackBundleLookupError(BaseWebpackLoaderException):
    """
    The bundle name was invalid.
    """

    def __init__(self, msg=""):
        stats.count("WebpackBundleLookupError")
        super().__init__(msg)


class UnsupportedRedisDataType(BaseException):
    """Unsupported Redis Data Type passed"""

    def __init__(self, msg=""):
        stats.count("UnsupportedRedisDataType")
        super().__init__(msg)


class DataNotRetrievable(BaseException):
    """Data was expected but is not retrievable"""

    def __init__(self, msg=""):
        stats.count("DataNotRetrievable")
        super().__init__(msg)


class MissingConfigurationValue(BaseException):
    """Unable to find expected configuration value"""

    def __init__(self, msg=""):
        stats.count("MissingConfigurationValue")
        super().__init__(msg)


class ExpiredData(BaseException):
    """Data was retrieved but is older than expected"""

    def __init__(self, msg=""):
        stats.count("ExpiredData")
        super().__init__(msg)


class UnsupportedChangeType(BaseException):
    """Unsupported Change Type"""

    def __init__(self, msg=""):
        stats.count("UnsupportedChangeType")
        super().__init__(msg)


class ResourceNotFound(BaseException):
    """Resource Not Found"""

    def __init__(self, msg=""):
        stats.count("ResourceNotFound")
        super().__init__(msg)


class UnableToAuthenticate(BaseException):
    """Unable to authenticate user or app"""

    def __init__(self, msg=""):
        stats.count("UnableToAuthenticate")
        super().__init__(msg)


class SilentException(BaseException):
    """
    Exception Traceback will not be printed (Useful for OIDC/SAML Redirects when we want Tornado to stop
    processing a request)
    """

    def __init__(self, msg=""):
        stats.count("SilentException")
        super().__init__(msg)
