from pathlib import Path
from typing import Dict

from src.log_exc.logger import Logger


class PowerBiReport:

    def __init__(
        self,
        logger: Logger,
        settings: Dict[str, str],
    ) -> None:

        self.logger = logger.getChild(__name__)
        self.logger.info(f"'{self}' object generated.")

        self.settings = settings
        self.file_name = self.settings['model']['powerbi_report_name']

    def generate_powerbi_report(
        self,
        std_file_name: str = "report.pbix"
    ) -> None:

        if not self.file_name:
            self.file_name = std_file_name

        self.logger.debug(f"PowerBI report file '{self.file_name}' created.")
