"""Module defining the DataTable class.

The DataTable class is designed to handle and manipulate data tables. 
DataTable encapsulates all information about data used for defining the numerical
problem. 
"""
from typing import Any, Dict, Iterator, List, Optional, Tuple

import cvxpy as cp
import pandas as pd

from cvxlab.log_exc import exceptions as exc
from cvxlab.log_exc.logger import Logger
from cvxlab.support import util


class DataTable:
    """DataTable class is the basic structure for handling problem data.

    The DataTable embeds all information about data used for defining the numerical
    problem. It includes attributes for storing metadata, set coordinates, basic 
    data properties and information, variables list, as well as methods for handling
    and manipulating the data.

    Attributes:

    - logger (Logger): Logger object for logging information, warnings, and errors.
    - name (str): Name of the data table.
    - description (Optional[str]): Metadata for the data table. Default is None.
    - type (Optional[str | dict]): Type of allowed data defined in Defaults class. 
        Default is None.
    - domain (Optional[str]): Domain of the endogenous variable:
        'integer' for integer variables, 'boolean' for binary {0,1} variables.
        None means continuous (default).
    - coordinates (Optional[list]): List of coordinates that define the data structure. 
        Default is None.
    - variables_info (Optional[Dict[str, Any]]): Dictionary containing information
        about variables. Default is None.
    - coordinates_headers (Dict[str, str]): Dictionary mapping coordinates to 
        their headers. Default is an empty dictionary.
    - coordinates_values (Dict[str, Any]): Dictionary mapping coordinates to 
        their values. Default is an empty dictionary.
    - coordinates_dataframe (Optional[pd.DataFrame]): DataFrame representation 
        of coordinates. Default is None.
    - table_headers (Dict[str, Any]): Dictionary of table headers and their types.
        Default is an empty dictionary.
    - foreign_keys (Dict[str, Any]): Dictionary defining foreign key relationships.
        Default is an empty dictionary.
    - cvxpy_var (Optional[Dict[Any, cp.Variable] | cp.Variable]): CVXPY
        variable associated with endogenous data tables. It can be a single
        variable or a dictionary keyed by sub-problem/scenario. Default is None.
    - variables_list (List[str]): List of variables derived from variables_info. 
        By default, it corresponds to the keys of variables_info.

    """

    def __init__(
            self,
            logger: Logger,
            key_name: str,
            **table_info,
    ):
        """Initialize a new instance of the DataTable class.

        This constructor initializes the DataTable with a logger and various
        attributes that define the data table's properties and structure. 
        Data table information is passed as keyword arguments and set as attributes.
        Attributes are fetched and elaborated using helper methods, then other 
        properties are initialized based on the fetched attributes.

        Args:
            logger (Logger): Logger object for logging operations.
            key_name (str): Name of the data table.
            **table_info: Arbitrary keyword arguments containing data table 
                information.
        """
        self.logger = logger.get_child(__name__)

        self.name: str = key_name
        self.description: Optional[str] = None
        self.type: Optional[str | dict] = None
        self.domain: Optional[str] = None
        self.coordinates: Optional[list] = None
        self.variables_info: Optional[Dict[str, Any]] = None

        self.fetch_attributes(table_info)

        self.coordinates_headers: Dict[str, str] = {}
        self.coordinates_values: Dict[str, Any] = {}
        self.coordinates_dataframe: Optional[dict | pd.DataFrame] = None
        self.table_headers: Dict[str, Any] = {}
        self.foreign_keys: Dict[str, Any] = {}
        self.cvxpy_var: Optional[
            Dict[Any, cp.Variable] | cp.Variable] = None

        self.variables_list: List[str] = list(self.variables_info.keys())

    @property
    def table_length(self) -> int:
        """Return the number of rows in the coordinates dataframe/s.

        This property looks the coordinates_dataframe attribute and returns the number
        of rows it contains. If the coordinates_dataframe is a dictionary of
        DataFrames, it returns the number of rows in the first DataFrame found.
        The DataFrame rows correspond to the number of entries in the data table
        related to a combination of inter-problem sets.

        Returns:
            int: The number of rows in the coordinates_dataframe, corresponding 
                to the number of entries in data table related to a combination 
                of inter-problem sets.

        Raises:
            MissingDataError: If the coordinates dataframe has not initialized.
            TypeError: If the coordinates dataframe is neither a DataFrame nor
                a dictionary of DataFrames.
        """
        if self.coordinates_dataframe is None:
            msg = f"Data table '{self.name}' | Coordinates dataframe not defined."
            self.logger.error(msg)
            raise exc.MissingDataError(msg)

        if isinstance(self.coordinates_dataframe, pd.DataFrame):
            return len(self.coordinates_dataframe)

        elif isinstance(self.coordinates_dataframe, dict):
            first_key = next(iter(self.coordinates_dataframe))
            return len(self.coordinates_dataframe[first_key])

        else:
            msg = f"Data table '{self.name}' | Coordinates dataframe must be a " \
                "DataFrame or a dictionary of DataFrames."
            self.logger.error(msg)
            raise TypeError(msg)

    def fetch_attributes(self, table_info: Dict[str, Any]) -> None:
        """Fetch and set attributes from the provided table information.

        This method iterates over the provided dictionary of table information
        and sets the corresponding attributes of the DataTable instance if they
        are not None.
        If the 'coordinates' attribute is provided as a string, it is converted 
        to a list containing that string.

        Args:
            table_info (Dict[str, Any]): Dictionary with data-table attributes
                loaded from model settings.
        """
        for key, value in table_info.items():
            if value is not None:
                setattr(self, key, value)

        if self.coordinates:
            if isinstance(self.coordinates, str):
                self.coordinates = [self.coordinates]

    def generate_coordinates_dataframes(
            self,
            sets_split_problems: Optional[Dict[str, str]] = None
    ) -> None:
        """Generate data structure for data tables.

        This method generates the 'coordianates_dataframe' for the data table,
        based on 'coordinates' and 'coordinates_values' attributes.
        If the data table is defined for zero or one intra-problem set, a dataframe
        is generated. In case more than one intra-problem set (i.e. 'sets_split_problems' 
        is provided), a dictionary of dataframes is generated, each corresponding 
        to a combination of inter-problem sets. 
        Before generating the dataframes, the method checks if all the intra-problem
        sets are defined as data table coordinates.

        Args:
            sets_split_problems (Optional[Dict[str, str]], optional): A dictionary 
                of keys to filter the coordinates values. Defaults to None.

        Raises:
            MissingDataError: If 'self.coordinates' or 'self.coordinates_values' 
                are not defined.
            SettingsError: If any of the intra-problem sets are not defined
                as data table coordinates.
            TypeError: If 'self.coordinates_values' is not a dictionary.
        """
        if not self.coordinates or not self.coordinates_values:
            msg = "Coordinates and related values must be defined for " \
                f"data table '{self.name}'."
            self.logger.error(msg)
            raise exc.MissingDataError(msg)

        if not isinstance(self.coordinates_values, dict):
            msg = "Coordinates values must be a dictionary."
            self.logger.error(msg)
            raise TypeError(msg)

        coordinates_df = util.unpivot_dict_to_dataframe(
            self.coordinates_values
        )

        if not sets_split_problems:
            self.coordinates_dataframe = coordinates_df

        else:
            # sets_split_problems must be in the coordinates_values keys
            missing_coords = set(sets_split_problems) - set(self.coordinates)
            if missing_coords:
                msg = f"Data table '{self.name}' | The following inter-problem " \
                    "sets coordinates not defined as data table coordinates: " \
                    f"{missing_coords}"
                self.logger.error(msg)
                raise exc.SettingsError(msg)

            coords_split_problems = {
                key: value
                for key, value in self.coordinates_values.items()
                if key in sets_split_problems.values()
            }
            coords_split_problems_df = util.unpivot_dict_to_dataframe(
                coords_split_problems
            )

            coordinates_dataframe_dict = {}

            for set_split_problem in coords_split_problems_df.index:
                coords_filter: pd.Series = \
                    coords_split_problems_df.loc[set_split_problem]
                coords_filter_df = coords_filter.to_frame().T

                coordinates_dataframe_dict[set_split_problem] = pd.merge(
                    left=coords_filter_df,
                    right=coordinates_df,
                    on=coords_filter_df.columns.tolist(),
                )

            self.coordinates_dataframe = coordinates_dataframe_dict

    def __repr__(self) -> str:
        """Return a string representation of the DataTable instance."""
        avoid_representation = ('logger', 'data', 'coordinates_dataframe')
        output = ''
        for key, value in self.__dict__.items():
            if key in avoid_representation:
                continue
            output += f'\n{key}: {value}'
        return output

    def __iter__(self) -> Iterator[Tuple[Any, Any]]:
        """Iterate over the attributes of the DataTable instance."""
        avoid_iteration = ('logger', 'data', 'coordinates_dataframe')
        for key, value in self.__dict__.items():
            if key in avoid_iteration:
                continue
            yield key, value
