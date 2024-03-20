from typing import Any, Dict, Iterator, List, Tuple

from esm.log_exc.logger import Logger


class DataTable:
    """
    tbd
    """

    def __init__(
            self,
            logger: Logger,
            **kwargs,
    ) -> None:

        self.logger = logger.getChild(__name__)

        self.name: str = None
        self.type: str = None
        self.coordinates: List[str] = []
        self.coordinates_headers: Dict[str, str] = {}
        self.coordinates_values: Dict[str, Any] = {}
        self.table_headers: Dict[str, Any] = {}
        self.variables_info: Dict[str, Any] = {}
        self.foreign_keys: Dict[str, Any] = {}

        for key, value in kwargs.items():
            setattr(self, key, value)

        self.variable_list: List[str] = list(self.variables_info.keys())

    def __repr__(self) -> str:
        output = ''
        for key, value in self.__dict__.items():
            if key not in ('data', 'logger'):
                output += f'\n{key}: {value}'
        return output

    def __iter__(self) -> Iterator[Tuple[Any, Any]]:
        for key, value in self.__dict__.items():
            if key not in ('data', 'logger'):
                yield key, value
