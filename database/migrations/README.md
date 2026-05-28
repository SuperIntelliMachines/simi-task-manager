# Database Migrations

Place versioned SQL migrations in this directory.

Naming convention:

```text
V001__initial_platform_schema.sql
V002__agents_workflows_channels.sql
V003__approval_templates_preferences.sql
```

Rules:

- Use `V` prefix.
- Use zero-padded versions.
- Use a double underscore after the version.
- Use lowercase snake_case descriptions.
- Wrap migrations in `BEGIN;` and `COMMIT;`.
- Include rollback notes.
- Do not edit migrations after they have been applied to a shared environment.

See `docs/database-migrations-and-deployment.md` for the full process.

