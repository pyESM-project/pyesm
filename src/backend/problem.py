from typing import Any, List, Union

import pandas as pd
import numpy as np
import cvxpy as cx

from src.log_exc.logger import Logger
from src.util import constants, util
from src.util.file_manager import FileManager
from src.backend.index import Index


class Problem:

    cvxpy_var_column_header = 'variable'

    def __init__(
            self,
            logger: Logger,
            files: FileManager,
            settings: dict,
            index: Index,
    ) -> None:

        self.logger = logger.getChild(__name__)
        self.logger.info(f"'{self}' object initialization...")

        self.files = files
        self.settings = settings
        self.index = index

        self.logger.info(f"'{self}' object initialized.")

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    def create_variable(
            self,
            type: str,
            shape: [int, int],
            name: str = None,
    ) -> Union[cx.Variable, cx.Parameter]:

        if type == 'endogenous':
            return cx.Variable(shape=shape, name=name)
        elif type == 'exogenous':
            return cx.Parameter(shape=shape, name=name)
        else:
            error = f"Unsupported variable type: {type}"
            self.logger.error(error)
            raise ValueError(error)

    def data_to_variable(
            self,
            variable: cx.Parameter,
            data: Union[pd.DataFrame, np.ndarray]
    ) -> None:

        if not isinstance(variable, cx.Parameter):
            error = "Data can only be assigned to exogenous variables."
            self.logger.error(error)
            raise ValueError(error)

        if isinstance(data, pd.DataFrame):
            data_array = data.values
        elif isinstance(data, np.ndarray):
            data_array = data
        else:
            error = "Supported data formats: pandas DataFrame or a numpy array."
            self.logger.error(error)
            raise ValueError(error)

        variable.value = data_array

    def generate_vars_dataframes(self) -> None:

        self.logger.debug(
            f"Generating variables dataframes of cvxpy variables.")

        for variable in self.index.variables.values():

            variable.data = util.unpivot_dict_to_dataframe(
                data_dict=variable.coordinates,
                key_order=variable.var_parsing_hierarchy
            )

            variable.data[self.cvxpy_var_column_header] = [
                self.create_variable(
                    type=variable.type,
                    shape=variable.shape_size,
                    name=variable.symbol + str(variable.shape)
                )
                for _ in variable.data.index
            ]
