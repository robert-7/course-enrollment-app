#!/usr/bin/env bash

# shellcheck disable=SC2034

APP_NAME="course-enrollment-app"
ECS_CLUSTER_NAME="course-enrollment-app"
ECS_SERVICE_NAME="course-enrollment-app-svc"
ALB_NAME="course-enrollment-app-alb"
TARGET_GROUP_NAME="course-enrollment-app-tg"
ALB_SECURITY_GROUP_NAME="alb-sg"
TASK_SECURITY_GROUP_NAME="ecs-tasks-sg"
LOG_GROUP_NAME="/ecs/course-enrollment-app"
SECRET_KEY_PARAMETER_NAME="/course-enrollment-app/SECRET_KEY"
MONGO_URI_PARAMETER_NAME="/course-enrollment-app/MONGO_URI"
GITHUB_ACTIONS_ROLE_NAME="GitHubActions-CourseEnrollmentApp"
TASK_EXECUTION_ROLE_NAME="ECSTaskExecutionRole-CourseEnrollmentApp"
OIDC_PROVIDER_URL="token.actions.githubusercontent.com"
CFN_CLUSTER_STACK_PREFIX="Infra-ECS-Cluster-${ECS_CLUSTER_NAME}-"
CFN_SERVICE_STACK_PREFIX="ECS-Console-V2-Service-${ECS_SERVICE_NAME}-${ECS_CLUSTER_NAME}-"
CDK_REBUILD_STACK_NAME="CourseEnrollmentAppStack"
