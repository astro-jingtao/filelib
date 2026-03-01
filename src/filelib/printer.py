class Printer:
    def __init__(self, dry_run=False, run_log=False, verbose=False, ignore_warning=False):
        self.dry_run = dry_run
        self.run_log = run_log
        self.verbose = verbose
        self.ignore_warning = ignore_warning

    def print_dry_run(self, message):
        if self.dry_run:
            print(f"[dry-run] {message}")
    
    def print_run_log(self, message):
        if self.run_log and not self.dry_run:
            print(message)

    def print_general_run_log(self, message):
        self.print_dry_run(message)
        self.print_run_log(message)
    
    def print_verbose(self, message):
        if self.verbose:
            print(message)

    def print_warning(self, message):
        if not self.ignore_warning:
            print(f"Warning: {message}")

    