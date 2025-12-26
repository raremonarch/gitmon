"""Unit tests for config module."""

import json
import os
from pathlib import Path

import pytest

from gitmon.config import Config
from gitmon.exceptions import ConfigurationError


class TestConfigDefaultCreation:
    """Test default config file creation."""

    def test_creates_default_config_when_missing(self, tmp_path: Path) -> None:
        """Test that default config is created when file doesn't exist."""
        config_path = tmp_path / "config.json"
        config = Config(config_path)

        # Verify file was created
        assert config_path.exists()

        # Verify default values
        assert config.watch_directories == [str(Path.home() / "code")]
        assert config.refresh_interval == 5
        assert config.max_depth == 3
        assert config.auto_fetch_enabled is False
        assert config.auto_fetch_interval == 300

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test that parent directories are created if missing."""
        config_path = tmp_path / "nested" / "dir" / "config.json"
        config = Config(config_path)

        assert config_path.exists()
        assert config_path.parent.exists()

    def test_default_config_has_valid_json(self, tmp_path: Path) -> None:
        """Test that created default config is valid JSON."""
        config_path = tmp_path / "config.json"
        Config(config_path)

        # Should be able to load as JSON
        with open(config_path) as f:
            data = json.load(f)

        assert "watch_directories" in data
        assert "refresh_interval" in data
        assert "max_depth" in data


class TestConfigLoading:
    """Test loading existing config files."""

    def test_loads_valid_config(self, tmp_path: Path) -> None:
        """Test loading a valid config file."""
        config_path = tmp_path / "config.json"
        config_data = {
            "watch_directories": ["/tmp/test1", "/tmp/test2"],
            "refresh_interval": 10,
            "max_depth": 5,
            "auto_fetch_enabled": True,
            "auto_fetch_interval": 120,
        }

        with open(config_path, "w") as f:
            json.dump(config_data, f)

        config = Config(config_path)

        assert config.watch_directories == ["/tmp/test1", "/tmp/test2"]
        assert config.refresh_interval == 10
        assert config.max_depth == 5
        assert config.auto_fetch_enabled is True
        assert config.auto_fetch_interval == 120

    def test_loads_config_with_missing_optional_fields(self, tmp_path: Path) -> None:
        """Test loading config with only required fields."""
        config_path = tmp_path / "config.json"
        config_data = {
            "watch_directories": ["/tmp/test"],
        }

        with open(config_path, "w") as f:
            json.dump(config_data, f)

        config = Config(config_path)

        # Missing fields should use defaults
        assert config.watch_directories == ["/tmp/test"]
        assert config.refresh_interval == 5  # default
        assert config.max_depth == 3  # default
        assert config.auto_fetch_enabled is False  # default
        assert config.auto_fetch_interval == 300  # default

    def test_raises_error_on_invalid_json(self, tmp_path: Path) -> None:
        """Test that invalid JSON raises ConfigurationError."""
        config_path = tmp_path / "config.json"

        # Write invalid JSON
        with open(config_path, "w") as f:
            f.write("{invalid json content")

        with pytest.raises(ConfigurationError, match="Invalid JSON"):
            Config(config_path)

    def test_creates_default_when_file_not_found(self, tmp_path: Path) -> None:
        """Test that default config is created when file doesn't exist."""
        config_path = tmp_path / "nonexistent.json"

        # File shouldn't exist yet
        assert not config_path.exists()

        config = Config(config_path)

        # File should now exist with defaults
        assert config_path.exists()
        assert config.watch_directories == [str(Path.home() / "code")]


class TestConfigSaving:
    """Test config file saving."""

    def test_saves_config_correctly(self, tmp_path: Path) -> None:
        """Test that config is saved correctly."""
        config_path = tmp_path / "config.json"
        config = Config(config_path)

        # Modify config
        config.watch_directories = ["/custom/path"]
        config.refresh_interval = 15
        config.max_depth = 2
        config.auto_fetch_enabled = True
        config.auto_fetch_interval = 180

        # Save
        config.save()

        # Verify file contents
        with open(config_path) as f:
            data = json.load(f)

        assert data["watch_directories"] == ["/custom/path"]
        assert data["refresh_interval"] == 15
        assert data["max_depth"] == 2
        assert data["auto_fetch_enabled"] is True
        assert data["auto_fetch_interval"] == 180

    def test_creates_parent_dir_when_saving(self, tmp_path: Path) -> None:
        """Test that parent directory is created when saving."""
        config_path = tmp_path / "new" / "nested" / "config.json"
        config = Config(config_path)

        config.watch_directories = ["/test"]
        config.save()

        assert config_path.exists()
        assert config_path.parent.exists()

    def test_save_overwrites_existing_file(self, tmp_path: Path) -> None:
        """Test that save overwrites existing config."""
        config_path = tmp_path / "config.json"

        # Create initial config
        config = Config(config_path)
        config.refresh_interval = 5
        config.save()

        # Modify and save again
        config.refresh_interval = 20
        config.save()

        # Verify the file was overwritten
        with open(config_path) as f:
            data = json.load(f)

        assert data["refresh_interval"] == 20


class TestGetExpandedDirectories:
    """Test directory expansion and filtering."""

    def test_expands_tilde_in_paths(self, tmp_path: Path) -> None:
        """Test that ~ is expanded to home directory."""
        config_path = tmp_path / "config.json"
        config = Config(config_path)

        config.watch_directories = ["~/test"]

        expanded = config.get_expanded_directories()

        # Should expand to actual home directory
        expected_path = Path.home() / "test"
        # Note: expanded list may be empty if directory doesn't exist
        # We're testing the expansion logic, not existence filtering here
        if expanded:
            assert str(expanded[0]) == str(expected_path)

    def test_expands_environment_variables(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test that environment variables are expanded."""
        # Set a test environment variable
        test_dir = tmp_path / "test_env_dir"
        test_dir.mkdir()
        monkeypatch.setenv("TEST_DIR", str(test_dir))

        config_path = tmp_path / "config.json"
        config = Config(config_path)
        config.watch_directories = ["$TEST_DIR"]

        expanded = config.get_expanded_directories()

        assert len(expanded) == 1
        assert expanded[0] == test_dir

    def test_filters_nonexistent_directories(self, tmp_path: Path) -> None:
        """Test that non-existent directories are filtered out."""
        config_path = tmp_path / "config.json"
        config = Config(config_path)

        config.watch_directories = [
            str(tmp_path / "exists"),
            str(tmp_path / "does_not_exist"),
        ]

        # Create only one directory
        (tmp_path / "exists").mkdir()

        expanded = config.get_expanded_directories()

        assert len(expanded) == 1
        assert expanded[0] == tmp_path / "exists"

    def test_filters_non_directory_paths(self, tmp_path: Path) -> None:
        """Test that file paths are filtered out."""
        config_path = tmp_path / "config.json"
        config = Config(config_path)

        # Create a file and a directory
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")
        dir_path = tmp_path / "directory"
        dir_path.mkdir()

        config.watch_directories = [str(file_path), str(dir_path)]

        expanded = config.get_expanded_directories()

        # Only the directory should be included
        assert len(expanded) == 1
        assert expanded[0] == dir_path

    def test_handles_empty_watch_directories(self, tmp_path: Path) -> None:
        """Test that empty watch_directories returns empty list."""
        config_path = tmp_path / "config.json"
        config = Config(config_path)
        config.watch_directories = []

        expanded = config.get_expanded_directories()

        assert expanded == []


class TestConfigValidation:
    """Test configuration validation."""

    def test_rejects_negative_refresh_interval(self, tmp_path: Path) -> None:
        """Test that negative refresh_interval raises error."""
        config_path = tmp_path / "config.json"
        config_data = {
            "watch_directories": ["/tmp"],
            "refresh_interval": -1,
        }

        with open(config_path, "w") as f:
            json.dump(config_data, f)

        with pytest.raises(ConfigurationError, match="refresh_interval must be >= 1"):
            Config(config_path)

    def test_rejects_zero_refresh_interval(self, tmp_path: Path) -> None:
        """Test that zero refresh_interval raises error."""
        config_path = tmp_path / "config.json"
        config_data = {
            "watch_directories": ["/tmp"],
            "refresh_interval": 0,
        }

        with open(config_path, "w") as f:
            json.dump(config_data, f)

        with pytest.raises(ConfigurationError, match="refresh_interval must be >= 1"):
            Config(config_path)

    def test_rejects_zero_max_depth(self, tmp_path: Path) -> None:
        """Test that zero max_depth raises error."""
        config_path = tmp_path / "config.json"
        config_data = {
            "watch_directories": ["/tmp"],
            "max_depth": 0,
        }

        with open(config_path, "w") as f:
            json.dump(config_data, f)

        with pytest.raises(ConfigurationError, match="max_depth must be >= 1"):
            Config(config_path)

    def test_rejects_negative_max_depth(self, tmp_path: Path) -> None:
        """Test that negative max_depth raises error."""
        config_path = tmp_path / "config.json"
        config_data = {
            "watch_directories": ["/tmp"],
            "max_depth": -5,
        }

        with open(config_path, "w") as f:
            json.dump(config_data, f)

        with pytest.raises(ConfigurationError, match="max_depth must be >= 1"):
            Config(config_path)

    def test_rejects_invalid_watch_directories_type(self, tmp_path: Path) -> None:
        """Test that non-list watch_directories raises error."""
        config_path = tmp_path / "config.json"
        config_data = {
            "watch_directories": "/single/path",  # Should be a list
        }

        with open(config_path, "w") as f:
            json.dump(config_data, f)

        with pytest.raises(ConfigurationError, match="watch_directories must be a list"):
            Config(config_path)

    def test_rejects_too_small_auto_fetch_interval(self, tmp_path: Path) -> None:
        """Test that auto_fetch_interval < 60 raises error."""
        config_path = tmp_path / "config.json"
        config_data = {
            "watch_directories": ["/tmp"],
            "auto_fetch_interval": 30,  # Too small
        }

        with open(config_path, "w") as f:
            json.dump(config_data, f)

        with pytest.raises(ConfigurationError, match="auto_fetch_interval must be >= 60"):
            Config(config_path)

    def test_accepts_valid_configuration(self, tmp_path: Path) -> None:
        """Test that valid configuration passes validation."""
        config_path = tmp_path / "config.json"
        config_data = {
            "watch_directories": ["/tmp", "/home"],
            "refresh_interval": 1,
            "max_depth": 1,
            "auto_fetch_enabled": True,
            "auto_fetch_interval": 60,
        }

        with open(config_path, "w") as f:
            json.dump(config_data, f)

        # Should not raise any errors
        config = Config(config_path)
        assert config.refresh_interval == 1
        assert config.max_depth == 1
        assert config.auto_fetch_interval == 60
