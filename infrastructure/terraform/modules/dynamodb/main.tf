# DynamoDB Module

variable "name_prefix" {
  type = string
}

variable "billing_mode" {
  type    = string
  default = "PAY_PER_REQUEST"
}

variable "tags" {
  type    = map(string)
  default = {}
}

# Sessions Table
resource "aws_dynamodb_table" "sessions" {
  name         = "${var.name_prefix}-sessions"
  billing_mode = var.billing_mode
  hash_key     = "session_id"

  attribute {
    name = "session_id"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  global_secondary_index {
    name            = "user_id-index"
    hash_key        = "user_id"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-sessions"
  })
}

# Briefings Table
resource "aws_dynamodb_table" "briefings" {
  name         = "${var.name_prefix}-briefings"
  billing_mode = var.billing_mode
  hash_key     = "user_id"
  range_key    = "generated_at"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "generated_at"
    type = "S"
  }

  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = merge(var.tags, {
    Name = "${var.name_prefix}-briefings"
  })
}

# Outputs
output "sessions_table_name" {
  value = aws_dynamodb_table.sessions.name
}

output "sessions_table_arn" {
  value = aws_dynamodb_table.sessions.arn
}

output "briefings_table_name" {
  value = aws_dynamodb_table.briefings.name
}

output "briefings_table_arn" {
  value = aws_dynamodb_table.briefings.arn
}

output "table_arns" {
  value = [
    aws_dynamodb_table.sessions.arn,
    aws_dynamodb_table.briefings.arn
  ]
}
