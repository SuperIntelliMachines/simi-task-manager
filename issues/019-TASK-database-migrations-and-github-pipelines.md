---
title: "[ATM-019] [Task] Database Migrations and GitHub Deployment Pipelines"
labels: [task, database, github-actions, gcp, deployment, P0]
milestone: "Agentic Task Manager MVP"
assignees: ""
---

# ATM-019 - Database Migrations and GitHub Deployment Pipelines

## Objective

Implement and validate database migration support and GitHub Actions deployment pipelines using the same operating pattern as GyantrAI.

## Reference

Read:

- `docs/database-migrations-and-deployment.md`
- `.github/workflows/database-migrations.yml`
- `.github/workflows/deploy-dev.yml`
- `.github/workflows/deploy.yml`

## Implementation Steps

1. Confirm GCP target resources:
   - project ID
   - region
   - Artifact Registry repository
   - Cloud SQL instance
   - database name
   - backend Cloud Run service name
   - frontend Cloud Run service name

2. Configure GitHub repository secrets:
   - `GCP_SA_KEY`
   - `INSTANCE_CONNECTION_NAME`
   - `DATABASE_PASSWORD`
   - `JWT_SECRET_KEY`
   - `OPENAI_API_KEY`
   - `ANTHROPIC_API_KEY`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_WEBHOOK_SECRET`
   - `TELEGRAM_WEBHOOK_URL`
   - `WHATSAPP_PHONE_NUMBER_ID`
   - `WHATSAPP_ACCESS_TOKEN`
   - `WHATSAPP_VERIFY_TOKEN`
   - `WHATSAPP_APP_SECRET`
   - `REDIS_URL`

3. Add initial SQL migrations:
   - `V001__initial_platform_schema.sql`
   - `V002__agents_workflows_channels.sql`
   - `V003__approval_templates_preferences.sql`
   - `V004__insurance_mvp.sql`
   - `V005__admin_support_access.sql`

4. Validate migrations locally:
   - apply to a clean PostgreSQL database
   - apply to a database with previous migrations already applied
   - verify `schema_migrations` records checksums and execution time

5. Validate GitHub migration workflow:
   - pull request validates SQL syntax
   - pull request checks migration naming convention
   - workflow dispatch dry-run shows pending migrations
   - workflow dispatch apply mode applies migrations once
   - repeated apply skips already-applied migrations

6. Validate deployment workflows after backend/frontend scaffolding exists:
   - backend tests run
   - frontend tests run
   - backend image builds and pushes
   - frontend image builds and pushes
   - backend deploys to Cloud Run
   - frontend deploys to Cloud Run
   - health checks pass

7. Add production safety:
   - GitHub environment protection for production
   - required reviewer for production deploy
   - non-concurrent migration/deploy jobs
   - deployment summary in GitHub Step Summary

## Acceptance Criteria

- [ ] Migration directory and naming convention are documented.
- [ ] GitHub migration workflow validates SQL and naming convention.
- [ ] Migration workflow creates `schema_migrations` if missing.
- [ ] Migration workflow applies pending migrations exactly once.
- [ ] Deploy workflows use GCP auth and Artifact Registry.
- [ ] Deploy workflows pass required secrets to Cloud Run without printing secret values.
- [ ] Production deployments are manual and protected.
- [ ] Docs list all required GitHub secrets and GCP roles.

## Test Cases

- Invalid migration name fails workflow validation.
- Empty migration directory does not fail validation.
- Already-applied migration is skipped.
- Failed migration stops the workflow.
- Cloud Run deploy uses Simi service names.
- Backend health check calls `/healthz`.
- Workflow does not try to build Docker images before Dockerfiles exist.

## Validation

```bash
# Local SQL naming check
Get-ChildItem database\migrations\*.sql | Sort-Object Name

# Local migration apply
$env:PGPASSWORD = "devpassword"
psql -h localhost -p 5432 -U postgres -d simi_task_manager -v ON_ERROR_STOP=1 -f database\migrations\V001__initial_platform_schema.sql

# GitHub workflows
gh workflow list
gh workflow run "Database Migrations" -f environment=development -f dry_run=true
gh run list --workflow "Database Migrations"
```

