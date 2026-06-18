from __future__ import unicode_literals

import json
import os
import shutil

from .capture import ARTIFACT_DIR, SCENARIOS, capture_all, run_scenario


class TestCharacterizationCapture:
    def test_all_scenarios_captured(self):
        tmpdir = ARTIFACT_DIR + "_tmp"
        os.makedirs(tmpdir, exist_ok=True)
        try:
            results = capture_all(artifact_dir=tmpdir)

            for result in results:
                name = result["name"]
                assert isinstance(
                    result["status"], int
                ), "{}: status should be int, got {}".format(
                    name, type(result["status"])
                )
                assert isinstance(
                    result["stdout"], str
                ), "{}: stdout should be str".format(name)
                assert isinstance(
                    result["stderr"], str
                ), "{}: stderr should be str".format(name)

            artifact_files = [f for f in os.listdir(tmpdir) if f.endswith(".json")]
            assert len(artifact_files) == len(
                results
            ), "Expected {} artifact files, found {}".format(
                len(results), len(artifact_files)
            )

            for fname in artifact_files:
                filepath = os.path.join(tmpdir, fname)
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                assert "name" in data
                assert "status" in data
                assert "stdout" in data
                assert "stderr" in data
                assert "args" in data

        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_no_key_scenarios_exit_one(self):
        no_key_scenarios = [
            s
            for s in SCENARIOS
            if "no_key" in s["name"] and not s.get("needs_postgres")
        ]

        for scenario in no_key_scenarios:
            result = run_scenario(scenario)
            assert (
                result["status"] == 1
            ), "{} expected exit 1, got {}: stderr={!r}".format(
                scenario["name"], result["status"], result["stderr"][:200]
            )
            assert result["stderr"], "{} expected stderr output, got empty".format(
                scenario["name"]
            )

    def test_missing_package_scenarios_exit_one(self):
        missing_pkg_scenarios = [
            s
            for s in SCENARIOS
            if s.get("mock_import_error") and not s.get("needs_postgres")
        ]

        for scenario in missing_pkg_scenarios:
            result = run_scenario(scenario)
            assert (
                result["status"] == 1
            ), "{} expected exit 1, got {}: stderr={!r}".format(
                scenario["name"], result["status"], result["stderr"][:200]
            )
            assert (
                "AI extras" in result["stderr"] or "requires the AI" in result["stderr"]
            ), "{} expected 'AI extras' error, got: {!r}".format(
                scenario["name"], result["stderr"][:200]
            )

    def test_success_empty_diff_scenarios_exit_zero(self):
        success_scenarios = [
            s
            for s in SCENARIOS
            if "empty_diff" in s["name"]
            and s.get("mock_anthropic")
            and not s.get("needs_postgres")
        ]

        for scenario in success_scenarios:
            result = run_scenario(scenario)
            assert (
                result["status"] == 0
            ), "{} expected exit 0, got {}: stderr={!r}".format(
                scenario["name"], result["status"], result["stderr"][:200]
            )
            stdout = result["stdout"]
            if "--output json" in " ".join(scenario["args"]) or "--output" in " ".join(
                scenario["args"]
            ):
                import json

                data = json.loads(stdout)
                assert "version" in data
                assert "summary" in data
                assert data["summary"]["total_statements"] == 0
            else:
                assert (
                    "No schema differences detected" in stdout
                    or "The schemas are identical" in stdout
                ), "{} expected 'No differences' in stdout, got: {!r}".format(
                    scenario["name"], stdout[:300]
                )

    def test_explain_drift_runtime_error_exits_one(self):
        scenario = next(
            s for s in SCENARIOS if s["name"] == "explain_drift_runtime_error"
        )
        result = run_scenario(scenario)
        assert result["status"] == 1, "Expected exit 1, got {}: stderr={!r}".format(
            result["status"], result["stderr"][:200]
        )

    def test_generate_success_has_output(self):
        scenario = next(s for s in SCENARIOS if s["name"] == "generate_success")
        result = run_scenario(scenario)
        assert result["status"] == 0, "Expected exit 0, got {}: stderr={!r}".format(
            result["status"], result["stderr"][:200]
        )
        assert result["stdout"], "Expected stdout output"
        assert (
            "ALTER TABLE" in result["stdout"] or result["stdout"].strip()
        ), "Expected SQL-like output, got: {!r}".format(result["stdout"][:200])

    def test_explain_drift_success_has_drift_analysis(self):
        scenario = next(s for s in SCENARIOS if s["name"] == "explain_drift_success")
        result = run_scenario(scenario)
        assert result["status"] == 0, "Expected exit 0, got {}: stderr={!r}".format(
            result["status"], result["stderr"][:200]
        )
        assert (
            "Drift Analysis" in result["stdout"] or "Drift" in result["stdout"]
        ), "Expected drift analysis in stdout, got: {!r}".format(result["stdout"][:300])
