"""Configuration file handling for gitmon."""

import os
from pathlib import Path
from typing import List
import json


class Config:
    """Handle gitmon configuration."""

    DEFAULT_CONFIG_PATH = Path.home() / ".config" / "gitmon" / "config.json"

    def __init__(self, config_path: Path = None):
        """Initialize configuration handler.

        Args:
            config_path: Path to configuration file. Defaults to ~/.config/gitmon/config.json
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.watch_directories: List[str] = []
        self.refresh_interval: int = 5
        self.max_depth: int = 3
        self.load()

    def load(self) -> None:
        """Load configuration from file."""
        if not self.config_path.exists():
            self._create_default_config()
            return

        try:
            with open(self.config_path, 'r') as f:
                data = json.load(f)
                self.watch_directories = data.get('watch_directories', [])
                self.refresh_interval = data.get('refresh_interval', 5)
                self.max_depth = data.get('max_depth', 3)
        except (json.JSONDecodeError, IOError) as e:
            raise ValueError(f"Error loading config from {self.config_path}: {e}")

    def _create_default_config(self) -> None:
        """Create default configuration file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        default_config = {
            "watch_directories": [
                str(Path.home() / "code"),
            ],
            "refresh_interval": 5,
            "max_depth": 3
        }

        with open(self.config_path, 'w') as f:
            json.dump(default_config, f, indent=2)

        self.watch_directories = default_config['watch_directories']
        self.refresh_interval = default_config['refresh_interval']
        self.max_depth = default_config['max_depth']

    def save(self) -> None:
        """Save configuration to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "watch_directories": self.watch_directories,
            "refresh_interval": self.refresh_interval,
            "max_depth": self.max_depth
        }

        with open(self.config_path, 'w') as f:
            json.dump(data, f, indent=2)

    def get_expanded_directories(self) -> List[Path]:
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
