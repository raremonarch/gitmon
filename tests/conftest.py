"""Pytest configuration and shared fixtures for gitmon tests."""

import subprocess
import tempfile
from pathlib import Path
from typing import Any, Optional

import pytest

from gitmon.config import Config
from gitmon.scanner import GitCommandRunner


@pytest.fixture
def tmp_git_repo(tmp_path: Path) -> Path:
    """Create a temporary git repository for testing.

    Args:
        tmp_path: Pytest's temporary directory fixture

    Returns:
        Path to the temporary git repository
    """
    repo_path = tmp_path / "test_repo"
    repo_path.mkdir()

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    # Create an initial commit
    test_file = repo_path / "README.md"
    test_file.write_text("# Test Repository\n")
    subprocess.run(["git", "add", "README.md"], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )

    return repo_path


@pytest.fixture
def tmp_git_repo_with_remote(tmp_git_repo: Path, tmp_path: Path) -> Path:
    """Create a git repository with a remote configured.

    Args:
        tmp_git_repo: Basic git repo fixture
        tmp_path: Pytest's temporary directory fixture

    Returns:
        Path to the git repository with remote
    """
    # Create a bare remote repo
    remote_path = tmp_path / "remote_repo.git"
    subprocess.run(
        ["git", "init", "--bare", str(remote_path)], check=True, capture_output=True
    )

    # Add remote to test repo
    subprocess.run(
        ["git", "remote", "add", "origin", f"git@github.com:testuser/testrepo.git"],
        cwd=tmp_git_repo,
        check=True,
        capture_output=True,
    )

    return tmp_git_repo


@pytest.fixture
def mock_config(tmp_path: Path) -> Config:
    """Create a mock Config object for testing.

    Args:
        tmp_path: Pytest's temporary directory fixture

    Returns:
        Config object with test settings
    """
    config_path = tmp_path / "test_config.json"
    config = Config(config_path)
    config.watch_directories = [str(tmp_path)]
    config.refresh_interval = 1
    config.max_depth = 2
    config.auto_fetch_enabled = False
    config.auto_fetch_interval = 60
    return config


class MockGitRunner:
    """Mock git command runner for testing."""

    def __init__(self, responses: Optional[dict[str, tuple[int, str, str]]] = None):
        """Initialize mock runner with predefined responses.

        Args:
            responses: Dictionary mapping command patterns to (returncode, stdout, stderr) tuples
        """
        self.responses = responses or {}
        self.calls: list[tuple[Path, list[str]]] = []

    def run(
        self, cwd: Path, args: list[str], timeout: int = 5
    ) -> subprocess.CompletedProcess[str]:
        """Mock git command execution.

        Args:
            cwd: Working directory
            args: Command arguments
            timeout: Timeout (ignored in mock)

        Returns:
            Mocked CompletedProcess
        """
        # Record the call
        self.calls.append((cwd, args))

        # Find matching response
        command_key = " ".join(args)
        for pattern, (returncode, stdout, stderr) in self.responses.items():
            if pattern in command_key:
                return subprocess.CompletedProcess(
                    args=args, returncode=returncode, stdout=stdout, stderr=stderr
                )

        # Default response for unmatched commands
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")


@pytest.fixture
def mock_git_runner() -> MockGitRunner:
    """Create a mock git runner with default responses.

    Returns:
        MockGitRunner with common git command responses
    """
    responses = {
        "branch --show-current": (0, "main\n", ""),
        "remote get-url": (0, "git@github.com:testuser/testrepo.git\n", ""),
        "status --porcelain": (0, "", ""),  # Clean repo
        "rev-list --left-right --count": (0, "0\t0\n", ""),  # No divergence
        "log origin/HEAD": (0, "Test commit message\n", ""),
        "fetch --all": (0, "", ""),
    }
    return MockGitRunner(responses)


@pytest.fixture
def mock_git_runner_with_changes() -> MockGitRunner:
    """Create a mock git runner simulating a repo with changes.

    Returns:
        MockGitRunner configured to simulate uncommitted changes
    """
    responses = {
        "branch --show-current": (0, "feature-branch\n", ""),
        "remote get-url": (0, "git@github.com:testuser/testrepo.git\n", ""),
        "status --porcelain": (0, " M modified_file.py\n", ""),  # Modified file
        "rev-list --left-right --count": (0, "2\t3\n", ""),  # 2 ahead, 3 behind
        "log origin/HEAD": (0, "Latest remote commit\n", ""),
        "fetch --all": (0, "", ""),
    }
    return MockGitRunner(responses)
