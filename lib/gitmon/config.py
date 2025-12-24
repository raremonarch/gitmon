"""Configuration file handling for gitmon."""

import json
import logging
import os
from pathlib import Path
from typing import Any, Optional, cast

from .exceptions import ConfigurationError

logger = logging.getLogger(__name__)


class Config:
    """Handle gitmon configuration."""

    DEFAULT_CONFIG_PATH = Path.home() / ".config" / "gitmon" / "config.json"

    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration handler.

        Args:
            config_path: Path to configuration file. Defaults to ~/.config/gitmon/config.json
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.watch_directories: list[str] = []
        self.refresh_interval: int = 5
        self.max_depth: int = 3
        self.auto_fetch_enabled: bool = False
        self.auto_fetch_interval: int = 300
        self.load()

    def load(self) -> None:
        """Load configuration from file."""
        if not self.config_path.exists():
            logger.info(f"Config file not found at {self.config_path}, creating default config")
            self._create_default_config()
            return

        try:
            logger.debug(f"Loading configuration from {self.config_path}")
            with open(self.config_path) as f:
                data: dict[str, Any] = json.load(f)
                self.watch_directories = cast("list[str]", data.get("watch_directories", []))
                self.refresh_interval = cast("int", data.get("refresh_interval", 5))
                self.max_depth = cast("int", data.get("max_depth", 3))
                self.auto_fetch_enabled = cast("bool", data.get("auto_fetch_enabled", False))
                self.auto_fetch_interval = cast("int", data.get("auto_fetch_interval", 300))
            logger.debug(
                f"Successfully loaded configuration: {len(self.watch_directories)} watch directories"
            )
        except OSError as e:
            logger.error(f"Failed to read config file {self.config_path}: {e}")
            raise ConfigurationError(f"Error reading config from {self.config_path}: {e}") from e
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file {self.config_path}: {e}")
            raise ConfigurationError(f"Invalid JSON in config file {self.config_path}: {e}") from e

        # Validate configuration values
        self._validate()

    def _validate(self) -> None:
        """Validate configuration values.

        Raises:
            ConfigurationError: If any configuration value is invalid.
        """
        if not isinstance(self.watch_directories, list):
            raise ConfigurationError(
                f"watch_directories must be a list, got {type(self.watch_directories).__name__}"
            )

        if self.refresh_interval < 1:
            raise ConfigurationError(f"refresh_interval must be >= 1, got {self.refresh_interval}")

        if self.max_depth < 1:
            raise ConfigurationError(f"max_depth must be >= 1, got {self.max_depth}")

        if self.auto_fetch_interval < 60:
            raise ConfigurationError(
                f"auto_fetch_interval must be >= 60 seconds, got {self.auto_fetch_interval}"
            )

    def _create_default_config(self) -> None:
        """Create default configuration file."""
        try:
            logger.info(f"Creating default config at {self.config_path}")
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            default_config: dict[str, Any] = {
                "watch_directories": [
                    str(Path.home() / "code"),
                ],
                "refresh_interval": 5,
                "max_depth": 3,
                "auto_fetch_enabled": False,
                "auto_fetch_interval": 300,
            }

            with open(self.config_path, "w") as f:
                json.dump(default_config, f, indent=2)

            self.watch_directories = cast("list[str]", default_config["watch_directories"])
            self.refresh_interval = cast("int", default_config["refresh_interval"])
            self.max_depth = cast("int", default_config["max_depth"])
            self.auto_fetch_enabled = cast("bool", default_config["auto_fetch_enabled"])
            self.auto_fetch_interval = cast("int", default_config["auto_fetch_interval"])

            logger.info("Default config created successfully")
        except (OSError, PermissionError) as e:
            logger.error(f"Failed to create default config at {self.config_path}: {e}")
            raise ConfigurationError(f"Failed to create default config: {e}") from e

    def save(self) -> None:
        """Save configuration to file."""
        try:
            logger.debug(f"Saving configuration to {self.config_path}")
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "watch_directories": self.watch_directories,
                "refresh_interval": self.refresh_interval,
                "max_depth": self.max_depth,
                "auto_fetch_enabled": self.auto_fetch_enabled,
                "auto_fetch_interval": self.auto_fetch_interval,
            }

            with open(self.config_path, "w") as f:
                json.dump(data, f, indent=2)

            logger.debug("Configuration saved successfully")
        except (OSError, PermissionError) as e:
            logger.error(f"Failed to save config to {self.config_path}: {e}")
            raise ConfigurationError(f"Failed to save config: {e}") from e

    def get_expanded_directories(self) -> list[Path]:
        """Get watch directories with environment variables expanded.

        Returns:
            List of Path objects with expanded paths
        """
        expanded = []
        for directory in self.watch_directories:
            # Expand environment variables and user home
            expanded_path = Path(os.path.expandvars(os.path.expanduser(directory)))
            if expanded_path.exists() and expanded_path.is_dir():
                expanded.append(expanded_path)
        return expanded
