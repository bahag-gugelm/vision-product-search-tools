from pathlib import Path


# wrapper for writing output files
# in parts of fixed size.
class RotatingTextWriter:
    def __init__(
        self,
        file: Path,
        encoding: str = "utf8",
        mode: str = "at",
        newline: str = "",
        rollover_prefix: str = "part",
        max_size_b: int = None,
        max_lines: int = None,
    ) -> None:
        self._file = file
        self.fname = file.stem
        self.fext = file.suffix
        self.mode = mode
        self.encoding = encoding
        self.newline = newline
        self.rollover_prefix = rollover_prefix and f"_{rollover_prefix}_" or ""
        self.max_size_b = max_size_b
        self.max_lines = max_lines
        self.rollover_count = 0
        self.curr_lines_written = 0
        self.total_lines_written = 0
        self.stream = None

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        if self.stream:
            self.stream.close()

    def _open_file(self):
        self.stream = self._file.open(mode=self.mode, encoding=self.encoding, newline=self.newline, buffering=1)

    def do_rollover(self) -> None:
        self.stream.close()
        self.stream = None
        self.rollover_count += 1
        self._file = Path(self._file.parent / f"{self.fname}{self.rollover_prefix}{self.rollover_count}{self.fext}")
        self.curr_lines_written = 0

    @property
    def curr_fsize(self) -> int:
        return self._file.stat().st_size

    @property
    def rollover_needed(self) -> bool:
        return (self.max_size_b and self.max_size_b - self.curr_fsize <= 2048) or (
            self.max_lines and self.curr_lines_written == self.max_lines
        )

    def count_written(self) -> None:
        self.curr_lines_written += 1
        self.total_lines_written += 1

    def write(self, line: str) -> None:
        if not self.stream:
            self._open_file()
        self.stream.write(line)
        self.count_written()
        if self.rollover_needed:
            self.do_rollover()
