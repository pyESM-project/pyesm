from typing import Any, Dict, Iterator, List, Tuple

import cvxpy as cp
import pandas as pd

from esm.log_exc import exceptions as exc
from esm.log_exc.logger import Logger
from esm.support import util


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
        self.coordinates_dataframe: pd.DataFrame = None
        self.table_headers: Dict[str, Any] = {}
        self.variables_info: Dict[str, Any] = {}
        self.foreign_keys: Dict[str, Any] = {}
        self.cvxpy_var: cp.Variable = None

        for key, value in kwargs.items():
            setattr(self, key, value)

        self.variables_list: List[str] = list(self.variables_info.keys())

    def __repr__(self) -> str:
        avoid_representation = ('logger', 'data', 'coordinates_dataframe')
        output = ''
        for key, value in self.__dict__.items():
            if key in avoid_representation:
                continue
            output += f'\n{key}: {value}'
        return output

    def __iter__(self) -> Iterator[Tuple[Any, Any]]:
        avoid_iteration = ('logger', 'data', 'coordinates_dataframe')
        for key, value in self.__dict__.items():
            if key in avoid_iteration:
                continue
            yield key, value

    @property
    def table_length(self) -> int:
        if self.coordinates_dataframe is not None:
            return len(self.coordinates_dataframe)
        else:
            msg = f"Lenght of data table '{self.name}' unknown."
            self.logger.error(msg)
            raise exc.MissingDataError(msg)

    def generate_coordinates_dataframe(self) -> None:
        if self.coordinates:
            self.coordinates_dataframe = util.unpivot_dict_to_dataframe(
                self.coordinates_values
            )
        else:
            msg = f"Coordinates must be defined for data table '{self.name}'."
            self.logger.error(msg)
            raise exc.MissingDataError(msg)
