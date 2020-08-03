# generated by datamodel-codegen:
#   filename:  swagger.yaml
#   timestamp: 2020-08-03T20:39:13+00:00

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
    owner: Optional[str] = Field(
        None, description="email address of team or individual who owns this resource"
    )
    approvers: Optional[List[str]] = None
    resource_type: str
    last_updated: Optional[datetime] = Field(
        None, description="last time resource was updated from source-of-truth"
    )


class RequestModel(BaseModel):
    id: str
    arn: constr(
        regex="(^arn:([^:]*):([^:]*):([^:]*):(|\*|[\d]{12}|cloudfront|aws):(.+)$)|^\*$"
    ) = Field(..., description="ARN of principal being modified")
    timestamp: datetime
    justification: str
    requester_email: str
    approvers: List[str] = Field(
        ...,
        description="list of approvers, derived from approvers of `resource`s in `changes`",
    )
    status: str
    cross_account: Optional[bool] = Field(
        None, description="if true, the request touches cross-account resources"
    )


class GeneratorType(Enum):
    advanced = "advanced"
    crud_lookup = "crud_lookup"
    ec2 = "ec2"
    generic = "generic"
    rds = "rds"
    route53 = "route53"
    s3 = "s3"
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
    )
    generator_type: GeneratorType
    resource_arn: constr(
        regex="(^arn:([^:]*):([^:]*):([^:]*):(|\*|[\d]{12}|cloudfront|aws):(.+)$)|(^\*$)"
    ) = Field(
        ...,
        description="The ARN of the resource being accessed. This is often an SQS/SNS/S3/etc. ARN. It is possible that the\nresource policy will need to be modified if the change is approved and successful.",
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
        None, description="Optional condition for the change"
    )
    service: Optional[str] = None
    bucket_prefix: Optional[str] = None


class AdvancedChangeGeneratorModel(ChangeGeneratorModel):
    iam_action: Optional[str] = None
    resource: Optional[str] = None


class GenericChangeGeneratorModel(ChangeGeneratorModel):
    action_groups: List[str]


class ActionGroup(Enum):
    read = "read"
    write = "write"
    list = "list"
    tagging = "tagging"
    permissions_management = "permissions-management"


class CrudChangeGeneratorModel(ChangeGeneratorModel):
    action_groups: List[ActionGroup]
    service_name: str


class ActionGroup1(Enum):
    list = "list"
    get = "get"
    put = "put"
    delete = "delete"


class S3ChangeGeneratorModel(ChangeGeneratorModel):
    bucket_prefix: str
    action_groups: List[ActionGroup1]


class ActionGroup2(Enum):
    get_queue_attributes = "get_queue_attributes"
    set_queue_attributes = "set_queue_attributes"
    receive_messages = "receive_messages"
    send_messages = "send_messages"
    delete_messages = "delete_messages"


class SQSChangeGeneratorModel(ChangeGeneratorModel):
    action_groups: List[ActionGroup2]


class ActionGroup3(Enum):
    get_topic_attributes = "get_topic_attributes"
    set_topic_attributes = "set_topic_attributes"
    publish = "publish"
    subscribe = "subscribe"
    unsubscribe = "unsubscribe"


class SNSChangeGeneratorModel(ChangeGeneratorModel):
    action_groups: List[ActionGroup3]


class ChangeType(Enum):
    inline_policy = "inline_policy"
    managed_policy = "managed_policy"
    resource_policy = "resource_policy"
    assume_role_policy = "assume_role_policy"


class Status(Enum):
    applied = "applied"
    not_applied = "not_applied"


class ChangeModel(BaseModel):
    principal_arn: constr(
        regex="(^arn:([^:]*):([^:]*):([^:]*):(|\*|[\d]{12}|cloudfront|aws):(.+)$)|^\*$"
    )
    change_type: ChangeType
    resources: List[ResourceModel]
    version: Optional[str] = 2.0
    status: Status
    id: Optional[str] = None


class Action(Enum):
    attach = "attach"
    detach = "detach"


class Action1(Enum):
    attach = "attach"
    detach = "detach"


class ManagedPolicyChangeModel(ChangeModel):
    arn: constr(
        regex="(^arn:([^:]*):([^:]*):([^:]*):(|\*|[\d]{12}|cloudfront|aws):(.+)$)|^\*$"
    )
    policy_name: str
    action: Action1


class ArnArray(BaseModel):
    __root__: List[
        constr(regex="^arn:([^:]*):([^:]*):([^:]*):(|\*|[\d]{12}|cloudfront|aws):(.+)$")
    ]


class PolicyModel(BaseModel):
    version: Optional[str] = Field(None, description="AWS Policy Version")
    policy_document: Optional[Dict[str, Any]] = Field(
        None, description="JSON policy document"
    )
    policy_sha256: str = Field(..., description="hash of the policy_document json")


class PolicyStatement(BaseModel):
    action: List[str] = Field(..., description="AWS Policy Actions")
    effect: str = Field(..., description="Allow | Deny")
    resource: List[str] = Field(..., description="AWS Resource ARNs")
    sid: Optional[constr(regex="^([a-zA-Z0-9]+)*")] = Field(
        None, description="Statement identifier"
    )


class RoleModel(BaseModel):
    name: str
    account_id: constr(min_length=12, max_length=12)
    account_name: Optional[str] = None
    arn: Optional[
        constr(
            regex="(^arn:([^:]*):([^:]*):([^:]*):(|\*|[\d]{12}|cloudfront|aws):(.+)$)|^\*$"
        )
    ] = None


class CloudTrailError(BaseModel):
    event_call: Optional[str] = None
    count: Optional[int] = None


class CloudTrailErrorArray(BaseModel):
    cloudtrail_errors: Optional[List[CloudTrailError]] = None


class CloudTrailDetailsModel(BaseModel):
    error_url: Optional[str] = None
    errors: Optional[CloudTrailErrorArray] = None


class S3Error(BaseModel):
    error_call: Optional[str] = None
    count: Optional[int] = None
    bucket_name: Optional[str] = None
    request_prefix: Optional[str] = None
    status_code: Optional[int] = None
    status_text: Optional[str] = None
    role_arn: Optional[
        constr(
            regex="(^arn:([^:]*):([^:]*):([^:]*):(|\*|[\d]{12}|cloudfront|aws):(.+)$)|^\*$"
        )
    ] = None


class S3ErrorArray(BaseModel):
    s3_errors: Optional[List[S3Error]] = None


class S3DetailsModel(BaseModel):
    query_url: Optional[str] = None
    error_url: Optional[str] = None
    errors: Optional[S3ErrorArray] = None


class AppDetailsModel(BaseModel):
    name: Optional[str] = None
    owner: Optional[str] = None
    owner_url: Optional[str] = None
    app_url: Optional[str] = None


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
    templated: Optional[bool] = None
    template_link: Optional[str] = None


class UserModel(BaseModel):
    email: Optional[str] = None
    extended_info: Optional[Dict[str, Any]] = None
    details_url: Optional[str] = None
    photo_url: Optional[str] = None


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
    action_results: Optional[List[ActionResult]] = None


class ChangeGeneratorModelArray(BaseModel):
    changes: List[
        Union[
            S3ChangeGeneratorModel,
            SQSChangeGeneratorModel,
            SNSChangeGeneratorModel,
            CrudChangeGeneratorModel,
            GenericChangeGeneratorModel,
        ]
    ]


class InlinePolicyChangeModel(ChangeModel):
    policy_name: str
    new: bool
    action: Optional[Action] = "attach"
    policy: PolicyModel
    old_policy: Optional[PolicyModel] = None


class AssumeRolePolicyChangeModel(ChangeModel):
    policy: PolicyModel
    old_policy: Optional[PolicyModel] = None


class ResourcePolicyChangeModel(ChangeModel):
    arn: constr(
        regex="(^arn:([^:]*):([^:]*):([^:]*):(|\*|[\d]{12}|cloudfront|aws):(.+)$)|^\*$"
    )
    autogenerated: Optional[bool] = False
    sourceChangeID: Optional[str] = Field(
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
        ]
    ]


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
