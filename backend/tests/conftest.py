"""Wspólna konfiguracja testów: automatyczne znaczniki ``unit`` / ``integration`` wg katalogu.

Uruchamianie wybranego poziomu: ``pytest -m unit`` albo ``pytest -m integration``.
Katalog ``tests/integration/`` powstanie w późniejszym etapie (patrz AGENTS.md).
"""

from pathlib import Path

import pytest


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        parts = Path(str(item.path)).parts
        if "unit" in parts:
            item.add_marker(pytest.mark.unit)
        elif "integration" in parts:
            item.add_marker(pytest.mark.integration)
