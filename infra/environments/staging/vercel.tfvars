environment = "staging"

vercel_token = ""

project_name = "dj-tech"

framework = "nextjs"

git_repository = "dj-tech/dj-tech"

build_command = "npm run build"

output_directory = ".next"

dev_command = "npm run dev"

install_command = "npm install"

node_version = "20.x"

serverless_function_region = "iad1"

custom_domain = "staging.djtech.xyz"

environment_variables = {
  "NODE_ENV" = { value = "staging", type = "plaintext" }
  "API_URL" = { value = "https://api-staging.djtech.xyz", type = "plaintext" }
  "NEXT_PUBLIC_APP_URL" = { value = "https://staging.djtech.xyz", type = "plaintext" }
}