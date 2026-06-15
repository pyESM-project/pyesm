"""Module defining the Variable class.

The Variable class manages the characteristics and behaviors of variables used 
in optimization models. It facilitates operations such as defining constants, 
reshaping data, and interfacing with SQL database tables for data manipulation.
The class incorporates functionality to handle complex variable structures 
that may include dimensions, mapping of related tables, and operations that 
convert SQL data to formats usable by optimization tools like cvxpy.
"""
from typing import Any, Dict, Iterator, List, Optional, Tuple

import cvxpy as cp
import pandas as pd

from cvxlab.defaults import Defaults
from cvxlab.log_exc import exceptions as exc
from cvxlab.log_exc.logger import Logger
from cvxlab.support import util


class Variable:
    """Manages the operations of variables used in optimization models.

    Attributes:

    - logger (Logger): Logger object for logging information, warnings, and errors.
    - symbol (Optional[str]): The symbolic name of the variable.
    - type (Optional[str]): The type of the variable (available types defined 
        in Defaults.SymbolicDefinitions.VARIABLE_TYPES).
    - rows (Dict[str, Any]): Information about the rows dimension of the variable.
    - cols (Dict[str, Any]): Information about the columns dimension of the variable.
    - value (Optional[str]): Value type of the variable, only defined in case 
        of Defaults (e.g. identity matrix, ...).
    - blank_fill (Optional[float]): Value to fill in case of missing data. Only 
        defined for exogenous variables, reducing effort in inserting numerical 
        data by the user.
    - uncertainty_measure (Optional[str | bool]): Uncertainty measure metadata
        associated with the variable, if any.
    - related_table (Optional[str]): The database table that collect the subset
        numerical data associated to the variable.
    - var_info (Optional[Dict[str, Any]]): Raw information about the variable
        fetched from the model setup file/s.
    - coordinates_info (Dict[str, Any]): Maps the basic information about the 
        variable coordinates, including sets defining variable shapes (rows, cols), 
        inter-problem and intra-problem dimensions. Basic information includes
        the set names and the related database table headers.
    - coordinates (Dict[str, Any]): Mapping specific coordinates values to the 
        corresponding variable dimensions (rows, cols), inter-problem and
        intra-problem sets, including set key and related values.
    - data (Optional[pd.DataFrame]): Defines dataframe (or a dictionary of 
        dataframes in case the variable is of multiple types) identifying 
        information about data associated to the variable. Specifically, the 
        dataframe includes the number of scenarios (linear combination of 
        inter-problem sets, if any), the cvxpy variables, the associated filters
        (identifying the related variable data in data tables), and the key of
        the related numerical problem.

    """

    def __init__(
            self,
            logger: Logger,
            **variable_info,
    ):
        """Initialize a new instance of the Variable class.

        This constructor initializes a Variable object with various attributes
        that define its properties and behavior provided by the 'variable_info'
        dictionary. Such attributes are fetched and rearranged based on the 
        'fetch_attributes' and 'rearrange_var_info' methods.

        Args:
            logger (Logger): Logger object for logging operations within the class.
            **variable_info: Keyword arguments defining variable features.
        """
        self.logger = logger.get_child(__name__)

        self.symbol: Optional[str] = None
        self.type: Optional[str] = None
        self.rows: Dict[str, Any] = {}
        self.cols: Dict[str, Any] = {}
        self.value: Optional[str] = None
        self.blank_fill: Optional[float] = None
        self.uncertainty_measure: Optional[bool] = False
        self.related_table: Optional[str] = None
        self.var_info: Optional[Dict[str, Any]] = None
        self.nonneg: Optional[bool] = False

        self.fetch_attributes(variable_info)
        self.rearrange_var_info()

        self.coordinates_info: Dict[str, Any] = {}
        self.coordinates: Dict[str, Any] = {}
        self.data: Optional[pd.DataFrame | dict] = None

    def fetch_attributes(self, variable_info: Dict[str, Any]) -> None:
        """Fetch and set attributes from the provided variable information.

        This method iterates over the provided dictionary of variable attributes
        and sets the corresponding attributes of the Variable instance if they
        are not None. This method is called upon initialization of the Variable class.

        Args:
            variable_info (Dict[str, Any]): Dictionary containing variable attributes.
        """
        for key, value in variable_info.items():
            if value is not None:
                setattr(self, key, value)

    def rearrange_var_info(self) -> None:
        """Rearrange the raw information provided by var_info.

        This method takes the raw variable attributes and rearrange the information
        in the variable instance attributes. This method is called upon initialization 
        of the Variable class.
        """
        value_key = Defaults.Labels.VALUE_KEY
        blank_fill_key = Defaults.Labels.BLANK_FILL_KEY
        filter_key = Defaults.Labels.FILTERS
        set_key = Defaults.Labels.SET
        dim_key = Defaults.Labels.DIM
        sign_key = Defaults.Labels.NONNEG_KEY
        uncertainty_measure_key = Defaults.UncertaintySettings.UNCERTAINTY_MEASURE_KEY
        dimensions = Defaults.SymbolicDefinitions.DIMENSIONS

        if self.var_info is None:
            return

        self.value = self.var_info.get(value_key, None)
        self.blank_fill = self.var_info.get(blank_fill_key, None)
        self.nonneg = self.var_info.get(sign_key, False)
        self.uncertainty_measure = self.var_info.get(
            uncertainty_measure_key,
            None,
        )

        # get rows and cols information
        for dimension in [dimensions['ROWS'], dimensions['COLS']]:
            shape_set = util.fetch_dict_primary_key(
                dictionary=self.var_info,
                second_level_key=dim_key,
                second_level_value=dimension,
            )

            if not shape_set:
                continue

            dim_info = []

            # multiple sets may define each dimension
            for shape in shape_set:
                dim_info_data: dict = self.var_info.get(shape, None)
                dim_info.append({
                    set_key: shape,
                    filter_key: dim_info_data.get(filter_key, None),
                })

            if dimension == dimensions['ROWS']:
                self.rows = dim_info
            elif dimension == dimensions['COLS']:
                self.cols = dim_info

    def _get_variable_shape(self, dimension_data: List[Dict[str, Any]]) -> str:
        """Extract compound set keys from dimension data.

        Args:
            dimension_data (List[Dict[str, Any]]): List of dictionaries containing
                set information for a dimension.

        Returns:
            Union[str, int]: Compound set key joined with ' | ' separator, or 1 
                if dimension is empty/undefined.
        """
        set_key = Defaults.Labels.SET

        if isinstance(dimension_data, list) and len(dimension_data) > 0:
            sets = [
                dim.get(set_key)
                for dim in dimension_data
                if dim.get(set_key)
            ]
            if len(sets) >= 1:
                return sets
            else:
                return 1
        return 1

    @property
    def shape_sets(self) -> List[str | int]:
        """Return the sets defining the shape of the variable (rows, cols).

        Returns:
            List[Union[str, int]]: A list containing set identifiers or 
                rows and cols of the variable. In case of multiple sets defining
                a dimension, the sets are returned as a list. If a dimension is
                not defined, it returns 1.
        """
        if self.rows is None and self.cols is None:
            return []

        rows_shape = self._get_variable_shape(self.rows)
        cols_shape = self._get_variable_shape(self.cols)
        return [rows_shape, cols_shape]

    @property
    def intra_sets(self) -> List[str]:
        """Return a list of intra-problem sets of the variable.

        Returns:
            List[str]: A list containing the intra-problem sets keys.
        """
        intra_dim_key = Defaults.SymbolicDefinitions.DIMENSIONS['INTRA']
        intra_dim_dict: dict = self.coordinates_info.get(intra_dim_key, None)

        if intra_dim_dict is None:
            return []

        return list(intra_dim_dict.keys())

    @property
    def shape_size(self) -> List[int]:
        """Return the rows-cols dimension size of the variable.

        Computes and returns the size of each dimension in the variable. 
        For compound dimensions (multiple sets), the size is the Cartesian product
        of all set lengths in that dimension.
        This is useful for determining the dimensionality of the data associated 
        with the variable. If a dimension is not defined, it is considered to have
        a size of 1.

        Returns:
            Tuple[int]: A tuple containing the size of each dimension.
        """
        dimensions = Defaults.SymbolicDefinitions.DIMENSIONS

        if not self.coordinates:
            return []

        shape_size = []

        for dimension in [dimensions['ROWS'], dimensions['COLS']]:
            if self.coordinates[dimension]:
                coord_length = util.dict_values_cartesian_product(
                    self.coordinates[dimension]
                )
                shape_size.append(coord_length)
            else:
                shape_size.append(1)

        return shape_size

    @property
    def dims_labels(self) -> List[str | List[str] | None]:
        """Return the tables headers defining the variable dimensions.

        This property retrieves the name labels for each dimension of the variable, 
        typically used for identifying matrix dimensions.

        Returns:
            List[Union[str, List[str], None]]: A list containing labels for each 
                dimension of the variable. Single-label dimensions return a string,
                multi-label dimensions return a list of strings, undefined dimensions
                return None.
        """
        dimensions = Defaults.SymbolicDefinitions.DIMENSIONS
        dims_labels = []

        for dim in [dimensions['ROWS'], dimensions['COLS']]:
            if self.coordinates_info.get(dim):
                dims_labels.append(
                    list(self.coordinates_info[dim].values())
                )
            else:
                dims_labels.append(None)

        return dims_labels

    @property
    def dims_items(self) -> List[Optional[List[str]]]:
        """Return the list of items in each dimension of the variable.

        This property retrieves the items for each dimension of the variable 
        (rows, cols), returning a list of two lists including them.

        Returns:
            List[List[str]]: Lists of items for each dimension.
        """
        dimensions = Defaults.SymbolicDefinitions.DIMENSIONS
        dims_items = []

        for dim in [dimensions['ROWS'], dimensions['COLS']]:
            if self.coordinates.get(dim):
                dims_items.append(list(self.coordinates[dim].values()))
            else:
                dims_items.append(None)

        return dims_items

    @property
    def is_square(self) -> bool:
        """Return True if the variable matrix is square.

        Returns:
            bool: True if the variable matrix is square, False otherwise.
        """
        if len(self.shape_sets) != 2:
            return False

        if len(self.shape_size) == 2 and \
                self.shape_size[0] == self.shape_size[1]:
            return True
        else:
            return False

    @property
    def is_vector(self) -> bool:
        """Return True if the variable is a vector.

        Returns:
            bool: True if the variable is a vector, False otherwise.
        """
        if len(self.shape_size) == 1 or 1 in self.shape_size:
            return True
        return False

    @property
    def sets_parsing_hierarchy(self) -> Dict[str, str]:
        """Return a dictionary representing the hierarchy of variable dimensions.

        Retrieves the hierarchical structure of sets parsing for the variable,
        specifically related to inter-problem and intra-problem sets.

        Returns:
            Dict[str, str]: Dictionary representing the hierarchy of sets parsing.
        """
        dimensions = Defaults.SymbolicDefinitions.DIMENSIONS

        if not self.coordinates_info:
            self.logger.warning(
                f"Coordinates_info not defined for variable '{self.symbol}'.")
            return []

        return {
            **self.coordinates_info[dimensions['INTER']],
            **self.coordinates_info[dimensions['INTRA']],
        }

    @property
    def sets_parsing_hierarchy_values(self) -> Dict[str, str]:
        """Return a dictionary representing the hierarchy of variable dimensions with items.

        Retrieves the hierarchical structure of sets parsing for the variable,
        specifically related to inter-problem and intra-problem sets. Reports the
        actual items of the sets, instead of the set names.

        Returns:
            Dict[str, str]: Dictionary with parsing hierarchy keys and the related
                list of items as values.
        """
        dimensions = Defaults.SymbolicDefinitions.DIMENSIONS

        if not self.coordinates_info:
            self.logger.warning(
                f"Coordinates_info not defined for variable '{self.symbol}'.")
            return []

        return {
            **self.coordinates[dimensions['INTRA']],
            **self.coordinates[dimensions['INTER']],
        }

    @property
    def all_coordinates(self) -> Dict[str, List[str] | None]:
        """Return a dictionary of all coordinates key-values related to the variable.

        The property returns a dictionary with keys as set keys and values the 
        related set items, for all dimensions of the variable. 
        In case a variable has the same coordinates in different dimensions, 
        only one of them is reported. This occurs in case a variable has rows and
        columns defined by the same set.

        Returns:
            Dict[str, List[str] | None]: Dictionary containing coordinates keys
                and related items.
        """
        if not self.coordinates_info:
            self.logger.warning(
                f"Coordinates not defined for variable '{self.symbol}'.")
            return []

        all_coordinates = {}
        for coordinates in self.coordinates.values():
            all_coordinates.update(coordinates)
        return all_coordinates

    @property
    def all_coordinates_w_headers(self) -> Dict[str, List[str] | None]:
        """Return a dictionary of all coordinates headers-values related to the variable.

        The property returns a dictionary with keys as set name headers and values 
        the related set items, for all dimensions of the variable. 
        In case a variable has the same coordinates in different dimensions, 
        only one of them is reported. This occurs in case a variable has rows and
        columns defined by the same set.

        Returns:
            Dict[str, List[str] | None]: Dictionary containing coordinates name
                headers and and related items as values.
        """
        if not self.coordinates_info:
            self.logger.warning(
                f"Coordinates not defined for variable '{self.symbol}'.")
            return []

        if not self.coordinates:
            self.logger.warning(
                f"Coordinates not defined for variable '{self.symbol}'.")
            return []

        all_coords_w_headers = {}
        for category in Defaults.SymbolicDefinitions.DIMENSIONS.values():
            coords_info = self.coordinates_info.get(category, {})
            coords = self.coordinates.get(category, {})

            for key, table_header in coords_info.items():
                table_values = coords.get(key, [])

                if table_header in all_coords_w_headers:
                    all_coords_w_headers[table_header].extend(table_values)
                else:
                    all_coords_w_headers[table_header] = table_values

        # remove duplicates
        for key in all_coords_w_headers:
            all_coords_w_headers[key] = list(
                dict.fromkeys(all_coords_w_headers[key])
            )

        return all_coords_w_headers

    def none_data_coordinates(self, row: int) -> Dict[str, Any] | None:
        """Return coordinates of None data values in cvxpy variables.

        This method checks if there are None data values in the cvxpy variables 
        and returns the related coordinates (rows in Variable.data and related 
        hierarchy coordinates).

        Args:
            row (int): Identifies the row of Variable.data item (i.e., one 
                specific cvxpy variable).

        Returns:
            Optional[Dict[str, Any]]: Dictionary with keys being the rows where 
                cvxpy variable values are None and values being the names of 
                the sets that identify the variable. Returns None if all data 
                is present.

        Raises:
            ValueError: If the data attribute is not initialized correctly or
                the cxvpy variable header is missing.
            KeyError: If the passed row number is out of bounds.
        """
        cvxpy_var_header = Defaults.Labels.CVXPY_VAR

        if self.data is None \
                or not isinstance(self.data, pd.DataFrame) \
                or cvxpy_var_header not in self.data.columns:
            msg = "Data is not initialized correctly or CVXPY variable header is missing."
            self.logger.error(msg)
            raise ValueError(msg)

        if row < 0 or row > len(self.data):
            msg = f"Passed row number out of bound for variable " \
                f"table '{self.related_table}'. Valid rows between " \
                f"0 and {len(self.data)}."
            self.logger.error(msg)
            raise KeyError(msg)

        cvxpy_var: cp.Variable | cp.Parameter | cp.Constant = \
            self.data.at[row, cvxpy_var_header]

        if cvxpy_var.value is None:
            return {
                key: self.data.loc[row, value]
                for key, value in self.sets_parsing_hierarchy.items()
            }

        return None

    @staticmethod
    def build_axis(
        target_labels: List[str] | None,
        target_items: List[List[str]] | None,
    ) -> pd.Index | pd.MultiIndex | None:
        """Build a pandas Index or MultiIndex from labels/items.

        Args:
            target_labels: List of dimension labels (single or multiple) or None.
            target_items: List of lists of items matching labels, or None.

        Returns:
            pd.Index | pd.MultiIndex | None: Constructed index; None if insufficient data.
        """
        if not target_labels or not target_items:
            return None

        # Multi-level
        if len(target_labels) > 1:
            levels = [list(lvl) for lvl in target_items]
            idx = pd.MultiIndex.from_product(levels, names=target_labels)
            # enforce str type on each level
            idx = idx.set_levels([lvl.map(str) for lvl in idx.levels])
            return idx

        # Single level
        items = target_items[0]
        idx = pd.Index(items, name=target_labels[0])
        return idx.map(str)

    def reshaping_normalized_table_data(
            self,
            data: pd.DataFrame,
            var_key: str | None = None,
    ) -> pd.DataFrame:
        """Reshape normalized table data to match cvxpy variable shape.

        This method takes a Dataframe with data fetched from SQLite database variable
        table as a normalized table, and elaborate it to get the shape required by 
        the cvxpy variable (two-dimensions matrix).

        Args:
            data (pd.DataFrame): data filtered from the SQLite variable table,
                related to a unique cvxpy variable.
            var_key (Optional[str]): The variable key for logging purposes.

        Returns:
            pd.DataFrame: data reshaped and pivoted to be used as cvxpy values.
        """
        values_header = Defaults.Labels.VALUES_FIELD['values'][0]

        index_label, columns_label = self.dims_labels
        index_items, columns_items = self.dims_items

        # Case of a scalar with no rows/cols labels (scalars)
        if all(item is None for item in self.dims_labels):
            index_label = ''

        # Pivot the data to reshape it according to variable dimensions
        pivoted_data = data.pivot_table(
            index=index_label,
            columns=columns_label,
            values=values_header,
            aggfunc='first'
        )

        # Build target index and columns
        target_index = self.build_axis(index_label, index_items)
        target_columns = self.build_axis(columns_label, columns_items)

        # Reindex to ensure the correct order of the data
        pivoted_data = pivoted_data.reindex(
            index=target_index,
            columns=target_columns,
        )

        if pivoted_data.isna().any().any():
            msg = (
                "Reshaping variable data failed | "
                f"Variable '{var_key}' | NaN values after pivot/reindex."
                if var_key else
                "Reshaping variable data failed | NaN values after pivot/reindex."
            )
            self.logger.error(msg)
            raise exc.OperationalError(msg)

        return pivoted_data

    def define_constant(self, value_type: str) -> None:
        """Define values of a constant of a specific user-defined types.

        This method validates the provided value type against a set of allowed 
        values. Depending on the value type, the method either creates a constant 
        of the specified type or raises an error if the value type is not supported.

        NOTICE THAT the constant creation receives as argument the variable shape 
        size only. More complex constants may require additional arguments, which can be 
        added in future developments.

        Args:
            value_type (str): The type of the constant to be created. User-defined 
            constants are defined in util_constants module and registered in
            Defaults.SymbolicDefinitions.ALLOWED_CONSTANTS.

        Raises:
            exc.SettingsError: If the provided value type is not supported.
        """
        allowed_constants = Defaults.SymbolicDefinitions.ALLOWED_CONSTANTS

        if value_type not in allowed_constants:
            msg = f"Constant definition | type: '{value_type}' not supported. " \
                f"Supported value types: {allowed_constants.keys()}"
            self.logger.error(msg)
            raise exc.SettingsError(msg)

        factory_function = allowed_constants[value_type]

        try:
            return factory_function(self.shape_size)
        except Exception as e:
            msg = (
                f"Constant generation failed | Variable: '{self.symbol}' | "
                f"Type: '{value_type}' | Error: {type(e).__name__}: {str(e)}"
            )
            self.logger.error(msg)
            raise exc.OperationalError(msg) from e

    def __repr__(self) -> str:
        """Provide a string representation of the Variable object."""
        excluded_keys = ['data', 'logger', 'var_info']

        output = ''
        for key, value in self.__dict__.items():
            if key not in excluded_keys:
                output += f'\n{key}: {value}'
        return output

    def __iter__(self) -> Iterator[Tuple[Any, Any]]:
        """Iterate over the instance's attributes, excluding data and logger."""
        for key, value in self.__dict__.items():
            if key not in ('data', 'logger'):
                yield key, value
