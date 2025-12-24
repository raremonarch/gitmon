# GitMon - Git Repository Monitor

A terminal user interface (TUI) for monitoring multiple git repositories at a glance.

## Features

- Monitor multiple git repositories from configured directories
- Display repository name, remote owner, current branch, and status
- Show tracking information (commits ahead/behind)
- Auto-refresh at configurable intervals
- Manual and automatic git fetch for all repositories
- Clean, colorful TUI built with Textual

## Installation

### Prerequisites

- Python 3.7+
- Git

Dependencies are automatically installed in a virtual environment on first run.

### Setup

1. Clone or copy the gitmon directory to your preferred location
2. Add the `bin` directory to your PATH, or create a symlink:

```bash
# Option 1: Add to PATH in your shell config (~/.bashrc, ~/.zshrc, etc.)
export PATH="$PATH:/path/to/gitmon/bin"

# Option 2: Create symlink in a directory already in PATH
ln -s /path/to/gitmon/bin/gitmon ~/.local/bin/gitmon
```

3. Run gitmon for the first time:
```bash
gitmon
```

On first run, gitmon will automatically:
- Create a virtual environment in `venv/`
- Install all required dependencies (textual)
- Create a default configuration file

### Alternative: Install with pipx

```bash
pipx install git+https://github.com/raremonarch/gitmon.git
```

## Configuration

On first run, gitmon creates a default configuration file at:
```
~/.config/gitmon/config.json
```

### Configuration Options

- `watch_directories`: Array of directory paths to scan for git repositories
- `refresh_interval`: Seconds between automatic refreshes (default: 5)
- `max_depth`: Maximum directory depth to search for repositories (default: 3)
- `auto_fetch_enabled`: Enable automatic fetching of all repositories (default: false)
- `auto_fetch_interval`: Seconds between automatic fetches (default: 300, minimum: 60)

### Example Configuration

```json
{
  "watch_directories": [
    "~/code",
    "~/projects",
    "/path/to/other/repos"
  ],
  "refresh_interval": 5,
  "max_depth": 3,
  "auto_fetch_enabled": false,
  "auto_fetch_interval": 300
}
```

## Usage

Start monitoring:
```bash
gitmon
```

Use custom config:
```bash
gitmon --config /path/to/config.json
```

### Keyboard Shortcuts

- `r` - Refresh repository information
- `f` - Fetch updates from all remotes (runs `git fetch --all` for each repo)
- `a` - Toggle auto-fetch on/off (updates config file)
- `c` - Open configuration file in editor ($EDITOR or vim)
- `q` - Quit application

### Automatic Fetching

GitMon can automatically fetch updates from remotes at regular intervals:

- **Toggle on/off**: Press `a` to toggle auto-fetch (saves to config file immediately)
- **Manual config**: Set `auto_fetch_enabled: true` in your config file
- Configure fetch frequency with `auto_fetch_interval` (default: 300 seconds / 5 minutes)
- Minimum interval is 60 seconds to avoid excessive network traffic
- Fetch operations run in the background with progress display
- Current status shown in info bar: "Auto-fetch: ON (300s)" or "Auto-fetch: OFF"
- Manual refresh (press `r`) or automatic refresh will show updated tracking info after fetch completes

When a fetch is running (manual or automatic):
- Progress is displayed showing which repo is being fetched (e.g., "Fetching 3/10: gitmon...")
- Completion message shows success/failure counts
- Failed fetches display error messages for troubleshooting
- The display automatically refreshes after fetch completes to show new tracking information
- Enabling auto-fetch triggers an immediate fetch to populate status indicators

## Repository Information

GitMon displays the following information for each repository:

- **Repository**: Repository name (directory name)
- **Owner**: Extracted from remote URL (owner/organization)
- **Branch**: Current branch name
- **Status**:
  - ○ clean - No uncommitted changes and no stashes
  - ◐ stashed - Clean working directory but has stashed changes
  - ● changes - Uncommitted changes present
  - ✗ error - Error accessing repository
- **Tracking**: Commits ahead (↑) and behind (↓) remote
  - When auto-fetch is enabled, also shows fetch status:
    - ✓ (green) - Last fetch succeeded
    - ✗ (red) - Last fetch failed (e.g., SSH key missing, authentication failure)
    - Hover over any row to see fetch error details when a fetch has failed

## Scanning Behavior

- GitMon recursively scans each configured directory up to the configured `max_depth` (default: 3 levels)
- When a `.git` folder is found, that directory is recognized as a repository and scanning stops descending into it
- Hidden directories (starting with `.`) are skipped during scanning
- Directories without read permissions are silently skipped
- Results are sorted alphabetically by repository name

This approach efficiently finds repositories nested in subdirectories while avoiding unnecessary scanning inside repository directories (like `node_modules`, `.git`, etc.).

## Troubleshooting

### "python3 is required"
Install Python 3.7 or higher for your system

### Dependencies not installing
If automatic setup fails:
1. Ensure you have `python3-venv` package installed (on some Linux distributions)
2. Manually create venv: `python3 -m venv /path/to/gitmon/venv`
3. Activate and install: `source /path/to/gitmon/venv/bin/activate && pip install -e /path/to/gitmon`

### Repositories not showing
- Verify the directory paths in your config file
- Ensure directories contain git repositories (have `.git` folder)
- Check that paths are accessible and properly expanded (~ for home, etc.)

### Clean installation
To start fresh, remove the venv and config:
```bash
rm -rf /path/to/gitmon/venv
rm -rf ~/.config/gitmon
```

## License

MIT License - feel free to modify and distribute.
