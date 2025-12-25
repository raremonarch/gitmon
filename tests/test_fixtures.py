"""Test that fixtures are working correctly."""

from pathlib import Path

from gitmon.config import Config
from gitmon.scanner import GitCommandRunner


def test_tmp_git_repo_fixture(tmp_git_repo: Path) -> None:
    """Test that tmp_git_repo fixture creates a valid git repository."""
    assert tmp_git_repo.exists()
    assert (tmp_git_repo / ".git").exists()
    assert (tmp_git_repo / "README.md").exists()


def test_mock_config_fixture(mock_config: Config) -> None:
    """Test that mock_config fixture creates a valid Config object."""
    assert isinstance(mock_config, Config)
    assert mock_config.refresh_interval == 1
    assert mock_config.max_depth == 2
    assert not mock_config.auto_fetch_enabled


def test_mock_git_runner_fixture(mock_git_runner: GitCommandRunner) -> None:
    """Test that mock_git_runner fixture works."""
    result = mock_git_runner.run(Path("/tmp"), ["git", "branch", "--show-current"])
    assert result.returncode == 0
    assert "main" in result.stdout
