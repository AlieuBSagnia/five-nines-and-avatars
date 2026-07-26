# Prima Tech Challenge

A small user-management API (FastAPI + DynamoDB + S3), containerised,
provisioned via Terraform, and deployed to Kubernetes via a custom Helm
chart, with a GitHub Actions CI/CD pipeline.

## Architecture

```
                        ┌────────────────────┐
   kubectl / Helm ────► │   Kubernetes (EKS   │
                        │   or minikube)      │
                        │  ┌───────────────┐  │
                        │  │ Deployment    │  │      IRSA (prod) or
                        │  │ (2-10 pods,   │──┼───►  static creds (dev)
                        │  │  HPA + PDB)   │  │            │
                        │  └───────┬───────┘  │            ▼
                        │          │ Service   │   ┌─────────────────┐
                        └──────────┼───────────┘   │  DynamoDB table  │
                                   │                │  (users)         │
                            GET /users              └─────────────────┘
                            POST /user                       ▲
                                   │                          │
                                   ▼                ┌─────────────────┐
                          FastAPI app (app/)         │  S3 bucket       │
                          ├─ main.py   (routes)      │  (avatars/)      │
                          ├─ db.py     (DynamoDB)────┘                  │
                          ├─ storage.py(S3)──────────────────────────────┘
                          └─ config.py (env-driven settings)
```

Terraform provisions the DynamoDB table, S3 bucket, and IAM policy/roles
(including an optional IRSA trust relationship for EKS). The same Terraform
code targets either **LocalStack** (default, free, for local dev/testing)
or **real AWS** by toggling a single variable.

## Repo layout

```
app/                    FastAPI application code
tests/                  pytest suite (mocks AWS with moto — no external deps)
terraform/              IaC for DynamoDB, S3, IAM/IRSA
helm/prima-api/         Helm chart for Kubernetes deployment
.github/workflows/ci.yml  CI/CD pipeline
Dockerfile              Multi-stage, non-root, healthchecked image
docker-compose.yml       One-command local stack: LocalStack + Terraform + API
```

## Prerequisites

- Docker & Docker Compose
- Python 3.12 (for running tests without Docker)
- Terraform >= 1.5
- Helm >= 3.14 and `kubectl`, if testing the Kubernetes deployment
- minikube, if testing the Helm chart locally (optional — Task 4 testing is
  explicitly optional per the brief)

## Running it

### 1. Fastest path: full local stack in one command

```bash
docker compose up --build
```

This brings up LocalStack, applies the Terraform (creating the table/bucket),
then starts the API wired to point at LocalStack. Once it's up:

```bash
curl -X POST http://localhost:8000/user \
  -F "name=Test User" \
  -F "email=test-user@prima.it" \
  -F "avatar=@/path/to/some-image.png"

curl http://localhost:8000/users
```

Expected `GET /users` response matches the spec exactly:

```json
[
  {
    "avatar_url": "http://localhost:4566/prima-tech-challenge/avatars/<uuid>.png",
    "email": "test-user@prima.it",
    "name": "Test User"
  }
]
```
(On real AWS, `avatar_url` naturally becomes the standard
`https://<bucket>.s3.<region>.amazonaws.com/...` form — see `S3_PUBLIC_BASE_URL`
in `app/config.py`.)

### 2. Running tests (no Docker needed)

```bash
pip install -r requirements-dev.txt
pytest -v
```

Tests use `moto` to mock DynamoDB and S3 in-process, so they run in CI or
locally with zero external services and zero AWS costs.

### 3. Terraform on its own

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars   # defaults already target LocalStack
terraform init
terraform apply
```

To point at real AWS instead (only if you're certain you're within Free
Tier — DynamoDB/S3 usage here is trivial and should cost nothing under
Free Tier limits): set `localstack_endpoint = ""` in `terraform.tfvars`
and ensure your AWS credentials are configured normally (`aws configure`
or standard env vars).

### 4. Helm chart (optional, per the brief)

Render only (no cluster needed) — this is what CI does:

```bash
helm lint helm/prima-api
helm template prima-api helm/prima-api
```

Deploy to minikube:

```bash
minikube start
eval $(minikube docker-env)
docker build -t prima-tech-challenge/api:local .

# LocalStack running on the host, reachable from minikube via host-gateway
localstack start -d

helm install prima-api ./helm/prima-api -f ./helm/prima-api/values-local.yaml
kubectl port-forward svc/prima-api 8000:80
curl http://localhost:8000/healthz
```

## Design decisions worth calling out

- **`email` as the DynamoDB partition key.** It's the natural unique
  business key for a user, and using it directly avoids introducing a
  synthetic ID nobody asked for. `create_user` uses a conditional
  `PutItem` (`attribute_not_exists(email)`) so duplicate signups fail
  loudly (`409`) instead of silently overwriting data.
- **Avatar object keys are random UUIDs, not user-supplied filenames** —
  avoids path traversal and key-collision/overwrite from untrusted input.
- **`/healthz` vs `/readyz`.** Liveness never touches DynamoDB, so a slow
  or down dependency doesn't cause Kubernetes to crash-loop-restart a
  perfectly healthy process; readiness does check DynamoDB, so traffic is
  pulled from a pod that can't actually serve requests, without killing it.
- **`readOnlyRootFilesystem: true`** in the pod's securityContext, with a
  single `emptyDir` mounted at `/tmp` for FastAPI's multipart upload
  spooling — keeps the attack surface small without breaking uploads.
- **Least-privilege IAM.** The app's policy only grants the four DynamoDB
  actions and two S3 actions it actually uses, scoped to the specific table
  ARN and `avatars/*` prefix — no wildcards.
- **IRSA is wired but optional.** `eks_oidc_provider_arn`/`_url` are empty
  by default (per the brief, no EKS cluster is being stood up to test
  against). When populated, Terraform creates the trust relationship and
  the Helm chart's ServiceAccount picks up the resulting role ARN via
  `serviceAccount.eksRoleArn` — no static AWS keys ever need to live in the
  cluster. A plain IAM user + access key is provisioned in parallel purely
  for LocalStack/minikube testing, where there's no OIDC provider to trust.

## What I'd do differently / extend first for a real production rollout

This is intentionally scoped to demonstrate the required pieces end-to-end
rather than gold-plate any one of them. In priority order, here's what I'd
tackle next:

1. **Remote Terraform state with locking** (S3 backend + DynamoDB lock
   table, or Terraform Cloud) — right now state is local, which doesn't
   survive a second engineer or a second laptop.
2. **Split Terraform into environments/workspaces** (dev/staging/prod) with
   a proper module structure, instead of one flat root module — this repo
   optimizes for reviewability over that structure.
3. **Replace the public S3 bucket policy with signed URLs or CloudFront +
   OAC.** Public-read on `avatars/*` is simple and matches the spec's
   plain `avatar_url` field, but a production system would serve avatars
   through CloudFront with Origin Access Control and no public bucket
   policy at all, or return short-lived pre-signed URLs.
4. **Rate limiting and auth** on the API — right now anyone can call
   `POST /user`. I'd add an API gateway or a sidecar (e.g. Envoy) for
   rate limiting, and real authn/authz (API keys or OIDC) before this
   touches the public internet.
5. **Structured logging + tracing** (JSON logs, OpenTelemetry) instead of
   plain `logging` — needed for real observability once this runs at scale
   with multiple replicas.
6. **A GSI on DynamoDB** if query patterns grow beyond "scan everything" —
   fine for a small user table today, expensive at scale.
7. **Multi-worker ASGI server** (`gunicorn` managing `uvicorn` workers, or
   more replicas + smaller per-pod resource requests) — a single `uvicorn`
   process per pod is fine for this exercise but underuses multi-core
   nodes.
8. **Canary/blue-green rollout strategy** (Argo Rollouts or Flagger) rather
   than plain `RollingUpdate` — safer for a service with real user traffic.
9. **Secrets via External Secrets Operator / AWS Secrets Manager**, not
   Kubernetes `Secret` objects with plain base64 (which is what
   `awsCredentials.create` uses here for local-only testing) — base64 is
   not encryption, and I'd never rely on it for anything beyond a local
   dev convenience.

## A note on things I couldn't execute directly

I don't have network access or Docker/Terraform/Helm/kubectl binaries in
the environment I wrote this in, so I wasn't able to literally run
`pytest`, `docker build`, `terraform apply`, or `helm lint` myself before
handing this over. I've hand-checked every file against the FastAPI, boto3,
moto, Terraform AWS provider, and Helm APIs/syntax I'm confident in, but
please run the commands in this README yourself as your first step, and
treat anything that doesn't behave as documented as a bug report I'd want
to fix.
