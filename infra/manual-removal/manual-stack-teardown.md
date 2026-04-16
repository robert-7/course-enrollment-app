# Manual AWS Stack Teardown

This document describes how to manually remove the **pre-CDK** AWS resources
for the Course Enrollment App if you do not want to use
[`remove_manual_stack.sh`](/home/robert/src/github.com/robert-7/course-enrollment-app/infra/manual-removal/remove_manual_stack.sh).
The shell scripts in this folder share their AWS resource names from
[`common_manual_stack_vars.sh`](/home/robert/src/github.com/robert-7/course-enrollment-app/infra/manual-removal/common_manual_stack_vars.sh)
and their common logging/AWS helper functions from
[`common_manual_stack_helpers.sh`](/home/robert/src/github.com/robert-7/course-enrollment-app/infra/manual-removal/common_manual_stack_helpers.sh)
so the teardown and verification logic stay aligned.

Use this only for the old manually created stack. Do **not** use it against a
CDK-managed environment unless you intentionally want to bypass CloudFormation.

## Validation Scripts

This folder now includes two complementary validation scripts:

- [`validate_stack_is_up.sh`](/home/robert/src/github.com/robert-7/course-enrollment-app/infra/manual-removal/validate_stack_is_up.sh)
  checks that the stack is currently up and healthy. Run this before teardown,
  and run it again after the CDK rebuild completes.
- [`validate_manual_stack_teardown_completed.sh`](/home/robert/src/github.com/robert-7/course-enrollment-app/infra/manual-removal/validate_manual_stack_teardown_completed.sh)
  checks that the old manual resources are gone after teardown.
- [`validate_cdk_predeploy.sh`](/home/robert/src/github.com/robert-7/course-enrollment-app/infra/manual-removal/validate_cdk_predeploy.sh)
  checks the post-teardown prerequisites for the first `cdk deploy`, including
  Docker, ACM certificate status, GitHub OIDC provider handling, and `cdk synth`.

## Assumptions

- You are already authenticated to AWS from your shell:

  ```bash
  aws login
  ```

- Your AWS CLI session is still valid:

  ```bash
  aws sts get-caller-identity
  ```

- You are pointed at the correct AWS account:
  expected account from `infra/.env`: `CDK_DEFAULT_ACCOUNT`
- You are working in `us-east-1`
- You understand this is destructive and intended to be run once for the
  manual-to-CDK cutover
- You have already preserved any values you still need later:
  `CDK_VPC_ID`, `CDK_PUBLIC_SUBNET_IDS`, `CDK_CERTIFICATE_ARN`,
  `CDK_SECRET_KEY`, and `CDK_MONGO_URI`

## Things Not To Delete

Leave these external dependencies alone:

- MongoDB Atlas cluster and data
- Namecheap DNS records
- ACM certificate and its DNS validation records
- GitHub repository secrets and variables unless you intentionally want to
  recreate them

## Resources To Remove

The manually created stack includes these AWS resources:

- CloudFormation console stacks that may own the ECS cluster/service names, such
  as `Infra-ECS-Cluster-course-enrollment-app-*` and
  `ECS-Console-V2-Service-course-enrollment-app-svc-course-enrollment-app-*`
- ECS service `course-enrollment-app-svc`
- ECS task definitions in family `course-enrollment-app`
- ECS cluster `course-enrollment-app`
- ALB `course-enrollment-app-alb`
- target group `course-enrollment-app-tg`
- security groups `alb-sg` and `ecs-tasks-sg`
- log group `/ecs/course-enrollment-app`
- SSM parameters `/course-enrollment-app/SECRET_KEY` and
  `/course-enrollment-app/MONGO_URI`
- IAM roles `GitHubActions-CourseEnrollmentApp` and
  `ECSTaskExecutionRole-CourseEnrollmentApp`
- GitHub OIDC provider for `token.actions.githubusercontent.com`
- ECR repository `course-enrollment-app`

## Manual Deletion Order

Delete resources in this order to avoid dependency errors:

1. Delete any leftover CloudFormation console stacks for the ECS cluster/service.
1. Scale ECS service to zero and delete it.
1. Deregister active ECS task definitions for family `course-enrollment-app`.
1. Delete the ECS cluster `course-enrollment-app`.
1. Delete the ALB listeners on ports `80` and `443`.
1. Delete the ALB `course-enrollment-app-alb`.
1. Delete the target group `course-enrollment-app-tg`.
1. Delete the security groups `alb-sg` and `ecs-tasks-sg`.
1. Delete the CloudWatch log group `/ecs/course-enrollment-app`.
1. Delete the SSM parameters `/course-enrollment-app/SECRET_KEY` and
   `/course-enrollment-app/MONGO_URI`.
1. Delete the IAM roles `GitHubActions-CourseEnrollmentApp` and
   `ECSTaskExecutionRole-CourseEnrollmentApp`.
1. Delete the GitHub OIDC provider for
   `token.actions.githubusercontent.com` only if nothing else in the account
   depends on it.
1. Delete the ECR repository `course-enrollment-app`.

## Recommended Verification

Before moving on to CDK deploy, run the dedicated verification script:

```bash
bash infra/manual-removal/validate_manual_stack_teardown_completed.sh
bash infra/manual-removal/validate_cdk_predeploy.sh
```

The first script checks that the main manual-stack resources are gone and exits
non-zero if any of them still exist. The second script verifies that the first
CDK deploy is actually ready to proceed.

## Next Step

After the manual stack is removed, the intended rebuild path is:

```bash
cd infra
cdk deploy CourseEnrollmentAppStack
```

For the first clean-room deploy, keep `CDK_BOOTSTRAP_USE_LOCAL_IMAGE=true` in
`infra/.env` so CDK can bootstrap the ECS service from a locally built Docker
image even though the rebuilt ECR repository starts empty. If the GitHub OIDC
provider from the manual stack still exists, set
`CDK_GITHUB_OIDC_PROVIDER_ARN` in `infra/.env` so CDK reuses it instead of
trying to create a duplicate provider.
