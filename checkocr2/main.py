"""Application bootstrap for package-based launchers."""

from __future__ import annotations

import importlib

from .launcher_bootstrap import ensure_repo_venv

ensure_repo_venv()

main = importlib.import_module(".app", __package__).main

if __name__ == "__main__":
    main()
