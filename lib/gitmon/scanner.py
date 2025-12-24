"""Git repository scanner and information extractor."""

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol

logger = logging.getLogger(__name__)


class GitCommandRunner(Protocol):
    """Protocol for running git commands (allows for test mocking)."""

    def run(self, cwd: Path, args: list[str], timeout: int = 5) -> subprocess.CompletedProcess[str]:
        """Run a git command in the specified directory.

        Args:
            cwd: Working directory for the command
            args: Command arguments (including 'git')
            timeout: Timeout in seconds

        Returns:
            CompletedProcess with stdout/stderr as text

        Raises:
            subprocess.TimeoutExpired: If command times out
            subprocess.CalledProcessError: If command fails
        """
        ...


class SubprocessGitRunner:
    """Default git command runner using subprocess."""

    def run(self, cwd: Path, args: list[str], timeout: int = 5) -> subprocess.CompletedProcess[str]:
        """Run a git command using subprocess.

        Args:
            cwd: Working directory for the command
            args: Command arguments (including 'git')
            timeout: Timeout in seconds

        Returns:
            CompletedProcess with stdout/stderr as text
        """
        return subprocess.run(
            args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,  # We handle errors manually
        )


@dataclass
class RepoInfo:
    """Information about a git repository."""

    name: str
    path: Path
    remote_owner: str
    current_branch: str
    status: str  # "clean", "stashed", "changes", or "error"
    ahead: int = 0
    behind: int = 0
    stash_count: int = 0
    remote_commit_message: str = ""
    error: Optional[str] = None
    fetch_status: Optional[str] = None  # "success", "failed", or None if not fetched yet


class GitScanner:
    """Scanner for finding and analyzing git repositories."""

    def __init__(
        self,
        watch_directories: list[Path],
        max_depth: int = 3,
        runner: Optional[GitCommandRunner] = None,
    ):
        """Initialize scanner with directories to watch.

        Args:
            watch_directories: List of directories to scan for git repos
            max_depth: Maximum directory depth to search (default: 3)
            runner: Git command runner (defaults to SubprocessGitRunner)
        """
        self.watch_directories = watch_directories
        self.max_depth = max_depth
        self.runner = runner if runner is not None else SubprocessGitRunner()

    def find_repositories(self) -> list[Path]:
        """Find all git repositories in watch directories.

        Recursively searches up to max_depth levels deep. When a git repository
        is found, stops descending into that directory.

        Returns:
            List of paths to git repositories
        """
        repos: list[Path] = []
        for directory in self.watch_directories:
            if not directory.exists():
                continue

            # Search recursively with early stopping at git repos
            self._search_directory(directory, repos, current_depth=0)

        return sorted(repos, key=lambda p: p.name.lower())

    def _search_directory(self, directory: Path, repos: list[Path], current_depth: int) -> None:
        """Recursively search for git repositories with early stopping.

        Args:
            directory: Directory to search
            repos: List to append found repositories to
            current_depth: Current search depth
        """
        # Check if this directory is a git repo
        if (directory / ".git").exists():
            repos.append(directory)
            # Don't descend into git repositories
            return

        # Stop if we've reached max depth
        if current_depth >= self.max_depth:
            return

        # Search subdirectories
        try:
            for item in directory.iterdir():
                # Skip hidden directories (except .git which we already checked)
                if item.name.startswith("."):
                    continue

                if item.is_dir():
                    self._search_directory(item, repos, current_depth + 1)
        except PermissionError as e:
            # Skip directories we can't access
            logger.debug(f"Permission denied accessing directory {directory}: {e}")

    def get_repo_info(self, repo_path: Path) -> RepoInfo:
        """Get detailed information about a git repository.

        Args:
            repo_path: Path to the git repository

        Returns:
            RepoInfo object with repository details
        """
        try:
            # Get current branch
            branch_result = self.runner.run(
                repo_path, ["git", "branch", "--show-current"], timeout=5
            )
            current_branch = branch_result.stdout.strip() or "detached HEAD"

            # Get remote URL and extract owner and repo name
            remote_result = self.runner.run(
                repo_path, ["git", "remote", "get-url", "origin"], timeout=5
            )
            remote_url = remote_result.stdout.strip()
            remote_owner = self._extract_owner(remote_url)
            name = self._extract_repo_name(remote_url) or repo_path.name

            # Check for changes
            status_result = self.runner.run(repo_path, ["git", "status", "--porcelain"], timeout=5)
            has_changes = bool(status_result.stdout.strip())
            status = "changes" if has_changes else "clean"

            # Get ahead/behind count
            ahead, behind = self._get_tracking_status(repo_path)

            # Get remote commit message
            remote_commit_msg = self._get_remote_commit_message(repo_path)

            return RepoInfo(
                name=name,
                path=repo_path,
                remote_owner=remote_owner,
                current_branch=current_branch,
                status=status,
                ahead=ahead,
                behind=behind,
                remote_commit_message=remote_commit_msg,
            )

        except subprocess.TimeoutExpired as e:
            logger.warning(f"Git command timeout for {repo_path}: {e}")
            return RepoInfo(
                name=repo_path.name,
                path=repo_path,
                remote_owner="N/A",
                current_branch="N/A",
                status="error",
                error="Command timeout",
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed for {repo_path}: {e}")
            return RepoInfo(
                name=repo_path.name,
                path=repo_path,
                remote_owner="N/A",
                current_branch="N/A",
                status="error",
                error=f"Git command failed: {e}",
            )
        except (OSError, PermissionError) as e:
            logger.error(f"File system error accessing {repo_path}: {e}")
            return RepoInfo(
                name=repo_path.name,
                path=repo_path,
                remote_owner="N/A",
                current_branch="N/A",
                status="error",
                error=str(e),
            )

    def _extract_owner(self, remote_url: str) -> str:
        """Extract owner/organization from git remote URL.

        Args:
            remote_url: Git remote URL

        Returns:
            Owner/organization name or 'N/A'
        """
        if not remote_url:
            return "N/A"

        # Handle SSH URLs: git@github.com:owner/repo.git
        if remote_url.startswith("git@"):
            parts = remote_url.split(":")
            if len(parts) > 1:
                path_parts = parts[1].split("/")
                if path_parts:
                    return path_parts[0]

        # Handle HTTPS URLs: https://github.com/owner/repo.git
        if remote_url.startswith("http"):
            parts = remote_url.rstrip("/").split("/")
            if len(parts) >= 2:
                return parts[-2]

        # Handle local paths or other formats
        return remote_url.split("/")[0] if "/" in remote_url else "local"

    def _extract_repo_name(self, remote_url: str) -> str:
        """Extract repository name from git remote URL.

        Args:
            remote_url: Git remote URL

        Returns:
            Repository name or empty string if unavailable
        """
        if not remote_url:
            return ""

        # Handle SSH URLs: git@github.com:owner/repo.git
        if remote_url.startswith("git@"):
            parts = remote_url.split(":")
            if len(parts) > 1:
                path_parts = parts[1].split("/")
                if len(path_parts) >= 2:
                    # Remove .git extension if present
                    repo_name = path_parts[-1]
                    return repo_name.removesuffix(".git")

        # Handle HTTPS URLs: https://github.com/owner/repo.git
        if remote_url.startswith("http"):
            parts = remote_url.rstrip("/").split("/")
            if len(parts) >= 1:
                # Remove .git extension if present
                repo_name = parts[-1]
                return repo_name.removesuffix(".git")

        return ""

    def _get_remote_commit_message(self, repo_path: Path) -> str:
        """Get the most recent remote commit message.

        Args:
            repo_path: Path to the git repository

        Returns:
            Remote commit message or empty string if unavailable
        """
        try:
            result = self.runner.run(
                repo_path, ["git", "log", "origin/HEAD", "-1", "--pretty=format:%s"], timeout=5
            )

            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()

        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            pass

        return ""

    def _get_tracking_status(self, repo_path: Path) -> tuple[int, int]:
        """Get ahead/behind count for current branch.

        Args:
            repo_path: Path to the git repository

        Returns:
            Tuple of (ahead_count, behind_count)
        """
        try:
            result = self.runner.run(
                repo_path,
                ["git", "rev-list", "--left-right", "--count", "HEAD...@{upstream}"],
                timeout=5,
            )

            if result.returncode == 0 and result.stdout.strip():
                parts = result.stdout.strip().split()
                if len(parts) == 2:
                    ahead = int(parts[0])
                    behind = int(parts[1])
                    return ahead, behind

        except (subprocess.TimeoutExpired, ValueError, subprocess.CalledProcessError):
            pass

        return 0, 0

    def fetch_repo(self, repo_path: Path) -> tuple[bool, str]:
        """Fetch updates for a single repository.

        Args:
            repo_path: Path to the git repository

        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            logger.debug(f"Fetching repository: {repo_path}")
            result = self.runner.run(repo_path, ["git", "fetch", "--all"], timeout=30)

            if result.returncode == 0:
                logger.debug(f"Successfully fetched {repo_path}")
                return True, "Success"

            error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
            logger.warning(f"Failed to fetch {repo_path}: {error_msg}")
            return False, error_msg

        except subprocess.TimeoutExpired:
            logger.warning(f"Fetch timeout for {repo_path}")
            return False, "Timeout (30s)"
        except (OSError, PermissionError) as e:
            logger.error(f"File system error fetching {repo_path}: {e}")
            return False, str(e)
        except subprocess.CalledProcessError as e:
            logger.error(f"Git fetch command failed for {repo_path}: {e}")
            return False, str(e)

    def fetch_all(self) -> dict[Path, tuple[bool, str]]:
        """Fetch updates for all repositories.

        Returns:
            Dictionary mapping repo paths to (success, message) tuples
        """
        repos = self.find_repositories()
        results = {}
        for repo in repos:
            results[repo] = self.fetch_repo(repo)
        return results

    def scan_all(self) -> list[RepoInfo]:
        """Scan all repositories and return their information.

        Returns:
            List of RepoInfo objects
        """
        repos = self.find_repositories()
        return [self.get_repo_info(repo) for repo in repos]
