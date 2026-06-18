#!/usr/bin/env python
"""
Compare two directories of characterization artifacts and report drift.

Usage:
    python scripts/compare_characterization.py <current_dir> <base_dir> [--strict]

Outputs:
  - unified diff per scenario to stdout
  - summary table to stdout
  - summary table to $GITHUB_STEP_SUMMARY if set

Exit codes:
  0    always (informational), unless --strict is passed
  1    any drift detected (only with --strict)
"""

from __future__ import unicode_literals

import difflib
import json
import os
import sys


def load_artifacts(artifact_dir):
    result = {}
    if not os.path.isdir(artifact_dir):
        return result
    for fname in os.listdir(artifact_dir):
        if not fname.endswith(".json"):
            continue
        filepath = os.path.join(artifact_dir, fname)
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        result[data["name"]] = data
    return result


def compare_artifacts(current, base):
    diffs = {}

    all_names = sorted(set(list(current.keys()) + list(base.keys())))

    for name in all_names:
        if name not in current:
            diffs[name] = "MISSING_IN_CURRENT"
        elif name not in base:
            diffs[name] = "MISSING_IN_BASE"
        else:
            cur = current[name]
            base_artifact = base[name]

            if cur == base_artifact:
                diffs[name] = "MATCH"
            else:
                diffs[name] = "DRIFT"

    return diffs, all_names


def format_diff(current, base_artifact, name):
    if name not in current:
        return ["=== {}: MISSING IN CURRENT ===".format(name)]
    if name not in base_artifact:
        return ["=== {}: MISSING IN BASE ===".format(name)]

    cur = current[name]
    base_val = base_artifact[name]
    lines = []

    for key in sorted(set(list(cur.keys()) + list(base_val.keys()))):
        cur_val = json.dumps(cur.get(key), indent=2, sort_keys=True, ensure_ascii=False)
        base_val_str = json.dumps(
            base_val.get(key), indent=2, sort_keys=True, ensure_ascii=False
        )
        if cur_val != base_val_str:
            diff_lines = list(
                difflib.unified_diff(
                    base_val_str.splitlines(True),
                    cur_val.splitlines(True),
                    fromfile="base/{}".format(key),
                    tofile="current/{}".format(key),
                    lineterm="",
                )
            )
            if diff_lines:
                lines.append("--- Field: {} ---".format(key))
                lines.extend(diff_lines)
                lines.append("")

    return lines


def write_summary_table(diffs, all_names, file=sys.stdout):
    sep = "+" + "-" * 32 + "+" + "-" * 18 + "+"
    file.write(sep + "\n")
    file.write("| {:<30} | {:<16} |\n".format("Scenario", "Result"))
    file.write(sep + "\n")

    drift_count = 0
    match_count = 0
    missing_count = 0

    for name in all_names:
        result = diffs[name]
        if result == "MATCH":
            match_count += 1
        elif result == "DRIFT":
            drift_count += 1
        elif result.startswith("MISSING"):
            missing_count += 1

        file.write("| {:<30} | {:<16} |\n".format(name, result))

    file.write(sep + "\n")

    total = len(all_names)
    file.write(
        "Summary: {} total, {} match, {} drift, {} missing\n".format(
            total, match_count, drift_count, missing_count
        )
    )

    return drift_count > 0


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Compare characterization artifacts for drift detection"
    )
    parser.add_argument("current_dir", help="Directory with current-run artifacts")
    parser.add_argument("base_dir", help="Directory with base-branch artifacts")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 if any drift is detected (default: exit 0 always)",
    )
    args = parser.parse_args()

    current = load_artifacts(args.current_dir)
    base = load_artifacts(args.base_dir)

    if not current:
        print("ERROR: No artifacts found in current_dir: {}".format(args.current_dir))
        sys.exit(0 if not args.strict else 1)

    if not base:
        print("WARNING: No artifacts found in base_dir: {}".format(args.base_dir))
        print("This is expected on the first run or after artifact expiry.")
        print(
            "Nothing to compare — this run's artifacts will serve as the new baseline."
        )
        sys.exit(0)

    diffs, all_names = compare_artifacts(current, base)

    for name in all_names:
        if diffs[name] != "MATCH":
            diff_lines = format_diff(current, base, name)
            if diff_lines:
                for line in diff_lines:
                    print(line)

    has_drift = write_summary_table(diffs, all_names, file=sys.stdout)

    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a", encoding="utf-8") as f:
            f.write("## CLI Characterization Drift Report\n\n")
            f.write("<pre>\n")
            write_summary_table(diffs, all_names, file=f)
            f.write("</pre>\n")
            f.write("\n")
            if has_drift:
                f.write(
                    "**Drift detected!** Review the diff above to confirm whether "
                    "the output change is intentional.\n"
                )
            else:
                f.write("No drift detected. All scenarios match the baseline.\n")

    if args.strict and has_drift:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
