#!/usr/bin/env python
"""
Download the most recent characterization artifact from the base branch.

Uses the GitHub REST API via GITHUB_TOKEN. Designed for use in CI after the
current-run artifacts have been uploaded.

Environment variables:
  GITHUB_TOKEN       — GitHub token for API calls
  GITHUB_REPOSITORY  — owner/repo (e.g. "postgresql-tools/migra")
  GITHUB_HEAD_REF    — PR head ref (used to find the base branch)
  GITHUB_BASE_REF    — PR base ref (e.g. "master")

Output:
  Downloads the artifact archive into tests/characterization/_base_artifacts/
  and extracts it there.

Exit codes:
  0 — artifact downloaded and extracted successfully
  0 — no artifact found (expected on first run / after expiry); logs a warning
  1 — unexpected error
"""

from __future__ import unicode_literals

import json
import os
import sys
import tempfile
import zipfile
from urllib.request import Request, urlopen

ARTIFACT_NAME_PREFIX = "characterization-"
OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tests",
    "characterization",
    "_base_artifacts",
)


def api_get(url, token):
    req = Request(url)
    req.add_header("Authorization", "Bearer {}".format(token))
    req.add_header("Accept", "application/vnd.github.v3+json")
    resp = urlopen(req)
    return json.loads(resp.read().decode("utf-8"))


def api_get_stream(url, token):
    req = Request(url)
    req.add_header("Authorization", "Bearer {}".format(token))
    req.add_header("Accept", "application/vnd.github.v3+json")
    return urlopen(req)


def main():
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    base_ref = os.environ.get("GITHUB_BASE_REF", "master")

    if not token:
        print("WARNING: GITHUB_TOKEN not set, cannot download base artifact.")
        sys.exit(0)

    if not repo:
        print("WARNING: GITHUB_REPOSITORY not set, cannot download base artifact.")
        sys.exit(0)

    api_base = "https://api.github.com/repos/{}".format(repo)

    # List artifacts for the repo, sorted by created_at desc
    try:
        data = api_get(
            "{}/actions/artifacts?per_page=30".format(api_base),
            token,
        )
    except Exception as e:
        print("WARNING: Failed to list artifacts: {}".format(e))
        sys.exit(0)

    artifacts = data.get("artifacts", [])

    # Filter: name starts with prefix, and was created on the base branch
    # (GitHub artifacts store the workflow run's branch in the artifact metadata
    #  but we don't have direct branch info in the artifact list API response.
    #  Instead, we filter by artifacts whose workflow_run.head_branch matches base_ref.)
    # Actually, the artifacts API response includes workflow_run.head_branch.
    # Let's filter by that.
    candidates = []
    for art in artifacts:
        name = art.get("name", "")
        if not name.startswith(ARTIFACT_NAME_PREFIX):
            continue
        wf_run = art.get("workflow_run", {})
        if not wf_run:
            # Fall back to name matching — the old format might not have run info
            candidates.append(art)
            continue
        head_branch = wf_run.get("head_branch", "")
        if head_branch == base_ref:
            candidates.append(art)

    if not candidates:
        print(
            "WARNING: No characterization artifact found for branch '{}'. "
            "This is normal on the first run or after artifact expiry (5-day retention).".format(
                base_ref
            )
        )
        sys.exit(0)

    # Sort by created_at descending, pick the most recent
    candidates.sort(key=lambda a: a.get("created_at", ""), reverse=True)
    target = candidates[0]
    artifact_id = target["id"]
    created_at = target.get("created_at", "unknown")

    print(
        "Downloading artifact id={} (created: {}) from branch '{}'".format(
            artifact_id, created_at, base_ref
        )
    )

    # Download the artifact zip
    download_url = "{}/actions/artifacts/{}/zip".format(api_base, artifact_id)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    try:
        resp = api_get_stream(download_url, token)
        data = resp.read()
    except Exception as e:
        print("WARNING: Failed to download artifact: {}".format(e))
        sys.exit(0)

    # Extract zip
    with tempfile.TemporaryFile() as tmp:
        tmp.write(data)
        tmp.seek(0)
        with zipfile.ZipFile(tmp) as zf:
            zf.extractall(OUTPUT_DIR)

    # Verify something was extracted
    extracted = os.listdir(OUTPUT_DIR)
    print("Downloaded and extracted {} files to {}".format(len(extracted), OUTPUT_DIR))
    sys.exit(0)


if __name__ == "__main__":
    main()
