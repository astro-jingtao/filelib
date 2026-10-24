"""Printing helpers for dry-run previews, run logs, and warnings.

``Printer`` is the internal output adapter used by ``filelib.operator``:
each print method is gated by a flag captured at construction time.
"""


class Printer:
    """Route messages to dry-run / run-log / verbose / warning output."""

    def __init__(
        self,
        dry_run: bool = False,
        run_log: bool = False,
        verbose: bool = False,
        ignore_warning: bool = False,
    ) -> None:
        """Store the output flags that gate the print methods."""
        self.dry_run = dry_run
        self.run_log = run_log
        self.verbose = verbose
        self.ignore_warning = ignore_warning

    def print_dry_run(self, message: str) -> None:
        """Print ``message`` with a ``[dry-run]`` prefix when enabled."""
        if self.dry_run:
            print(f"[dry-run] {message}")

    def print_run_log(self, message: str) -> None:
        """Print ``message`` as a run-log line when enabled (never in dry-run)."""
        if self.run_log and not self.dry_run:
            print(message)

    def print_general_run_log(self, message: str) -> None:
        """Print as a dry-run preview or a run-log line, whichever mode is active."""
        self.print_dry_run(message)
        self.print_run_log(message)

    def print_verbose(self, message: str) -> None:
        """Print ``message`` only in verbose mode."""
        if self.verbose:
            print(message)

    def print_warning(self, message: str) -> None:
        """Print ``message`` with a ``Warning: `` prefix unless suppressed."""
        if not self.ignore_warning:
            print(f"Warning: {message}")
