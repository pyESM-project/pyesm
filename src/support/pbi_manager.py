from typing import Dict

from src.log_exc.logger import Logger


class PBIManager:

    def __init__(
        self,
        logger: Logger,
        settings: Dict[str, str],
    ) -> None:

        self.logger = logger.getChild(__name__)
        self.logger.info(f"'{self}' object generated.")

        self.settings = settings
        self.file_name = None

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    def generate_powerbi_report(
        self,
        file_name: str,
    ) -> None:

        if not self.file_name:
            self.file_name = file_name

        self.logger.debug(
            f"Generation of PowerBI report file '{self.file_name}'.")
