"""
S3 document loader.

Streams raw file bytes from S3 and yields (s3_key, bytes, etag) tuples.
Access-role is resolved from the S3 key prefix so it never has to be
manually tagged per document — the folder IS the security boundary.

Prefix → access_role mapping:
  s3://bucket/hr/       → HR-Admin
  s3://bucket/finance/  → Finance
  s3://bucket/staff/    → General-Staff
  s3://bucket/public/   → Public
"""
from __future__ import annotations

import io
from typing import Generator

import boto3
from botocore.exceptions import ClientError

from config import cfg
from utils import logger

# Map top-level S3 prefixes to RBAC roles
PREFIX_ROLE_MAP: dict[str, str] = {
    "hr/":      "HR-Admin",
    "finance/": "Finance",
    "staff/":   "General-Staff",
    "public/":  "Public",
}

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md", ".csv", ".xlsx"}


def _resolve_role(key: str) -> str:
    """Return the access_role for a given S3 key based on its prefix."""
    for prefix, role in PREFIX_ROLE_MAP.items():
        if key.startswith(prefix):
            return role
    # Default to most restrictive if prefix is unknown
    logger.warning(f"Unknown prefix for key '{key}' — defaulting to HR-Admin")
    return "HR-Admin"


def _is_supported(key: str) -> bool:
    return any(key.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS)


def stream_documents(
    prefix: str = "",
    override_role: str | None = None,
) -> Generator[tuple[str, bytes, str, str], None, None]:
    """
    Yield (s3_key, raw_bytes, access_role, etag) for every supported
    document under `prefix` in the configured S3 bucket.

    Args:
        prefix: S3 key prefix to scan (e.g. "hr/" or "" for all).
        override_role: Force a specific access_role (useful in tests).

    Yields:
        (key, raw_bytes, access_role, etag)
    """
    s3 = boto3.client("s3")

    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=cfg.s3_bucket, Prefix=prefix)

    for page in pages:
        for obj in page.get("Contents", []):
            key: str = obj["Key"]
            etag: str = obj.get("ETag", "").strip('"')

            if not _is_supported(key):
                logger.debug(f"Skipping unsupported file: {key}")
                continue

            access_role = override_role or _resolve_role(key)

            try:
                buf = io.BytesIO()
                s3.download_fileobj(cfg.s3_bucket, key, buf)
                buf.seek(0)
                raw = buf.read()
                logger.info(f"Fetched s3://{cfg.s3_bucket}/{key} ({len(raw):,} bytes) [{access_role}]")
                yield key, raw, access_role, etag

            except ClientError as exc:
                logger.error(f"Failed to download {key}: {exc}")
                continue


def fetch_single(key: str) -> tuple[bytes, str, str]:
    """
    Fetch a single document by its exact S3 key.

    Returns:
        (raw_bytes, access_role, etag)
    """
    s3 = boto3.client(
        "s3")
    response = s3.get_object(Bucket=cfg.s3_bucket, Key=key)
    raw = response["Body"].read()
    etag = response.get("ETag", "").strip('"')
    role = _resolve_role(key)
    return raw, role, etag
