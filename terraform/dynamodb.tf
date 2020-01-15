resource "aws_dynamodb_table" "consoleme_users_global" {
  name           = "consoleme_users_global"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "username"
  # range_key      = "GameTitle"

  attribute {
    name = "username"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = false
  }
}

resource "aws_dynamodb_table" "consoleme_requests_global" {
  name           = "consoleme_requests_global"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "request_id"
  # range_key      = "GameTitle"

  attribute {
    name = "request_id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = false
  }
}

resource "aws_dynamodb_table" "consoleme_audit_global" {
  name           = "consoleme_audit_global"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "uuid"
  range_key      = "group"

  attribute {
    name = "uuid"
    type = "S"
  }

  attribute {
    name = "group"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = false
  }
}

resource "aws_dynamodb_table" "consoleme_policies_global" {
  name           = "consoleme_policies_global"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "account_id"

  attribute {
    name = "account_id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = false
  }
}

resource "aws_dynamodb_table" "consoleme_iamroles_global" {
  name           = "consoleme_iamroles_global"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "arn"
  range_key       = "accountId"

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

resource "aws_dynamodb_table" "consoleme_config_global" {
  name           = "consoleme_config_global"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "id"

  attribute {
    name = "id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = false
  }
}

resource "aws_dynamodb_table" "consoleme_policy_requests" {
  name           = "consoleme_policy_requests"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "request_id"

  attribute {
    name = "request_id"
    type = "S"
  }

  attribute {
    name = "arn"
    type = "S"
  }

  global_secondary_index {
    name               = "arn-request_id-index"
    hash_key           = "arn"
    write_capacity     = 10
    read_capacity      = 10
    projection_type    = "INCLUDE"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = false
  }
}