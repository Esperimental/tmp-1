from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


def main(workspace: Path) -> None:
    result = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=workspace)
    result.check_returncode()

    sys.path.insert(0, str(workspace / "src"))
    from inventory_cli.store import Inventory

    path = Path(tempfile.mkdtemp()) / "nested" / "inventory.json"
    Inventory(path).add("resistor", 1)
    assert Inventory(path).items() == [("resistor", 1)]


if __name__ == "__main__":
    main(Path(sys.argv[1]))
