#!/bin/bash

API_URL="${PAPERCLIP_API_URL:-https://api.paperclip.ing}"
API_KEY="${PAPERCLIP_API_KEY}"

if [[ -z "$API_KEY" ]]; then
  echo "Error: PAPERCLIP_API_KEY is not set" >&2
  exit 1
fi

# Debug: Print first 20 characters of API_KEY
key_preview="${API_KEY:0:20}"
echo "API_KEY preview: $key_preview..."

if [[ "$#" -lt 2 ]]; then
  echo "Usage: $0 --issue-id <issue-id> --status <status> [--comment <comment>] [--title <title>] [--priority <priority>] [--assignee-agent-id <id>]" >&2
  exit 1
fi

# Parse arguments
while [[ "$#" -gt 0 ]]; do
  case $1 in
    --issue-id)
      ISSUE_ID="$2"
      shift 2
      ;;
    --status)
      STATUS="$2"
      shift 2
      ;;
    --comment)
      COMMENT="$2"
      shift 2
      ;;
    --title)
      TITLE="$2"
      shift 2
      ;;
    --priority)
      PRIORITY="$2"
      shift 2
      ;;
    --assignee-agent-id)
      ASSIGNEE_AGENT_ID="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

# Validate required fields
if [[ -z "$ISSUE_ID" || -z "$STATUS" ]]; then
  echo "Error: --issue-id and --status are required" >&2
  exit 1
fi

# Build payload
PAYLOAD="{\"status\": \"$STATUS\"}"

# Create a temporary file for comment data
if [[ -n "$COMMENT" ]]; then
  TEMP_COMMENT_FILE=$(mktemp)
  echo "$COMMENT" > "$TEMP_COMMENT_FILE"
  
  # Use jq to properly format the comment payload with escaped newlines
  PAYLOAD=$(jq -n \
    --arg status "$STATUS" \
    --arg comment "$(cat "$TEMP_COMMENT_FILE")" \
    '{status: $status, comment: $comment}')
  
  rm -f "$TEMP_COMMENT_FILE"
fi

if [[ -n "$TITLE" ]]; then
  PAYLOAD=$(jq -n \
    --argjson payload "$PAYLOAD" \
    --arg title "$TITLE" \
    '{status: $payload.status, title: $title}')
fi

if [[ -n "$PRIORITY" ]]; then
  PAYLOAD=$(jq -n \
    --argjson payload "$PAYLOAD" \
    --arg priority "$PRIORITY" \
    '{status: $payload.status, priority: $priority}')
fi

if [[ -n "$ASSIGNEE_AGENT_ID" ]]; then
  PAYLOAD=$(jq -n \
    --argjson payload "$PAYLOAD" \
    --arg agent_id "$ASSIGNEE_AGENT_ID" \
    '{status: $payload.status, assigneeAgentId: $agent_id}')
fi

echo "Payload: $PAYLOAD"

# Make the API call
ENDPOINT="$API_URL/api/issues/$ISSUE_ID"
echo "Updating issue $ISSUE_ID at $ENDPOINT"
echo "Payload: $PAYLOAD"

echo -n "CURL:
"
curl -v -X PATCH "$ENDPOINT" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -H "X-Paperclip-Run-Id: $PAPERCLIP_RUN_ID" \
  -d "$PAYLOAD"

echo ""
echo "API call completed"