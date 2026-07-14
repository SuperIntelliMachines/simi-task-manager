-- Run once in pgAdmin (as postgres / table owner) if the app user cannot read policy_custom_reminders.
-- Error symptom: "permission denied for table policy_custom_reminders"

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE public.policy_custom_reminders TO simi_user;
GRANT USAGE, SELECT ON SEQUENCE public.policy_custom_reminders_id_seq TO simi_user;
