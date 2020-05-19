from marshmallow import Schema, fields


class ManagedPolicy(Schema):
    action = fields.Str(required=True)
    arn = fields.Str(required=True)


class InlinePolicy(Schema):
    action = fields.Str(required=True)
    policy_name = fields.Str(required=True, load_from="policyname")
    policy_document = fields.Str(load_from="policydocument")


class Tags(Schema):
    action = fields.Str(required=True)
    key = fields.Str(required=True)
    value = fields.Str()


class AssumeRolePolicyDocument(Schema):
    action = fields.Str(required=True)
    assume_role_policy_document = fields.Str(required=True)


class RoleUpdaterRequest(Schema):
    arn = fields.Str(required=True)
    inline_policies = fields.Nested(InlinePolicy, many=True)
    managed_policies = fields.Nested(ManagedPolicy, many=True)
    assume_role_policy_document = fields.Nested(AssumeRolePolicyDocument)
    tags = fields.Nested(Tags, many=True)
    requester = fields.Str()
