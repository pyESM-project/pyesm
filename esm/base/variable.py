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
        self.type: str = None

        for key, value in kwargs.items():
            setattr(self, key, value)

        self.coordinates_info: Dict[str, Any] = {}
        self.coordinates: Dict[str, Any] = {}
        # self.data: pd.DataFrame = None

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

        Raises:
            ValueError: If the shape format is incorrect or if a variable 
                coordinate is not found.
        """

        shape_size = []

        for item in self.shape:
            if isinstance(item, str):
                if item not in self.coordinates_table_headers.keys():
                    error = f"Variable '{self.symbol}': '{item}' is not " \
                        "a valid variable coordinate."
                    raise ValueError(error)
                coordinate_key = self.coordinates_table_headers[item][0]
                shape_size.append(len(self.coordinates[coordinate_key]))

            elif isinstance(item, int):
                shape_size.append(item)

            else:
                error = "Wrong shape format: valid formats are 'str' or 'int'"
                raise ValueError(error)

        return shape_size

    @property
    def is_square(self) -> bool:
        """Checks if the variable matrix is square.

        Returns:
            bool: True if the variable matrix is square, False otherwise.
        """

        if len(self.shape) != 2:
            return False
        if self.shape[0] == self.shape[1]:
            return True
        else:
            return False

    @property
    def is_vector(self) -> bool:
        """Checks if the variable matrix is a vector.

        Returns:
            bool: True if the variable is a vector, False otherwise.
        """

        return True if len(self.shape) == 1 or 1 in self.shape else False

    @property
    def dim_labels(self) -> List[str]:
        """Retrieves the labels for each dimension of the variable.

        Returns:
            List[str]: A list containing the labels for each dimension.
        """

        return [self.get_dim_label(dim) for dim, _ in enumerate(self.shape)]

    @property
    def dim_items(self) -> List[List[str]]:
        """Retrieves the items for each variable dimension.

        Returns:
            List[List[str]]: A list containing the items for each dimension.
        """

        return [self.get_dim_items(dim) for dim, _ in enumerate(self.shape)]

    def get_dim_label(self, dimension: Literal[0, 1]) -> str | int:
        """Retrieves the label for a specific dimension of the variable.

        Args:
            dimension (Literal[0, 1]): The dimension to retrieve the label for:
                0 -> Rows, 1 -> Columns.

        Returns:
            Union[str, int]: The label for the specified dimension.

        Raises:
            ValueError: If the dimension is not 0 (rows) or 1 (columns).
        """

        if dimension not in [0, 1]:
            raise ValueError("Dimension must be 0 (rows) or 1 (columns).")

        dim_label = self.table_headers.get(
            self.shape[dimension])

        return dim_label[0] if isinstance(dim_label, list) else dim_label

    def get_dim_items(self, dimension: Literal[0, 1]) -> List[str]:
        """Retrieves the items for a specific dimension of the variable.

        Args:
            dimension (Literal[0, 1]): The dimension to retrieve the items for:
                0 -> Rows, 1 -> Columns.

        Returns:
            List[str]: A list containing the items for the specified dimension.

        Raises:
            ValueError: If the dimension is not 0 (rows) or 1 (columns).
        """

        if dimension not in [0, 1]:
            raise ValueError("Dimension must be 0 (rows) or 1 (columns).")

        dim_name = self.shape[dimension]

        if isinstance(dim_name, int):
            return None
        else:
            dim_label = self.table_headers[dim_name][0]
            return self.coordinates[dim_label]

    def none_data_coordinates(self, row: int) -> Dict:
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

        pivoted_data = data.pivot_table(
            index=self.dim_labels[0],
            columns=self.dim_labels[1] or None,
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

        # ADD HERE SPECIAL IDENTITY (define factory function in util module)

        else:
            msg = f"Variable value type '{value_type}' not supported. "
            f"Supported value types: {constants._ALLOWED_CONSTANTS.keys()}"
            self.logger.error(msg)
            raise exc.SettingsError(msg)

        if msg:
            self.logger.error(msg)
            raise exc.ConceptualModelError(msg)
