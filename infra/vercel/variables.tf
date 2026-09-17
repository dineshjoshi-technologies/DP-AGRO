variable "environment" {
  description = "Environment name (staging, production)"
  type        = string
}

variable "vercel_token" {
  description = "Vercel access token"
  type        = string
}

variable "project_name" {
  description = "Vercel project name"
  type        = string
  default     = "dj-tech"
}

variable "framework" {
  description = "Framework preset (nextjs, remix, vite, etc.)"
  type        = string
  default     = "nextjs"
}

variable "git_repository" {
  description = "Git repository (org/repo)"
  type        = string
}

variable "build_command" {
  description = "Build command"
  type        = string
  default     = "npm run build"
}

variable "output_directory" {
  description = "Output directory"
  type        = string
  default     = ".next"
}

variable "dev_command" {
  description = "Development command"
  type        = string
  default     = "npm run dev"
}

variable "install_command" {
  description = "Install command"
  type        = string
  default     = "npm install"
}

variable "node_version" {
  description = "Node.js version"
  type        = string
  default     = "20.x"
}

variable "serverless_function_region" {
  description = "Serverless function region"
  type        = string
  default     = "iad1"
}

variable "custom_domain" {
  description = "Custom domain (optional)"
  type        = string
  default     = ""
}

variable "environment_variables" {
  description = "Environment variables for the project"
  type        = map(object({
    value = string
    type  = string
  }))
  default = {}
}