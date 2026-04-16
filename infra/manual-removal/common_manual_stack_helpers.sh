#!/usr/bin/env bash

color_enabled() {
    [[ -t 1 && -z "${NO_COLOR:-}" ]]
}


_log_with_color() {
    local label="$1"
    local color_code="$2"
    local message="$3"

    if color_enabled; then
        printf '\033[%sm[%s]\033[0m %s\n' "${color_code}" "${label}" "${message}"
    else
        printf '[%s] %s\n' "${label}" "${message}"
    fi
}


log_info() {
    _log_with_color "INFO" "34" "$*"
}


log_success() {
    _log_with_color "SUCCESS" "32" "$*"
}


log_warn() {
    if color_enabled; then
        printf '\033[33m[WARN]\033[0m %s\n' "$*" >&2
    else
        printf '[WARN] %s\n' "$*" >&2
    fi
}


log_error() {
    if color_enabled; then
        printf '\033[31m[ERROR]\033[0m %s\n' "$*" >&2
    else
        printf '[ERROR] %s\n' "$*" >&2
    fi
}


die() {
    log_error "$*"
    exit 1
}


require_cmd() {
    command -v "$1" >/dev/null 2>&1 || die "Required command not found: $1"
}


dotenv_value() {
    local key="$1"
    local file="$2"

    if [[ ! -f "${file}" ]]; then
        return 0
    fi

    grep -E "^${key}=" "${file}" | tail -n 1 | cut -d '=' -f 2-
}


aws_regional() {
    aws --region "${AWS_REGION}" "$@"
}


stack_names_with_prefix() {
    local prefix="$1"

    aws cloudformation list-stacks \
        --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE UPDATE_ROLLBACK_COMPLETE ROLLBACK_COMPLETE DELETE_FAILED CREATE_FAILED ROLLBACK_FAILED UPDATE_ROLLBACK_FAILED \
        --query "StackSummaries[?starts_with(StackName, \`${prefix}\`)].StackName" \
        --output text 2>/dev/null || true
}


stack_exists_by_name() {
    local stack_name="$1"
    local output

    output="$(aws cloudformation list-stacks \
        --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE UPDATE_ROLLBACK_COMPLETE ROLLBACK_COMPLETE DELETE_FAILED CREATE_FAILED ROLLBACK_FAILED UPDATE_ROLLBACK_FAILED \
        --query "StackSummaries[?StackName==\`${stack_name}\`].StackName | [0]" \
        --output text 2>/dev/null || true)"
    [[ -n "${output}" && "${output}" != "None" ]]
}
