# generated by datamodel-codegen:
#   filename:  swagger.yaml
#   timestamp: 2021-03-09T01:15:09+00:00

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, constr


class ResourceModel(BaseModel):
    arn: constr(
        regex="(^arn:([^:]*):([^:]*):([^:]*):(|\*|[\d]{12}|cloudfront|aws):(.+)$)|^\*$"
    ) = Field(..., description="resource ARN")
    name: str = Field(..., description="Resource Name")
    account_id: Optional[str] = Field(None, description="AWS account ID")
    region: Optional[str] = Field(None, description="Region")
    account_name: Optional[str] = Field(
        None, description="human-friendly AWS account name"
    )
    policy_sha256: Optional[str] = Field(
        None, description="hash of the most recent resource policy seen by ConsoleMe"
    )
    policy: Optional[str] = None
    actions: Optional[List[str]] = None
    owner: Optional[str] = Field(
        None, description="email address of team or individual who owns this resource"
    )
    approvers: Optional[List[str]] = None
    resource_type: str
    last_updated: Optional[datetime] = Field(
        None, description="last time resource was updated from source-of-truth"
    )


class RequestStatus(Enum):
    pending = "pending"
    cancelled = "cancelled"
    approved = "approved"
    rejected = "rejected"


class RequestModel(BaseModel):
    id: str
    arn: constr(
        regex="(^arn:([^:]*):([^:]*):([^:]*):(|\*|[\d]{12}|cloudfront|aws):(.+)$)|^\*$"
    ) = Field(
        ...,
        description="ARN of principal being modified",
        example="arn:aws:iam::123456789012:role/super_awesome_admin",
    )
    timestamp: datetime
    justification: str
    requester_email: str
    approvers: List[str] = Field(
        ...,
        description="list of approvers, derived from approvers of `resource`s in `changes`",
    )
    request_status: RequestStatus
    cross_account: Optional[bool] = Field(
        None, description="if true, the request touches cross-account resources"
    )
    arn_url: Optional[str] = Field(None, description="the principal arn's URL")
    admin_auto_approve: Optional[bool] = False


class GeneratorType(Enum):
    advanced = "advanced"
    crud_lookup = "crud_lookup"
    ec2 = "ec2"
    generic = "generic"
    rds = "rds"
    route53 = "route53"
    s3 = "s3"
    ses = "ses"
    sns = "sns"
    sqs = "sqs"
    sts = "sts"


class ChangeGeneratorModel(BaseModel):
    principal_arn: Optional[
        constr(
            regex="(^arn:([^:]*):([^:]*):([^:]*):(|\*|[\d]{12}|cloudfront|aws):(.+)$)|^\*$"
        )
    ] = Field(
        None,
        description="The principal (Source ARN) associated with the Change. This is most commomly an IAM role ARN.\nThe principal ARN is associated with the entity whose policy will be modified if the change is\napproved and successful.",
        example="arn:aws:iam::123456789012:role/exampleRole",
    )
    generator_type: GeneratorType
    resource_arn: constr(
        regex="(^arn:([^:]*):([^:]*):([^:]*):(|\*|[\d]{12}|cloudfront|aws):(.+)$)|(^\*$)"
    ) = Field(
        ...,
        description="The ARN of the resource being accessed. This is often an SQS/SNS/S3/etc. ARN. It is possible that the\nresource policy will need to be modified if the change is approved and successful.",
        example="arn:aws:sqs:us-east-1:123456789012:sqs_queue",
    )
    version: Optional[str] = Field(2.0, description="Version")
    user: Optional[str] = Field(
        None, description="Email address of user creating the change"
    )
    action_groups: Optional[List[str]] = Field(None, description="Action groups")
    policy_name: Optional[constr(regex="^[a-zA-Z0-9+=,.@\\-_]+$")] = Field(
        None, description="Optional policy name for the change, if applicable."
    )
    effect: Optional[constr(regex="^(Allow|Deny)$")] = Field(
        "Allow", description="The effect. By default, this is allow"
    )
    condition: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional condition for the change",
        example='{\n    "StringEquals": {"iam:PassedToService": "ec2.amazonaws.com"},\n    "StringLike": {\n        "iam:AssociatedResourceARN": [\n            "arn:aws:ec2:us-east-1:111122223333:instance/*",\n            "arn:aws:ec2:us-west-1:111122223333:instance/*"\n        ]\n    }\n}',
    )
    service: Optional[str] = None
    bucket_prefix: Optional[str] = None


class AdvancedChangeGeneratorModel(ChangeGeneratorModel):
    generator_type: constr(regex="advanced")
    iam_action: Optional[str] = Field(None, example="kinesis:AddTagsToStream")
    resource: Optional[str] = Field(None, example="*")


class GenericChangeGeneratorModel(ChangeGeneratorModel):
    action_groups: List[str]


class CrudChangeGeneratorModel(ChangeGeneratorModel):
    generator_type: constr(regex="crud_lookup")
    action_groups: List[str]
    service_name: str


class S3ChangeGeneratorModel(ChangeGeneratorModel):
    generator_type: constr(regex="s3")
    resource_arn: str = Field(
        ...,
        description="The ARN of the S3 resource being accessed.",
        example="arn:aws:s3:::example_bucket",
    )
    bucket_prefix: str = Field(..., example="/awesome/prefix/*")
    action_groups: List[str]


class SQSChangeGeneratorModel(ChangeGeneratorModel):
    generator_type: constr(regex="sqs")
    action_groups: List[str]


class SNSChangeGeneratorModel(ChangeGeneratorModel):
    generator_type: constr(regex="sns")
    action_groups: List[str]


class SESChangeGeneratorModel(ChangeGeneratorModel):
    generator_type: constr(regex="ses")
    from_address: str
    action_groups: Optional[List[str]] = None


class Status(Enum):
    applied = "applied"
    not_applied = "not_applied"
    cancelled = "cancelled"


class ChangeModel(BaseModel):
    principal_arn: constr(
        regex="(^arn:([^:]*):([^:]*):([^:]*):(|\*|[\d]{12}|cloudfront|aws):(.+)$)|^\*$"
    )
    change_type: str
    resources: Optional[List[ResourceModel]] = []
    version: Optional[str] = 2.0
    status: Optional[Status] = "not_applied"
    id: Optional[str] = None
    autogenerated: Optional[bool] = False
    updated_by: Optional[str] = None


class Action(Enum):
    attach = "attach"
    detach = "detach"


class TagAction(Enum):
    create = "create"
    update = "update"
    delete = "delete"


class ResourceTagChangeModel(ChangeModel):
    original_key: Optional[str] = Field(
        None,
        description="original_key is used for renaming a key to something else. This is optional.",
        example="key_to_be_renamed",
    )
    key: Optional[str] = Field(
        None,
        description="This is the desired key name for the tag. If a tag key is being renamed, this is what it will be renamed\nto. Otherwise, this key name will be used when creating or updating a tag.",
        example="desired_key_name",
    )
    original_value: Optional[str] = None
    value: Optional[str] = None
    change_type: Optional[constr(regex="resource_tag")] = None
    tag_action: TagAction


class Action1(Enum):
    attach = "attach"
    detach = "detach"


class ManagedPolicyChangeModel(ChangeModel):
    arn: constr(
        regex="(^arn:([^:]*):([^:]*):([^:]*):(|\*|[\d]{12}|cloudfront|aws):(.+)$)|^\*$"
    )
    change_type: Optional[constr(regex="managed_policy")] = None
    action: Action1


class ArnArray(BaseModel):
    __root__: List[
        constr(regex="^arn:([^:]*):([^:]*):([^:]*):(|\*|[\d]{12}|cloudfront|aws):(.+)$")
    ]


class Status1(Enum):
    active = "active"
    deleted = "deleted"
    created = "created"
    suspended = "suspended"


class Type(Enum):
    aws = "aws"
    gcp = "gcp"


class Environment(Enum):
    prod = "prod"
    test = "test"


class CloudAccountModel(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    status: Optional[Status1] = None
    type: Optional[Type] = None
    sync_enabled: Optional[bool] = None
    sensitive: Optional[bool] = False
    environment: Optional[Environment] = None
    aliases: Optional[List[str]] = None
    email: Optional[str] = None


class PolicyModel(BaseModel):
    version: Optional[str] = Field(None, description="AWS Policy Version")
    policy_document: Optional[Dict[str, Any]] = Field(
        None, description="JSON policy document"
    )
    policy_sha256: Optional[str] = Field(
        None, description="hash of the policy_document json"
    )


class PolicyStatement(BaseModel):
    action: List[str] = Field(..., description="AWS Policy Actions")
    effect: str = Field(..., description="Allow | Deny")
    resource: List[str] = Field(..., description="AWS Resource ARNs")
    sid: Optional[constr(regex="^([a-zA-Z0-9]+)*")] = Field(
        None, description="Statement identifier"
    )


class RoleModel(BaseModel):
    name: str = Field(..., example="super_awesome_admin")
    account_id: constr(min_length=12, max_length=12) = Field(
        ..., example="123456789012"
    )
    account_name: Optional[str] = Field(None, example="super_awesome")
    arn: Optional[
        constr(
            regex="(^arn:([^:]*):([^:]*):([^:]*):(|\*|[\d]{12}|cloudfront|aws):(.+)$)|^\*$"
        )
    ] = Field(None, example="arn:aws:iam::123456789012:role/super_awesome_admin")


class CloudTrailError(BaseModel):
    event_call: Optional[str] = Field(None, example="sqs:CreateQueue")
    count: Optional[int] = Field(None, example=5)


class CloudTrailErrorArray(BaseModel):
    cloudtrail_errors: Optional[List[CloudTrailError]] = None


class CloudTrailDetailsModel(BaseModel):
    error_url: Optional[str] = Field(
        None, example="https://cloudtrail_logs/for/role_arn"
    )
    errors: Optional[CloudTrailErrorArray] = None


class S3Error(BaseModel):
    error_call: Optional[str] = Field(None, example="s3:PutObject")
    count: Optional[int] = Field(None, example=5)
    bucket_name: Optional[str] = Field(None, example="bucket_name")
    request_prefix: Optional[str] = Field(None, example="folder/file.txt")
    status_code: Optional[int] = Field(None, example=403)
    status_text: Optional[str] = Field(None, example="AccessDenied")
    role_arn: Optional[
        constr(
            regex="(^arn:([^:]*):([^:]*):([^:]*):(|\*|[\d]{12}|cloudfront|aws):(.+)$)|^\*$"
        )
    ] = Field(None, example="arn:aws:iam::123456789012:role/roleName")


class S3ErrorArray(BaseModel):
    s3_errors: Optional[List[S3Error]] = None


class S3DetailsModel(BaseModel):
    query_url: Optional[str] = Field(
        None, example="https://s3_log_query/for/role_or_bucket_arn"
    )
    error_url: Optional[str] = Field(
        None, example="https://s3_error_query/for/role_or_bucket_arn"
    )
    errors: Optional[S3ErrorArray] = None


class AppDetailsModel(BaseModel):
    name: Optional[str] = Field(None, example="app_name")
    owner: Optional[str] = Field(None, example="owner@example.com")
    owner_url: Optional[str] = Field(None, example="https://link_to_owner_group")
    app_url: Optional[str] = Field(
        None, example="https://link_to_app_ci_pipeline_for_app"
    )


class AppDetailsArray(BaseModel):
    app_details: Optional[List[AppDetailsModel]] = None


class ExtendedRoleModel(RoleModel):
    inline_policies: List[Dict[str, Any]]
    assume_role_policy_document: Optional[Dict[str, Any]] = None
    cloudtrail_details: Optional[CloudTrailDetailsModel] = None
    s3_details: Optional[S3DetailsModel] = None
    apps: Optional[AppDetailsArray] = None
    managed_policies: List[Dict[str, Any]]
    tags: List[Dict[str, Any]]
    config_timeline_url: Optional[str] = Field(
        None, description="A link to the role's AWS Config Timeline"
    )
    templated: Optional[bool] = None
    template_link: Optional[str] = None
    created_time: Optional[str] = None
    updated_time: Optional[str] = None
    last_used_time: Optional[str] = None
    description: Optional[str] = None


class UserModel(BaseModel):
    email: Optional[str] = None
    extended_info: Optional[Dict[str, Any]] = None
    details_url: Optional[str] = Field(None, example="https://details_about/user")
    photo_url: Optional[str] = Field(
        None, example="https://user_photos/user_thumbnail.jpg"
    )


class ApiErrorModel(BaseModel):
    status: Optional[int] = None
    title: Optional[str] = None
    message: Optional[str] = None


class Options(BaseModel):
    assume_role_policy: Optional[bool] = False
    tags: Optional[bool] = False
    copy_description: Optional[bool] = False
    description: Optional[str] = None
    inline_policies: Optional[bool] = False
    managed_policies: Optional[bool] = False


class CloneRoleRequestModel(BaseModel):
    account_id: constr(min_length=12, max_length=12)
    role_name: str
    dest_account_id: constr(min_length=12, max_length=12)
    dest_role_name: str
    options: Options


class ActionResult(BaseModel):
    status: Optional[str] = None
    message: Optional[str] = None


class CreateCloneRequestResponse(BaseModel):
    errors: Optional[int] = None
    role_created: Optional[bool] = None
    action_results: Optional[List[ActionResult]] = None


class RoleCreationRequestModel(BaseModel):
    account_id: constr(min_length=12, max_length=12)
    role_name: str
    description: Optional[str] = None
    instance_profile: Optional[bool] = True


class RequestCreationResponse(BaseModel):
    errors: Optional[int] = None
    request_created: Optional[bool] = None
    request_id: Optional[str] = None
    request_url: Optional[str] = None
    action_results: Optional[List[ActionResult]] = None


class Command(Enum):
    add_comment = "add_comment"
    approve_request = "approve_request"
    reject_request = "reject_request"
    cancel_request = "cancel_request"
    apply_change = "apply_change"
    update_change = "update_change"
    cancel_change = "cancel_change"
    move_back_to_pending = "move_back_to_pending"


class RequestModificationBaseModel(BaseModel):
    command: Command


class CommentRequestModificationModel(RequestModificationBaseModel):
    comment_text: str


class UpdateChangeModificationModel(RequestModificationBaseModel):
    policy_document: Dict[str, Any]
    change_id: str


class ApplyChangeModificationModel(RequestModificationBaseModel):
    policy_document: Optional[Dict[str, Any]] = None
    change_id: str


class CancelChangeModificationModel(RequestModificationBaseModel):
    policy_document: Optional[Dict[str, Any]] = None
    change_id: str


class ChangeRequestStatusModificationModel(RequestModificationBaseModel):
    pass


class MoveToPendingRequestModificationModel(RequestModificationBaseModel):
    pass


class PolicyRequestChange(BaseModel):
    policy_document: Dict[str, Any]
    change_id: str


class ApproveRequestModificationModel(RequestModificationBaseModel):
    policy_request_changes: Optional[List[PolicyRequestChange]] = None


class PolicyRequestModificationRequestModel(BaseModel):
    modification_model: Union[
        CommentRequestModificationModel,
        UpdateChangeModificationModel,
        ApplyChangeModificationModel,
        ApproveRequestModificationModel,
        MoveToPendingRequestModificationModel,
        ChangeRequestStatusModificationModel,
    ]


class PolicyRequestModificationResponseModel(BaseModel):
    errors: Optional[int] = None
    action_results: Optional[List[ActionResult]] = None


class AuthenticationResponse(BaseModel):
    authenticated: Optional[bool] = None
    errors: Optional[List[str]] = None
    username: Optional[str] = None
    groups: Optional[List[str]] = None


class UserManagementAction(Enum):
    create = "create"
    update = "update"
    delete = "delete"


class UserManagementModel(BaseModel):
    user_management_action: Optional[UserManagementAction] = None
    username: Optional[str] = None
    password: Optional[str] = None
    groups: Optional[List[str]] = None


class LoginAttemptModel(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    after_redirect_uri: Optional[str] = None


class RegistrationAttemptModel(BaseModel):
    username: str
    password: str


class Status2(Enum):
    success = "success"
    error = "error"
    redirect = "redirect"


class WebResponse(BaseModel):
    status: Optional[Status2] = None
    reason: Optional[str] = Field(
        None,
        example=["authenticated_redirect", "authentication_failure", "not_configured"],
    )
    redirect_url: Optional[str] = None
    status_code: Optional[int] = None
    message: Optional[str] = None
    errors: Optional[List[str]] = None
    data: Optional[Dict[str, Any]] = None


class PolicyCheckModelItem(BaseModel):
    issue: Optional[str] = None
    detail: Optional[str] = None
    location: Optional[str] = None
    severity: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None


class PolicyCheckModel(BaseModel):
    __root__: List[PolicyCheckModelItem]


class ChangeGeneratorModelArray(BaseModel):
    changes: List[
        Union[
            S3ChangeGeneratorModel,
            SQSChangeGeneratorModel,
            SNSChangeGeneratorModel,
            SESChangeGeneratorModel,
            CrudChangeGeneratorModel,
            GenericChangeGeneratorModel,
        ]
    ]


class InlinePolicyChangeModel(ChangeModel):
    policy_name: Optional[str] = None
    new: Optional[bool] = True
    action: Optional[Action] = "attach"
    change_type: Optional[constr(regex="inline_policy")] = None
    policy: Optional[PolicyModel] = None
    old_policy: Optional[PolicyModel] = None


class AssumeRolePolicyChangeModel(ChangeModel):
    change_type: Optional[constr(regex="assume_role_policy")] = None
    policy: Optional[PolicyModel] = None
    old_policy: Optional[PolicyModel] = None
    source_change_id: Optional[str] = Field(
        None,
        description="the change model ID of the source change, that this change was generated from",
    )


class ResourcePolicyChangeModel(ChangeModel):
    change_type: Optional[constr(regex="resource_policy")] = None
    arn: constr(
        regex="(^arn:([^:]*):([^:]*):([^:]*):(|\*|[\d]{12}|cloudfront|aws):(.+)$)|^\*$"
    )
    source_change_id: Optional[str] = Field(
        None,
        description="the change model ID of the source change, that this change was generated from",
    )
    supported: Optional[bool] = Field(
        None,
        description="whether we currently support this type of resource policy change or not",
    )
    policy: PolicyModel
    old_policy: Optional[PolicyModel] = None


class ChangeModelArray(BaseModel):
    changes: List[
        Union[
            InlinePolicyChangeModel,
            ManagedPolicyChangeModel,
            ResourcePolicyChangeModel,
            AssumeRolePolicyChangeModel,
            ResourceTagChangeModel,
        ]
    ]


class CloudAccountModelArray(BaseModel):
    accounts: Optional[List[CloudAccountModel]] = None


class CommentModel(BaseModel):
    id: str
    timestamp: datetime
    edited: Optional[bool] = None
    last_modified: Optional[datetime] = None
    user_email: str
    user: Optional[UserModel] = None
    text: str


class RequestCreationModel(BaseModel):
    changes: ChangeModelArray
    justification: str
    admin_auto_approve: Optional[bool] = False


class ExtendedRequestModel(RequestModel):
    changes: ChangeModelArray
    requester_info: UserModel
    reviewer: Optional[str] = None
    comments: Optional[List[CommentModel]] = None
