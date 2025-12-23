# GitMon Pre-Release Hardening Checklist

This document tracks all tasks needed to harden GitMon for a stable release. Items are organized by priority and estimated effort.

## Phase 1: Quick Wins (Foundation) ✅ COMPLETED

### Code Quality Setup

- [x] Add development dependencies to `pyproject.toml`
  - [x] pytest>=7.0.0
  - [x] ~~pytest-textual~~ (not available, removed)
  - [x] pytest-cov
  - [x] mypy>=1.0.0
  - [x] ruff>=0.1.0
- [x] Add Ruff configuration to `pyproject.toml`
- [x] Add MyPy configuration to `pyproject.toml`
- [x] Run `ruff check .` and fix any issues
- [x] Run `mypy lib/gitmon` and fix type errors

### Type Annotations

- [x] Add `-> None` to `main()` in `__main__.py:11`
- [x] Add `-> str` to `_get_timestamp()` in `tui.py:265`
- [x] Add `-> None` to all GitMonApp methods that don't return values
- [x] Add `-> None` to all Config methods that don't return values
- [x] Add `-> ComposeResult` import and type to `compose()` in `tui.py:117`
- [x] Add `Optional[Path]` to `Config.__init__` parameter
- [x] Add type parameters to generic classes (DataTable[Any], App[None])
- [x] Use modern `list[T]` instead of `typing.List[T]` (Python 3.9+)

### Code Refactoring

- [x] Extract duplicate sorting logic in `tui.py`
  - [x] Create `_get_sorted_repos() -> list[RepoInfo]` method
  - [x] Replace sorting in `action_refresh()` (line 161)
  - [x] Replace sorting in `_show_repo_info()` (line 225)

### CSS Extraction

- [x] Create `lib/gitmon/gitmon.tcss` file
- [x] Move inline CSS from `tui.py:46-98` to external file
- [x] Update `GitMonApp` to use `CSS_PATH` instead of `CSS` attribute
- [x] Verify styling still works correctly after extraction
- [x] Add CSS file to package data in `pyproject.toml`

### Version Management

- [x] Remove hardcoded version from `__main__.py:42`
- [x] Use `importlib.metadata.version("gitmon")` instead
- [x] Ensure version only defined in `__init__.py` and `pyproject.toml`

### Additional Improvements

- [x] Updated `requires-python` to `>=3.9` (mypy requirement)
- [x] Enabled mypy strict mode for maximum type safety
- [x] Added pytest configuration to `pyproject.toml`
- [x] All linting and type checks passing

## Phase 2: Configuration Hardening

### Validation (30 minutes)

- [ ] Add validation in `config.py` `load()` method
  - [ ] Validate `refresh_interval >= 1`
  - [ ] Validate `max_depth >= 1`
  - [ ] Validate `watch_directories` is a list
- [ ] Add tests for invalid config values
- [ ] Handle validation errors gracefully with helpful messages

## Phase 3: Error Handling & Logging

### Custom Exceptions (20 minutes)

- [ ] Create `exceptions.py` module
- [ ] Define `GitMonError` base exception
- [ ] Define `GitCommandError(GitMonError)` for git failures
- [ ] Define `ConfigurationError(GitMonError)` for config issues
- [ ] Replace `ValueError` raises with `ConfigurationError`

### Logging Setup (45 minutes)

- [ ] Add Python `logging` configuration to `__main__.py`
- [ ] Replace bare `except Exception` in `tui.py:35` with specific exceptions
- [ ] Add logging to `scanner.py` for git command failures
- [ ] Add logging to `config.py` for file operations
- [ ] Add `--verbose` / `--debug` CLI flag for log levels
- [ ] Log to `~/.local/share/gitmon/gitmon.log` or similar

### Narrow Exception Handling (30 minutes)

- [ ] Review all `except Exception` clauses
- [ ] Replace with specific exception types
- [ ] Add proper error recovery or propagation
- [ ] Ensure errors reach user with helpful messages

## Phase 4: Dependency Injection & Testability

### Git Command Abstraction (1 hour)

- [ ] Create `GitCommandRunner` class in `scanner.py`
  - [ ] Define `run(cwd: Path, args: list[str])` method
  - [ ] Implement default subprocess-based runner
- [ ] Refactor `GitScanner.__init__` to accept optional `runner` parameter
- [ ] Update all `subprocess.run()` calls to use `self.runner.run()`
- [ ] Test with mock runner to verify abstraction works

### TUI Testability (30 minutes)

- [ ] Extract subprocess import from `action_open_config()` in `tui.py`
- [ ] Consider making editor command configurable
- [ ] Ensure TUI methods can be tested without running full app

## Phase 5: Test Infrastructure

### Basic Setup (1 hour)

- [ ] Create `tests/` directory structure
  - [ ] `tests/__init__.py`
  - [ ] `tests/conftest.py`
  - [ ] `tests/unit/__init__.py`
  - [ ] `tests/integration/__init__.py`
  - [ ] `tests/tui/__init__.py`
- [ ] Add pytest configuration to `pyproject.toml`

  ```toml
  [tool.pytest.ini_options]
  testpaths = ["tests"]
  python_files = ["test_*.py"]
  python_classes = ["Test*"]
  python_functions = ["test_*"]
  addopts = "-v --cov=gitmon --cov-report=term-missing"
  ```

- [ ] Create `tests/conftest.py` with common fixtures
  - [ ] `tmp_git_repo` fixture for creating test repos
  - [ ] `mock_config` fixture
  - [ ] `mock_git_runner` fixture

## Phase 6: Unit Tests - Config Module

### Config Tests (2 hours)

- [ ] Create `tests/unit/test_config.py`
- [ ] Test default config creation
  - [ ] Verify default file is created in correct location
  - [ ] Verify default values are set correctly
- [ ] Test config loading
  - [ ] Test loading valid config file
  - [ ] Test loading config with missing optional fields
  - [ ] Test loading invalid JSON (should raise ConfigurationError)
  - [ ] Test loading non-existent file (should create default)
- [ ] Test config saving
  - [ ] Verify JSON is written correctly
  - [ ] Verify directory is created if missing
- [ ] Test `get_expanded_directories()`
  - [ ] Test tilde expansion (`~/code`)
  - [ ] Test environment variable expansion (`$HOME/code`)
  - [ ] Test filtering non-existent directories
  - [ ] Test filtering non-directory paths
- [ ] Test config validation
  - [ ] Test negative `refresh_interval` raises error
  - [ ] Test zero `max_depth` raises error
  - [ ] Test invalid `watch_directories` type raises error

## Phase 7: Unit Tests - Scanner Module

### Scanner Tests (3 hours)

- [ ] Create `tests/unit/test_scanner.py`
- [ ] Create `MockGitRunner` helper class for tests
- [ ] Test `_get_tracking_status()`
  - [ ] Test ahead only (`5\t0`)
  - [ ] Test behind only (`0\t3`)
  - [ ] Test ahead and behind (`5\t3`)
  - [ ] Test no tracking info (empty output)
  - [ ] Test git command failure
- [ ] Test `_get_remote_commit_message()`
  - [ ] Test successful commit message fetch
  - [ ] Test no remote configured
  - [ ] Test remote exists but no commits
  - [ ] Test git command failure
- [ ] Test `_get_stash_count()`
  - [ ] Test no stashes (0)
  - [ ] Test multiple stashes
  - [ ] Test git command failure
- [ ] Test `get_repo_info()`
  - [ ] Test clean repo
  - [ ] Test repo with uncommitted changes
  - [ ] Test repo with stashed changes
  - [ ] Test repo with both changes and stashes
  - [ ] Test detached HEAD state
  - [ ] Test repo with no remote
  - [ ] Test repo ahead of remote
  - [ ] Test repo behind remote
- [ ] Test `find_repositories()`
  - [ ] Test finding single repo
  - [ ] Test finding nested repos
  - [ ] Test respecting max_depth
  - [ ] Test skipping non-git directories
  - [ ] Test handling permission errors gracefully

### RepoInfo Tests (30 minutes)

- [ ] Create `tests/unit/test_models.py`
- [ ] Test RepoInfo dataclass creation
- [ ] Test default values
- [ ] Test all fields populate correctly

## Phase 8: Integration Tests

### Git Integration Tests (2 hours)

- [ ] Create `tests/integration/test_git_scenarios.py`
- [ ] Create fixture for real temporary git repo
- [ ] Test scanning real git repository
  - [ ] Initialize repo, verify detection
  - [ ] Add remote, verify remote_owner extraction
  - [ ] Create commits, verify branch detection
  - [ ] Create tracking branch, verify ahead/behind
- [ ] Test edge cases with real repos
  - [ ] Detached HEAD state
  - [ ] Merge conflicts (unmerged files)
  - [ ] Bare repositories
  - [ ] Submodules (should they be scanned?)
- [ ] Test performance with many repos
  - [ ] Create 50+ test repos
  - [ ] Verify scan completes in reasonable time

### CLI Integration Tests (1 hour)

- [ ] Create `tests/integration/test_cli.py`
- [ ] Test `--config` argument parsing
- [ ] Test `--version` output
- [ ] Test `--help` output
- [ ] Test invalid arguments handling
- [ ] Test exit codes for various error conditions

## Phase 9: TUI Tests

### Textual App Tests (2 hours)

- [ ] Create `tests/tui/test_app.py`
- [ ] Test app initialization
  - [ ] Verify table is created with correct columns
  - [ ] Verify auto-refresh timer is set
- [ ] Test table rendering with mock data
  - [ ] Test rendering clean repos
  - [ ] Test rendering repos with changes
  - [ ] Test rendering repos with stashes
  - [ ] Test rendering repos with errors
  - [ ] Test color coding for status column
- [ ] Test actions
  - [ ] Test `action_refresh()` updates table
  - [ ] Test `action_quit()` exits app
  - [ ] Test `action_open_config()` (mock subprocess)
- [ ] Test hover behavior
  - [ ] Test hover shows correct repo info
  - [ ] Test hover panel hides when mouse leaves
  - [ ] Test hover with no repos
- [ ] Test info bar updates
  - [ ] Verify stats are calculated correctly
  - [ ] Verify stats display format

## Phase 10: Documentation

### Code Documentation (2 hours)

- [ ] Add docstrings to all public methods in `scanner.py`
- [ ] Add docstrings to all public methods in `config.py`
- [ ] Add docstrings to all public methods in `tui.py`
- [ ] Ensure all docstrings follow Google or NumPy style
- [ ] Add module-level docstrings where missing

### Project Documentation (1 hour)

- [ ] Create `CONTRIBUTING.md`
  - [ ] Development setup instructions
  - [ ] Running tests
  - [ ] Code style guidelines
  - [ ] Submitting PRs
- [ ] Update `README.md`
  - [ ] Add badges (tests passing, coverage, version)
  - [ ] Add installation from PyPI instructions (future)
  - [ ] Add development setup section
  - [ ] Link to CONTRIBUTING.md
- [ ] Review and update `CLAUDE.md` if needed

## Phase 11: CI/CD

### GitHub Actions (1 hour)

- [ ] Create `.github/workflows/test.yml`
  - [ ] Run tests on push and PR
  - [ ] Test on Python 3.7, 3.11, 3.13
  - [ ] Run ruff linting
  - [ ] Run mypy type checking
  - [ ] Run pytest with coverage
  - [ ] Upload coverage to Codecov (optional)
- [ ] Create `.github/workflows/release.yml`
  - [ ] Trigger on git tags
  - [ ] Build package
  - [ ] Publish to PyPI (when ready)
- [ ] Add status badges to README.md

### Pre-commit Hooks (30 minutes)

- [ ] Create `.pre-commit-config.yaml`
  - [ ] Add ruff formatter
  - [ ] Add ruff linter
  - [ ] Add mypy
  - [ ] Add trailing whitespace fixer
- [ ] Document pre-commit setup in CONTRIBUTING.md

## Phase 12: Final Polish

### Code Cleanup (1 hour)

- [ ] Remove any commented-out code
- [ ] Remove any debug print statements
- [ ] Ensure consistent import ordering (ruff will help)
- [ ] Review all TODOs and FIXMEs in code
- [ ] Ensure consistent naming conventions

### Performance Review (1 hour)

- [ ] Profile git command execution times
- [ ] Consider caching remote commit messages
- [ ] Consider parallel git operations for multiple repos
- [ ] Review max_depth default (is 3 appropriate?)

### Security Review (30 minutes)

- [ ] Review all subprocess calls for command injection risks
- [ ] Ensure file paths are validated before use
- [ ] Review config file permissions
- [ ] Ensure no secrets could be logged

### Final Testing (1 hour)

- [ ] Run full test suite and verify 100% pass
- [ ] Run on actual development machine with real repos
- [ ] Test with large numbers of repos (50+)
- [ ] Test with repos in various states
- [ ] Test error recovery (permission denied, network issues, etc.)
- [ ] Test on fresh Python environment

## Release Checklist

### Version 1.0.0 Release

- [ ] All tests passing
- [ ] Coverage >= 80%
- [ ] All type errors resolved
- [ ] All linting errors resolved
- [ ] Documentation complete
- [ ] CHANGELOG.md created and updated
- [ ] Version bumped to 1.0.0 in `pyproject.toml` and `__init__.py`
- [ ] Git tag created: `git tag -a v1.0.0 -m "Release v1.0.0"`
- [ ] PyPI package built: `python -m build`
- [ ] PyPI package uploaded: `python -m twine upload dist/*`
- [ ] GitHub release created with release notes
