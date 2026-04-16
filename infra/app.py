import os
from pathlib import Path

import aws_cdk as cdk
from course_enrollment_stack import CourseEnrollmentAppStack
from dotenv import load_dotenv


load_dotenv(Path(__file__).with_name(".env"))


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _optional_env(name: str) -> str:
    return os.environ.get(name, "").strip()


def _bool_env(name: str, *, default: bool) -> bool:
    value = os.environ.get(name, "").strip().lower()
    if not value:
        return default
    return value in {"1", "true", "yes", "on"}


def _required_subnet_ids() -> list[str]:
    subnet_ids = [
        subnet_id.strip()
        for subnet_id in _required_env("CDK_PUBLIC_SUBNET_IDS").split(",")
        if subnet_id.strip()
    ]
    if len(subnet_ids) < 2:
        raise RuntimeError(
            "CDK_PUBLIC_SUBNET_IDS must include at least two "
            "comma-separated subnet IDs."
        )
    return subnet_ids


app = cdk.App()

CourseEnrollmentAppStack(
    app,
    "CourseEnrollmentAppStack",
    stack_name="CourseEnrollmentAppStack",
    env=cdk.Environment(
        account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
        region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1"),
    ),
    vpc_id=_required_env("CDK_VPC_ID"),
    public_subnet_ids=_required_subnet_ids(),
    certificate_arn=_required_env("CDK_CERTIFICATE_ARN"),
    github_oidc_provider_arn=_optional_env("CDK_GITHUB_OIDC_PROVIDER_ARN"),
    image_tag=_optional_env("CDK_IMAGE_TAG"),
    bootstrap_use_local_image=_bool_env(
        "CDK_BOOTSTRAP_USE_LOCAL_IMAGE",
        default=True,
    ),
    secret_key_value=_required_env("CDK_SECRET_KEY"),
    mongo_uri_value=_required_env("CDK_MONGO_URI"),
)

app.synth()
