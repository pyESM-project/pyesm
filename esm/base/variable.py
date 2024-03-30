from typing import Any, Dict, Iterator, List, Literal, Tuple
import numpy as np

import pandas as pd
from esm import constants
from esm.log_exc import exceptions as exc
from esm.log_exc.logger import Logger
from esm.support import util


class Variable:
    """
    tbd
    """

    def __init__(
            self,
            logger: Logger,
            **kwargs,
    ) -> None:

        self.logger = logger.getChild(__name__)

        self.rows: Dict[str, Any] = {}
        self.cols: Dict[str, Any] = {}
        self.value: str = None
        self.related_table: str = None
        self.related_dims_map: pd.DataFrame = None
        self.type: str = None

        for key, value in kwargs.items():
            setattr(self, key, value)

        self.coordinates_info: Dict[str, Any] = {}
        self.coordinates: Dict[str, Any] = {}
        self.data: pd.DataFrame = None

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

    @property
    def shape(self) -> List[str | int]:
        rows_shape = self.rows['set'] if 'set' in self.rows else 1
        cols_shape = self.cols['set'] if 'set' in self.cols else 1
        return [rows_shape, cols_shape]

    @property
    def shape_size(self) -> List[int]:
        """Computes and returns the size of each dimension in the variable.

        Returns:
            List[int]: A list containing the size of each dimension in 
                the shape.
        """
        shape_size = []

        for dimension in ['rows', 'cols']:
            if self.coordinates[dimension]:
                shape_size.append(len(*self.coordinates[dimension].values()))
            else:
                shape_size.append(1)

        return shape_size

    @property
    def dim_labels(self) -> List[str]:
        """Retrieves the labels for each dimension of the variable.

        Returns:
            List[str]: A list containing the labels for each dimension.
        """
        dim_labels = []

        for dimension in ['rows', 'cols']:
            if self.coordinates_info[dimension]:
                dim_labels.append(
                    list(self.coordinates_info[dimension].values())[0])
            else:
                dim_labels.append(None)

        return dim_labels

    @property
    def dim_items(self) -> List[List[str]]:
        """Retrieves the items for each variable dimension.

        Returns:
            List[List[str]]: A list containing the items for each dimension.
        """
        dim_items = []

        for dimension in ['rows', 'cols']:
            if self.coordinates[dimension]:
                dim_items.append(
                    list(*self.coordinates[dimension].values()))
            else:
                dim_items.append(None)

        return dim_items

    @property
    def dims_sets(self) -> Dict[str, str]:
        """Get the sets names corresponding to the rows and cols dimension of
        the variable. If a dimension has not a corrsponding set, it returns
        None as a value of the resulting dictionary.

        Returns:
            Dict[str]: A dictionary containing dimension name as keys and 
                corresponding set name as values.
        """
        dims_sets = {}

        for dim in ['rows', 'cols']:
            if dim in self.coordinates_info:
                dim_set: dict = self.coordinates_info[dim]

                if dim_set:
                    dims_sets[dim] = next(iter(dim_set.keys()), None)
                else:
                    dims_sets[dim] = None

        return dims_sets

    @property
    def is_square(self) -> bool:
        """Checks if the variable matrix is square.

        Returns:
            bool: True if the variable matrix is square, False otherwise.
        """

        if len(self.shape) != 2:
            return False
        if self.shape_size[0] == self.shape_size[1]:
            return True
        else:
            return False

    @property
    def is_vector(self) -> bool:
        """Checks if the variable matrix is a vector.

        Returns:
            bool: True if the variable is a vector, False otherwise.
        """

        if len(self.shape_size) == 1 or 1 in self.shape_size:
            return True
        else:
            return False

    @property
    def sets_parsing_hierarchy(self) -> Dict[str, str]:
        return {
            **self.coordinates_info['intra'],
            **self.coordinates_info['inter'],
        }

    @property
    def sets_parsing_hierarchy_values(self) -> Dict[str, str]:
        return {
            **self.coordinates['intra'],
            **self.coordinates['inter'],
        }

    def none_data_coordinates(self, row: int) -> Dict[str, Any]:
        """Checks if there are None data values in cvxpy variables and returns
        the related coordinates (row in Variable.data and related hierarchy 
        coordinates).

        Args:
            row (int): identifies the row of Variable.data item (i.e. one 
            specific cvxpy variable).

        Returns:
            Dict: 
                keys: are rows where cvxpy variables values are None.
                values: the names of the sets that identify the variable.

        Raises:
            KeyError: in case passed row is less than zero or exceeds number of
                rows of variable.data.
        """
        cvxpy_var_header = constants._CVXPY_VAR_HEADER
        data_table = self.data[cvxpy_var_header]

        if row < 0 or row > len(data_table):
            msg = f"Passed row number must be between 0 and the rows of " \
                f"variable table '{self.symbol}' ({len(data_table)})."
            self.logger.error(msg)
            raise KeyError(msg)

        if data_table[row].value is None:
            return {
                key: self.data.loc[row, value]
                for key, value in self.sets_parsing_hierarchy.items()
            }

        return None

    def reshaping_sqlite_table_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """It takes a dataframe with data fetched from SQLite database variable
        table, in the form of a Pandas DataFrame, and elaborate it to get 
        the shape required by the cvxpy variable (two-dimensions matrix).

        Args:
            data (pd.DataFrame): data filtered from the SQLite variable table,
            related to a unique cvxpy variable.

        Returns:
            pd.DataFrame: data reshaped and pivoted to be used as cvxpy values.
        """
        values_header = constants._STD_VALUES_FIELD['values'][0]

        # case of a scalar with no rows/cols labels (scalars)
        if all(item is None for item in self.dim_labels):
            index = ''
            columns = None

        # all other variables with rows/cols labels (scalars, vectors/matrices)
        else:
            index = self.dim_labels[0]
            columns = self.dim_labels[1]

        pivoted_data = data.pivot_table(
            index=index,
            columns=columns,
            values=values_header,
            aggfunc='first'
        )

        pivoted_data = pivoted_data.reindex(
            index=self.dim_items[0],
            columns=self.dim_items[1]
        )

        return pivoted_data

    def reshaping_variable_data(self, row: int) -> pd.DataFrame:
        """Takes values in a cvxpy variable identified by a row in 
        Variable.data, then pivots and adjust it to return data in the same 
        shape of SQLite database variable (except for the 'id' column).

        Args:
            row (int): identifies the row of Variable.data item (i.e. one 
            specific cvxpy variable).

        Returns:
            pd.DataFrame: data variable shaped as the variable SQLite table.
        """

        values_header = constants._STD_VALUES_FIELD['values'][0]
        cvxpy_var_header = constants._CVXPY_VAR_HEADER

        unpivoted_data = pd.DataFrame(
            data=self.data[cvxpy_var_header][row].value,
            index=self.dim_items[0],
            columns=self.dim_items[1],
        ).stack().reset_index()

        unpivoted_data.columns = [*self.dim_labels, values_header]

        columns_to_drop = [
            col for col in unpivoted_data.columns if col == None]

        unpivoted_data = unpivoted_data.drop(
            columns=columns_to_drop,
            errors='ignore'
        )

        completion_data = self.data.loc[
            row, self.sets_parsing_hierarchy.values()]

        tabled_data = util.merge_series_to_dataframe(
            series=completion_data,
            dataframe=unpivoted_data
        )

        return tabled_data

    def define_constant(
            self,
            value_type: str,
    ) -> int | np.ndarray | np.matrix:
        """Defines a constant of a specific type. This method validates the 
        provided value type against a set of allowed values. Depending on the 
        value type, it either creates a variable type or raises an error if 
        the value type is not supported.

        Constants allowed:
            - 'identity': identity matrix.
            - 'sum_vector': summation vector (vector of 1s).
            - 'lower_triangular': lower triangular matrix of 1s(inc. diagonal)
            - 'identity_rcot': special identity matrix for rcot problems

        Parameters:
        value_type (str): The type of the constant to be created. 

        Returns:
        int | np.ndarray | np.matrix: The created constant. It could be 
            an integer, a numpy array, or a numpy matrix.

        Raises:
            - exc.SettingsError: If the provided value type is not supported.
            - exc.ConceptualModelError: If the shape of the variable is not 
                suitable for creating the constant.
        """

        util.validate_selection(
            valid_selections=constants._ALLOWED_CONSTANTS.keys(),
            selection=value_type,
        )

        factory_function, *args = constants._ALLOWED_CONSTANTS[value_type]

        if value_type == 'identity':
            if self.is_square:
                return factory_function(self.shape_size[0])
            else:
                msg = 'Identity matrix must be square. Check variable shape.'

        elif value_type == 'sum_vector':
            if self.is_vector:
                return factory_function(self.shape_size)
            else:
                msg = 'Summation vector must be a vector (one dimension). ' \
                    'Check variable shape.'

        elif value_type == 'lower_triangular':
            if self.is_square:
                return factory_function(self.shape_size[0])
            else:
                msg = 'Lower triangular matrix must be square. ' \
                    'Check variable shape.'

        elif value_type == 'identity_rcot':
            if self.related_dims_map is not None and \
                    not self.related_dims_map.empty:
                return factory_function(self.related_dims_map)
            else:
                msg = 'Identity_rcot matrix supported only for variables ' \
                    'with dimensions defined by the same set, or when one set ' \
                    'is defined by items defined as aggregation of items of ' \
                    'another set.'

        else:
            msg = f"Variable 'value': '{value_type}' not supported. " \
                f"Supported value types: {constants._ALLOWED_CONSTANTS.keys()}"
            self.logger.error(msg)
            raise exc.SettingsError(msg)

        if msg:
            self.logger.error(msg)
            raise exc.ConceptualModelError(msg)
