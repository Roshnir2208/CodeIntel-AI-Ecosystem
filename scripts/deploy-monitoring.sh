#!/usr/bin/env bash
set -euo pipefail

STACK_NAME="${1:-codeintel-monitoring}"
ALERT_EMAIL="${2:-${ALERT_EMAIL:-}}"
NAMESPACE="${NAMESPACE:-CodeIntelAPI}"
ALARM_PERIOD_SECONDS="${ALARM_PERIOD_SECONDS:-60}"
LOW_REQUEST_THRESHOLD_PER_MINUTE="${LOW_REQUEST_THRESHOLD_PER_MINUTE:-1}"
TEMPLATE_PATH="infrastructure/cloudwatch-monitoring.yaml"

if [[ -z "${ALERT_EMAIL}" ]]; then
  echo "Usage: $0 [stack-name] <alert-email>"
  echo "Or set ALERT_EMAIL in environment."
  exit 1
fi

echo "Deploying CloudWatch monitoring stack '${STACK_NAME}'..."
aws cloudformation deploy \
  --stack-name "${STACK_NAME}" \
  --template-file "${TEMPLATE_PATH}" \
  --parameter-overrides \
    Namespace="${NAMESPACE}" \
    AlertEmail="${ALERT_EMAIL}" \
    AlarmPeriodSeconds="${ALARM_PERIOD_SECONDS}" \
    LowRequestThresholdPerMinute="${LOW_REQUEST_THRESHOLD_PER_MINUTE}"

echo "Deployment completed. Stack outputs:"
aws cloudformation describe-stacks \
  --stack-name "${STACK_NAME}" \
  --query "Stacks[0].Outputs[*].[OutputKey,OutputValue]" \
  --output table

echo "Note: Confirm the SNS email subscription from your inbox before alarms can notify you."
