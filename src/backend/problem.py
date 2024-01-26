from typing import Any, List, Dict, Union

import pandas as pd
import numpy as np
import cvxpy as cx
from src.constants import constants

from src.log_exc.logger import Logger
from src.support import util
from src.support.file_manager import FileManager
from src.backend.index import Index, Variable


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

    def create_cvxpy_variable(
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

    def data_to_cvxpy_variable(
            self,
            cvxpy_var: cx.Parameter,
            data: Union[pd.DataFrame, np.ndarray]
    ) -> None:

        if not isinstance(cvxpy_var, cx.Parameter):
            error = "Data can only be assigned to exogenous variables."
            self.logger.error(error)
            raise ValueError(error)

        if isinstance(data, pd.DataFrame):
            cvxpy_var.value = data.values
        elif isinstance(data, np.ndarray):
            cvxpy_var.value = data
        else:
            error = "Supported data formats: pandas DataFrame or a numpy array."
            self.logger.error(error)
            raise ValueError(error)

    def generate_vars_dataframe(
            self,
            variable: Variable,
    ) -> pd.DataFrame:
        """For a Variable object, generates a Pandas DataFrame with the  
        hierarchy structure, the related cvxpy variables and the dictionary to
        filter the sql table for fetching data.
        """

        cvxpy_header = constants._CVXPY_VAR_HEADER
        filter_header = constants._FILTER_DICT_HEADER

        self.logger.debug(
            f"Generating variable '{variable.symbol}' dataframe "
            "(cvxpy object, filter dictionary).")

        var_data = util.unpivot_dict_to_dataframe(
            data_dict=variable.coordinates,
            key_order=variable.sets_parsing_hierarchy.values()
        )

        var_data[cvxpy_header] = None
        var_data[filter_header] = None

        for row in var_data.index:

            var_data.at[row, cvxpy_header] = \
                self.create_cvxpy_variable(
                    type=variable.type,
                    shape=variable.shape_size,
                    name=variable.symbol + str(variable.shape))

            var_filter = {}

            for header in var_data.loc[row].index:

                if header in variable.sets_parsing_hierarchy.values():
                    var_filter[header] = [var_data.loc[row][header]]

                elif header == cvxpy_header:
                    for dim in variable.shape:
                        if isinstance(dim, int):
                            pass
                        elif isinstance(dim, str):
                            dim_header = variable.table_headers[dim][0]
                            var_filter[dim_header] = variable.coordinates[dim_header]

                elif header == filter_header:
                    pass

                else:
                    error = f"Variable 'data' dataframe headers mismatch."
                    self.logger.error(error)
                    raise ValueError(error)

            var_data.at[row, filter_header] = var_filter

        return var_data
