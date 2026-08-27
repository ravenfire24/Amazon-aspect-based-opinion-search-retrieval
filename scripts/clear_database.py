from __future__ import annotations

import os
import sys

import pymysql

from import_reviews import load_local_env, parse_database_url


TABLES = [
    "reports",
    "search_results",
    "search_queries",
    "review_aspects",
    "aspects",
    "reviews",
    "datasets",
]


def main() -> int:
    load_local_env()
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        print("DATABASE_URL is required.", file=sys.stderr)
        return 1

    if os.environ.get("CONFIRM_CLEAR_DATABASE") != "yes":
        print(
            "Refusing to clear database. Set CONFIRM_CLEAR_DATABASE=yes to continue.",
            file=sys.stderr,
        )
        return 1

    connection = pymysql.connect(**parse_database_url(database_url))

    try:
        with connection.cursor() as cursor:
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

            for table in TABLES:
                cursor.execute(f"TRUNCATE TABLE {table}")
                print(f"Cleared {table}")

            cursor.execute("SET FOREIGN_KEY_CHECKS = 1")

        print("Database cleared.")
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
