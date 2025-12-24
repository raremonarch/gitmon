"""Main entry point for gitmon application."""

import argparse
import logging
import sys
from pathlib import Path
from typing import Optional

try:
    from importlib.metadata import version
except ImportError:
    from importlib_metadata import version  # type: ignore

from .config import Config
from .exceptions import ConfigurationError
from .tui import run_app

# Set up logging
logger = logging.getLogger(__name__)


def setup_logging(log_level: int, log_file: Optional[Path] = None) -> None:
    """Configure logging for gitmon.

    Args:
        log_level: Logging level (e.g., logging.INFO, logging.DEBUG)
        log_file: Optional path to log file. If None, only logs to console in debug mode.
    """
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # If debug mode, add console handler
    if log_level == logging.DEBUG:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # Add file handler if log file specified
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)


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
        """,
    )

    parser.add_argument(
        "--config",
        type=Path,
        help="Path to configuration file (default: ~/.config/gitmon/config.json)",
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging to file (~/.local/share/gitmon/gitmon.log)",
    )

    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable debug logging to console and file (implies --verbose)",
    )

    parser.add_argument("--version", action="version", version=f"gitmon {version('gitmon')}")

    args = parser.parse_args()

    # Configure logging based on arguments
    log_level = logging.WARNING  # Default: only warnings and errors
    log_file: Optional[Path] = None

    if args.debug:
        log_level = logging.DEBUG
        log_file = Path.home() / ".local" / "share" / "gitmon" / "gitmon.log"
    elif args.verbose:
        log_level = logging.INFO
        log_file = Path.home() / ".local" / "share" / "gitmon" / "gitmon.log"

    setup_logging(log_level, log_file)
    logger.info("Starting gitmon...")

    try:
        # Load configuration
        config = Config(args.config) if args.config else Config()
        logger.info(f"Loaded configuration from {config.config_path}")

        # Run the TUI application
        run_app(config)

    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        print("\nInterrupted by user", file=sys.stderr)
        sys.exit(130)
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e}")
        print(f"Configuration error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error occurred")
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
