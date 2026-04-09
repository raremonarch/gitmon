"""SSH key management utilities for gitmon."""

import logging
import os
import re
import subprocess
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def is_ssh_agent_running() -> bool:
    """Check if ssh-agent is available via SSH_AUTH_SOCK."""
    auth_sock = os.environ.get("SSH_AUTH_SOCK")
    return bool(auth_sock and Path(auth_sock).exists())


def _get_key_fingerprint(key_path: Path) -> Optional[str]:
    """Get the fingerprint of an SSH key file."""
    try:
        result = subprocess.run(
            ["ssh-keygen", "-lf", str(key_path)],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            parts = result.stdout.split()
            if len(parts) >= 2:
                return parts[1]
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def is_key_loaded(key_path: Path) -> bool:
    """Check if a specific key is currently loaded in ssh-agent by fingerprint."""
    fingerprint = _get_key_fingerprint(key_path)
    if not fingerprint:
        return False
    try:
        result = subprocess.run(
            ["ssh-add", "-l"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return fingerprint in result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False


def get_identity_file_for_host(hostname: str) -> Optional[Path]:
    """Get the effective SSH identity file for a hostname using 'ssh -G'.

    Works with or without ~/.ssh/config — SSH returns the default identity
    file path even when there is no explicit config entry for the host.
    Returns the first identity file that exists on disk, or None.
    """
    try:
        result = subprocess.run(
            ["ssh", "-G", hostname],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if line.startswith("identityfile "):
                    path_str = line[13:].strip()
                    path = Path(path_str.replace("~", str(Path.home())))
                    if path.exists():
                        return path
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass
    return None


def extract_ssh_host(remote_url: str) -> Optional[str]:
    """Extract the SSH hostname from a git remote URL.

    Handles git@host:path and ssh://[user@]host/path formats.
    Returns None for HTTPS or local URLs.
    """
    if remote_url.startswith("git@"):
        m = re.match(r"git@([^:]+):", remote_url)
        if m:
            return m.group(1)
    if remote_url.startswith("ssh://"):
        m = re.match(r"ssh://(?:[^@]+@)?([^/:]+)", remote_url)
        if m:
            return m.group(1)
    return None


def get_ssh_hosts_for_repos(repo_paths: list[Path]) -> set[str]:
    """Collect unique SSH hostnames from origin remote URLs of the given repos."""
    hosts: set[str] = set()
    for repo_path in repo_paths:
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                host = extract_ssh_host(result.stdout.strip())
                if host:
                    hosts.add(host)
        except (subprocess.TimeoutExpired, OSError):
            pass
    return hosts


def get_keys_needing_load(hosts: set[str]) -> list[tuple[str, Path]]:
    """Return (hostname, key_path) pairs for SSH keys that are not yet in the agent.

    Deduplicates by key path so the same key file is only returned once even if
    it covers multiple hosts.
    """
    needing_load: list[tuple[str, Path]] = []
    seen_keys: set[Path] = set()

    for host in sorted(hosts):
        key_path = get_identity_file_for_host(host)
        if key_path is None or key_path in seen_keys:
            continue
        seen_keys.add(key_path)
        if not is_key_loaded(key_path):
            needing_load.append((host, key_path))

    return needing_load


def ssh_add_keys(key_paths: list[Path]) -> dict[Path, bool]:
    """Run ssh-add for each key. Must be called with terminal access (TUI suspended).

    Returns a mapping of key_path -> success.
    """
    results: dict[Path, bool] = {}
    for key_path in key_paths:
        try:
            result = subprocess.run(["ssh-add", str(key_path)], timeout=60)
            results[key_path] = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as e:
            logger.warning(f"ssh-add failed for {key_path}: {e}")
            results[key_path] = False
    return results
