#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_INFRA_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DOTENV_FILE="${ROOT_INFRA_DIR}/.env"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common_manual_stack_vars.sh"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/common_manual_stack_helpers.sh"

AWS_REGION="${AWS_REGION:-${AWS_DEFAULT_REGION:-us-east-1}}"
export AWS_REGION
export AWS_DEFAULT_REGION="${AWS_REGION}"
export AWS_PAGER=""


require_cmd aws
require_cmd docker
require_cmd cdk

ACCOUNT_ID="$(aws sts get-caller-identity --query 'Account' --output text)"
EXPECTED_ACCOUNT_ID="$(dotenv_value CDK_DEFAULT_ACCOUNT "${DOTENV_FILE}")"
if [[ -n "${EXPECTED_ACCOUNT_ID}" && "${ACCOUNT_ID}" != "${EXPECTED_ACCOUNT_ID}" ]]; then
    die "Authenticated AWS account (${ACCOUNT_ID}) does not match infra/.env account (${EXPECTED_ACCOUNT_ID})."
fi
log_success "Authenticated AWS account matches infra/.env."

if ! docker info >/dev/null 2>&1; then
    die "Docker is not responding. Start Docker before the first CDK deploy."
fi
log_success "Docker is available."

bash "${SCRIPT_DIR}/validate_manual_stack_teardown_completed.sh"

CERTIFICATE_ARN="$(dotenv_value CDK_CERTIFICATE_ARN "${DOTENV_FILE}")"
[[ -n "${CERTIFICATE_ARN}" ]] || die "CDK_CERTIFICATE_ARN is missing from infra/.env."

CERTIFICATE_STATUS="$(aws_regional acm describe-certificate \
    --certificate-arn "${CERTIFICATE_ARN}" \
    --query 'Certificate.Status' \
    --output text 2>/dev/null || true)"
[[ "${CERTIFICATE_STATUS}" == "ISSUED" ]] || die "ACM certificate ${CERTIFICATE_ARN} is not ISSUED."
log_success "ACM certificate is ISSUED."

CONFIGURED_OIDC_ARN="$(dotenv_value CDK_GITHUB_OIDC_PROVIDER_ARN "${DOTENV_FILE}")"
EXISTING_OIDC_ARN="$(
    aws iam list-open-id-connect-providers \
        --query "OpenIDConnectProviderList[?Arn=='arn:aws:iam::${ACCOUNT_ID}:oidc-provider/${OIDC_PROVIDER_URL}'].Arn | [0]" \
        --output text 2>/dev/null || true
)"

if [[ "${EXISTING_OIDC_ARN}" == "None" ]]; then
    EXISTING_OIDC_ARN=""
fi

if [[ -n "${EXISTING_OIDC_ARN}" ]]; then
    [[ -n "${CONFIGURED_OIDC_ARN}" ]] || die "GitHub OIDC provider still exists in AWS. Set CDK_GITHUB_OIDC_PROVIDER_ARN in infra/.env before deploy."
    [[ "${CONFIGURED_OIDC_ARN}" == "${EXISTING_OIDC_ARN}" ]] || die "CDK_GITHUB_OIDC_PROVIDER_ARN does not match the existing GitHub OIDC provider ARN (${EXISTING_OIDC_ARN})."
    log_success "CDK is configured to reuse the existing GitHub OIDC provider."
else
    if [[ -n "${CONFIGURED_OIDC_ARN}" ]]; then
        die "CDK_GITHUB_OIDC_PROVIDER_ARN is set, but that OIDC provider is not present in AWS."
    fi
    log_success "No existing GitHub OIDC provider detected; CDK will create it."
fi

pushd "${ROOT_INFRA_DIR}" >/dev/null
cdk synth >/dev/null
popd >/dev/null
log_success "cdk synth completed successfully."

log_success "CDK pre-deploy validation completed successfully."
