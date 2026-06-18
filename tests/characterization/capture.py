from __future__ import unicode_literals

import io
import json
import os
from unittest.mock import MagicMock, patch

from .scenarios import SCENARIOS

ARTIFACT_DIR = os.path.join(os.path.dirname(__file__), "_artifacts")


def outs():
    return io.StringIO(), io.StringIO()


def _mock_anthropic(response_text):
    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock()]
    mock_message.content[0].text = response_text
    mock_client.messages.create.return_value = mock_message
    return patch("anthropic.Anthropic", return_value=mock_client)


def _mock_import_error():
    import builtins

    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "anthropic":
            raise ImportError("No module named 'anthropic'")
        return original_import(name, *args, **kwargs)

    return patch("builtins.__import__", side_effect=mock_import)


def run_scenario(scenario):
    from migra.command import parse_args, run

    out, err = outs()

    patches = []

    if scenario.get("env") is not None:
        patches.append(patch.dict("os.environ", scenario["env"], clear=True))

    if "load_config_return" in scenario:
        patches.append(
            patch(
                "migra.ai_explain.load_config",
                return_value=scenario["load_config_return"],
            )
        )

    if scenario.get("mock_import_error"):
        patches.append(_mock_import_error())

    if scenario.get("mock_anthropic"):
        response_text = scenario.get(
            "mock_anthropic_response",
            "Mock Anthropic response for characterization.",
        )
        if scenario.get("mock_runtime_error"):
            mock_client = MagicMock()
            mock_client.messages.create.side_effect = RuntimeError("AI failure")
            patches.append(patch("anthropic.Anthropic", return_value=mock_client))
        else:
            patches.append(_mock_anthropic(response_text))

    if scenario.get("mock_inspector"):
        patches.append(patch("schemainspect.get_inspector", return_value=MagicMock()))
        patches.append(patch("migra.db_inspector._fetch_table_sizes", return_value={}))

    for p in patches:
        p.start()

    try:
        args = parse_args(scenario["args"])
        status = run(args, out=out, err=err)
        stdout = out.getvalue()
        stderr = err.getvalue()
    except Exception as exc:
        stdout = out.getvalue()
        stderr = err.getvalue() + "\nUNEXPECTED_EXCEPTION: {}".format(exc)
        status = -1
    finally:
        for p in reversed(patches):
            p.stop()

    return {
        "name": scenario["name"],
        "args": scenario["args"],
        "status": status,
        "stdout": stdout,
        "stderr": stderr,
        "description": scenario.get("description", ""),
    }


def capture_all(scenarios=None, artifact_dir=None):
    if scenarios is None:
        scenarios = SCENARIOS
    if artifact_dir is None:
        artifact_dir = ARTIFACT_DIR

    os.makedirs(artifact_dir, exist_ok=True)

    results = []
    for scenario in scenarios:
        result = run_scenario(scenario)
        results.append(result)

        filename = "{}.json".format(result["name"])
        filepath = os.path.join(artifact_dir, filename)

        json.dump(
            result,
            open(filepath, "w", encoding="utf-8"),
            indent=2,
            sort_keys=True,
            ensure_ascii=False,
        )

    return results
