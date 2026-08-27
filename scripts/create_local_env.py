from __future__ import annotations

import getpass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env.local"
DEFAULT_HOST = "mysql-host.example.com"
DEFAULT_PORT = "3306"
DEFAULT_USER = "user"
DEFAULT_DATABASE = "review_intelligence"
DEFAULT_CA_PATH = Path.home() / "Downloads" / "ca.pem"


def prompt(default: str, label: str) -> str:
    value = input(f"{label} [{default}]: ").strip()
    return value or default


def main() -> int:
    if ENV_PATH.exists():
        overwrite = input(".env.local already exists. Overwrite it? [y/N]: ")

        if overwrite.strip().lower() != "y":
            print("Canceled. Existing .env.local was left unchanged.")
            return 0

    host = prompt(DEFAULT_HOST, "MySQL host")
    port = prompt(DEFAULT_PORT, "MySQL port")
    user = prompt(DEFAULT_USER, "MySQL user")
    database = prompt(DEFAULT_DATABASE, "MySQL database")
    ca_path = prompt(str(DEFAULT_CA_PATH), "CA certificate path")
    password = getpass.getpass("MySQL password: ")

    if not password:
        print("Password is required.")
        return 1

    env_content = "\n".join(
        [
            (
                "DATABASE_URL="
                f"mysql://{user}:{password}@{host}:{port}/{database}?ssl-mode=REQUIRED"
            ),
            f"MYSQL_DATABASE={database}",
            f"MYSQL_CA_CERT_PATH={ca_path}",
            "MYSQL_SSL_REJECT_UNAUTHORIZED=true",
            "IMPORT_BATCH_SIZE=100",
            "IMPORT_LIMIT=20000",
            "",
        ]
    )

    ENV_PATH.write_text(env_content, encoding="utf-8")
    print(f"Wrote {ENV_PATH}")
    print("Do not commit this file. It is ignored by .gitignore.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
