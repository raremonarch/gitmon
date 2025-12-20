"""Git repository scanner and information extractor."""

import subprocess
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass


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
    error: Optional[str] = None


class GitScanner:
    """Scanner for finding and analyzing git repositories."""

    def __init__(self, watch_directories: List[Path], max_depth: int = 3):
        """Initialize scanner with directories to watch.

        Args:
            watch_directories: List of directories to scan for git repos
            max_depth: Maximum directory depth to search (default: 3)
        """
        self.watch_directories = watch_directories
        self.max_depth = max_depth

    def find_repositories(self) -> List[Path]:
        """Find all git repositories in watch directories.

        Recursively searches up to max_depth levels deep. When a git repository
        is found, stops descending into that directory.

        Returns:
            List of paths to git repositories
        """
        repos = []
        for directory in self.watch_directories:
            if not directory.exists():
                continue

            # Search recursively with early stopping at git repos
            self._search_directory(directory, repos, current_depth=0)

        return sorted(repos, key=lambda p: p.name.lower())

    def _search_directory(self, directory: Path, repos: List[Path], current_depth: int) -> None:
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
                if item.name.startswith('.'):
                    continue

                if item.is_dir():
                    self._search_directory(item, repos, current_depth + 1)
        except PermissionError:
            # Skip directories we can't access
            pass

    def get_repo_info(self, repo_path: Path) -> RepoInfo:
        """Get detailed information about a git repository.

        Args:
            repo_path: Path to the git repository

        Returns:
            RepoInfo object with repository details
        """
        name = repo_path.name

        try:
            # Get current branch
            branch_result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            current_branch = branch_result.stdout.strip() or "detached HEAD"

            # Get remote URL and extract owner
            remote_result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            remote_url = remote_result.stdout.strip()
            remote_owner = self._extract_owner(remote_url)

            # Check for changes
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=5
            )
            has_changes = bool(status_result.stdout.strip())
            status = "changes" if has_changes else "clean"

            # Get ahead/behind count
            ahead, behind = self._get_tracking_status(repo_path)

            return RepoInfo(
                name=name,
                path=repo_path,
                remote_owner=remote_owner,
                current_branch=current_branch,
                status=status,
                ahead=ahead,
                behind=behind
            )

        except subprocess.TimeoutExpired:
            return RepoInfo(
                name=name,
                path=repo_path,
                remote_owner="N/A",
                current_branch="N/A",
                status="error",
                error="Command timeout"
            )
        except Exception as e:
            return RepoInfo(
                name=name,
                path=repo_path,
                remote_owner="N/A",
                current_branch="N/A",
                status="error",
                error=str(e)
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

    def _get_tracking_status(self, repo_path: Path) -> tuple[int, int]:
        """Get ahead/behind count for current branch.

        Args:
            repo_path: Path to the git repository

        Returns:
            Tuple of (ahead_count, behind_count)
        """
        try:
            result = subprocess.run(
                ["git", "rev-list", "--left-right", "--count", "HEAD...@{upstream}"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=5
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

    def scan_all(self) -> List[RepoInfo]:
        """Scan all repositories and return their information.

        Returns:
            List of RepoInfo objects
        """
        repos = self.find_repositories()
        return [self.get_repo_info(repo) for repo in repos]
