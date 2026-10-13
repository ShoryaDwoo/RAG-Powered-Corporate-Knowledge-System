#!/usr/bin/env python3
"""
CLI entrypoint for running the ingestion pipeline.

Usage:
    # Ingest everything
    python run_ingest.py

    # Ingest a specific S3 prefix
    python run_ingest.py --prefix hr/

    # Re-ingest a single file (deletes stale vectors first)
    python run_ingest.py --key hr/leave_policy_2026.pdf

    # Re-ingest all (replaces stale vectors)
    python run_ingest.py --reingest
"""
import argparse
import sys

from ingestion.pipeline import run_full_ingest, ingest_single_document
from utils import logger


def main():
    parser = argparse.ArgumentParser(description="RAG Pipeline Ingestion CLI")
    parser.add_argument("--prefix", default="", help="S3 prefix to scan (default: all)")
    parser.add_argument("--key", default=None, help="Ingest a single S3 key")
    parser.add_argument("--reingest", action="store_true", help="Delete stale vectors before re-ingesting")
    args = parser.parse_args()

    if args.key:
        logger.info(f"Single-document ingest: {args.key}")
        result = ingest_single_document(args.key, reingest=args.reingest)
        if result["error"]:
            logger.error(f"Failed: {result['error']}")
            sys.exit(1)
        logger.info(f"Done: {result['chunks']} chunks ingested")
    else:
        logger.info(f"Full ingest | prefix='{args.prefix}' | reingest={args.reingest}")
        stats = run_full_ingest(prefix=args.prefix, reingest=args.reingest)
        logger.info(
            f"Summary — documents: {stats['processed']}, "
            f"chunks: {stats['chunks']}, "
            f"errors: {len(stats['errors'])}"
        )
        if stats["errors"]:
            for err in stats["errors"]:
                logger.error(err)
            sys.exit(1)


if __name__ == "__main__":
    main()
