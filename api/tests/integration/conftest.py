import subprocess
from pathlib import Path

import pytest

DOC_A = """---
id: doc-a
kind: doc
schema_version: 1
title: Alpha
space: platform/handbook
---
Alpha body
"""

DOC_B = """---
id: doc-b
kind: doc
schema_version: 1
title: Beta
space: org/risk-portfolio
---
Beta body
"""

# Missing schema_version — must be quarantined (INV-ST-3).
DOC_INVALID = """---
id: doc-bad
kind: doc
title: NoVersion
space: platform/handbook
---
bad
"""


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def _write(root: Path, rel: str, content: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "spike@scree.test")
    _git(tmp_path, "config", "user.name", "spike")
    _write(tmp_path, "docs/a.md", DOC_A)
    _write(tmp_path, "docs/b.md", DOC_B)
    _write(tmp_path, "docs/bad.md", DOC_INVALID)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "seed")
    return tmp_path


# A Space as a folder tree: nested docs + a per-folder upload (attachment).
ONBOARDING = """---
id: doc-onboarding
kind: doc
schema_version: 1
title: Onboarding
space: platform/handbook
---
See diagram.
"""

DEEP = """---
id: doc-deep
kind: doc
schema_version: 1
title: Deep
space: platform/handbook
---
Nested page.
"""


@pytest.fixture
def tree_repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "spike@scree.test")
    _git(tmp_path, "config", "user.name", "spike")
    _write(tmp_path, "onboarding/index.md", ONBOARDING)
    _write(tmp_path, "onboarding/diagram.png", "PNGDATA")  # per-folder upload
    _write(tmp_path, "onboarding/sub/deep.md", DEEP)  # nested page (hierarchy)
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "seed tree")
    return tmp_path
