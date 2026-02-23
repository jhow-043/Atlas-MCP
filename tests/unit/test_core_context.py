"""Tests for the CoreContextProvider module."""

from __future__ import annotations

from pathlib import Path

import pytest

from atlas_mcp.context.core import CoreContextProvider

# Use the actual project root for testing
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def provider() -> CoreContextProvider:
    """Return a CoreContextProvider using the real project root."""
    return CoreContextProvider(project_root=_PROJECT_ROOT)


class TestCoreContextProviderInit:
    """Tests for CoreContextProvider initialization."""

    def test_should_accept_explicit_root(self) -> None:
        """Validate that an explicit root path is stored."""
        root = Path("/some/path")
        provider = CoreContextProvider(project_root=root)
        assert provider._root == root

    def test_should_discover_root_automatically(self) -> None:
        """Validate that root is discovered via pyproject.toml."""
        provider = CoreContextProvider()
        assert (provider._root / "pyproject.toml").exists()

    def test_should_return_empty_dict_if_no_pyproject(self, tmp_path: Path) -> None:
        """Validate graceful fallback when no pyproject.toml is found.

        When running inside a container (or any path without pyproject.toml),
        _load_pyproject returns an empty dict instead of raising.
        """
        provider = CoreContextProvider(project_root=tmp_path)
        result = provider._load_pyproject()
        assert result == {}


class TestCoreContextProviderStack:
    """Tests for the get_stack method."""

    def test_should_return_project_name(self, provider: CoreContextProvider) -> None:
        """Validate that the stack includes the project name."""
        stack = provider.get_stack()
        assert stack["project"] == "atlas-mcp"

    def test_should_return_version(self, provider: CoreContextProvider) -> None:
        """Validate that the stack includes the project version."""
        stack = provider.get_stack()
        assert "version" in stack
        assert isinstance(stack["version"], str)

    def test_should_return_python_language(self, provider: CoreContextProvider) -> None:
        """Validate that language info is present."""
        stack = provider.get_stack()
        assert stack["language"]["name"] == "Python"
        assert "3.12" in stack["language"]["version"]

    def test_should_return_runtime(self, provider: CoreContextProvider) -> None:
        """Validate runtime is Asyncio."""
        stack = provider.get_stack()
        assert stack["runtime"] == "Asyncio"

    def test_should_return_dependencies(self, provider: CoreContextProvider) -> None:
        """Validate that dependencies list is populated."""
        stack = provider.get_stack()
        assert isinstance(stack["dependencies"], list)
        assert len(stack["dependencies"]) > 0
        dep_str = " ".join(stack["dependencies"])
        assert "mcp" in dep_str

    def test_should_return_dev_dependencies(self, provider: CoreContextProvider) -> None:
        """Validate that dev dependencies list is populated."""
        stack = provider.get_stack()
        assert isinstance(stack["dev_dependencies"], list)
        assert len(stack["dev_dependencies"]) > 0

    def test_should_return_linting_config(self, provider: CoreContextProvider) -> None:
        """Validate that linting configuration is included."""
        stack = provider.get_stack()
        assert stack["linting"]["tool"] == "Ruff"
        assert stack["linting"]["line_length"] == 100

    def test_should_return_ci(self, provider: CoreContextProvider) -> None:
        """Validate CI field."""
        stack = provider.get_stack()
        assert stack["ci"] == "GitHub Actions"

    def test_should_cache_pyproject(self, provider: CoreContextProvider) -> None:
        """Validate that pyproject.toml is only loaded once."""
        provider.get_stack()
        first_ref = provider._pyproject
        provider.get_stack()
        assert provider._pyproject is first_ref


class TestCoreContextProviderConventions:
    """Tests for the get_conventions method."""

    def test_should_return_style_section(self, provider: CoreContextProvider) -> None:
        """Validate that style conventions are present."""
        conventions = provider.get_conventions()
        assert "style" in conventions
        assert conventions["style"]["line_length"] == 100
        assert conventions["style"]["quote_style"] == "double"

    def test_should_return_docstring_convention(self, provider: CoreContextProvider) -> None:
        """Validate docstring convention is google."""
        conventions = provider.get_conventions()
        assert conventions["docstrings"]["convention"] == "google"

    def test_should_return_import_order(self, provider: CoreContextProvider) -> None:
        """Validate import ordering rules."""
        conventions = provider.get_conventions()
        assert "imports" in conventions
        assert "atlas_mcp" in conventions["imports"]["known_first_party"]

    def test_should_return_naming_conventions(self, provider: CoreContextProvider) -> None:
        """Validate naming convention rules."""
        conventions = provider.get_conventions()
        assert conventions["naming"]["classes"] == "PascalCase"
        assert conventions["naming"]["functions"] == "snake_case"

    def test_should_return_testing_config(self, provider: CoreContextProvider) -> None:
        """Validate testing configuration."""
        conventions = provider.get_conventions()
        assert conventions["testing"]["framework"] == "pytest"
        assert conventions["testing"]["pattern"] == "Arrange → Act → Assert"


class TestCoreContextProviderStructure:
    """Tests for the get_structure method."""

    def test_should_return_project_root(self, provider: CoreContextProvider) -> None:
        """Validate that project root path is included."""
        structure = provider.get_structure()
        assert "project_root" in structure
        assert str(_PROJECT_ROOT) in structure["project_root"]

    def test_should_return_tree(self, provider: CoreContextProvider) -> None:
        """Validate that tree is a dict with children."""
        structure = provider.get_structure()
        assert "tree" in structure
        tree = structure["tree"]
        assert tree["type"] == "directory"
        assert isinstance(tree["children"], list)

    def test_should_include_src_directory(self, provider: CoreContextProvider) -> None:
        """Validate that src/ appears in the tree."""
        structure = provider.get_structure()
        children_names = [c["name"] for c in structure["tree"]["children"]]
        assert "src" in children_names

    def test_should_include_tests_directory(self, provider: CoreContextProvider) -> None:
        """Validate that tests/ appears in the tree."""
        structure = provider.get_structure()
        children_names = [c["name"] for c in structure["tree"]["children"]]
        assert "tests" in children_names

    def test_should_exclude_pycache(self, provider: CoreContextProvider) -> None:
        """Validate that __pycache__ is excluded from tree."""
        structure = provider.get_structure()

        def _find_names(node: dict) -> list[str]:  # type: ignore[type-arg]
            names = [node.get("name", "")]
            for child in node.get("children", []):
                names.extend(_find_names(child))
            return names

        all_names = _find_names(structure["tree"])
        assert "__pycache__" not in all_names

    def test_should_exclude_git_directory(self, provider: CoreContextProvider) -> None:
        """Validate that .git is excluded from tree."""
        structure = provider.get_structure()

        def _find_names(node: dict) -> list[str]:  # type: ignore[type-arg]
            names = [node.get("name", "")]
            for child in node.get("children", []):
                names.extend(_find_names(child))
            return names

        all_names = _find_names(structure["tree"])
        assert ".git" not in all_names

    def test_should_return_key_files(self, provider: CoreContextProvider) -> None:
        """Validate that key files are listed."""
        structure = provider.get_structure()
        assert "key_files" in structure
        assert "pyproject.toml" in structure["key_files"]
        assert "README.md" in structure["key_files"]

    def test_should_handle_missing_ruff_toml(self, tmp_path: Path) -> None:
        """Validate that missing ruff.toml returns empty config."""
        # Create a minimal pyproject.toml
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text('[project]\nname = "test"\nversion = "0.1.0"\n')

        provider = CoreContextProvider(project_root=tmp_path)
        stack = provider.get_stack()
        # Should still work with defaults
        assert stack["linting"]["line_length"] == 100
