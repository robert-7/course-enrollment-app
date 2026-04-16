from pathlib import Path
from typing import Sequence

import aws_cdk as cdk
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_ecr as ecr
from aws_cdk import aws_ecs as ecs
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_iam as iam
from aws_cdk import aws_logs as logs
from aws_cdk import aws_ssm as ssm
from aws_cdk import CfnOutput
from aws_cdk import custom_resources as cr
from aws_cdk import RemovalPolicy
from constructs import Construct


class CourseEnrollmentAppStack(cdk.Stack):
    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        *,
        vpc_id: str,
        public_subnet_ids: Sequence[str],
        certificate_arn: str,
        image_tag: str,
        bootstrap_use_local_image: bool,
        secret_key_value: str,
        mongo_uri_value: str,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        app_name = "course-enrollment-app"
        service_name = "course-enrollment-app-svc"
        alb_name = "course-enrollment-app-alb"
        target_group_name = "course-enrollment-app-tg"
        alb_sg_name = "alb-sg"
        task_sg_name = "ecs-tasks-sg"
        log_group_name = "/ecs/course-enrollment-app"
        secret_key_parameter_name = "/course-enrollment-app/SECRET_KEY"
        mongo_uri_parameter_name = "/course-enrollment-app/MONGO_URI"

        vpc = ec2.Vpc.from_lookup(self, "Vpc", vpc_id=vpc_id)
        public_subnet_selection = ec2.SubnetSelection(
            subnet_filters=[ec2.SubnetFilter.by_ids(list(public_subnet_ids))]
        )
        repository_root = Path(__file__).resolve().parent.parent

        repository = ecr.Repository(
            self,
            "Repository",
            repository_name=app_name,
            image_tag_mutability=ecr.TagMutability.IMMUTABLE,
            image_scan_on_push=False,
            encryption=ecr.RepositoryEncryption.AES_256,
            removal_policy=RemovalPolicy.DESTROY,
            empty_on_delete=True,
        )

        oidc_provider = iam.OpenIdConnectProvider(
            self,
            "GitHubOidcProvider",
            url="https://token.actions.githubusercontent.com",
            client_ids=["sts.amazonaws.com"],
        )

        github_actions_role = iam.Role(
            self,
            "GitHubActionsRole",
            role_name="GitHubActions-CourseEnrollmentApp",
            description=(
                "Allows GitHub Actions on robert-7/course-enrollment-app main branch "
                "to push images to ECR and deploy to ECS."
            ),
            assumed_by=iam.FederatedPrincipal(
                oidc_provider.open_id_connect_provider_arn,
                conditions={
                    "StringEquals": {
                        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                    },
                    "StringLike": {
                        "token.actions.githubusercontent.com:sub": (
                            "repo:robert-7/course-enrollment-app:ref:refs/heads/main"
                        ),
                    },
                },
                assume_role_action="sts:AssumeRoleWithWebIdentity",
            ),
        )

        task_execution_role = iam.Role(
            self,
            "TaskExecutionRole",
            role_name="ECSTaskExecutionRole-CourseEnrollmentApp",
            description=(
                "Allows ECS tasks for course-enrollment-app to pull images from ECR, "
                "write logs to CloudWatch, and fetch SSM parameters."
            ),
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AmazonECSTaskExecutionRolePolicy"
                )
            ],
        )
        task_role = iam.Role(
            self,
            "TaskRole",
            description="Application task role for course-enrollment-app ECS tasks.",
            assumed_by=iam.ServicePrincipal("ecs-tasks.amazonaws.com"),
        )

        secret_key_parameter_resource = self._secure_string_parameter(
            "SecretKeyParameter",
            secret_key_parameter_name,
            secret_key_value,
            "Flask SECRET_KEY for course-enrollment-app production deployment",
        )
        mongo_uri_parameter_resource = self._secure_string_parameter(
            "MongoUriParameter",
            mongo_uri_parameter_name,
            mongo_uri_value,
            "MongoDB connection string for course-enrollment-app production deployment",
        )

        secret_key_parameter = (
            ssm.StringParameter.from_secure_string_parameter_attributes(
                self,
                "SecretKeyParameterReference",
                parameter_name=secret_key_parameter_name,
            )
        )
        mongo_uri_parameter = (
            ssm.StringParameter.from_secure_string_parameter_attributes(
                self,
                "MongoUriParameterReference",
                parameter_name=mongo_uri_parameter_name,
            )
        )

        task_execution_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameters"],
                resources=[
                    self._parameter_arn(secret_key_parameter_name),
                    self._parameter_arn(mongo_uri_parameter_name),
                ],
            )
        )

        log_group = logs.LogGroup(
            self,
            "ApplicationLogGroup",
            log_group_name=log_group_name,
            retention=logs.RetentionDays.ONE_MONTH,
            removal_policy=RemovalPolicy.DESTROY,
        )

        cluster = ecs.Cluster(
            self,
            "Cluster",
            cluster_name=app_name,
            vpc=vpc,
        )

        alb_security_group = ec2.SecurityGroup(
            self,
            "AlbSecurityGroup",
            vpc=vpc,
            security_group_name=alb_sg_name,
            description="ALB security group for course-enrollment-app",
            allow_all_outbound=False,
        )
        task_security_group = ec2.SecurityGroup(
            self,
            "TaskSecurityGroup",
            vpc=vpc,
            security_group_name=task_sg_name,
            description="ECS task security group for course-enrollment-app",
            allow_all_outbound=False,
        )

        alb_security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(80),
            "Allow HTTP traffic from the internet",
        )
        alb_security_group.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(443),
            "Allow HTTPS traffic from the internet",
        )
        alb_security_group.add_egress_rule(
            task_security_group,
            ec2.Port.tcp(5000),
            "Allow ALB traffic to ECS tasks",
        )

        task_security_group.add_ingress_rule(
            alb_security_group,
            ec2.Port.tcp(5000),
            "Allow the ALB to reach ECS tasks",
        )
        task_security_group.add_egress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(443),
            "Allow outbound HTTPS",
        )
        task_security_group.add_egress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(27017),
            "Allow outbound MongoDB Atlas traffic",
        )

        load_balancer = elbv2.ApplicationLoadBalancer(
            self,
            "ApplicationLoadBalancer",
            vpc=vpc,
            internet_facing=True,
            load_balancer_name=alb_name,
            security_group=alb_security_group,
            vpc_subnets=public_subnet_selection,
        )

        target_group = elbv2.ApplicationTargetGroup(
            self,
            "ApplicationTargetGroup",
            target_group_name=target_group_name,
            vpc=vpc,
            port=5000,
            protocol=elbv2.ApplicationProtocol.HTTP,
            target_type=elbv2.TargetType.IP,
            health_check=elbv2.HealthCheck(
                enabled=True,
                path="/index",
                healthy_http_codes="200",
                healthy_threshold_count=2,
                unhealthy_threshold_count=3,
                interval=cdk.Duration.seconds(30),
                timeout=cdk.Duration.seconds(5),
            ),
        )

        task_definition = ecs.FargateTaskDefinition(
            self,
            "TaskDefinition",
            family=app_name,
            cpu=256,
            memory_limit_mib=512,
            execution_role=task_execution_role,
            task_role=task_role,
        )
        if bootstrap_use_local_image:
            container_image = ecs.ContainerImage.from_asset(str(repository_root))
        else:
            if not image_tag:
                raise RuntimeError(
                    "CDK_IMAGE_TAG is required when "
                    "CDK_BOOTSTRAP_USE_LOCAL_IMAGE is false."
                )
            container_image = ecs.ContainerImage.from_ecr_repository(
                repository, tag=image_tag
            )

        container = task_definition.add_container(
            "ApplicationContainer",
            container_name=app_name,
            image=container_image,
            environment={"APP_ENV": "production"},
            secrets={
                "SECRET_KEY": ecs.Secret.from_ssm_parameter(secret_key_parameter),
                "MONGO_URI": ecs.Secret.from_ssm_parameter(mongo_uri_parameter),
            },
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="ecs",
                log_group=log_group,
            ),
        )
        container.add_port_mappings(
            ecs.PortMapping(
                container_port=5000,
                host_port=5000,
                protocol=ecs.Protocol.TCP,
                app_protocol=ecs.AppProtocol.http,
                name="course-enrollment-app-5000-tcp",
            )
        )

        task_definition.node.add_dependency(secret_key_parameter_resource)
        task_definition.node.add_dependency(mongo_uri_parameter_resource)

        service = ecs.FargateService(
            self,
            "Service",
            cluster=cluster,
            service_name=service_name,
            task_definition=task_definition,
            desired_count=1,
            assign_public_ip=True,
            security_groups=[task_security_group],
            vpc_subnets=public_subnet_selection,
            circuit_breaker=ecs.DeploymentCircuitBreaker(
                enable=True,
                rollback=True,
            ),
            min_healthy_percent=100,
            max_healthy_percent=200,
            enable_ecs_managed_tags=True,
        )

        target_group.add_target(
            service.load_balancer_target(
                container_name=app_name,
                container_port=5000,
            )
        )

        elbv2.CfnListener(
            self,
            "HttpsListener",
            load_balancer_arn=load_balancer.load_balancer_arn,
            port=443,
            protocol="HTTPS",
            certificates=[
                elbv2.CfnListener.CertificateProperty(certificate_arn=certificate_arn)
            ],
            ssl_policy="ELBSecurityPolicy-TLS13-1-2-Res-PQ-2025-09",
            default_actions=[
                elbv2.CfnListener.ActionProperty(
                    type="forward",
                    target_group_arn=target_group.target_group_arn,
                )
            ],
        )

        elbv2.CfnListener(
            self,
            "HttpRedirectListener",
            load_balancer_arn=load_balancer.load_balancer_arn,
            port=80,
            protocol="HTTP",
            default_actions=[
                elbv2.CfnListener.ActionProperty(
                    type="redirect",
                    redirect_config=elbv2.CfnListener.RedirectConfigProperty(
                        protocol="HTTPS",
                        port="443",
                        host="#{host}",
                        path="/#{path}",
                        query="#{query}",
                        status_code="HTTP_301",
                    ),
                )
            ],
        )

        github_actions_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ecr:GetAuthorizationToken"],
                resources=["*"],
            )
        )
        github_actions_role.add_to_policy(
            iam.PolicyStatement(
                actions=[
                    "ecr:BatchCheckLayerAvailability",
                    "ecr:InitiateLayerUpload",
                    "ecr:UploadLayerPart",
                    "ecr:CompleteLayerUpload",
                    "ecr:PutImage",
                ],
                resources=[repository.repository_arn],
            )
        )
        github_actions_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ecs:DescribeServices", "ecs:DescribeTaskDefinition"],
                resources=["*"],
            )
        )
        github_actions_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ecs:RegisterTaskDefinition"],
                resources=["*"],
            )
        )
        github_actions_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ecs:UpdateService"],
                resources=[self._ecs_service_arn(cluster.cluster_name, service_name)],
            )
        )
        github_actions_role.add_to_policy(
            iam.PolicyStatement(
                actions=["iam:PassRole"],
                resources=[task_execution_role.role_arn, task_role.role_arn],
            )
        )

        CfnOutput(
            self,
            "LoadBalancerDnsName",
            value=load_balancer.load_balancer_dns_name,
            description="DNS name for the application load balancer.",
        )
        CfnOutput(
            self,
            "GitHubActionsRoleArn",
            value=github_actions_role.role_arn,
            description="Role ARN for the GitHub Actions deploy role.",
        )
        CfnOutput(
            self,
            "EcrRepositoryUri",
            value=repository.repository_uri,
            description="Repository URI for the ECS application image.",
        )

    def _secure_string_parameter(
        self,
        construct_id: str,
        parameter_name: str,
        parameter_value: str,
        description: str,
    ) -> cr.AwsCustomResource:
        parameter_arn = self._parameter_arn(parameter_name)

        return cr.AwsCustomResource(
            self,
            construct_id,
            install_latest_aws_sdk=False,
            on_create=cr.AwsSdkCall(
                service="SSM",
                action="putParameter",
                parameters={
                    "Name": parameter_name,
                    "Description": description,
                    "Type": "SecureString",
                    "Value": parameter_value,
                    "Tier": "Standard",
                    "Overwrite": True,
                },
                physical_resource_id=cr.PhysicalResourceId.of(parameter_name),
            ),
            on_update=cr.AwsSdkCall(
                service="SSM",
                action="putParameter",
                parameters={
                    "Name": parameter_name,
                    "Description": description,
                    "Type": "SecureString",
                    "Value": parameter_value,
                    "Tier": "Standard",
                    "Overwrite": True,
                },
                physical_resource_id=cr.PhysicalResourceId.of(parameter_name),
            ),
            on_delete=cr.AwsSdkCall(
                service="SSM",
                action="deleteParameter",
                parameters={"Name": parameter_name},
                ignore_error_codes_matching="ParameterNotFound",
            ),
            policy=cr.AwsCustomResourcePolicy.from_statements(
                [
                    iam.PolicyStatement(
                        actions=["ssm:PutParameter", "ssm:DeleteParameter"],
                        resources=[parameter_arn],
                    )
                ]
            ),
        )

    def _parameter_arn(self, parameter_name: str) -> str:
        return self.format_arn(
            service="ssm",
            resource="parameter",
            resource_name=parameter_name.lstrip("/"),
        )

    def _ecs_service_arn(self, cluster_name: str, service_name: str) -> str:
        return self.format_arn(
            service="ecs",
            resource="service",
            resource_name=f"{cluster_name}/{service_name}",
        )
