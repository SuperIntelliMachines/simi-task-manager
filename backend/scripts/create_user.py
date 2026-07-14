#!/usr/bin/env python
"""Create or upsert a user in the database by calling psql.

This script prompts for DB connection info, the user email and password,
hashes the password using bcrypt, and runs a temporary SQL file to insert
the organization and user if they do not already exist.

It does not require Python DB driver packages; it shells out to `psql`.
"""
import getpass
import subprocess
import tempfile
import os
import textwrap
import sys

try:
    import bcrypt
except Exception:
    print("bcrypt is required. Install with: python -m pip install bcrypt")
    raise


TEMPLATE = """
INSERT INTO organizations (name, created_at, updated_at)
SELECT '{org}', now(), now()
WHERE NOT EXISTS (SELECT 1 FROM organizations WHERE name = '{org}');

INSERT INTO users (organization_id, email, hashed_password, is_active, role, created_at, updated_at)
SELECT id, '{email}', '{hash}', true, '{role}', now(), now()
FROM organizations
WHERE name = '{org}'
  AND NOT EXISTS (SELECT 1 FROM users WHERE email = '{email}');
"""


def main():
    print("Create or upsert a user in the task_manager database.")
    db_host = input("DB host [localhost]: ") or "localhost"
    db_port = input("DB port [5432]: ") or "5432"
    db_name = input("DB name [task_manager]: ") or "task_manager"
    db_user = input("DB user [atm_user]: ") or "atm_user"
    db_pass = getpass.getpass("DB password for user {}: ".format(db_user))

    email = input("User email to create [admin@example.com]: ") or "admin@example.com"
    pwd = getpass.getpass("Password for {}: ".format(email))
    role = input("Role [platform_admin]: ") or "platform_admin"
    org = input("Organization name [SIMI]: ") or "SIMI"

    # bcrypt limits passwords to 72 bytes; truncate if necessary
    raw = pwd.encode()
    if len(raw) > 72:
        raw = raw[:72]
    # hash password using bcrypt
    hashed = bcrypt.hashpw(raw, bcrypt.gensalt()).decode()

    sql = TEMPLATE.format(org=org.replace("'", "''"), email=email.replace("'", "''"), hash=hashed.replace("'", "''"), role=role)

    with tempfile.NamedTemporaryFile("w+", suffix=".sql", delete=False) as tf:
        tf.write(sql)
        tf.flush()
        tmp_path = tf.name

    env = os.environ.copy()
    env["PGPASSWORD"] = db_pass

    cmd = [
        "psql",
        "-h",
        db_host,
        "-p",
        str(db_port),
        "-U",
        db_user,
        "-d",
        db_name,
        "-f",
        tmp_path,
    ]

    print("Running psql to apply seed SQL...")
    try:
        completed = subprocess.run(cmd, env=env, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(completed.stdout)
        print("User insertion completed — verify in database.")
    except subprocess.CalledProcessError as exc:
        print("psql failed:")
        print(exc.stderr)
        print("Temporary SQL file left at:", tmp_path)
        sys.exit(1)
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass


if __name__ == "__main__":
    main()
