"""Error monitoring agent for the Bookstore API.

Scans ``logs/app.log`` for ERROR and CRITICAL entries, reporting them to
both the console (color-coded) and a persistent report file.

Usage:
    python scripts/monitor_errors.py            # poll every 5 minutes
    python scripts/monitor_errors.py --once      # single scan, then exit
    python scripts/monitor_errors.py --interval 60  # poll every 60 seconds
"""

from __future__ import annotations

import argparse
import json
import re
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parents[1] / "logs"
LOG_FILE = LOG_DIR / "app.log"
POSITION_FILE = LOG_DIR / ".monitor_position"
REPORT_FILE = LOG_DIR / "monitor_report.log"

# Matches the structured log format produced by logging_config.py:
#   2026-02-27 14:30:00 | ERROR    | app.core.exceptions | message
LOG_PATTERN = re.compile(
    r"^(?P<timestamp>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"
    r" \| (?P<level>\S+)\s*"
    r"\| (?P<logger>\S+)"
    r" \| (?P<message>.+)$"
)

ERROR_LEVELS = {"ERROR", "CRITICAL"}

# ANSI color codes
RED = "\033[91m"
MAGENTA = "\033[95m"
GRAY = "\033[90m"
BOLD = "\033[1m"
RESET = "\033[0m"


# ---------------------------------------------------------------------------
# Position tracking — avoids re-reporting old errors across runs
# ---------------------------------------------------------------------------

@dataclass
class LogPosition:
    offset: int = 0
    file_size: int = 0

    def save(self) -> None:
        POSITION_FILE.parent.mkdir(parents=True, exist_ok=True)
        POSITION_FILE.write_text(
            json.dumps({"offset": self.offset, "file_size": self.file_size}),
            encoding="utf-8",
        )

    @classmethod
    def load(cls) -> LogPosition:
        if not POSITION_FILE.exists():
            return cls()
        try:
            data = json.loads(POSITION_FILE.read_text(encoding="utf-8"))
            return cls(offset=data["offset"], file_size=data["file_size"])
        except (json.JSONDecodeError, KeyError):
            return cls()


# ---------------------------------------------------------------------------
# Log parsing
# ---------------------------------------------------------------------------

@dataclass
class LogEntry:
    timestamp: str
    level: str
    logger: str
    message: str


def parse_log_line(line: str) -> LogEntry | None:
    """Parse a single log line. Returns an entry only for ERROR/CRITICAL."""
    m = LOG_PATTERN.match(line.strip())
    if not m:
        return None
    if m.group("level") not in ERROR_LEVELS:
        return None
    return LogEntry(
        timestamp=m.group("timestamp"),
        level=m.group("level"),
        logger=m.group("logger"),
        message=m.group("message"),
    )


def scan_new_entries(position: LogPosition) -> tuple[list[LogEntry], LogPosition]:
    """Read new lines from the log file starting at *position*.

    Detects log rotation (file size < saved offset) and resets to 0.
    Returns parsed error entries and the updated position.
    """
    if not LOG_FILE.exists():
        return [], position

    current_size = LOG_FILE.stat().st_size

    # Log rotation detected — file is smaller than last known size.
    if current_size < position.file_size:
        position = LogPosition(offset=0, file_size=current_size)

    if current_size == position.offset:
        return [], position  # nothing new

    entries: list[LogEntry] = []
    with LOG_FILE.open("r", encoding="utf-8") as fh:
        fh.seek(position.offset)
        for line in fh:
            entry = parse_log_line(line)
            if entry:
                entries.append(entry)
        new_offset = fh.tell()

    new_position = LogPosition(offset=new_offset, file_size=current_size)
    return entries, new_position


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def _level_color(level: str) -> str:
    if level == "CRITICAL":
        return MAGENTA
    return RED


def print_colored(entries: list[LogEntry]) -> None:
    """Print error entries with ANSI colors."""
    for e in entries:
        color = _level_color(e.level)
        print(
            f"{GRAY}{e.timestamp}{RESET} "
            f"{color}{BOLD}{e.level:<8}{RESET} "
            f"{GRAY}{e.logger}{RESET} "
            f"{color}{e.message}{RESET}"
        )


def write_report(entries: list[LogEntry]) -> None:
    """Append entries to the persistent report file."""
    if not entries:
        return
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    with REPORT_FILE.open("a", encoding="utf-8") as fh:
        fh.write(f"\n--- Scan at {now} — {len(entries)} error(s) ---\n")
        for e in entries:
            fh.write(f"{e.timestamp} | {e.level:<8} | {e.logger} | {e.message}\n")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run_monitor(*, once: bool = False, interval: int = 300) -> None:
    """Main monitoring loop.

    Args:
        once: If True, run a single scan and exit.
        interval: Seconds between scans (default 300 = 5 min).
    """
    print(f"{BOLD}Error Monitor{RESET} — watching {LOG_FILE}")
    if not once:
        print(f"Polling every {interval}s. Press Ctrl+C to stop.\n")

    position = LogPosition.load()

    try:
        while True:
            entries, position = scan_new_entries(position)
            position.save()

            if entries:
                print_colored(entries)
                write_report(entries)
                print(f"\n  {BOLD}{len(entries)} error(s){RESET} written to {REPORT_FILE}\n")
            else:
                now = datetime.now(UTC).strftime("%H:%M:%S")
                print(f"{GRAY}[{now}] No new errors.{RESET}")

            if once:
                break

            time.sleep(interval)
    except KeyboardInterrupt:
        print(f"\n{BOLD}Monitor stopped.{RESET}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Bookstore API error monitor")
    parser.add_argument(
        "--once", action="store_true", help="Run a single scan and exit"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Polling interval in seconds (default: 300)",
    )
    args = parser.parse_args()
    run_monitor(once=args.once, interval=args.interval)


if __name__ == "__main__":
    main()
