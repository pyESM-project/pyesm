from pathlib import Path

from esm.log_exc.logger import Logger
from esm.support.dotdict import DotDict


class PBIManager:

    def __init__(
        self,
        logger: Logger,
        settings: DotDict[str, str],
        paths: DotDict[str, str | Path]
    ) -> None:

        self.logger = logger.getChild(__name__)
        self.logger.debug(f"'{self}' object generated.")

        self.settings = settings
        self.paths = paths

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    def generate_powerbi_report(self) -> None:
        pbi_report_file = self.settings['powerbi_report_file']

        self.logger.debug(
            f"Generation of PowerBI report file '{pbi_report_file}'.")
