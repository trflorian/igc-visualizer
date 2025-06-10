from pathlib import Path


class IGCParser:
    """
    Parse IGC files according to the IGC_FORMAT_2008 specification.
    https://xp-soaring.github.io/igc_file_format/igc_format_2008.html
    """

    def __init__(self, file_path: str) -> None:
        self.file_path = Path(file_path)

        self._validate_file_path()

        self.parse()

    def _validate_file_path(self) -> None:
        if not self.file_path.exists():
            raise FileNotFoundError(f"File {self.file_path} does not exist")
        if not self.file_path.suffix == ".igc":
            raise ValueError("File must have a .igc extension")

    def parse(self) -> None:
        with open(self.file_path, "r") as file:
            self.lines = file.readlines()
