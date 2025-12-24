"""Textual TUI interface for gitmon."""

from pathlib import Path
from typing import Any, Optional

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.events import MouseMove
from textual.message import Message
from textual.widgets import DataTable, Footer, Header, Static
from textual.worker import Worker, WorkerState

from .config import Config
from .scanner import GitScanner, RepoInfo


class HoverableDataTable(DataTable[Any]):
    """DataTable with mouse hover support."""

    class RowHovered(Message):
        """Message posted when mouse hovers over a row."""

        def __init__(self, row_index: int):
            super().__init__()
            self.row_index = row_index

    def on_mouse_move(self, event: MouseMove) -> None:
        """Handle mouse movement within the table."""
        # Post a custom message to parent app with row information
        try:
            # Calculate row from mouse position
            relative_y = event.y - 1  # Subtract header row
            if relative_y >= 0:
                self.post_message(self.RowHovered(row_index=relative_y))
            else:
                self.post_message(self.RowHovered(row_index=-1))
        except Exception:
            self.post_message(self.RowHovered(row_index=-1))

    def on_leave(self, _event: Any) -> None:
        """Handle mouse leaving the table."""
        self.post_message(self.RowHovered(row_index=-1))


class GitMonApp(App[None]):
    """Git Repository Monitor TUI Application."""

    CSS_PATH = Path(__file__).parent / "gitmon.tcss"

    BINDINGS = [
        Binding("r", "refresh", "Refresh", priority=True),
        Binding("f", "fetch", "Fetch All", priority=True),
        Binding("a", "toggle_auto_fetch", "Auto-Fetch", priority=True),
        Binding("q", "quit", "Quit", priority=True),
        Binding("c", "open_config", "Config", priority=True),
    ]

    def __init__(self, config: Config):
        """Initialize the application.

        Args:
            config: Configuration object
        """
        super().__init__()
        self.config = config
        self.scanner = GitScanner(config.get_expanded_directories(), config.max_depth)
        self.repos: list[RepoInfo] = []
        self._fetch_worker: Optional[Worker[dict[Path, tuple[bool, str]]]] = None
        self._auto_fetch_timer = None
        self._fetch_results: dict[Path, tuple[bool, str]] = {}  # Track fetch status by repo path

    def compose(self) -> ComposeResult:
        """Compose the application layout."""
        yield Header()
        yield Static(id="info-bar")
        yield HoverableDataTable()
        yield Static(id="fetch-status")
        yield Static(id="hover-info")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the application when mounted."""
        self.title = "GitMon - Git Repository Monitor"

        # Setup the data table
        table = self.query_one(DataTable)
        table.cursor_type = "none"
        table.zebra_stripes = True
        table.can_focus = False  # Disable focus to prevent keyboard interaction

        # Add columns
        table.add_column("Repository", width=50)
        table.add_column("Branch", width=20)
        table.add_column("Status", width=15)
        table.add_column("Tracking", width=15)

        # Initial scan
        self.action_refresh()

        # Set up auto-refresh timer
        self.set_interval(self.config.refresh_interval, self.action_refresh)

        # Set up auto-fetch timer and trigger initial fetch if enabled
        if self.config.auto_fetch_enabled:
            self._auto_fetch_timer = self.set_interval(
                self.config.auto_fetch_interval, self.action_fetch
            )
            # Trigger an immediate fetch on startup to populate status indicators
            self.action_fetch()

    def _get_sorted_repos(self) -> list[RepoInfo]:
        """Get repositories sorted by owner then name.

        Returns:
            List of RepoInfo sorted alphabetically by owner (case-insensitive), then by name.
        """
        return sorted(self.repos, key=lambda r: (r.remote_owner.lower(), r.name.lower()))

    def action_refresh(self) -> None:
        """Refresh repository information."""
        table = self.query_one(DataTable)
        info_bar = self.query_one("#info-bar", Static)

        # Update info bar
        info_bar.update(f"Scanning repositories... (Last refresh: {self._get_timestamp()})")

        # Scan repositories
        self.repos = self.scanner.scan_all()

        # Apply fetch status from previous fetch results
        for repo in self.repos:
            if repo.path in self._fetch_results:
                success, _ = self._fetch_results[repo.path]
                repo.fetch_status = "success" if success else "failed"

        # Sort repositories by owner then name
        sorted_repos = self._get_sorted_repos()

        # Clear and repopulate table
        table.clear()
        for repo in sorted_repos:
            # Format status with color
            if repo.status == "clean":
                status = Text("○ clean", style="green")
            elif repo.status == "stashed":
                status = Text("◐ stashed", style="blue")
            elif repo.status == "changes":
                status = Text("● changes", style="yellow")
            else:
                status = Text("✗ error", style="red")

            # Format tracking info with fetch status first, then branch divergence
            tracking_parts = []

            # Add fetch status indicator first if auto-fetch is enabled
            if self.config.auto_fetch_enabled and repo.fetch_status:
                if repo.fetch_status == "success":
                    tracking_parts.append(Text("✓", style="green"))
                else:  # failed
                    tracking_parts.append(Text("✗", style="red"))

            # Add branch divergence indicators
            if repo.ahead > 0 or repo.behind > 0:
                if repo.ahead > 0:
                    tracking_parts.append(Text(f"↑ {repo.ahead}"))
                if repo.behind > 0:
                    tracking_parts.append(Text(f"↓ {repo.behind}"))

            # Combine all parts with spacing
            if tracking_parts:
                tracking = Text("  ").join(tracking_parts)
            else:
                tracking = ""

            # Format repository with owner
            # Escape square brackets to prevent Rich markup interpretation
            repo_display = f"\\[{repo.remote_owner}] {repo.name}"

            # Add row
            table.add_row(repo_display, Text(repo.current_branch, style="cyan"), status, tracking)

        # Update info bar with stats
        clean_count = sum(1 for r in self.repos if r.status == "clean")
        stashed_count = sum(1 for r in self.repos if r.status == "stashed")
        changes_count = sum(1 for r in self.repos if r.status == "changes")
        error_count = sum(1 for r in self.repos if r.status == "error")

        stats = f"Directories: {len(self.config.watch_directories)} | "
        stats += f"Repositories: {len(self.repos)} | "
        stats += f"Clean: {clean_count}"
        if stashed_count > 0:
            stats += f" | Stashed: {stashed_count}"
        if changes_count > 0:
            stats += f" | Changes: {changes_count}"
        if error_count > 0:
            stats += f" | Errors: {error_count}"

        # Add auto-fetch status
        if self.config.auto_fetch_enabled:
            stats += f" | Auto-fetch: ON ({self.config.auto_fetch_interval}s)"
        else:
            stats += " | Auto-fetch: OFF"

        info_bar.update(stats)

    def action_fetch(self) -> None:
        """Fetch updates for all repositories in background."""
        # Check if a fetch is already running
        if self._fetch_worker and self._fetch_worker.state == WorkerState.RUNNING:
            fetch_status = self.query_one("#fetch-status", Static)
            fetch_status.update("Fetch already in progress...")
            fetch_status.styles.display = "block"
            return

        # Show fetch status widget and start the background fetch worker
        fetch_status = self.query_one("#fetch-status", Static)
        fetch_status.styles.display = "block"
        self._fetch_worker = self.run_worker(self._fetch_all_repos, thread=True)

    def _fetch_all_repos(self) -> dict[Path, tuple[bool, str]]:
        """Background worker to fetch all repositories with progress updates."""
        fetch_status = self.query_one("#fetch-status", Static)
        repo_paths = self.scanner.find_repositories()
        total = len(repo_paths)
        results = {}

        for idx, repo_path in enumerate(repo_paths, 1):
            # Update progress in UI
            repo_name = repo_path.name
            self.call_from_thread(
                fetch_status.update,
                f"[{self._get_timestamp()}] Fetching {idx}/{total}: {repo_name}...",
            )

            # Fetch the repo
            success, message = self.scanner.fetch_repo(repo_path)
            results[repo_path] = (success, message)

        # Count results and collect failures
        success_count = sum(1 for success, _ in results.values() if success)
        fail_count = total - success_count
        failures = [(path, msg) for path, (success, msg) in results.items() if not success]

        # Update final message
        if fail_count == 0:
            final_message = (
                f"[{self._get_timestamp()}] Fetch complete: {success_count} repos updated"
            )
        else:
            # Show first few failures with error messages
            error_details = "\n".join([f"  - {path.name}: {msg}" for path, msg in failures[:3]])
            if fail_count > 3:
                error_details += f"\n  ... and {fail_count - 3} more"
            final_message = f"[{self._get_timestamp()}] Fetch complete: {success_count} succeeded, {fail_count} failed\n{error_details}"

        self.call_from_thread(fetch_status.update, final_message)

        # Store fetch results for display in tracking column (keyed by repo path)
        self._fetch_results = {path: (success, msg) for path, (success, msg) in results.items()}

        # Trigger refresh from main thread
        self.call_from_thread(self.action_refresh)

        # Hide fetch status after 5 seconds
        def hide_fetch_status() -> None:
            fetch_status.styles.display = "none"

        self.call_from_thread(self.set_timer, 5, hide_fetch_status)

        return results

    def action_toggle_auto_fetch(self) -> None:
        """Toggle automatic fetch on/off and save config."""
        # Toggle the setting
        self.config.auto_fetch_enabled = not self.config.auto_fetch_enabled

        # Save updated config
        try:
            self.config.save()
        except Exception as e:
            fetch_status = self.query_one("#fetch-status", Static)
            fetch_status.update(f"Error saving config: {e}")
            fetch_status.styles.display = "block"
            self.set_timer(3, lambda: setattr(fetch_status.styles, "display", "none"))
            return

        # Update timer and trigger fetch if enabling
        if self.config.auto_fetch_enabled:
            # Start the auto-fetch timer
            if self._auto_fetch_timer:
                self._auto_fetch_timer.stop()
            self._auto_fetch_timer = self.set_interval(
                self.config.auto_fetch_interval, self.action_fetch
            )
            status_msg = f"Auto-fetch enabled (every {self.config.auto_fetch_interval}s)"

            # Refresh display first to show new status
            self.action_refresh()

            # Trigger an immediate fetch to populate status indicators
            self.action_fetch()
        else:
            # Stop the auto-fetch timer
            if self._auto_fetch_timer:
                self._auto_fetch_timer.stop()
                self._auto_fetch_timer = None
            status_msg = "Auto-fetch disabled"

            # Refresh display to update info bar
            self.action_refresh()

            # Show notification
            fetch_status = self.query_one("#fetch-status", Static)
            fetch_status.update(f"[{self._get_timestamp()}] {status_msg}")
            fetch_status.styles.display = "block"

            # Hide notification after 3 seconds
            def hide_notification() -> None:
                fetch_status.styles.display = "none"

            self.set_timer(3, hide_notification)

    def _show_repo_info(self, row_index: int) -> None:
        """Show repository info for the given row index."""
        hover_info = self.query_one("#hover-info", Static)

        if row_index < 0 or row_index >= len(self.repos):
            hover_info.styles.display = "none"
            return

        # Get the sorted repository list (same order as displayed)
        sorted_repos = self._get_sorted_repos()
        repo = sorted_repos[row_index]

        # Format hover information
        lines = []

        # Add remote commit info
        commit_line = (
            f"Last Remote Commit: {repo.remote_commit_message}"
            if repo.remote_commit_message
            else "Last Remote Commit: (no commit info)"
        )
        lines.append(commit_line)

        # Add path
        lines.append(f"Path: {repo.path}")

        # Add fetch status information if auto-fetch is enabled and we have results
        if self.config.auto_fetch_enabled and repo.path in self._fetch_results:
            success, error_msg = self._fetch_results[repo.path]
            if success:
                lines.append("Fetch Status: ✓ Success")
            else:
                lines.append(f"Fetch Status: ✗ Failed - {error_msg}")

        hover_text = "\n".join(lines)

        # Update the widget
        hover_info.update(hover_text)
        hover_info.styles.display = "block"

    def on_hoverable_data_table_row_hovered(self, message: HoverableDataTable.RowHovered) -> None:
        """Handle row hover events from the HoverableDataTable."""
        hover_info = self.query_one("#hover-info", Static)

        if message.row_index < 0 or message.row_index >= len(self.repos):
            hover_info.styles.display = "none"
        else:
            self._show_repo_info(message.row_index)

    def action_open_config(self) -> None:
        """Open configuration file in default editor."""
        import os
        import subprocess

        editor = os.environ.get("EDITOR", "vim")

        # Suspend the app to properly restore terminal for the editor
        with self.suspend():
            subprocess.run([editor, str(self.config.config_path)])

    def _get_timestamp(self) -> str:
        """Get current timestamp string."""
        from datetime import datetime

        return datetime.now().strftime("%H:%M:%S")


def run_app(config: Optional[Config] = None) -> None:
    """Run the gitmon TUI application.

    Args:
        config: Optional configuration object. If None, default config is loaded.
    """
    if config is None:
        config = Config()

    app = GitMonApp(config)
    app.run()
