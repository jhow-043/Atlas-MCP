"""Core Context Layer — reads real project metadata.

Provides the ``CoreContextProvider`` class which reads from
``pyproject.toml``, ``ruff.toml`` and the filesystem to produce
structured data for the core context resources.
"""

from __future__ import annotations

import logging
import tomllib
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CoreContextProvider:
    """Read and provide core project context from real sources.

    The provider reads ``pyproject.toml`` and ``ruff.toml`` from
    the project root, and scans the directory structure under ``src/``.

    Args:
        project_root: Path to the project root directory.
    """

    def __init__(self, project_root: Path | None = None) -> None:
        """Initialize with a project root path.

        Args:
            project_root: Path to the project root.
                Defaults to the discovered project root via pyproject.toml.
        """
        self._root = project_root or self._discover_root()
        self._pyproject: dict[str, Any] | None = None
        self._ruff_config: dict[str, Any] | None = None

    @staticmethod
    def _discover_root() -> Path:
        """Walk up from the package directory to find the project root.

        Returns:
            The directory containing ``pyproject.toml``.
            Falls back to the package directory with a warning if
            ``pyproject.toml`` is not found (e.g. inside a Docker
            container where only the wheel is installed).
        """
        current = Path(__file__).resolve().parent
        for parent in [current, *current.parents]:
            if (parent / "pyproject.toml").exists():
                return parent
        logger.warning(
            "Could not find pyproject.toml in any parent directory — "
            "using package directory as root (running inside container?)."
        )
        return current

    def _load_pyproject(self) -> dict[str, Any]:
        """Load and cache ``pyproject.toml``.

        Returns:
            The parsed TOML data, or empty dict if file doesn't exist.
        """
        if self._pyproject is None:
            pyproject_path = self._root / "pyproject.toml"
            if pyproject_path.exists():
                with pyproject_path.open("rb") as f:
                    self._pyproject = tomllib.load(f)
            else:
                logger.warning("pyproject.toml not found at %s", pyproject_path)
                self._pyproject = {}
        return self._pyproject

    def _load_ruff_config(self) -> dict[str, Any]:
        """Load and cache ``ruff.toml``.

        Returns:
            The parsed TOML data, or empty dict if file doesn't exist.
        """
        if self._ruff_config is None:
            ruff_path = self._root / "ruff.toml"
            if ruff_path.exists():
                with ruff_path.open("rb") as f:
                    self._ruff_config = tomllib.load(f)
            else:
                self._ruff_config = {}
        return self._ruff_config

    def get_stack(self) -> dict[str, Any]:
        """Return the technology stack from real project sources.

        Reads ``pyproject.toml`` for project name, version, Python
        requirement, dependencies, and dev tools.  Reads ``ruff.toml``
        for linting configuration.

        Returns:
            A dictionary with the technology stack data.
        """
        pyproject = self._load_pyproject()
        ruff = self._load_ruff_config()
        project = pyproject.get("project", {})

        dependencies = project.get("dependencies", [])
        dev_deps = project.get("optional-dependencies", {}).get("dev", [])

        return {
            "project": project.get("name", "unknown"),
            "version": project.get("version", "0.0.0"),
            "language": {
                "name": "Python",
                "version": project.get("requires-python", ">=3.12"),
            },
            "runtime": "Asyncio",
            "package_manager": "uv",
            "dependencies": dependencies,
            "dev_dependencies": dev_deps,
            "linting": {
                "tool": "Ruff",
                "line_length": ruff.get("line-length", 100),
                "target_version": ruff.get("target-version", "py312"),
                "rules": ruff.get("lint", {}).get("select", []),
            },
            "type_checking": {"tool": "mypy", "mode": "strict"},
            "ci": "GitHub Actions",
        }

    def get_conventions(self) -> dict[str, Any]:
        """Return the project coding conventions.

        Extracts conventions from ``ruff.toml`` and ``pyproject.toml``:
        line length, quote style, indent style, docstring convention,
        import order, naming conventions, and test patterns.

        Returns:
            A dictionary with coding conventions.
        """
        ruff = self._load_ruff_config()
        pyproject = self._load_pyproject()

        format_config = ruff.get("format", {})
        lint_config = ruff.get("lint", {})
        pydocstyle = lint_config.get("pydocstyle", {})
        isort_config = lint_config.get("isort", {})

        pytest_config = pyproject.get("tool", {}).get("pytest", {}).get("ini_options", {})

        return {
            "style": {
                "line_length": ruff.get("line-length", 100),
                "indent_style": format_config.get("indent-style", "space"),
                "quote_style": format_config.get("quote-style", "double"),
                "line_ending": format_config.get("line-ending", "lf"),
            },
            "docstrings": {
                "convention": pydocstyle.get("convention", "google"),
                "language": "English",
            },
            "imports": {
                "known_first_party": isort_config.get("known-first-party", []),
                "order": [
                    "standard library",
                    "third-party",
                    "first-party",
                ],
            },
            "naming": {
                "packages": "snake_case",
                "classes": "PascalCase",
                "functions": "snake_case",
                "constants": "UPPER_SNAKE_CASE",
                "private": "prefix _",
            },
            "testing": {
                "framework": "pytest",
                "async_mode": pytest_config.get("asyncio_mode", "auto"),
                "test_prefix": "test_should_ or test_when_",
                "pattern": "Arrange → Act → Assert",
            },
        }

    def get_structure(self) -> dict[str, Any]:
        """Return the project directory structure.

        Scans the filesystem under the project root, excluding hidden
        directories, ``__pycache__``, ``.venv``, ``node_modules``, and
        common build artifacts.

        Returns:
            A dictionary with directory tree and key files.
        """
        excluded = {
            "__pycache__",
            ".venv",
            ".git",
            ".mypy_cache",
            ".pytest_cache",
            ".ruff_cache",
            "node_modules",
            ".eggs",
            "*.egg-info",
        }

        def _scan(path: Path, max_depth: int = 4, depth: int = 0) -> dict[str, Any]:
            """Recursively scan directory structure.

            Args:
                path: The directory to scan.
                max_depth: Maximum recursion depth.
                depth: Current depth.

            Returns:
                A dict representing the directory tree.
            """
            result: dict[str, Any] = {"name": path.name, "type": "directory", "children": []}

            if depth >= max_depth:
                result["children"].append({"name": "...", "type": "truncated"})
                return result

            try:
                entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name))
            except PermissionError:
                return result

            for entry in entries:
                if entry.name in excluded or entry.name.startswith("."):
                    continue
                if entry.is_dir():
                    result["children"].append(_scan(entry, max_depth, depth + 1))
                else:
                    result["children"].append({"name": entry.name, "type": "file"})

            return result

        tree = _scan(self._root)

        key_files = []
        for name in ["pyproject.toml", "ruff.toml", "README.md", "CHANGELOG.md", "LICENSE"]:
            if (self._root / name).exists():
                key_files.append(name)

        return {
            "project_root": str(self._root),
            "tree": tree,
            "key_files": key_files,
        }
