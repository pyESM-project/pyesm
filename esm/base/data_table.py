"""
data_table.py 

@author: Matteo V. Rocco
@institution: Politecnico di Milano

This module provides the DataTable class which is designed to handle and 
manipulate data tables within the package. DataTable encapsulates the data 
storage and transformation functionalities required for complex data operations, 
including handling of CVXPY variables for optimization problems, dynamic data 
structures for coordinates, and integration with pandas for data manipulation.

DataTable is instrumental in structuring and interfacing data for use in 
mathematical models and data analysis within the application.
"""
from typing import Any, Dict, Iterator, List, Optional, Tuple

import cvxpy as cp
import pandas as pd

from esm.log_exc import exceptions as exc
from esm.log_exc.logger import Logger
from esm.support import util


class DataTable:
    """
    A class for managing and interfacing table data for analysis and modeling 
    within the application.

    Attributes:
        logger (Logger): Logger object for logging information, warnings, and errors.
        name (Optional[str]): Name of the data table.
        type (Optional[str]): Type of data table (e.g., 'endogenous', 'exogenous').
        coordinates (List[str]): List of coordinates that define the data structure.
        coordinates_headers (Dict[str, str]): Dictionary mapping coordinates to 
            their headers.
        coordinates_values (Dict[str, Any]): Dictionary mapping coordinates to 
            their values.
        coordinates_dataframe (Optional[pd.DataFrame]): DataFrame representation 
            of coordinates.
        table_headers (Dict[str, Any]): Dictionary of table headers and their types.
        variables_info (Dict[str, Any]): Dictionary containing information about 
            variables.
        foreign_keys (Dict[str, Any]): Dictionary defining foreign key relationships.
        cvxpy_var (Optional[cp.Variable | cp.Parameter | cp.Constant]): CVXPY 
            variable associated with the data table for optimization modeling.
        variables_list (List[str]): List of variables derived from variables_info.

    Methods:
        table_length: Property that returns the number of rows in the 
            coordinates dataframe.
        generate_coordinates_dataframe: Generates a dataframe from coordinates 
            values.
    """

    def __init__(
            self,
            logger: Logger,
            **kwargs,
    ) -> None:
        """
        Initializes a new instance of the DataTable class.

        Args:
            logger (Logger): Logger object for logging operations.
            **kwargs: Arbitrary keyword arguments that can set any attribute 
                of the class.
        """
        self.logger = logger.getChild(__name__)

        self.name: Optional[str] = None
        self.type: Optional[str] = None
        self.coordinates: List[str] = []
        self.coordinates_headers: Dict[str, str] = {}
        self.coordinates_values: Dict[str, Any] = {}
        self.coordinates_dataframe: Optional[pd.DataFrame] = None
        self.table_headers: Dict[str, Any] = {}
        self.variables_info: Dict[str, Any] = {}
        self.foreign_keys: Dict[str, Any] = {}
        self.cvxpy_var: Optional[
            cp.Variable | cp.Parameter | cp.Constant] = None

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
        """
        Returns the number of rows in the coordinates dataframe.

        Returns:
            int: The number of rows in the dataframe.

        Raises:
            MissingDataError: If the coordinates dataframe is not initialized.
        """
        if self.coordinates_dataframe is not None:
            return len(self.coordinates_dataframe)
        else:
            msg = f"Lenght of data table '{self.name}' unknown."
            self.logger.error(msg)
            raise exc.MissingDataError(msg)

    def generate_coordinates_dataframe(self) -> None:
        """
        Generates a pandas DataFrame from the coordinates values. This
        method requires that coordinates be predefined.

        Raises:
            MissingDataError: If coordinates are not defined.
        """
        if self.coordinates:
            self.coordinates_dataframe = util.unpivot_dict_to_dataframe(
                self.coordinates_values
            )
        else:
            msg = f"Coordinates must be defined for data table '{self.name}'."
            self.logger.error(msg)
            raise exc.MissingDataError(msg)
