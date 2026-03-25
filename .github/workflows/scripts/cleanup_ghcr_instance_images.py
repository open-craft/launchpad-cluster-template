#!/usr/bin/env python3
"""
Cleanup GHCR container versions using per-instance retention policies.

Usage:
  python3 cleanup_ghcr_instance_images.py \
    --package-name "phd-shared-cluster" \
    --instances-root "instances" \
    --instance-marker-file "config.yml" \
    --hash-length 8 \
    --repo "owner/repo" \
    --token-env "GITHUB_TOKEN" \
    --max-per-instance 1 \
    --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request

API_VERSION = "2026-03-10"


@dataclass(frozen=True)
class ParsedTag:
    tag: str
    tutor_version: str
    instance: str
    build_date: date


@dataclass(frozen=True)
class VersionInfo:
    version_id: int
    tags: tuple[str, ...]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cleanup GHCR package versions with per-instance retention."
    )
    parser.add_argument(
        "--package-name",
        required=True,
        help='GHCR package name, e.g. "<repo>/<suffix>"',
    )
    parser.add_argument(
        "--instances-root",
        default="instances",
        help="Path containing instance directories (default: instances)",
    )
    parser.add_argument(
        "--instance-marker-file",
        default="config.yml",
        help=(
            "Only directories containing this file are considered instances. "
            "Pass empty string to disable the marker check."
        ),
    )
    parser.add_argument(
        "--hash-length",
        type=int,
        default=8,
        help="Expected random hash suffix length in tags (default: 8)",
    )
    parser.add_argument(
        "--repo",
        default=os.getenv("GITHUB_REPOSITORY", ""),
        help='GitHub repository in "owner/repo" format (default: $GITHUB_REPOSITORY)',
    )
    parser.add_argument(
        "--token-env",
        default="GITHUB_TOKEN",
        help="Environment variable name that contains the GitHub token",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print actions without deleting versions",
    )
    policy_group = parser.add_mutually_exclusive_group(required=True)
    policy_group.add_argument(
        "--max-per-instance",
        type=int,
        help="Keep at most this many newest images per instance",
    )
    policy_group.add_argument(
        "--retention-days",
        type=int,
        help="Delete images older than this number of days per instance",
    )
    return parser.parse_args()


def load_instances(instances_root: Path, marker_file: str) -> set[str]:
    if not instances_root.exists():
        raise SystemExit(f"Instances root does not exist: {instances_root}")

    if not instances_root.is_dir():
        raise SystemExit(f"Instances root is not a directory: {instances_root}")

    instances: set[str] = set()
    for child in instances_root.iterdir():
        if not child.is_dir():
            continue

        if marker_file and not (child / marker_file).is_file():
            continue

        instances.add(child.name)

    return instances


def parse_build_date(raw: str) -> date | None:
    if re.fullmatch(r"\d{8}", raw):
        return datetime.strptime(raw, "%Y%m%d").date()

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        return datetime.strptime(raw, "%Y-%m-%d").date()

    return None


def parse_instance_tag(
    tag: str, known_instances: set[str], hash_length: int
) -> ParsedTag | None:
    if hash_length <= 0:
        raise ValueError("hash_length must be positive")

    tail_pattern = re.compile(
        rf"^(?P<prefix>.+)-(?P<raw_date>\d{{8}}|\d{{4}}-\d{{2}}-\d{{2}})-(?P<hash>[a-z0-9]{{{hash_length}}})$"
    )

    match = tail_pattern.fullmatch(tag)
    if not match:
        return None

    raw_date = match.group("raw_date")
    build_date = parse_build_date(raw_date)
    if build_date is None:
        return None

    prefix = match.group("prefix")
    for instance in sorted(known_instances, key=len, reverse=True):
        suffix = f"-{instance}"
        if not prefix.endswith(suffix):
            continue

        tutor_version = prefix[: -len(suffix)]
        if not tutor_version:
            continue

        return ParsedTag(
            tag=tag,
            tutor_version=tutor_version,
            instance=instance,
            build_date=build_date,
        )

    return None


def gh_request(method: str, url: str, token: str) -> tuple[Any, dict[str, str]]:
    req = request.Request(
        url=url,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "launchpad-ghcr-cleanup",
        },
    )

    try:
        with request.urlopen(req) as response:  # noqa: S310
            body = response.read().decode("utf-8")
            payload = json.loads(body) if body else None
            return payload, dict(response.headers.items())
    except error.HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(
            f"GitHub API request failed: {method} {url} -> {exc.code} {details}"
        ) from exc


def get_owner_type(owner: str, repo: str, token: str) -> str:
    url = f"https://api.github.com/repos/{owner}/{repo}"
    payload, _ = gh_request("GET", url, token)

    owner_type = (payload or {}).get("owner", {}).get("type", "")
    if owner_type not in {"Organization", "User"}:
        raise SystemExit(f"Unsupported repository owner type: {owner_type!r}")

    return owner_type


def list_package_versions(
    owner: str, package_name: str, owner_type: str, token: str
) -> list[VersionInfo]:
    encoded_name = parse.quote(package_name, safe="")

    # NOTE: even though the cluster is mostly set up by organizations, we support users too.
    owner_path = f"orgs/{owner}" if owner_type == "Organization" else f"users/{owner}"
    base_url = f"https://api.github.com/{owner_path}/packages/container/{encoded_name}/versions"

    versions: list[VersionInfo] = []
    page = 1
    while True:
        url = f"{base_url}?per_page=100&page={page}"

        payload, _ = gh_request("GET", url, token)
        if not payload:
            break

        for item in payload:
            metadata = item.get("metadata", {}) if isinstance(item, dict) else {}
            container_meta = (
                metadata.get("container", {}) if isinstance(metadata, dict) else {}
            )
            raw_tags = (
                container_meta.get("tags", [])
                if isinstance(container_meta, dict)
                else []
            )
            tags = tuple(t for t in raw_tags if isinstance(t, str) and t)
            version_id = item.get("id")

            if not isinstance(version_id, int):
                continue

            versions.append(VersionInfo(version_id=version_id, tags=tags))

        if len(payload) < 100:
            break

        page += 1

    return versions


def choose_delete_tags(
    parsed_tags: list[ParsedTag],
    max_per_instance: int | None,
    retention_days: int | None,
    today_utc: date,
) -> set[str]:
    if max_per_instance is None and retention_days is None:
        raise ValueError("Either max_per_instance or retention_days must be set")

    if max_per_instance is not None and max_per_instance < 1:
        raise ValueError("max_per_instance must be >= 1")

    if retention_days is not None and retention_days < 0:
        raise ValueError("retention_days must be >= 0")

    by_instance: dict[str, list[ParsedTag]] = {}
    for entry in parsed_tags:
        by_instance.setdefault(entry.instance, []).append(entry)

    delete_tags: set[str] = set()
    for _, entries in by_instance.items():
        sorted_entries = sorted(
            entries,
            key=lambda item: (item.build_date, item.tag),
            reverse=True,
        )

        keep_tags: set[str] = set()
        if max_per_instance is not None:
            keep_tags = {item.tag for item in sorted_entries[:max_per_instance]}
        else:
            assert retention_days is not None
            cutoff = today_utc - timedelta(days=retention_days)

            for item in sorted_entries:
                if item.build_date >= cutoff:
                    keep_tags.add(item.tag)

        for item in filter(lambda item: item.tag not in keep_tags, sorted_entries):
            delete_tags.add(item.tag)

    return delete_tags


def build_version_delete_plan(
    versions: list[VersionInfo],
    known_instances: set[str],
    hash_length: int,
    max_per_instance: int | None,
    retention_days: int | None,
    today_utc: date,
) -> tuple[set[int], dict[str, str], list[str]]:
    parsed: list[ParsedTag] = []
    all_tags: set[str] = set()

    for version in versions:
        for tag in version.tags:
            all_tags.add(tag)
            parsed_item = parse_instance_tag(tag, known_instances, hash_length)

            if parsed_item is not None:
                parsed.append(parsed_item)

    delete_candidate_tags = choose_delete_tags(
        parsed_tags=parsed,
        max_per_instance=max_per_instance,
        retention_days=retention_days,
        today_utc=today_utc,
    )

    parsed_tags = {item.tag for item in parsed}
    keep_tags = parsed_tags - delete_candidate_tags

    tag_status: dict[str, str] = {}
    for tag in all_tags:
        if tag in keep_tags:
            tag_status[tag] = "keep"
        elif tag in delete_candidate_tags:
            tag_status[tag] = "delete"
        else:
            tag_status[tag] = "orphan"

    warnings: list[str] = []
    deletable_versions: set[int] = set()
    for version in versions:
        if not version.tags:
            deletable_versions.add(version.version_id)
            continue

        statuses = {tag_status.get(tag, "orphan") for tag in version.tags}
        if "keep" in statuses:
            if "orphan" in statuses:
                warnings.append(
                    f"Version {version.version_id} has orphan and keep tags; skipping delete."
                )
            continue

        deletable_versions.add(version.version_id)

    return deletable_versions, tag_status, warnings


def delete_package_version(
    owner_type: str,
    owner: str,
    package_name: str,
    version_id: int,
    token: str,
) -> None:
    encoded_name = parse.quote(package_name, safe="")
    owner_path = f"orgs/{owner}" if owner_type == "Organization" else f"users/{owner}"
    url = f"https://api.github.com/{owner_path}/packages/container/{encoded_name}/versions/{version_id}"

    gh_request("DELETE", url, token)


def main() -> None:
    args = parse_args()

    if "/" not in args.repo:
        raise SystemExit(
            '--repo must be in "owner/repo" format or $GITHUB_REPOSITORY must be set'
        )

    owner, repo_name = args.repo.split("/", 1)
    token = os.getenv(args.token_env, "")
    if not token:
        raise SystemExit(f"Missing token in environment variable: {args.token_env}")

    known_instances = load_instances(
        Path(args.instances_root), args.instance_marker_file
    )
    print(f"Loaded {len(known_instances)} instances from {args.instances_root}")

    owner_type = get_owner_type(owner=owner, repo=repo_name, token=token)
    versions = list_package_versions(
        owner=owner,
        package_name=args.package_name,
        owner_type=owner_type,
        token=token,
    )

    print(
        f"Found {len(versions)} versions for package '{args.package_name}' in {owner_type} owner '{owner}'"
    )

    today_utc = datetime.now(timezone.utc).date()
    deletable_versions, tag_status, warnings = build_version_delete_plan(
        versions=versions,
        known_instances=known_instances,
        hash_length=args.hash_length,
        max_per_instance=args.max_per_instance,
        retention_days=args.retention_days,
        today_utc=today_utc,
    )

    keep_count = sum(1 for status in tag_status.values() if status == "keep")
    delete_count = sum(1 for status in tag_status.values() if status == "delete")
    orphan_count = sum(1 for status in tag_status.values() if status == "orphan")

    print(
        f"Tag classification: keep={keep_count}, delete-candidate={delete_count}, orphan={orphan_count}"
    )

    for warn in warnings:
        print(f"WARNING: {warn}")

    sorted_ids = sorted(deletable_versions)
    if args.dry_run:
        print(f"Dry-run: would delete {len(sorted_ids)} versions: {sorted_ids}")
        return

    for version_id in sorted_ids:
        print(f"Deleting version {version_id}")
        delete_package_version(
            owner_type=owner_type,
            owner=owner,
            package_name=args.package_name,
            version_id=version_id,
            token=token,
        )

    print(f"Deleted {len(sorted_ids)} versions")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        raise SystemExit(130)
