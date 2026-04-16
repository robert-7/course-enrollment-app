#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_INFRA_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DOTENV_FILE="${ROOT_INFRA_DIR}/.env"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common_manual_stack_vars.sh"
# shellcheck source=infra/manual-removal/common_manual_stack_helpers.sh
source "${SCRIPT_DIR}/common_manual_stack_helpers.sh"

WAIT_TIMEOUT_SECONDS=900
WAIT_INTERVAL_SECONDS=10
ASSUME_YES=false
DELETE_OIDC_PROVIDER=false


usage() {
    cat <<'EOF'
Usage: bash infra/manual-removal/remove_manual_stack.sh [options]

Deletes the pre-CDK manually created AWS resources for the course enrollment
app and waits for dependent resources to disappear before continuing.

Options:
  --yes                    Skip the interactive confirmation prompt.
  --delete-oidc-provider   Also delete the GitHub OIDC provider for
                           token.actions.githubusercontent.com.
  --timeout SECONDS        Override the wait timeout (default: 900).
  --help                   Show this help text.

Notes:
  - This script does NOT delete MongoDB Atlas, Namecheap DNS, the ACM
    certificate, or GitHub repository secrets/variables.
  - The OIDC provider deletion is optional because it can be shared with other
    workloads in the same AWS account.
EOF
}

as_list() {
    local value="$1"
    if [[ -z "${value}" || "${value}" == "None" ]]; then
        return 0
    fi
    printf '%s\n' "${value}" | tr '\t' '\n' | sed '/^$/d'
}


wait_until() {
    local description="$1"
    local start_time
    start_time="$(date +%s)"
    shift

    while true; do
        if "$@"; then
            return 0
        fi

        if (( "$(date +%s)" - start_time >= WAIT_TIMEOUT_SECONDS )); then
            die "Timed out while waiting for ${description}"
        fi

        sleep "${WAIT_INTERVAL_SECONDS}"
    done
}


current_account_id() {
    aws sts get-caller-identity --query 'Account' --output text
}


load_balancer_arn() {
    aws_regional elbv2 describe-load-balancers \
        --names "${ALB_NAME}" \
        --query 'LoadBalancers[0].LoadBalancerArn' \
        --output text \
        2>/dev/null || true
}


target_group_arn() {
    aws_regional elbv2 describe-target-groups \
        --names "${TARGET_GROUP_NAME}" \
        --query 'TargetGroups[0].TargetGroupArn' \
        --output text \
        2>/dev/null || true
}


ecs_service_status() {
    aws_regional ecs describe-services \
        --cluster "${ECS_CLUSTER_NAME}" \
        --services "${ECS_SERVICE_NAME}" \
        --query 'services[0].status' \
        --output text \
        2>/dev/null || true
}


ecs_cluster_status() {
    aws_regional ecs describe-clusters \
        --clusters "${ECS_CLUSTER_NAME}" \
        --query 'clusters[0].status' \
        --output text \
        2>/dev/null || true
}


task_definition_arns() {
    aws_regional ecs list-task-definitions \
        --family-prefix "${APP_NAME}" \
        --status ACTIVE \
        --query 'taskDefinitionArns' \
        --output text \
        2>/dev/null || true
}


security_group_id() {
    local group_name="$1"
    local query='SecurityGroups[0].GroupId'
    local args=(
        ec2 describe-security-groups
        --filters
        "Name=group-name,Values=${group_name}"
    )

    if [[ -n "${VPC_ID}" ]]; then
        args+=("Name=vpc-id,Values=${VPC_ID}")
    fi

    aws_regional "${args[@]}" --query "${query}" --output text 2>/dev/null || true
}


log_group_exists() {
    local output
    output="$(aws_regional logs describe-log-groups \
        --log-group-name-prefix "${LOG_GROUP_NAME}" \
        --query 'logGroups[?logGroupName==`'"${LOG_GROUP_NAME}"'`].logGroupName' \
        --output text \
        2>/dev/null || true)"
    [[ -n "${output}" && "${output}" != "None" ]]
}


ssm_parameter_exists() {
    local name="$1"
    local output
    output="$(aws_regional ssm get-parameter \
        --name "${name}" \
        --query 'Parameter.Name' \
        --output text \
        2>/dev/null || true)"
    [[ -n "${output}" && "${output}" != "None" ]]
}


role_exists() {
    local role_name="$1"
    local output
    output="$(aws iam get-role \
        --role-name "${role_name}" \
        --query 'Role.RoleName' \
        --output text \
        2>/dev/null || true)"
    [[ -n "${output}" && "${output}" != "None" ]]
}


oidc_provider_arn() {
    local arn_list
    local arn
    local url

    arn_list="$(aws iam list-open-id-connect-providers \
        --query 'OpenIDConnectProviderList[].Arn' \
        --output text \
        2>/dev/null || true)"

    while IFS= read -r arn; do
        [[ -z "${arn}" ]] && continue
        url="$(aws iam get-open-id-connect-provider \
            --open-id-connect-provider-arn "${arn}" \
            --query 'Url' \
            --output text \
            2>/dev/null || true)"
        if [[ "${url}" == "${OIDC_PROVIDER_URL}" ]]; then
            printf '%s\n' "${arn}"
            return 0
        fi
    done < <(as_list "${arn_list}")
}


ecr_repository_exists() {
    local output
    output="$(aws_regional ecr describe-repositories \
        --repository-names "${APP_NAME}" \
        --query 'repositories[0].repositoryName' \
        --output text \
        2>/dev/null || true)"
    [[ -n "${output}" && "${output}" != "None" ]]
}


service_gone() {
    local status
    status="$(ecs_service_status)"
    [[ -z "${status}" || "${status}" == "None" || "${status}" == "INACTIVE" ]]
}


service_scaled_to_zero() {
    local output
    output="$(aws_regional ecs describe-services \
        --cluster "${ECS_CLUSTER_NAME}" \
        --services "${ECS_SERVICE_NAME}" \
        --query 'services[0].[desiredCount,runningCount,pendingCount]' \
        --output text \
        2>/dev/null || true)"
    [[ "${output}" == $'0\t0\t0' ]]
}


cluster_gone() {
    local status
    status="$(ecs_cluster_status)"
    [[ -z "${status}" || "${status}" == "None" || "${status}" == "INACTIVE" ]]
}


load_balancer_gone() {
    local arn
    arn="$(load_balancer_arn)"
    [[ -z "${arn}" || "${arn}" == "None" ]]
}


target_group_gone() {
    local arn
    arn="$(target_group_arn)"
    [[ -z "${arn}" || "${arn}" == "None" ]]
}


security_group_gone() {
    local group_name="$1"
    local group_id
    group_id="$(security_group_id "${group_name}")"
    [[ -z "${group_id}" || "${group_id}" == "None" ]]
}


log_group_gone() {
    ! log_group_exists
}


ssm_parameter_gone() {
    local name="$1"
    ! ssm_parameter_exists "${name}"
}


role_gone() {
    local role_name="$1"
    ! role_exists "${role_name}"
}


oidc_provider_gone() {
    [[ -z "$(oidc_provider_arn)" ]]
}


ecr_repository_gone() {
    ! ecr_repository_exists
}


stack_gone() {
    local stack_name="$1"
    ! stack_exists_by_name "${stack_name}"
}


confirm() {
    if [[ "${ASSUME_YES}" == "true" ]]; then
        return 0
    fi

    cat <<EOF
About to delete the pre-CDK manual AWS resources for ${APP_NAME}.

Account: ${CURRENT_ACCOUNT_ID}
Region:  ${AWS_REGION}
VPC:     ${VPC_ID:-<not-set>}

This script deletes:
- ECS service ${ECS_SERVICE_NAME}
- ECS cluster ${ECS_CLUSTER_NAME}
- ECS task definition revisions for family ${APP_NAME}
- ALB ${ALB_NAME}
- target group ${TARGET_GROUP_NAME}
- security groups ${ALB_SECURITY_GROUP_NAME} and ${TASK_SECURITY_GROUP_NAME}
- CloudWatch log group ${LOG_GROUP_NAME}
- SSM parameters ${SECRET_KEY_PARAMETER_NAME} and ${MONGO_URI_PARAMETER_NAME}
- IAM roles ${GITHUB_ACTIONS_ROLE_NAME} and ${TASK_EXECUTION_ROLE_NAME}
- ECR repository ${APP_NAME}
- GitHub OIDC provider (${OIDC_PROVIDER_URL}) only if --delete-oidc-provider is set

It does NOT delete MongoDB Atlas, Namecheap DNS, the ACM certificate, or GitHub
repository secrets/variables.
EOF

    read -r -p "Type 'delete manual stack' to continue: " confirmation
    [[ "${confirmation}" == "delete manual stack" ]] || die "Aborted."
}


delete_ecs_service() {
    if service_gone; then
        log_info "ECS service ${ECS_SERVICE_NAME} is already absent."
        return 0
    fi

    log_info "Scaling ECS service ${ECS_SERVICE_NAME} to zero."
    aws_regional ecs update-service \
        --cluster "${ECS_CLUSTER_NAME}" \
        --service "${ECS_SERVICE_NAME}" \
        --desired-count 0 \
        >/dev/null

    wait_until "ECS service ${ECS_SERVICE_NAME} to reach zero tasks" service_scaled_to_zero

    log_info "Deleting ECS service ${ECS_SERVICE_NAME}."
    aws_regional ecs delete-service \
        --cluster "${ECS_CLUSTER_NAME}" \
        --service "${ECS_SERVICE_NAME}" \
        --force \
        >/dev/null

    wait_until "ECS service ${ECS_SERVICE_NAME} deletion" service_gone
}


delete_ecs_task_definitions() {
    local arns
    local arn

    arns="$(task_definition_arns)"
    if [[ -z "${arns}" || "${arns}" == "None" ]]; then
        log_info "No active ECS task definition revisions found for family ${APP_NAME}."
        return 0
    fi

    while IFS= read -r arn; do
        [[ -z "${arn}" ]] && continue
        log_info "Deregistering ECS task definition ${arn}."
        aws_regional ecs deregister-task-definition \
            --task-definition "${arn}" \
            >/dev/null
    done < <(as_list "${arns}")
}


delete_ecs_cluster() {
    if cluster_gone; then
        log_info "ECS cluster ${ECS_CLUSTER_NAME} is already absent."
        return 0
    fi

    log_info "Deleting ECS cluster ${ECS_CLUSTER_NAME}."
    aws_regional ecs delete-cluster --cluster "${ECS_CLUSTER_NAME}" >/dev/null
    wait_until "ECS cluster ${ECS_CLUSTER_NAME} deletion" cluster_gone
}


delete_load_balancer() {
    local lb_arn
    local listener_arns
    local listener_arn

    lb_arn="$(load_balancer_arn)"
    if [[ -z "${lb_arn}" || "${lb_arn}" == "None" ]]; then
        log_info "Load balancer ${ALB_NAME} is already absent."
        return 0
    fi

    listener_arns="$(aws_regional elbv2 describe-listeners \
        --load-balancer-arn "${lb_arn}" \
        --query 'Listeners[].ListenerArn' \
        --output text \
        2>/dev/null || true)"
    while IFS= read -r listener_arn; do
        [[ -z "${listener_arn}" ]] && continue
        log_info "Deleting listener ${listener_arn}."
        aws_regional elbv2 delete-listener \
            --listener-arn "${listener_arn}" \
            >/dev/null || true
    done < <(as_list "${listener_arns}")

    log_info "Deleting load balancer ${ALB_NAME}."
    aws_regional elbv2 delete-load-balancer \
        --load-balancer-arn "${lb_arn}" \
        >/dev/null

    aws_regional elbv2 wait load-balancers-deleted \
        --load-balancer-arns "${lb_arn}" \
        >/dev/null 2>&1 || wait_until "load balancer ${ALB_NAME} deletion" load_balancer_gone
}


delete_target_group() {
    local tg_arn

    tg_arn="$(target_group_arn)"
    if [[ -z "${tg_arn}" || "${tg_arn}" == "None" ]]; then
        log_info "Target group ${TARGET_GROUP_NAME} is already absent."
        return 0
    fi

    log_info "Deleting target group ${TARGET_GROUP_NAME}."
    aws_regional elbv2 delete-target-group \
        --target-group-arn "${tg_arn}" \
        >/dev/null
    wait_until "target group ${TARGET_GROUP_NAME} deletion" target_group_gone
}


delete_security_group() {
    local group_name="$1"
    local group_id
    local start_time

    group_id="$(security_group_id "${group_name}")"
    if [[ -z "${group_id}" || "${group_id}" == "None" ]]; then
        log_info "Security group ${group_name} is already absent."
        return 0
    fi

    log_info "Deleting security group ${group_name} (${group_id})."
    start_time="$(date +%s)"
    while true; do
        if aws_regional ec2 delete-security-group --group-id "${group_id}" >/dev/null 2>&1; then
            break
        fi

        if security_group_gone "${group_name}"; then
            return 0
        fi

        if (( "$(date +%s)" - start_time >= WAIT_TIMEOUT_SECONDS )); then
            die "Timed out deleting security group ${group_name}. It may still have dependencies."
        fi

        log_warn "Security group ${group_name} still has dependencies. Waiting before retrying."
        sleep "${WAIT_INTERVAL_SECONDS}"
    done

    wait_until "security group ${group_name} deletion" security_group_gone "${group_name}"
}


delete_log_group() {
    if ! log_group_exists; then
        log_info "Log group ${LOG_GROUP_NAME} is already absent."
        return 0
    fi

    log_info "Deleting log group ${LOG_GROUP_NAME}."
    aws_regional logs delete-log-group --log-group-name "${LOG_GROUP_NAME}" >/dev/null
    wait_until "log group ${LOG_GROUP_NAME} deletion" log_group_gone
}


delete_ssm_parameter() {
    local parameter_name="$1"

    if ! ssm_parameter_exists "${parameter_name}"; then
        log_info "SSM parameter ${parameter_name} is already absent."
        return 0
    fi

    log_info "Deleting SSM parameter ${parameter_name}."
    aws_regional ssm delete-parameter --name "${parameter_name}" >/dev/null
    wait_until "SSM parameter ${parameter_name} deletion" ssm_parameter_gone "${parameter_name}"
}


delete_iam_role() {
    local role_name="$1"
    local attached_policies
    local attached_policy_arn
    local inline_policies
    local inline_policy_name

    if ! role_exists "${role_name}"; then
        log_info "IAM role ${role_name} is already absent."
        return 0
    fi

    attached_policies="$(aws iam list-attached-role-policies \
        --role-name "${role_name}" \
        --query 'AttachedPolicies[].PolicyArn' \
        --output text \
        2>/dev/null || true)"
    while IFS= read -r attached_policy_arn; do
        [[ -z "${attached_policy_arn}" ]] && continue
        log_info "Detaching managed policy ${attached_policy_arn} from role ${role_name}."
        aws iam detach-role-policy \
            --role-name "${role_name}" \
            --policy-arn "${attached_policy_arn}" \
            >/dev/null
    done < <(as_list "${attached_policies}")

    inline_policies="$(aws iam list-role-policies \
        --role-name "${role_name}" \
        --query 'PolicyNames' \
        --output text \
        2>/dev/null || true)"
    while IFS= read -r inline_policy_name; do
        [[ -z "${inline_policy_name}" ]] && continue
        log_info "Deleting inline policy ${inline_policy_name} from role ${role_name}."
        aws iam delete-role-policy \
            --role-name "${role_name}" \
            --policy-name "${inline_policy_name}" \
            >/dev/null
    done < <(as_list "${inline_policies}")

    log_info "Deleting IAM role ${role_name}."
    aws iam delete-role --role-name "${role_name}" >/dev/null
    wait_until "IAM role ${role_name} deletion" role_gone "${role_name}"
}


delete_oidc_provider() {
    local provider_arn

    if [[ "${DELETE_OIDC_PROVIDER}" != "true" ]]; then
        log_warn "Skipping OIDC provider deletion. Re-run with --delete-oidc-provider if you want to remove ${OIDC_PROVIDER_URL}."
        return 0
    fi

    provider_arn="$(oidc_provider_arn)"
    if [[ -z "${provider_arn}" ]]; then
        log_info "OIDC provider ${OIDC_PROVIDER_URL} is already absent."
        return 0
    fi

    log_info "Deleting OIDC provider ${provider_arn}."
    aws iam delete-open-id-connect-provider \
        --open-id-connect-provider-arn "${provider_arn}" \
        >/dev/null
    wait_until "OIDC provider ${OIDC_PROVIDER_URL} deletion" oidc_provider_gone
}


delete_ecr_repository() {
    if ! ecr_repository_exists; then
        log_info "ECR repository ${APP_NAME} is already absent."
        return 0
    fi

    log_info "Deleting ECR repository ${APP_NAME} and any remaining images."
    aws_regional ecr delete-repository \
        --repository-name "${APP_NAME}" \
        --force \
        >/dev/null
    wait_until "ECR repository ${APP_NAME} deletion" ecr_repository_gone
}


while (($# > 0)); do
    case "$1" in
        --yes)
            ASSUME_YES=true
            ;;
        --delete-oidc-provider)
            DELETE_OIDC_PROVIDER=true
            ;;
        --timeout)
            shift
            [[ $# -gt 0 ]] || die "Missing value for --timeout"
            WAIT_TIMEOUT_SECONDS="$1"
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            die "Unknown option: $1"
            ;;
    esac
    shift
done

require_cmd aws

export AWS_PAGER=""
AWS_REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-$(dotenv_value CDK_DEFAULT_REGION "${DOTENV_FILE}")}}"
AWS_REGION="${AWS_REGION:-us-east-1}"
export AWS_REGION
export AWS_DEFAULT_REGION="${AWS_REGION}"

VPC_ID="$(dotenv_value CDK_VPC_ID "${DOTENV_FILE}")"
EXPECTED_ACCOUNT_ID="$(dotenv_value CDK_DEFAULT_ACCOUNT "${DOTENV_FILE}")"
CURRENT_ACCOUNT_ID="$(current_account_id)"

if [[ -n "${EXPECTED_ACCOUNT_ID}" && "${CURRENT_ACCOUNT_ID}" != "${EXPECTED_ACCOUNT_ID}" ]]; then
    die "Authenticated AWS account (${CURRENT_ACCOUNT_ID}) does not match infra/.env account (${EXPECTED_ACCOUNT_ID})."
fi

confirm

delete_cloudformation_stack() {
    local stack_name="$1"

    if ! stack_exists_by_name "${stack_name}"; then
        log_info "CloudFormation stack ${stack_name} is already absent."
        return 0
    fi

    log_info "Deleting CloudFormation stack ${stack_name}."
    aws cloudformation delete-stack --stack-name "${stack_name}"
    aws cloudformation wait stack-delete-complete --stack-name "${stack_name}" >/dev/null 2>&1 || \
        wait_until "CloudFormation stack ${stack_name} deletion" stack_gone "${stack_name}"
}


delete_discovered_cloudformation_stacks() {
    local stack_name
    local service_stacks
    local cluster_stacks

    service_stacks="$(stack_names_with_prefix "${CFN_SERVICE_STACK_PREFIX}")"
    while IFS= read -r stack_name; do
        [[ -z "${stack_name}" || "${stack_name}" == "None" ]] && continue
        delete_cloudformation_stack "${stack_name}"
    done < <(as_list "${service_stacks}")

    cluster_stacks="$(stack_names_with_prefix "${CFN_CLUSTER_STACK_PREFIX}")"
    while IFS= read -r stack_name; do
        [[ -z "${stack_name}" || "${stack_name}" == "None" ]] && continue
        delete_cloudformation_stack "${stack_name}"
    done < <(as_list "${cluster_stacks}")

    if stack_exists_by_name "${CDK_REBUILD_STACK_NAME}"; then
        delete_cloudformation_stack "${CDK_REBUILD_STACK_NAME}"
    fi
}

delete_discovered_cloudformation_stacks
delete_ecs_service
delete_ecs_task_definitions
delete_ecs_cluster
delete_load_balancer
delete_target_group
delete_security_group "${ALB_SECURITY_GROUP_NAME}"
delete_security_group "${TASK_SECURITY_GROUP_NAME}"
delete_log_group
delete_ssm_parameter "${SECRET_KEY_PARAMETER_NAME}"
delete_ssm_parameter "${MONGO_URI_PARAMETER_NAME}"
delete_iam_role "${GITHUB_ACTIONS_ROLE_NAME}"
delete_iam_role "${TASK_EXECUTION_ROLE_NAME}"
delete_oidc_provider
delete_ecr_repository

log_success "Manual AWS stack teardown completed."
