# AWS staging environment

This directory is the **Phase 2 deployable staging environment**.

It provisions the production-shaped runtime needed for staging:

- VPC with isolated private data subnets and public application subnets
- HTTPS Application Load Balancer
- ECS Fargate API service
- ECS Fargate Celery worker service
- managed PostgreSQL (RDS)
- managed Redis (ElastiCache with TLS)
- encrypted/versioned S3 object storage
- immutable ECR repository with image scanning
- CloudWatch logs
- IAM task roles
- Secrets Manager credentials
- Route 53 staging DNS

The API and worker use the same immutable container image. The API is health-checked through `/ready`; the worker is independently scalable.

## Prerequisites

- AWS account with permissions to create the resources in this directory
- Terraform >= 1.6
- Docker
- an ACM certificate for the staging hostname
- a public Route 53 hosted zone
- AWS credentials locally or GitHub OIDC
- encrypted remote Terraform state for a shared environment

## Deploy

1. Copy `terraform.tfvars.example` to `terraform.tfvars` and set the real domain, certificate ARN and image URI.
2. Configure an encrypted remote state backend using `backend.tf.example`.
3. Initialize and validate:

~~~bash
terraform init
terraform fmt -check
terraform validate
~~~

4. Create the ECR repository first:

~~~bash
terraform apply -target=aws_ecr_repository.app
~~~

5. Build and push the immutable application image:

~~~bash
REGION=ap-south-1
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
REPO="$ACCOUNT.dkr.ecr.$REGION.amazonaws.com/reconciliation-platform"
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "$ACCOUNT.dkr.ecr.$REGION.amazonaws.com"
docker build -t "$REPO:$(git rev-parse HEAD)" .
docker push "$REPO:$(git rev-parse HEAD)"
~~~

6. Set `container_image` to that exact image tag and apply:

~~~bash
terraform plan -out=tfplan
terraform apply tfplan
~~~

## Staging smoke test

After DNS and ECS health checks settle:

~~~bash
curl -fsS https://staging.example.com/health
curl -fsS https://staging.example.com/ready
curl -fsS -H "X-API-Key: <staging-api-key>" -H "X-Tenant-ID: staging" https://staging.example.com/metrics
~~~

The API key is generated and stored in AWS Secrets Manager. Retrieve it only through an authorized operator workflow; never put it in Git or CI logs.

## Runtime contract

The staging deployment uses:

- `DATABASE_HOST/PORT/NAME/USER/PASSWORD` for managed PostgreSQL
- `JOB_QUEUE=celery` for distributed async processing
- `rediss://...` for encrypted Redis traffic
- `OBJECT_STORE=s3` for durable raw-object storage
- `AI_PROVIDER=none` by default
- tenant-scoped API-key mapping through Secrets Manager

The application still supports the existing `DATABASE_URL` path for local Compose and tests.

## Security boundaries

- PostgreSQL and Redis have no public ingress.
- Only the application security group can reach PostgreSQL/Redis.
- S3 blocks public access and uses encryption + versioning.
- ECS pulls secrets from Secrets Manager.
- ECR tags are immutable and images are scanned on push.
- HTTPS terminates at the ALB.
- Staging uses synthetic/customer-shaped data only.

## Rollback

Deploy the previous immutable ECR image tag/digest and apply the Terraform plan. ECS performs a rolling replacement while PostgreSQL/S3 state remains intact.

For database changes, keep schema changes backward compatible. The current application initializes missing tables idempotently; explicit migration tooling is a later hardening item.

## Important limitation

This repository now contains a **deployable AWS staging implementation**, but no live AWS environment is claimed from source control alone. A real staging URL requires the user's AWS account, DNS/certificate configuration and credentials. This distinction is intentional.
