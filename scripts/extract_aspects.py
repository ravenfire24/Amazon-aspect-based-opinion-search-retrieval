from __future__ import annotations

import os
import re
import ssl
import sys
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, unquote, urlparse

import pymysql


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATABASE = "review_intelligence"
EXTRACTOR_VERSION = "lexicon-aspect-v1"
SENTIMENT_MODEL_VERSION = "lexicon-sentiment-v1"
MAX_SENTENCES_PER_REVIEW = 4
DEFAULT_PAGE_SIZE = 250
DEFAULT_PROGRESS_EVERY = 10000

ASPECTS = [
    {
        "name": "battery life",
        "category": "power",
        "terms": [
            "battery",
            "batteries",
            "battery life",
            "charge",
            "charged",
            "charging",
            "recharge",
            "recharging",
            "power",
        ],
    },
    {
        "name": "charger",
        "category": "power",
        "terms": ["charger", "charging base", "dock", "adapter", "power cord"],
    },
    {
        "name": "software",
        "category": "software",
        "terms": ["software", "program", "application", "app", "firmware", "driver"],
    },
    {
        "name": "user interface",
        "category": "usability",
        "terms": ["interface", "menu", "menus", "navigation", "controls", "button", "buttons"],
    },
    {
        "name": "ease of use",
        "category": "usability",
        "terms": ["easy", "simple", "intuitive", "setup", "install", "installation", "manual"],
    },
    {
        "name": "performance",
        "category": "performance",
        "terms": ["fast", "slow", "speed", "performance", "lag", "freeze", "freezes", "crash"],
    },
    {
        "name": "screen",
        "category": "display",
        "terms": ["screen", "display", "lcd", "brightness", "backlight", "resolution"],
    },
    {
        "name": "sound quality",
        "category": "audio",
        "terms": ["sound", "audio", "speaker", "speakers", "volume", "headphones", "earbuds"],
    },
    {
        "name": "camera quality",
        "category": "camera",
        "terms": ["camera", "photo", "photos", "picture", "pictures", "flash", "lens"],
    },
    {
        "name": "build quality",
        "category": "hardware",
        "terms": ["quality", "durable", "durability", "fragile", "solid", "plastic", "cover"],
    },
    {
        "name": "fit and comfort",
        "category": "physical design",
        "terms": ["fit", "comfortable", "comfort", "size", "weight", "heavy", "light", "snug"],
    },
    {
        "name": "price and value",
        "category": "value",
        "terms": ["price", "cost", "cheap", "expensive", "value", "deal", "worth"],
    },
    {
        "name": "connectivity",
        "category": "connectivity",
        "terms": ["wireless", "wifi", "bluetooth", "usb", "connection", "connect", "signal"],
    },
    {
        "name": "storage and memory",
        "category": "storage",
        "terms": ["storage", "memory", "sd card", "card", "capacity", "gb", "mb"],
    },
    {
        "name": "customer support",
        "category": "support",
        "terms": ["support", "customer service", "warranty", "replacement", "refund", "returned"],
    },
]

POSITIVE_TERMS = {
    "accurate",
    "amazing",
    "best",
    "clear",
    "comfortable",
    "easy",
    "excellent",
    "fast",
    "good",
    "great",
    "happy",
    "impressive",
    "intuitive",
    "like",
    "love",
    "perfect",
    "powerful",
    "recommend",
    "reliable",
    "solid",
    "useful",
    "works",
}

NEGATIVE_TERMS = {
    "annoyance",
    "awful",
    "bad",
    "broken",
    "bug",
    "cheap",
    "complaining",
    "crash",
    "defect",
    "died",
    "difficult",
    "disappointing",
    "flaw",
    "fragile",
    "freeze",
    "horrible",
    "issue",
    "issues",
    "lame",
    "lost",
    "poor",
    "problem",
    "problems",
    "returned",
    "slow",
    "terrible",
    "weak",
    "worthless",
}

NEGATION_TERMS = {"not", "no", "never", "hardly", "without"}
WORD_RE = re.compile(r"[a-z0-9']+")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]

        os.environ.setdefault(key, value)


def load_local_env() -> None:
    node_env = os.environ.get("NODE_ENV", "development")

    for name in (
        f".env.{node_env}.local",
        ".env.local",
        f".env.{node_env}",
        ".env",
    ):
        load_env_file(PROJECT_ROOT / name)


def normalize_certificate(value: str) -> str:
    return value.strip().replace("\\n", "\n").replace("\\", "\n")


def create_ssl_context() -> ssl.SSLContext:
    ca = os.environ.get("MYSQL_CA_CERT", "").strip()
    ca_path = os.environ.get("MYSQL_CA_CERT_PATH", "").strip()
    reject_unauthorized = os.environ.get("MYSQL_SSL_REJECT_UNAUTHORIZED") != "false"

    if ca:
        return ssl.create_default_context(cadata=normalize_certificate(ca))

    if ca_path:
        return ssl.create_default_context(cafile=ca_path)

    if reject_unauthorized:
        return ssl.create_default_context()

    return ssl._create_unverified_context()


def parse_database_url(database_url: str) -> dict[str, Any]:
    parsed = urlparse(database_url)

    if parsed.scheme not in {"mysql", "mysql2"}:
        raise ValueError("DATABASE_URL must use the mysql:// scheme.")

    query = dict(parse_qsl(parsed.query))

    return {
        "host": parsed.hostname,
        "port": parsed.port or 3306,
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "database": os.environ.get("MYSQL_DATABASE") or parsed.path.lstrip("/")
        or DEFAULT_DATABASE,
        "charset": "utf8mb4",
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": True,
        "ssl": create_ssl_context() if query.get("ssl-mode") != "DISABLED" else None,
    }


def normalize_text(value: str | None) -> str:
    if not value:
        return ""

    return (
        value.replace("\\r\\n", "\n")
        .replace("\\n", "\n")
        .replace("\\r", "\n")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .strip()
    )


def split_sentences(text: str) -> list[str]:
    sentences = []

    for sentence in SENTENCE_SPLIT_RE.split(text):
        cleaned = re.sub(r"\s+", " ", sentence).strip()

        if len(cleaned) >= 20:
            sentences.append(cleaned)

    return sentences


def tokenize(text: str) -> list[str]:
    return WORD_RE.findall(text.lower())


def has_term(sentence_lower: str, term: str) -> bool:
    if " " in term:
        return term in sentence_lower

    return re.search(rf"\b{re.escape(term)}\b", sentence_lower) is not None


def infer_sentiment(sentence: str) -> tuple[str, float]:
    tokens = tokenize(sentence)
    positive = 0
    negative = 0

    for index, token in enumerate(tokens):
        window = tokens[max(0, index - 3) : index]
        negated = any(term in NEGATION_TERMS for term in window)

        if token in POSITIVE_TERMS:
            if negated:
                negative += 1
            else:
                positive += 1

        if token in NEGATIVE_TERMS:
            if negated:
                positive += 1
            else:
                negative += 1

    if positive > negative:
        return "positive", min(0.95, 0.62 + 0.08 * (positive - negative))

    if negative > positive:
        return "negative", min(0.95, 0.62 + 0.08 * (negative - positive))

    return "neutral", 0.55


def extract_review_aspects(review: dict[str, Any]) -> list[tuple[Any, ...]]:
    title = normalize_text(review.get("review_title"))
    text = normalize_text(review.get("review_text"))
    sentences = split_sentences(f"{title}. {text}")
    matches: list[tuple[Any, ...]] = []
    seen_pairs = set()

    for sentence in sentences:
        sentence_lower = sentence.lower()

        for aspect in ASPECTS:
            if not any(has_term(sentence_lower, term) for term in aspect["terms"]):
                continue

            key = (review["id"], aspect["name"], sentence[:160])

            if key in seen_pairs:
                continue

            sentiment, confidence = infer_sentiment(sentence)
            matches.append(
                (
                    review["id"],
                    aspect["name"],
                    sentence[:2000],
                    sentence[:4000],
                    sentiment,
                    confidence,
                    EXTRACTOR_VERSION,
                    SENTIMENT_MODEL_VERSION,
                )
            )
            seen_pairs.add(key)

            if len(matches) >= MAX_SENTENCES_PER_REVIEW:
                return matches

    return matches


def seed_aspects(cursor: pymysql.cursors.DictCursor) -> dict[str, int]:
    for aspect in ASPECTS:
        normalized_name = aspect["name"].lower()
        cursor.execute(
            """
            INSERT INTO aspects (name, normalized_name, category)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
              name = VALUES(name),
              category = VALUES(category)
            """,
            (aspect["name"], normalized_name, aspect["category"]),
        )

    cursor.execute("SELECT id, name FROM aspects")
    return {row["name"]: row["id"] for row in cursor.fetchall()}


def insert_review_aspects(
    cursor: pymysql.cursors.DictCursor,
    aspect_ids: dict[str, int],
    rows: list[tuple[Any, ...]],
) -> None:
    if not rows:
        return

    cursor.executemany(
        """
        INSERT INTO review_aspects
          (
            review_id,
            aspect_id,
            sentence,
            context,
            sentiment,
            confidence,
            extractor_version,
            sentiment_model_version
          )
        VALUES
          (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        [
            (
                review_id,
                aspect_ids[aspect_name],
                sentence,
                context,
                sentiment,
                confidence,
                extractor_version,
                sentiment_model_version,
            )
            for (
                review_id,
                aspect_name,
                sentence,
                context,
                sentiment,
                confidence,
                extractor_version,
                sentiment_model_version,
            ) in rows
        ],
    )


def main() -> int:
    load_local_env()
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        print("DATABASE_URL is required.", file=sys.stderr)
        return 1

    connection = pymysql.connect(**parse_database_url(database_url))
    page_size_config = int(os.environ.get("ASPECT_PAGE_SIZE") or DEFAULT_PAGE_SIZE)
    aspect_limit = int(os.environ.get("ASPECT_LIMIT") or "0")
    progress_every = int(os.environ.get("ASPECT_PROGRESS_EVERY") or DEFAULT_PROGRESS_EVERY)
    replace_existing = os.environ.get("ASPECT_REPLACE_EXISTING", "true") != "false"
    processed_reviews = 0
    inserted_aspects = 0
    last_id = 0
    next_progress_at = progress_every

    try:
        with connection.cursor() as cursor:
            if replace_existing:
                cursor.execute(
                    """
                    DELETE FROM review_aspects
                    WHERE extractor_version = %s
                    """,
                    (EXTRACTOR_VERSION,),
                )

            aspect_ids = seed_aspects(cursor)

            while True:
                remaining_clause = ""
                params: list[Any] = [last_id]

                if aspect_limit > 0:
                    remaining = aspect_limit - processed_reviews

                    if remaining <= 0:
                        break

                    page_size = min(page_size_config, remaining)
                else:
                    page_size = page_size_config

                cursor.execute(
                    f"""
                    SELECT id, review_title, review_text
                    FROM reviews
                    WHERE id > %s {remaining_clause}
                    ORDER BY id
                    LIMIT {page_size}
                    """,
                    params,
                )
                reviews = cursor.fetchall()

                if not reviews:
                    break

                rows = []

                for review in reviews:
                    rows.extend(extract_review_aspects(review))
                    last_id = max(last_id, review["id"])

                insert_review_aspects(cursor, aspect_ids, rows)
                processed_reviews += len(reviews)
                inserted_aspects += len(rows)

                if progress_every > 0 and processed_reviews >= next_progress_at:
                    print(
                        f"Processed {processed_reviews} reviews; "
                        f"inserted {inserted_aspects} aspect evidence rows..."
                    )
                    next_progress_at += progress_every

        print(
            f"Aspect extraction complete. Processed {processed_reviews} reviews; "
            f"inserted {inserted_aspects} evidence rows."
        )
        return 0
    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
