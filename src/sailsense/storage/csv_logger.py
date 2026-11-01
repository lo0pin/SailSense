import csv
from datetime import datetime
from pathlib import Path


class CsvLogger:
    """
    Einfacher CSV-Logger mit Tagesdateien.
    Schreibt Header automatisch, wenn eine neue Datei entsteht.
    """

    def __init__(self, log_dir: str | Path, prefix: str, fieldnames: list[str], flush_after_write: bool = True):
        self.log_dir = Path(log_dir)
        self.prefix = prefix
        self.fieldnames = fieldnames
        self.flush_after_write = flush_after_write

        self.log_dir.mkdir(parents=True, exist_ok=True)

        self.current_path = None
        self.file = None
        self.writer = None

    def _today_path(self) -> Path:
        date_str = datetime.now().strftime("%Y-%m-%d")
        return self.log_dir / f"{date_str}_{self.prefix}.csv"

    def _ensure_open_file(self):
        path = self._today_path()

        if path == self.current_path and self.file is not None:
            return

        if self.file is not None:
            self.file.close()

        file_exists = path.exists()
        self.current_path = path
        self.file = open(path, "a", newline="", encoding="utf-8")
        self.writer = csv.DictWriter(self.file, fieldnames=self.fieldnames)

        if not file_exists or path.stat().st_size == 0:
            self.writer.writeheader()
            self.file.flush()

    def write_row(self, row: dict):
        self._ensure_open_file()

        clean_row = {field: row.get(field) for field in self.fieldnames}
        self.writer.writerow(clean_row)

        if self.flush_after_write:
            self.file.flush()

    def close(self):
        if self.file is not None:
            self.file.close()
            self.file = None

    def __enter__(self):
        self._ensure_open_file()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
