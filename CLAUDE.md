# Claude Code Context for GitMon

## Repository Overview

GitMon is a Python TUI (Text User Interface) application built with [Textual](https://textual.textualize.io/) that monitors git repositories. It scans configured directories for git repos and displays their status, branches, and tracking information in a terminal-based table.

**Version:** 0.1.0
**Main Language:** Python 3
**TUI Framework:** Textual (>=0.40.0)

## Project Structure

```
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

- **GitMonApp class:** Main Textual application
- **DataTable structure:** 5 columns (Repository, Owner, Branch, Status, Tracking)
- **Column definitions:** Lines 95-100
- **Row rendering:** Lines 120-151 in `action_refresh()` method
- **CSS styling:** Lines 16-59
- **Key bindings:**
  - `r` - Manual refresh
  - `q` - Quit application
- **Auto-refresh:** Configurable interval (default 5 seconds)

### [lib/gitmon/scanner.py](lib/gitmon/scanner.py) - Git Analysis
- **RepoInfo dataclass:** Stores repository data (name, path, branch, status, ahead/behind counts, stash count)
- **GitScanner class:** Finds and analyzes repositories
  - `find_repositories()` - Recursive directory search for .git folders
  - `get_repo_info()` - Extracts branch, remote owner, git status
  - `_get_tracking_status()` - Parses `git rev-list --left-right --count HEAD...@{upstream}`

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

### Tracking Column (Arrows and Numbers)
- **Format:** `↑{ahead} ↓{behind}` or `—` (em dash if no tracking)
- **Example:** `↑5 ↓3` means 5 commits ahead, 3 commits behind upstream
- **Current width:** 15 characters
- **Known issue:** Arrows and numbers can overlap with insufficient spacing

## Common Tasks

### Fixing Display Issues
- **Location:** [lib/gitmon/tui.py](lib/gitmon/tui.py)
- **Column widths:** Lines 95-100 (increase width parameter)
- **Formatting:** Lines 132-142 (adjust spacing, use Rich Text objects)
- **CSS styling:** Lines 16-59 (add color/padding classes)

### Testing Changes
```bash
# Run from project root
./bin/gitmon

# Or with custom config
./bin/gitmon --config /path/to/config.json
```

### Adding New Columns
1. Add column to DataTable: Line ~100 in tui.py
2. Add data field to RepoInfo dataclass in scanner.py
3. Extract data in `get_repo_info()` method
4. Format and add to table row: Lines ~145-151 in tui.py

## Design Patterns

### Rich Text for Styling
Status column uses Textual's `Text` objects with inline styles:
```python
status = Text("● changes", style="yellow")
```

The Tracking column currently uses plain strings - should be converted to Rich Text for better spacing control.

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
