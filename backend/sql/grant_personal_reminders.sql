-- Run as table owner / postgres superuser.
-- Required when personal_reminders was created outside Alembic without app-role grants.

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.personal_reminders TO simi_user;
