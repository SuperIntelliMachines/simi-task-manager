# Database Migrations and GitHub Deployment Pipelines

## Purpose

This document defines how Simi Task Manager should manage database migrations, GCP secrets, and GitHub Actions deployments. The approach follows the existing GyantrAI pattern:

- SQL migrations under `database/migrations`
- `schema_migrations` tracking table
- GitHub Actions validation and dry-run on pull requests
- Cloud SQL Auth Proxy for CI/CD database access
- Cloud Run deployments for backend and frontend
- GitHub repository secrets for GCP and application credentials

## Migration Strategy

Use raw SQL migration files for production database changes. SQLAlchemy/Alembic may still be used locally for model comparison or migration generation, but the deploy pipeline applies versioned SQL files from `database/migrations`.

### Directory Structure

```text
database/
|-- migrations/
|   |-- README.md
|   |-- V001__initial_platform_schema.sql
|   |-- V002__approval_sessions_templates_preferences.sql
|   `-- V003__admin_support_access_sessions.sql
|-- modules/
|   |-- platform.sql
|   |-- insurance.sql
|   |-- channels.sql
|   `-- agents.sql
`-- schema.sql
```

### Naming Convention

Migration files must follow:

```text
V{VERSION}__{description}.sql
```

Examples:

- `V001__initial_platform_schema.sql`
- `V002__approval_sessions_templates_preferences.sql`
- `V003__admin_support_access_sessions.sql`

Rules:

- Use `V` prefix.
- Use zero-padded versions.
- Use a double underscore between version and description.
- Use lowercase snake_case descriptions.
- Do not edit a migration after it has been applied to any shared environment.

## Migration File Template

```sql
-- ============================================================================
-- MIGRATION V001: Initial Platform Schema
-- Generated: YYYY-MM-DD
-- Description: Creates initial tenant, task, channel, agent, and audit tables.
-- ============================================================================

BEGIN;

-- SQL statements here

COMMIT;

-- ============================================================================
-- ROLLBACK SCRIPT
-- ============================================================================
-- BEGIN;
-- DROP TABLE IF EXISTS example_table CASCADE;
-- DELETE FROM schema_migrations WHERE migration_name = 'V001__initial_platform_schema.sql';
-- COMMIT;
```

## Migration Tracking Table

The GitHub workflow creates this table automatically before applying migrations:

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
  id SERIAL PRIMARY KEY,
  migration_name VARCHAR(255) NOT NULL UNIQUE,
  applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  applied_by VARCHAR(100),
  checksum VARCHAR(64),
  execution_time_ms INTEGER
);
```

## Local Migration Commands

List migrations:

```powershell
Get-ChildItem database\migrations\*.sql | Sort-Object Name
```

Apply a migration to local PostgreSQL:

```powershell
$env:PGPASSWORD = "devpassword"
psql -h localhost -p 5432 -U postgres -d simi_task_manager -v ON_ERROR_STOP=1 -f database\migrations\V001__initial_platform_schema.sql
```

Check applied migrations:

```powershell
$env:PGPASSWORD = "devpassword"
psql -h localhost -p 5432 -U postgres -d simi_task_manager -c "SELECT * FROM schema_migrations ORDER BY applied_at;"
```

## GitHub Actions Workflows

The repository includes these workflow templates:

- `.github/workflows/database-migrations.yml`
- `.github/workflows/deploy-dev.yml`
- `.github/workflows/deploy.yml`

### database-migrations.yml

Purpose:

- Validate SQL syntax.
- Check migration naming convention.
- Dry-run pending migrations on pull requests when secrets are available.
- Apply pending migrations manually or on configured branch pushes.
- Generate schema diff summary.

Default behavior:

- Pull requests validate migration files.
- Manual dispatch can run dry-run or apply mode.
- Push to `main` and `dev` can apply pending migrations when migration files change.

### deploy-dev.yml

Purpose:

- Run backend/frontend tests.
- Optionally run migrations.
- Build backend and frontend Docker images.
- Push images to Artifact Registry.
- Deploy to Cloud Run development services.
- Run health checks.

This workflow is manual-first until application code exists.

### deploy.yml

Purpose:

- Production/staging deployment.
- Run migrations before deploy when enabled.
- Run schema drift check.
- Build and deploy backend/frontend images.
- Run health checks.

This workflow is manual-first until the team is ready to deploy from `main`.

## Required GitHub Secrets

Set these in GitHub repository settings under Actions secrets.

GCP:

- `GCP_SA_KEY`
- `INSTANCE_CONNECTION_NAME`
- `DATABASE_PASSWORD`

Application:

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

Optional:

- `DATABASE_USER`
- `DATABASE_NAME`
- `FRONTEND_BASE_URL`
- `SENTRY_DSN`

## GCP Service Account Permissions

The GitHub Actions service account should have the minimum roles needed:

- Artifact Registry Writer
- Cloud Run Admin
- Cloud SQL Client
- Service Account User for the runtime service account
- Secret Manager Secret Accessor only if workflows fetch secrets directly from GCP

Prefer GitHub environment protection for production deployments.

## Cloud Run Environment Variables

Backend Cloud Run service should receive:

- `ENVIRONMENT`
- `IS_CLOUD_RUN=true`
- `DB_USER`
- `DB_PASSWORD`
- `DB_NAME`
- `INSTANCE_CONNECTION_NAME`
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
- `LOG_LEVEL`
- `LOG_FORMAT=json`
- `LOG_SERVICE_NAME=simi-task-manager-backend`

Frontend Cloud Run service should receive:

- `BACKEND_URL`
- `VITE_API_URL=/api/v1`
- `VITE_ENVIRONMENT`

## Best Practices

- Keep migrations small and focused.
- Use `BEGIN` and `COMMIT`.
- Use `CREATE TABLE IF NOT EXISTS` and `DROP TABLE IF EXISTS` where appropriate.
- Use explicit indexes for workflow, reminder, message, and audit queries.
- Add comments for important tables.
- Include rollback notes at the bottom of each migration.
- Never modify already-applied migrations.
- Use forward-fix migrations for rollback in shared environments.
- Do not print secrets in workflow logs.
- Make migration jobs non-concurrent per branch/environment.
- Run migrations before backend deploy.

## Initial Migration Plan

Suggested first migrations:

1. `V001__initial_platform_schema.sql`
   - organizations
   - users
   - organization_memberships
   - contacts
   - tasks
   - task_assignments
   - reminders
   - reminder_attempts
   - inbound_messages
   - outbound_messages
   - audit_events

2. `V002__agents_workflows_channels.sql`
   - channel_connections
   - contact_channel_identities
   - workflow_templates
   - workflow_runs
   - agent_definitions
   - agent_invocations
   - agent_sessions

3. `V003__approval_templates_preferences.sql`
   - approval_requests
   - message_templates
   - notification_preferences

4. `V004__insurance_mvp.sql`
   - insurance_policies
   - insurance_leads

5. `V005__admin_support_access.sql`
   - support_access_sessions

## Validation Checklist

- [ ] Migration file name follows convention.
- [ ] SQL parses.
- [ ] Migration runs against a clean local database.
- [ ] Migration runs against a database with previous migrations applied.
- [ ] Rollback notes are included.
- [ ] New SQLAlchemy models match migration.
- [ ] Schema drift check passes.
- [ ] GitHub migration workflow summary is clean.

