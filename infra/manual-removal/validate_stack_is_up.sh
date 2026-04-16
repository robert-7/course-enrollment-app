#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_INFRA_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DOTENV_FILE="${ROOT_INFRA_DIR}/.env"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common_manual_stack_vars.sh"
# shellcheck source=infra/manual-removal/common_manual_stack_helpers.sh
source "${SCRIPT_DIR}/common_manual_stack_helpers.sh"

AWS_REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"
export AWS_REGION
export AWS_DEFAULT_REGION="${AWS_REGION}"
export AWS_PAGER=""


require_cmd aws

ACCOUNT_ID="$(aws sts get-caller-identity --query 'Account' --output text)"
EXPECTED_ACCOUNT_ID="$(dotenv_value CDK_DEFAULT_ACCOUNT "${DOTENV_FILE}")"
if [[ -n "${EXPECTED_ACCOUNT_ID}" && "${ACCOUNT_ID}" != "${EXPECTED_ACCOUNT_ID}" ]]; then
    die "Authenticated AWS account (${ACCOUNT_ID}) does not match infra/.env account (${EXPECTED_ACCOUNT_ID})."
fi

SERVICE_STATUS="$(aws_regional ecs describe-services \
    --cluster "${ECS_CLUSTER_NAME}" \
    --services "${ECS_SERVICE_NAME}" \
    --query 'services[0].status' \
    --output text 2>/dev/null || true)"
[[ "${SERVICE_STATUS}" == "ACTIVE" ]] || die "ECS service ${ECS_SERVICE_NAME} is not ACTIVE."
log_success "ECS service ${ECS_SERVICE_NAME} is ACTIVE."

SERVICE_COUNTS="$(aws_regional ecs describe-services \
    --cluster "${ECS_CLUSTER_NAME}" \
    --services "${ECS_SERVICE_NAME}" \
    --query 'services[0].[desiredCount,runningCount,pendingCount]' \
    --output text 2>/dev/null || true)"
[[ "${SERVICE_COUNTS}" == $'1\t1\t0' ]] || die "ECS service counts are not desired=1 running=1 pending=0 (got: ${SERVICE_COUNTS})."
log_success "ECS service counts are desired=1 running=1 pending=0."

LOAD_BALANCER_STATE="$(aws_regional elbv2 describe-load-balancers \
    --names "${ALB_NAME}" \
    --query 'LoadBalancers[0].State.Code' \
    --output text 2>/dev/null || true)"
[[ "${LOAD_BALANCER_STATE}" == "active" ]] || die "ALB ${ALB_NAME} is not active."
log_success "ALB ${ALB_NAME} is active."

TARGET_GROUP_HEALTH="$(aws_regional elbv2 describe-target-health \
    --target-group-arn "$(aws_regional elbv2 describe-target-groups \
        --names "${TARGET_GROUP_NAME}" \
        --query 'TargetGroups[0].TargetGroupArn' \
        --output text)" \
    --query 'TargetHealthDescriptions[0].TargetHealth.State' \
    --output text 2>/dev/null || true)"
[[ "${TARGET_GROUP_HEALTH}" == "healthy" ]] || die "Target group ${TARGET_GROUP_NAME} does not have a healthy target."
log_success "Target group ${TARGET_GROUP_NAME} has a healthy target."

SECRET_KEY_PRESENT="$(aws_regional ssm get-parameter \
    --name "${SECRET_KEY_PARAMETER_NAME}" \
    --query 'Parameter.Name' \
    --output text 2>/dev/null || true)"
[[ "${SECRET_KEY_PRESENT}" == "${SECRET_KEY_PARAMETER_NAME}" ]] || die "SSM parameter ${SECRET_KEY_PARAMETER_NAME} is missing."
log_success "SSM parameter ${SECRET_KEY_PARAMETER_NAME} is present."

MONGO_URI_PRESENT="$(aws_regional ssm get-parameter \
    --name "${MONGO_URI_PARAMETER_NAME}" \
    --query 'Parameter.Name' \
    --output text 2>/dev/null || true)"
[[ "${MONGO_URI_PRESENT}" == "${MONGO_URI_PARAMETER_NAME}" ]] || die "SSM parameter ${MONGO_URI_PARAMETER_NAME} is missing."
log_success "SSM parameter ${MONGO_URI_PARAMETER_NAME} is present."

TASK_EXECUTION_ROLE_PRESENT="$(aws iam get-role \
    --role-name "${TASK_EXECUTION_ROLE_NAME}" \
    --query 'Role.RoleName' \
    --output text 2>/dev/null || true)"
[[ "${TASK_EXECUTION_ROLE_PRESENT}" == "${TASK_EXECUTION_ROLE_NAME}" ]] || die "IAM role ${TASK_EXECUTION_ROLE_NAME} is missing."
log_success "IAM role ${TASK_EXECUTION_ROLE_NAME} is present."

GITHUB_ACTIONS_ROLE_PRESENT="$(aws iam get-role \
    --role-name "${GITHUB_ACTIONS_ROLE_NAME}" \
    --query 'Role.RoleName' \
    --output text 2>/dev/null || true)"
[[ "${GITHUB_ACTIONS_ROLE_PRESENT}" == "${GITHUB_ACTIONS_ROLE_NAME}" ]] || die "IAM role ${GITHUB_ACTIONS_ROLE_NAME} is missing."
log_success "IAM role ${GITHUB_ACTIONS_ROLE_NAME} is present."

REPOSITORY_PRESENT="$(aws_regional ecr describe-repositories \
    --repository-names "${APP_NAME}" \
    --query 'repositories[0].repositoryName' \
    --output text 2>/dev/null || true)"
[[ "${REPOSITORY_PRESENT}" == "${APP_NAME}" ]] || die "ECR repository ${APP_NAME} is missing."
log_success "ECR repository ${APP_NAME} is present."

LOAD_BALANCER_DNS="$(aws_regional elbv2 describe-load-balancers \
    --names "${ALB_NAME}" \
    --query 'LoadBalancers[0].DNSName' \
    --output text)"

log_success "AWS stack validation completed successfully."
log_info "ALB DNS: ${LOAD_BALANCER_DNS}"
