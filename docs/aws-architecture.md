# AWS Architecture for the Course Enrollment App

This document is the single source of truth for the AWS deployment design of the Course Enrollment App.
It captures architecture decisions, the system diagram, cost estimates, and the release strategy.

---

## Architecture Decision Records

### ADR-001: Container Orchestration -- ECS Fargate

| | |
|---|---|
| **Decision** | ECS Fargate |
| **Alternatives considered** | EC2, EKS, App Runner |
| **Rationale** | ECS Fargate is a serverless container runtime -- AWS manages the underlying EC2 fleet, eliminating OS patching and capacity planning. Tasks can scale to zero by setting the desired count to 0, reducing cost to ~$0 when not demoing. See the [ECS launch type comparison](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/launch_types.html) and [Fargate pricing](https://aws.amazon.com/fargate/pricing/). EKS adds Kubernetes complexity with no benefit at this scale; App Runner is simpler but less configurable for custom networking. |

---

### ADR-002: Database -- MongoDB Atlas M0

| | |
|---|---|
| **Decision** | MongoDB Atlas M0 (free cluster) |
| **Alternatives considered** | AWS DocumentDB, self-hosted MongoDB on EC2 |
| **Rationale** | MongoDB Atlas M0 is a [permanently free tier](https://www.mongodb.com/docs/atlas/reference/free-shared-limitations/) with 512 MB storage, sufficient for a demo. It is fully wire-compatible with MongoEngine (the ORM already in use), so no application changes are required. AWS DocumentDB is only compatible with the MongoDB 4.0 API and starts at ~$50/month; self-hosting on EC2 adds operational overhead and cost with no advantage. |

---

### ADR-003: Secrets Management -- SSM Parameter Store

| | |
|---|---|
| **Decision** | AWS SSM Parameter Store (Standard tier) |
| **Alternatives considered** | AWS Secrets Manager, environment variables embedded in the ECS task definition |
| **Rationale** | [SSM Parameter Store Standard tier](https://aws.amazon.com/systems-manager/pricing/) is free for up to 10,000 parameters -- the cheapest secure option available. Environment variables embedded directly in an ECS task definition are exposed in plaintext via the ECS API and AWS console, making them visible to any IAM principal with `ecs:DescribeTaskDefinition`. [AWS Secrets Manager](https://aws.amazon.com/secrets-manager/) adds automatic rotation and cross-account sharing but costs $0.40/secret/month, which is unnecessary for a short-lived demo. Both `SECRET_KEY` and `MONGO_URI` are stored here: the Atlas connection string embeds credentials (`mongodb+srv://user:password@cluster/`), making it sensitive despite looking like a plain URI. |

---

### ADR-004: GitHub → AWS Authentication -- OIDC (Keyless)

| | |
|---|---|
| **Decision** | GitHub Actions OIDC federation (keyless) |
| **Alternatives considered** | IAM access keys stored as GitHub Secrets |
| **Rationale** | [OpenID Connect (OIDC)](https://openid.net/connect/) is an identity layer on top of OAuth 2.0 that lets GitHub Actions prove its identity to AWS IAM using a short-lived token -- no static credentials are stored anywhere. This follows the [AWS IAM best practice of using temporary credentials for workloads](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html#bp-workloads-use-roles) and GitHub's [recommended approach for AWS deployments](https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services). Long-lived IAM access keys stored as GitHub Secrets are a common source of credential leaks and require manual rotation. |

---

### ADR-005: Infrastructure as Code -- AWS CDK (Python)

| | |
|---|---|
| **Decision** | AWS CDK (Python) |
| **Alternatives considered** | Terraform, CloudFormation (raw YAML/JSON), AWS SAM |
| **Rationale** | [Terraform](https://developer.hashicorp.com/terraform) is the more widely adopted IaC tool across the industry (multi-cloud, large ecosystem), but it requires learning HCL in addition to Python. [AWS CDK (Python)](https://docs.aws.amazon.com/cdk/v2/guide/home.html) was chosen because contributors need only one language, and its high-level constructs (e.g. `ecs_patterns.ApplicationLoadBalancedFargateService`) reduce boilerplate significantly versus raw [CloudFormation](https://aws.amazon.com/cloudformation/) YAML. [AWS SAM](https://aws.amazon.com/serverless/sam/) is optimised for Lambda/serverless workloads and is not a natural fit for a long-running Fargate service. The main tradeoff is that CDK is AWS-only and requires Node.js at synth time even for Python apps -- acceptable for a single-cloud demo. `cdk destroy` also makes full teardown of all provisioned resources trivial. |

---

### ADR-006: Load Balancer -- Application Load Balancer (ALB)

| | |
|---|---|
| **Decision** | Application Load Balancer (ALB) |
| **Alternatives considered** | Network Load Balancer (NLB), CloudFront |
| **Rationale** | ALB provides layer-7 HTTP/HTTPS routing and [integrates natively with ECS service discovery](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-load-balancing.html), including health checks and graceful task draining during deployments. The [AWS free tier covers 750 ALB-hours/month for the first 12 months](https://aws.amazon.com/elasticloadbalancing/pricing/), making it effectively free during initial evaluation. NLB operates at layer 4 (TCP) and lacks HTTP-level routing; CloudFront adds CDN caching which provides no benefit for a dynamic Flask app without static asset distribution requirements. |

---

## Architecture Diagram

```mermaid
flowchart TD
    Dev["Developer"]
    GHA["GitHub Actions\n(CI/CD)"]
    OIDC["AWS OIDC Provider\n(keyless auth)"]
    ECR["Amazon ECR\n(container registry)"]
    ECS["ECS Fargate Task\n(Flask / Gunicorn)"]
    ALB["Application Load Balancer\n(HTTPS)"]
    SSM["SSM Parameter Store\n(SECRET_KEY, MONGO_URI)"]
    CW["CloudWatch Logs"]
    Atlas["MongoDB Atlas M0\n(external, same region)"]
    Internet["Internet"]

    Dev -->|"git push / PR merge"| GHA
    GHA -->|"assume role via"| OIDC
    OIDC -->|"short-lived token"| GHA
    GHA -->|"docker push"| ECR
    GHA -->|"force-new-deployment"| ECS

    Internet -->|"HTTPS"| ALB
    ALB -->|"HTTP"| ECS

    ECS -->|"reads secrets at startup"| SSM
    ECS -->|"queries / writes"| Atlas
    ECS -->|"stdout / stderr"| CW

    ECR -.->|"pulls image"| ECS
```

> **Why is `MONGO_URI` a secret?** MongoDB Atlas connection strings embed credentials directly in the URI
> (e.g. `mongodb+srv://user:password@cluster.mongodb.net/`). Despite looking like a plain address, the URI
> is sensitive and must not be stored in the ECS task definition, where it would be visible in plaintext
> via the AWS console and ECS API. Storing it in SSM Standard tier costs nothing.
>
> **Why set `APP_ENV=production` in ECS?** The Flask app defaults to `development` when `APP_ENV` is unset
> so local Docker can still work over plain HTTP. In ECS behind an HTTPS ALB, `APP_ENV=production` must be
> set so session cookies are emitted with the `Secure` attribute and browsers will send them only over HTTPS.
>
> **Why must `FLASK_DEBUG` stay out of AWS?** Flask debug mode exposes the interactive Werkzeug debugger and
> is for local development only. Do not store `FLASK_DEBUG` in ECS task definitions or SSM parameters, and
> the app now fails fast if `APP_ENV=production` is combined with `FLASK_DEBUG=true`.
>
> **Why CloudWatch Logs?** CloudWatch is the native log driver for ECS Fargate
> ([`awslogs` driver](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/using_awslogs.html))
> and requires no extra infrastructure or agents. The [free tier](https://aws.amazon.com/cloudwatch/pricing/)
> covers 5 GB of log ingestion per month -- far more than a low-traffic demo will generate. Alternative
> aggregators (Datadog, Splunk, Grafana Cloud) all require paid plans at this scale.

---

## Cost Estimate

> All prices are approximate US East (us-east-1) on-demand rates as of 2026.

| Service | Configuration | Est. monthly cost |
|---|---|---|
| ECS Fargate | 0.25 vCPU / 0.5 GB RAM, running 24/7 | ~$10 |
| ALB | Free tier: 750 hrs/month for first 12 months | $0 → ~$16 |
| ECR | Free tier: 500 MB storage | $0 |
| SSM Parameter Store | Standard tier | $0 |
| MongoDB Atlas | M0 free cluster | $0 |
| CloudWatch Logs | Free tier: 5 GB ingestion/month | $0 |
| **Total** | | **~$10-26/month** |

> **Cost-saving tip:** Set ECS desired count to `0` when not demoing.
> This reduces the Fargate charge to ~$0, bringing the total monthly cost to near $0 while retaining all infrastructure.

---

## Release Strategy and Versioning

### Versioning scheme

The project follows [Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`):

| Component | When to increment |
|---|---|
| `MAJOR` | Breaking changes to the API or data model |
| `MINOR` | New features added in a backwards-compatible manner |
| `PATCH` | Backwards-compatible bug fixes |

The current AWS deployment milestone is **v2.0.0**.

### Release process

1. **Feature branch** -- all work is done on a branch off `main`.
1. **Pull request** -- PR is opened; CI runs linting, unit tests, and Playwright e2e tests.
1. **Merge to `main`** -- triggers the CD pipeline:
   - Docker image is built and pushed to ECR, tagged with the Git SHA and the semantic version tag (e.g., `v2.1.0`).
   - ECS service is updated via `force-new-deployment`; the old task is drained gracefully by the ALB.
1. **GitHub Release** -- a GitHub Release is created from the version tag, auto-generating a changelog from merged PRs.

### Docker image tagging convention

| Tag | Purpose |
|---|---|
| `latest` | Most recent build from `main` |
| `<git-sha>` | Immutable reference to an exact commit |
| `v<MAJOR.MINOR.PATCH>` | Stable release tag for rollbacks |

### Rollback procedure

To revert a bad deployment, re-tag a previous ECR image as `latest` and trigger a new ECS force-deployment,
or use the ECS console to point the service at a prior task definition revision.

---

## CDK Rebuild Workflow

Issue #60 adds a Python AWS CDK app under `infra/` that captures the current
AWS deployment as a **same-name rebuild stack**. This stack is intended for a
clean account or for use **after** manually tearing down the current hand-built
resources. It does **not** import or adopt the existing manual ECS/ALB/ECR/IAM
resources in place.

### Scope of the CDK stack

The CDK stack manages the AWS-only deployment resources for this app:

- ECR repository
- GitHub Actions OIDC provider and deploy role
- ECS task execution role
- Secure SSM parameters for `SECRET_KEY` and `MONGO_URI`
- CloudWatch log group
- ECS cluster, task definition, and Fargate service
- ALB, target group, listeners, and security groups

The following remain external to CDK:

- MongoDB Atlas cluster and data
- Namecheap DNS records
- ACM DNS validation workflow

The existing ACM certificate ARN is reused as an input rather than created by
the stack.

### Prerequisites

- AWS CLI authentication configured for the target account
- Node.js and the AWS CDK CLI installed locally
- Python 3.9+ available locally
- An existing ACM certificate ARN for `course-enrollment-app.robertlech.com`

AWS documents that the CDK CLI is installed with `npm install -g aws-cdk`, and
that Python CDK apps use standard Python tooling and require Node.js at synth
time.

### Required environment variables

Export the following values before synthesizing or deploying the stack:

```bash
export CDK_VPC_ID=vpc-...
export CDK_PUBLIC_SUBNET_IDS=subnet-...,subnet-...
export CDK_CERTIFICATE_ARN=arn:aws:acm:us-east-1:...
export CDK_GITHUB_OIDC_PROVIDER_ARN=arn:aws:iam::<account-id>:oidc-provider/token.actions.githubusercontent.com
export CDK_IMAGE_TAG=<existing-ecr-image-tag>
export CDK_SECRET_KEY=<strong-random-secret>
export CDK_MONGO_URI=<mongodb-atlas-uri>
```

An example file is provided at `infra/.env.example`.

If the GitHub OIDC provider from the manual stack is still present in IAM,
set `CDK_GITHUB_OIDC_PROVIDER_ARN` so CDK imports and reuses it. Leave that
variable unset only when the provider has already been deleted and you want the
stack to create a fresh one.

### Local usage

```bash
cd infra
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cdk synth
```

To deploy the rebuild stack after the old manually created stack has been
removed:

```bash
cd infra
cdk deploy CourseEnrollmentAppStack
```

If you still need to remove the original manually created AWS stack before that
first CDK deploy, the terminal-based teardown helpers now live under
`infra/manual-removal/`. Please view the
`[corresponding README](infra/manual-removal/manual-stack-teardown.md)`
for more details on how to run it. That folder includes:

- `validate_stack_is_up.sh` for pre-teardown and post-rebuild health checks
- `remove_manual_stack.sh` for the one-time manual-stack removal
- `validate_cdk_predeploy.sh` for the final pre-deploy guardrail check after
  teardown and before `cdk deploy`
- `validate_manual_stack_teardown_completed.sh` for post-teardown confirmation

To tear the CDK-managed stack down:

```bash
make aws-teardown
```

### Notes and limitations

- The stack uses the current production resource names. This means a first
  `cdk deploy` will conflict with the manually created resources unless those
  resources have already been removed.
- Account-level ECR registry scanning remains outside this stack; only the ECR
  repository itself is modeled.
- The CDK Python dependencies are distributed through PyPI as `aws-cdk-lib`
  and `constructs`. The current versions used in this repo are `2.243.0` and
  `10.5.1`, respectively.
