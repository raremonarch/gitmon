# Claude Code Context for GitMon

## Repository Overview

GitMon is a Python TUI (Text User Interface) application built with [Textual](https://textual.textualize.io/) that monitors git repositories. It scans configured directories for git repos and displays their status, branches, and tracking information in a terminal-based table.

**Version:** 0.1.0
**Main Language:** Python 3
**TUI Framework:** Textual (>=0.40.0)

## Project Structure

```plaintext
/home/david/code/gitmon/
├── bin/
│   └── gitmon              # Bash wrapper script (auto-creates venv, installs deps)
├── lib/gitmon/
│   ├── __init__.py         # Package initialization
│   ├── __main__.py         # Entry point (CLI arg parsing, app launch)
│   ├── config.py           # Configuration loading/management
│   ├── scanner.py          # Git repository scanning and analysis
│   └── tui.py              # Textual TUI interface *** KEY FILE ***
├── pyproject.toml          # Project metadata
├── requirements.txt        # Dependencies
├── config.example.json     # Example configuration
└── README.md               # Documentation
```

## Key Files

### [lib/gitmon/tui.py](lib/gitmon/tui.py) - The TUI Interface

**Most important file for UI changes.**

- **HoverableDataTable class:** Custom DataTable widget with mouse hover support (lines 15-40)
- **GitMonApp class:** Main Textual application
- **DataTable structure:** 4 columns (Repository, Branch, Status, Tracking)
  - Repository column displays as `[owner] repo-name` (combined owner and repo)
- **Column definitions:** Lines 137-140
- **Row rendering:** Lines 148-198 in `action_refresh()` method
- **Row sorting:** Alphabetically by owner then repo name (line 162)
- **CSS styling:** Lines 46-89
- **Mouse hover:** Displays remote commit message and local path on hover (lines 216-235)
- **Key bindings:**
  - `r` - Manual refresh
  - `q` - Quit application
  - `c` - Open configuration file
- **Auto-refresh:** Configurable interval (default 5 seconds)

### [lib/gitmon/scanner.py](lib/gitmon/scanner.py) - Git Analysis

- **RepoInfo dataclass:** Stores repository data (name, path, branch, status, ahead/behind counts, stash count, remote commit message)
- **GitScanner class:** Finds and analyzes repositories
  - `find_repositories()` - Recursive directory search for .git folders
  - `get_repo_info()` - Extracts branch, remote owner, git status
  - `_get_tracking_status()` - Parses `git rev-list --left-right --count HEAD...@{upstream}`
  - `_get_remote_commit_message()` - Fetches most recent remote commit message (lines 197-221)

### [lib/gitmon/config.py](lib/gitmon/config.py) - Configuration

- **Default location:** `~/.config/gitmon/config.json`
- **Configuration options:**
  - `watch_directories` - Paths to scan for repos
  - `refresh_interval` - Seconds between refreshes (default: 5)
  - `max_depth` - Max directory search depth (default: 3)

## Data Flow

1. **Startup:** `bin/gitmon` → `__main__.py` → loads config → launches `GitMonApp`
2. **Scanning:** `GitScanner.find_repositories()` finds all repos in watched directories
3. **Analysis:** For each repo, `get_repo_info()` extracts git status, branch, tracking info
4. **Rendering:** `tui.py` displays results in DataTable, auto-refreshes at interval

## Column Rendering Details

### Status Column (Color-coded)

- **Clean:** `○ clean` (green) - No changes, no stashes
- **Stashed:** `◐ stashed` (blue) - Has stashed changes
- **Changes:** `● changes` (yellow) - Uncommitted changes
- **Error:** `✗ error` (red) - Git command failed

### Repository Column (Combined Owner and Name)

- **Format:** `[owner] repo-name`
- **Example:** `[raremonarch] gitmon`
- **Width:** 50 characters
- **Sorting:** Alphabetically by owner (case-insensitive), then by repo name
- **Note:** Square brackets are escaped to prevent Rich markup interpretation

### Tracking Column (Arrows and Numbers)

- **Format:** `↑ {ahead}  ↓ {behind}` or empty string (if no tracking)
- **Example:** `↑ 5  ↓ 3` means 5 commits ahead, 3 commits behind upstream
- **Width:** 15 characters
- **Spacing:** Space between arrow and number, double space between indicators

### Mouse Hover Tooltip

- **Trigger:** Mouse hover over any table row (mouse-only, no keyboard navigation)
- **Display:** Panel appears below table showing:
  - Line 1: `Last Remote Commit: {commit message}`
  - Line 2: `Path: {local path}`
- **Styling:** Panel background with white text, no border
- **Implementation:** HoverableDataTable widget posts RowHovered messages on mouse movement

## Common Tasks

### Fixing Display Issues

- **Location:** [lib/gitmon/tui.py](lib/gitmon/tui.py)
- **Column widths:** Lines 137-140 (increase width parameter)
- **Formatting:** Lines 170-180 (adjust spacing, use Rich Text objects)
- **CSS styling:** Lines 46-89 (add color/padding classes)
- **Hover panel:** Lines 66-73 (adjust height, padding, colors)

### Testing Changes

```bash
# Run from project root
./bin/gitmon

# Or with custom config
./bin/gitmon --config /path/to/config.json
```

### Adding New Columns

1. Add column to DataTable: Lines 137-140 in tui.py
2. Add data field to RepoInfo dataclass in scanner.py (line 9)
3. Extract data in `get_repo_info()` method (lines 87-147)
4. Format and add to table row: Lines 183-191 in tui.py

### Modifying Hover Tooltip Content

1. Update `_show_repo_info()` method in tui.py (lines 216-235)
2. Access repo data via sorted_repos list
3. Format display text (currently 2 lines: commit message and path)
4. Adjust hover panel height in CSS if adding more lines (line 67)

## Design Patterns

### Rich Text for Styling

Status column uses Textual's `Text` objects with inline styles:

```python
status = Text("● changes", style="yellow")
```

Branch column also uses Rich Text with cyan styling. The Tracking column uses plain strings with spacing controlled by format strings.

### Mouse Hover Pattern

The HoverableDataTable extends DataTable to add mouse hover functionality:

- Captures `on_mouse_move()` events within the table
- Calculates row index from mouse Y position
- Posts custom `RowHovered` message to parent app
- Parent app handles message to show/hide hover panel

This pattern allows mouse-only interaction without keyboard cursor or focus.

### Error Handling

- Git commands wrapped in try/except
- Failed repos shown with "error" status
- Error messages stored in `RepoInfo.error` field

## Git Workflow

- **Main branch:** `main`
- **Commit style:** Descriptive, focus on "why" not "what"
- **Recent commits:**
  - a099d56 - Add stashed status detection
  - a0dd162 - Initial commit with basic monitoring

## Notes for Development

- The TUI auto-refreshes, so changes are visible after restart
- Column widths must accommodate both arrows (↑/↓) and multi-digit numbers
- Rich Text objects provide better control over spacing than plain strings
- Textual uses CSS-like styling - see framework docs for advanced layouts
