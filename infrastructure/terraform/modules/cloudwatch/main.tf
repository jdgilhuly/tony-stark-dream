# CloudWatch Module

variable "name_prefix" {
  type = string
}

variable "retention_in_days" {
  type    = number
  default = 7
}

variable "services" {
  type = list(string)
}

variable "tags" {
  type    = map(string)
  default = {}
}

# Log Groups for each service
resource "aws_cloudwatch_log_group" "services" {
  for_each = toset(var.services)

  name              = "/jarvis/${var.name_prefix}/${each.value}"
  retention_in_days = var.retention_in_days

  tags = merge(var.tags, {
    Service = each.value
  })
}

# Metric Alarms
resource "aws_cloudwatch_metric_alarm" "high_error_rate" {
  alarm_name          = "${var.name_prefix}-high-error-rate"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "5XXError"
  namespace           = "AWS/ApplicationELB"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "High 5XX error rate detected"

  dimensions = {
    LoadBalancer = "${var.name_prefix}-alb"
  }

  tags = var.tags
}

resource "aws_cloudwatch_metric_alarm" "high_latency" {
  alarm_name          = "${var.name_prefix}-high-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "TargetResponseTime"
  namespace           = "AWS/ApplicationELB"
  period              = 300
  extended_statistic  = "p95"
  threshold           = 3
  alarm_description   = "High p95 latency detected (>3s)"

  dimensions = {
    LoadBalancer = "${var.name_prefix}-alb"
  }

  tags = var.tags
}

# Dashboard
resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.name_prefix}-dashboard"

  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "metric"
        x      = 0
        y      = 0
        width  = 12
        height = 6
        properties = {
          title = "Request Count"
          view  = "timeSeries"
          stacked = false
          metrics = [
            ["AWS/ApplicationELB", "RequestCount", "LoadBalancer", "${var.name_prefix}-alb"]
          ]
          region = "us-east-1"
          period = 300
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 0
        width  = 12
        height = 6
        properties = {
          title = "Response Time"
          view  = "timeSeries"
          stacked = false
          metrics = [
            ["AWS/ApplicationELB", "TargetResponseTime", "LoadBalancer", "${var.name_prefix}-alb", { stat = "p50", label = "p50" }],
            ["...", { stat = "p95", label = "p95" }],
            ["...", { stat = "p99", label = "p99" }]
          ]
          region = "us-east-1"
          period = 300
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 6
        width  = 12
        height = 6
        properties = {
          title = "Error Rate"
          view  = "timeSeries"
          stacked = false
          metrics = [
            ["AWS/ApplicationELB", "HTTPCode_Target_4XX_Count", "LoadBalancer", "${var.name_prefix}-alb"],
            [".", "HTTPCode_Target_5XX_Count", ".", "."]
          ]
          region = "us-east-1"
          period = 300
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 6
        width  = 12
        height = 6
        properties = {
          title = "ECS CPU & Memory"
          view  = "timeSeries"
          stacked = false
          metrics = [
            ["AWS/ECS", "CPUUtilization", "ClusterName", "${var.name_prefix}-cluster"],
            [".", "MemoryUtilization", ".", "."]
          ]
          region = "us-east-1"
          period = 300
        }
      }
    ]
  })
}

# Outputs
output "log_group_names" {
  value = { for k, v in aws_cloudwatch_log_group.services : k => v.name }
}

output "log_group_arns" {
  value = { for k, v in aws_cloudwatch_log_group.services : k => v.arn }
}

output "dashboard_arn" {
  value = aws_cloudwatch_dashboard.main.dashboard_arn
}
