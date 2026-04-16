#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common_manual_stack_vars.sh"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common_manual_stack_helpers.sh"

AWS_REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"
export AWS_REGION
export AWS_DEFAULT_REGION="${AWS_REGION}"
export AWS_PAGER=""


resource_absent() {
    local description="$1"
    shift

    if "$@" >/dev/null 2>&1; then
        die "${description} still exists."
    fi

    log_success "${description} is absent."
}


no_matching_stacks_for_prefix() {
    local prefix="$1"
    local output

    output="$(stack_names_with_prefix "${prefix}")"
    [[ -z "${output}" || "${output}" == "None" ]]
}


require_cmd aws

aws sts get-caller-identity >/dev/null

service_absent() {
    local output
    output="$(aws_regional ecs describe-services \
        --cluster "${ECS_CLUSTER_NAME}" \
        --services "${ECS_SERVICE_NAME}" \
        --query 'services[0].status' \
        --output text 2>/dev/null || true)"
    [[ -z "${output}" || "${output}" == "None" || "${output}" == "INACTIVE" ]]
}

if service_absent; then
    log_success "ECS service ${ECS_SERVICE_NAME} is absent."
else
    die "ECS service ${ECS_SERVICE_NAME} still exists."
fi

resource_absent \
    "ALB ${ALB_NAME}" \
    aws_regional elbv2 describe-load-balancers \
        --names "${ALB_NAME}"

resource_absent \
    "ECR repository ${APP_NAME}" \
    aws_regional ecr describe-repositories \
        --repository-names "${APP_NAME}"

resource_absent \
    "SSM parameter ${SECRET_KEY_PARAMETER_NAME}" \
    aws_regional ssm get-parameter \
        --name "${SECRET_KEY_PARAMETER_NAME}"

resource_absent \
    "IAM role ${GITHUB_ACTIONS_ROLE_NAME}" \
    aws iam get-role \
        --role-name "${GITHUB_ACTIONS_ROLE_NAME}"

if no_matching_stacks_for_prefix "${CFN_SERVICE_STACK_PREFIX}"; then
    log_success "No leftover CloudFormation ECS service stacks remain."
else
    die "A leftover CloudFormation ECS service stack still exists."
fi

if no_matching_stacks_for_prefix "${CFN_CLUSTER_STACK_PREFIX}"; then
    log_success "No leftover CloudFormation ECS cluster stacks remain."
else
    die "A leftover CloudFormation ECS cluster stack still exists."
fi

if stack_exists_by_name "${CDK_REBUILD_STACK_NAME}"; then
    die "CloudFormation stack ${CDK_REBUILD_STACK_NAME} still exists."
else
    log_success "CloudFormation stack ${CDK_REBUILD_STACK_NAME} is absent."
fi

log_success "Manual stack teardown verification completed successfully."
