#!/usr/bin/env python3
"""Synthetic release and environment state engine."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ENVIRONMENTS = ("test", "uat", "production")
SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$")
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


class LabError(ValueError):
    """Raised when a requested transition violates the lab contract."""


def empty_state() -> dict[str, Any]:
    return {
        "schemaVersion": 1,
        "releaseCandidates": {},
        "environments": {
            name: {"digest": None, "sourceSha": None, "history": []}
            for name in ENVIRONMENTS
        },
    }


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return empty_state()
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("schemaVersion") != 1:
        raise LabError("Unsupported state schema")
    return state


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def require_sha(value: str) -> str:
    value = value.lower()
    if not SHA_PATTERN.fullmatch(value):
        raise LabError("Source SHA must contain exactly 40 hexadecimal characters")
    return value


def synthetic_digest(source_sha: str) -> str:
    payload = json.dumps(
        {"kind": "synthetic-release-candidate", "sourceSha": source_sha},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def build_release_candidate(
    state: dict[str, Any], source_sha: str, timestamp: str
) -> dict[str, str]:
    source_sha = require_sha(source_sha)
    if source_sha in state["releaseCandidates"]:
        raise LabError(f"Release candidate for {source_sha} already exists")
    manifest = {
        "sourceSha": source_sha,
        "tag": f"rc-{source_sha[:12]}",
        "digest": synthetic_digest(source_sha),
        "createdAt": timestamp,
    }
    state["releaseCandidates"][source_sha] = manifest
    return manifest


def promote(
    state: dict[str, Any],
    environment: str,
    digest: str,
    source_sha: str,
    operation: str,
    timestamp: str,
) -> dict[str, str]:
    if environment not in ENVIRONMENTS:
        raise LabError(f"Unknown environment: {environment}")
    if operation not in {"promote", "rollback"}:
        raise LabError(f"Unknown operation: {operation}")
    if not DIGEST_PATTERN.fullmatch(digest):
        raise LabError("Digest must use sha256:<64 lowercase hexadecimal> format")
    source_sha = require_sha(source_sha)
    candidate = state["releaseCandidates"].get(source_sha)
    if not candidate or candidate["digest"] != digest:
        raise LabError("Digest and source SHA do not identify one registered release candidate")

    target = state["environments"][environment]
    if operation == "promote":
        predecessor = {"uat": "test", "production": "uat"}.get(environment)
        if predecessor and state["environments"][predecessor]["digest"] != digest:
            raise LabError(f"{predecessor.upper()} does not contain {digest}")
    else:
        previous = {record["digest"] for record in target["history"]}
        if digest == target["digest"] or digest not in previous:
            raise LabError(f"Digest {digest} was not previously deployed to {environment}")

    record = {
        "environment": environment,
        "operation": operation,
        "digest": digest,
        "sourceSha": source_sha,
        "recordedAt": timestamp,
    }
    target["digest"] = digest
    target["sourceSha"] = source_sha
    target["history"].append(record)
    return record


def timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def write_output(path: str, value: dict[str, Any]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--state", default="state/lab-state.json")
    commands = root.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build")
    build.add_argument("--source-sha", required=True)
    build.add_argument("--output", required=True)

    deploy = commands.add_parser("promote")
    deploy.add_argument("--environment", choices=ENVIRONMENTS, required=True)
    deploy.add_argument("--operation", choices=("promote", "rollback"), required=True)
    deploy.add_argument("--digest", required=True)
    deploy.add_argument("--source-sha", required=True)
    deploy.add_argument("--output", required=True)
    return root


def main() -> int:
    args = parser().parse_args()
    state_path = Path(args.state)
    state = load_state(state_path)
    try:
        if args.command == "build":
            result = build_release_candidate(state, args.source_sha, timestamp())
        else:
            result = promote(
                state,
                args.environment,
                args.digest,
                args.source_sha,
                args.operation,
                timestamp(),
            )
        save_state(state_path, state)
        write_output(args.output, result)
    except LabError as exc:
        raise SystemExit(f"lab contract rejected the operation: {exc}") from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
