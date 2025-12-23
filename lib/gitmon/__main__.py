"""Main entry point for gitmon application."""

import argparse
import sys
from pathlib import Path

try:
    from importlib.metadata import version
except ImportError:
    from importlib_metadata import version  # type: ignore

from .config import Config
from .tui import run_app


def main() -> None:
    """Main entry point for gitmon."""
    parser = argparse.ArgumentParser(
        description="GitMon - Git Repository Monitor TUI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  gitmon                    Start monitoring with default config
  gitmon --config custom    Use custom config file

Configuration:
  Config file location: ~/.config/gitmon/config.json
  Edit config with: gitmon and press 'c' or directly edit the file

The config file should contain:
  {
    "watch_directories": ["/path/to/repos", "~/code"],
    "refresh_interval": 5
  }
        """
    )

    parser.add_argument(
        "--config",
        type=Path,
        help="Path to configuration file (default: ~/.config/gitmon/config.json)"
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"gitmon {version('gitmon')}"
    )

    args = parser.parse_args()

    try:
        # Load configuration
        config = Config(args.config) if args.config else Config()

        # Run the TUI application
        run_app(config)

    except KeyboardInterrupt:
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(130)
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
