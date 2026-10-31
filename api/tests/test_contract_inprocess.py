"""Every route against shared/contract schemas, in-process.

Runs the same checks as judge/contract.py, so the in-process app and the deployed
server are held to one list.

Owner: B. Filled in by: B1.
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest
from fastapi.testclient import TestClient

CONTRACT_PY = Path(__file__).resolve().parents[2] / "judge" / "contract.py"


def _load_contract() -> ModuleType:
    spec = importlib.util.spec_from_file_location("judge_contract", CONTRACT_PY)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


contract = _load_contract()


@pytest.mark.parametrize(("name", "fn"), contract.CHECKS, ids=[n for n, _ in contract.CHECKS])
def test_contract(name: str, fn: Callable[[TestClient], None], client: TestClient) -> None:
    fn(client)


def test_every_schema_is_valid() -> None:
    files = contract.CONTRACT_DIR.glob("*.json")
    names = sorted(p.name.removesuffix(".schema.json") for p in files)
    assert len(names) == 16
    for name in names:
        contract.load_schema(name)
