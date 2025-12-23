"""Textual TUI interface for gitmon."""

from textual.app import App, ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Header, Footer, DataTable, Static
from textual.binding import Binding
from textual.events import MouseMove
from textual.message import Message
from rich.text import Text

from .config import Config
from .scanner import GitScanner, RepoInfo


class HoverableDataTable(DataTable):
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

    def on_leave(self, _event) -> None:
        """Handle mouse leaving the table."""
        self.post_message(self.RowHovered(row_index=-1))


class GitMonApp(App):
    """Git Repository Monitor TUI Application."""

    CSS = """
    Screen {
        background: $surface;
    }

    Header {
        background: $panel;
    }

    Footer {
        background: $panel;
    }

    #info-bar {
        height: 3;
        background: $panel;
        padding: 1;
        color: $text;
    }

    #hover-info {
        height: 3;
        background: $panel;
        padding: 0 1;
        margin: 0;
        color: white;
        display: none;
    }

    DataTable {
        height: 1fr;
    }

    .status-clean {
        color: $success;
    }

    .status-changes {
        color: $warning;
    }

    .status-error {
        color: $error;
    }

    .branch {
        color: $accent;
    }

    .owner {
        color: $secondary;
    }
    """

    BINDINGS = [
        Binding("r", "refresh", "Refresh", priority=True),
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

    def compose(self) -> ComposeResult:
        """Compose the application layout."""
        yield Header()
        yield Static(id="info-bar")
        yield HoverableDataTable()
        yield Static(id="hover-info")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the application when mounted."""
        self.title = "GitMon - Git Repository Monitor"
        self.sub_title = f"Watching {len(self.config.watch_directories)} directories"

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

    def action_refresh(self) -> None:
        """Refresh repository information."""
        table = self.query_one(DataTable)
        info_bar = self.query_one("#info-bar", Static)

        # Update info bar
        info_bar.update(
            f"Scanning repositories... (Last refresh: {self._get_timestamp()})"
        )

        # Scan repositories
        self.repos = self.scanner.scan_all()

        # Sort repositories by owner then name
        sorted_repos = sorted(
            self.repos, key=lambda r: (r.remote_owner.lower(), r.name.lower())
        )

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

            # Format tracking info
            if repo.ahead > 0 or repo.behind > 0:
                parts = []
                if repo.ahead > 0:
                    parts.append(f"↑ {repo.ahead}")
                if repo.behind > 0:
                    parts.append(f"↓ {repo.behind}")
                tracking = "  ".join(parts)
            else:
                tracking = ""

            # Format repository with owner
            # Escape square brackets to prevent Rich markup interpretation
            repo_display = f"\\[{repo.remote_owner}] {repo.name}"

            # Add row
            table.add_row(
                repo_display, Text(repo.current_branch, style="cyan"), status, tracking
            )

        # Update info bar with stats
        clean_count = sum(1 for r in self.repos if r.status == "clean")
        stashed_count = sum(1 for r in self.repos if r.status == "stashed")
        changes_count = sum(1 for r in self.repos if r.status == "changes")
        error_count = sum(1 for r in self.repos if r.status == "error")

        stats = f"Repositories: {len(self.repos)} | "
        stats += f"Clean: {clean_count}"
        if stashed_count > 0:
            stats += f" | Stashed: {stashed_count}"
        if changes_count > 0:
            stats += f" | Changes: {changes_count}"
        if error_count > 0:
            stats += f" | Errors: {error_count}"

        info_bar.update(stats)

    def _show_repo_info(self, row_index: int) -> None:
        """Show repository info for the given row index."""
        hover_info = self.query_one("#hover-info", Static)

        if row_index < 0 or row_index >= len(self.repos):
            hover_info.styles.display = "none"
            return

        # Get the sorted repository list (same order as displayed)
        sorted_repos = sorted(
            self.repos, key=lambda r: (r.remote_owner.lower(), r.name.lower())
        )
        repo = sorted_repos[row_index]

        # Format hover information
        commit_line = (
            f"Last Remote Commit: {repo.remote_commit_message}"
            if repo.remote_commit_message
            else "Last Remote Commit: (no commit info)"
        )
        path_line = f"Path: {repo.path}"
        hover_text = f"{commit_line}\n{path_line}"

        # Update the widget
        hover_info.update(hover_text)
        hover_info.styles.display = "block"

    def on_hoverable_data_table_row_hovered(
        self, message: HoverableDataTable.RowHovered
    ) -> None:
        """Handle row hover events from the HoverableDataTable."""
        hover_info = self.query_one("#hover-info", Static)

        if message.row_index < 0 or message.row_index >= len(self.repos):
            hover_info.styles.display = "none"
        else:
            self._show_repo_info(message.row_index)

    def action_open_config(self) -> None:
        """Open configuration file in default editor."""
        import subprocess
        import os

        editor = os.environ.get("EDITOR", "vim")

        # Suspend the app to properly restore terminal for the editor
        with self.suspend():
            subprocess.run([editor, str(self.config.config_path)])

    def _get_timestamp(self) -> str:
        """Get current timestamp string."""
        from datetime import datetime

        return datetime.now().strftime("%H:%M:%S")


def run_app(config: Config = None) -> None:
    """Run the gitmon TUI application.

    Args:
        config: Optional configuration object. If None, default config is loaded.
    """
    if config is None:
        config = Config()

    app = GitMonApp(config)
    app.run()
