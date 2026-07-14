-- Template: fill the values below before running.
-- Replace <BCRYPT_HASH> with a bcrypt hash (see instructions below).
-- Replace <EMAIL> and <ORG_NAME> as desired.

-- Ensure organization exists
INSERT INTO organizations (name, created_at, updated_at)
SELECT '<ORG_NAME>', now(), now()
WHERE NOT EXISTS (SELECT 1 FROM organizations WHERE name = '<ORG_NAME>');

-- Insert user only if email is not present
INSERT INTO users (organization_id, email, hashed_password, is_active, role, created_at, updated_at)
SELECT id, '<EMAIL>', '<BCRYPT_HASH>', true, 'platform_admin', now(), now()
FROM organizations
WHERE name = '<ORG_NAME>'
  AND NOT EXISTS (SELECT 1 FROM users WHERE email = '<EMAIL>');
