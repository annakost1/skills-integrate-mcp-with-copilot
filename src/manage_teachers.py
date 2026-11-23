"""Create or update a teacher account in the local credentials file."""

import argparse
import getpass
import json
import os
import tempfile
from pathlib import Path

from app import current_dir, hash_password


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("username", help="Teacher username to add or update")
    args = parser.parse_args()

    password = getpass.getpass("Teacher password: ")
    confirmation = getpass.getpass("Confirm password: ")
    if not password:
        parser.error("Password cannot be empty")
    if password != confirmation:
        parser.error("Passwords do not match")

    credentials_path = Path(
        os.environ.get("TEACHER_CREDENTIALS_FILE", current_dir / "teachers.json")
    )
    try:
        with credentials_path.open(encoding="utf-8") as credentials_file:
            data = json.load(credentials_file)
    except FileNotFoundError:
        data = {"teachers": {}}
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        parser.error(f"Cannot read teacher credentials: {error}")

    teachers = data.get("teachers") if isinstance(data, dict) else None
    if not isinstance(teachers, dict) or not all(
        isinstance(username, str) and isinstance(password_hash, str)
        for username, password_hash in teachers.items()
    ):
        parser.error("Credentials file must contain a teachers object of password hashes")

    teachers[args.username] = hash_password(password)
    credentials_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=credentials_path.parent,
            delete=False,
        ) as credentials_file:
            temporary_path = credentials_file.name
            json.dump(data, credentials_file, indent=2)
            credentials_file.write("\n")
        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, credentials_path)
    finally:
        if temporary_path and os.path.exists(temporary_path):
            os.unlink(temporary_path)

    print(f"Teacher account '{args.username}' saved to {credentials_path}")


if __name__ == "__main__":
    main()
