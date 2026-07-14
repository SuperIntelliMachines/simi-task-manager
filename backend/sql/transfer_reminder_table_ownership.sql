-- Run once in pgAdmin (or psql) as postgres on database simi_task_manager.
-- Transfers reminder engine tables to the app role so Alembic DDL can run as simi_user.

ALTER TABLE IF EXISTS public.reminder_configs OWNER TO simi_user;
ALTER TABLE IF EXISTS public.reminder_instances OWNER TO simi_user;
ALTER SEQUENCE IF EXISTS public.reminder_configs_id_seq OWNER TO simi_user;
ALTER SEQUENCE IF EXISTS public.reminder_instances_id_seq OWNER TO simi_user;
