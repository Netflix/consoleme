resource "aws_dynamodb_table" "consoleme_audit_global" {
  name             = "consoleme_audit_global"
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"
  billing_mode     = "PROVISIONED"
  read_capacity    = 5
  write_capacity   = 5
  hash_key         = "uuid"
  range_key        = "group"

  point_in_time_recovery {
    enabled        = true
  }

  attribute {
    name = "uuid"
    type = "S"
  }

  attribute {
    name = "group"
    type = "S"
  }

  ttl {
    attribute_name = ""
    enabled        = false
  }
}

resource "aws_dynamodb_table" "consoleme_config_global" {
  name             = "consoleme_config_global"
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"
  billing_mode     = "PROVISIONED"
  read_capacity    = 5
  write_capacity   = 5
  hash_key         = "id"

  point_in_time_recovery {
    enabled        = true
  }

  attribute {
    name = "id"
    type = "S"
  }


  ttl {
    attribute_name = ""
    enabled        = false
  }
}


resource "aws_dynamodb_table" "consoleme_iamroles_global" {
  name             = "consoleme_iamroles_global"
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"
  billing_mode     = "PROVISIONED"
  read_capacity    = 5
  write_capacity   = 5
  hash_key         = "arn"
  range_key        = "accountId"

  point_in_time_recovery {
    enabled        = true
  }

  attribute {
    name = "arn"
    type = "S"
  }

  attribute {
    name = "accountId"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
}

resource "aws_dynamodb_table" "consoleme_policy_requests" {
  name             = "consoleme_policy_requests"
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"
  billing_mode     = "PROVISIONED"
  read_capacity    = 5
  write_capacity   = 5
  hash_key         = "request_id"

  point_in_time_recovery {
    enabled        = true
  }

  attribute {
    name = "request_id"
    type = "S"
  }

  ttl {
    attribute_name = ""
    enabled        = false
  }
}


resource "aws_dynamodb_table" "consoleme_requests_global" {
  name             = "consoleme_requests_global"
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"
  billing_mode     = "PROVISIONED"
  read_capacity    = 5
  write_capacity   = 5
  hash_key         = "request_id"

  point_in_time_recovery {
    enabled        = true
  }

  attribute {
    name = "request_id"
    type = "S"
  }

  ttl {
    attribute_name = ""
    enabled        = false
  }
}

resource "aws_dynamodb_table" "consoleme_resource_cache" {
  name             = "consoleme_resource_cache"
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"
  billing_mode     = "PROVISIONED"
  read_capacity    = 5
  write_capacity   = 5
  hash_key         = "resourceId"
  range_key        = "resourceType"

  point_in_time_recovery {
    enabled        = true
  }

  attribute {
    name = "resourceId"
    type = "S"
  }

  attribute {
    name = "resourceType"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
}


resource "aws_dynamodb_table" "consoleme_users_global" {
  name             = "consoleme_users_global"
  stream_enabled   = true
  stream_view_type = "NEW_AND_OLD_IMAGES"
  billing_mode     = "PROVISIONED"
  read_capacity    = 5
  write_capacity   = 5
  hash_key         = "username"

  point_in_time_recovery {
    enabled        = true
  }

  attribute {
    name = "username"
    type = "S"
  }

  ttl {
    attribute_name = ""
    enabled        = false
  }
}
