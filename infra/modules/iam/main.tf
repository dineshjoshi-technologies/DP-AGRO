terraform {
  required_version = ">= 1.5.0"
}

variable "environment" {
  description = "Environment name (staging, production)"
  type        = string
}

variable "ci_cd_role_name" {
  description = "Name for the CI/CD IAM role"
  type        = string
  default     = "ci-cd"
}

variable "workload_role_name" {
  description = "Name for the workload IAM role"
  type        = string
  default     = "workload"
}

variable "allowed_github_org" {
  description = "GitHub organization for OIDC trust"
  type        = string
  default     = ""
}

variable "allowed_github_repos" {
  description = "List of GitHub repositories allowed to assume the CI/CD role"
  type        = list(string)
  default     = []
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}

resource "aws_iam_role" "ci_cd" {
  name = "${var.environment}-${var.ci_cd_role_name}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Federated = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/token.actions.githubusercontent.com"
        }
        Condition = {
          StringLike = {
            "token.actions.githubusercontent.com:sub" = "repo:${var.allowed_github_org}/*"
          }
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          }
        }
      }
    ]
  })

  tags = merge(var.tags, {
    Name        = "${var.environment}-${var.ci_cd_role_name}"
    Environment = var.environment
  })
}

resource "aws_iam_policy" "ci_cd" {
  name = "${var.environment}-${var.ci_cd_role_name}-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "sts:AssumeRole"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:role/${var.environment}-*"
      },
      {
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Effect   = "Allow"
        Resource = [
          "arn:aws:s3:::${var.environment}-terraform-state*",
          "arn:aws:s3:::${var.environment}-terraform-state*/*"
        ]
      },
      {
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:DeleteItem"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:dynamodb:*:${data.aws_caller_identity.current.account_id}:table/${var.environment}-terraform-locks"
      }
    ]
  })

  tags = merge(var.tags, {
    Name        = "${var.environment}-${var.ci_cd_role_name}-policy"
    Environment = var.environment
  })
}

resource "aws_iam_role_policy_attachment" "ci_cd" {
  role       = aws_iam_role.ci_cd.name
  policy_arn = aws_iam_policy.ci_cd.arn
}

resource "aws_iam_role" "workload" {
  name = "${var.environment}-${var.workload_role_name}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })

  tags = merge(var.tags, {
    Name        = "${var.environment}-${var.workload_role_name}"
    Environment = var.environment
  })
}

resource "aws_iam_policy" "workload" {
  name = "${var.environment}-${var.workload_role_name}-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:secretsmanager:*:${data.aws_caller_identity.current.account_id}:secret:${var.environment}/*"
      },
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:logs:*:${data.aws_caller_identity.current.account_id}:log-group:/aws/${var.environment}/*"
      }
    ]
  })

  tags = merge(var.tags, {
    Name        = "${var.environment}-${var.workload_role_name}-policy"
    Environment = var.environment
  })
}

resource "aws_iam_role_policy_attachment" "workload" {
  role       = aws_iam_role.workload.name
  policy_arn = aws_iam_policy.workload.arn
}

data "aws_caller_identity" "current" {}

output "ci_cd_role_arn" {
  description = "ARN of the CI/CD IAM role"
  value       = aws_iam_role.ci_cd.arn
}

output "workload_role_arn" {
  description = "ARN of the workload IAM role"
  value       = aws_iam_role.workload.arn
}