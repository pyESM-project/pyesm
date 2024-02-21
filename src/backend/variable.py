from typing import Dict, List, Literal

import pandas as pd

from src.support import constants, util


class Variable:
    def __init__(
            self,
            **kwargs,
    ) -> None:

        self.symbol = None
        self.name = None
        self.type = None
        self.coordinates_info = {}
        self.shape = []

        for key, value in kwargs.items():
            setattr(self, key, value)

        self.coordinates_fields = {}
        self.table_headers = {}
        self.coordinates = {}
        self.foreign_keys = {}
        self.sets_parsing_hierarchy = {}
        self.sets_intra_problem = {}
        self.data = {}

    def __repr__(self) -> str:
        output = ''
        for key, value in self.__dict__.items():
            if key != 'data':
                output += f'\n{key}: {value}'
        return output

    @property
    def shape_size(self) -> List[int]:
        shape_size = []

        for item in self.shape:
            if isinstance(item, str):
                if item not in self.coordinates_fields.keys():
                    error = f"'{item}' is not a variable coordinate."
                    raise ValueError(error)
                coordinate_key = self.coordinates_fields[item][0]
                shape_size.append(len(self.coordinates[coordinate_key]))

            elif isinstance(item, int):
                shape_size.append(item)

            else:
                error = "Wrong shape format: valid formats are 'str' or 'int'"
                raise ValueError(error)

        return shape_size

    @property
    def dim_labels(self) -> List[str]:
        return [self.get_dim_label(dim) for dim, _ in enumerate(self.shape)]

    @property
    def dim_items(self) -> List[List[str]]:
        return [self.get_dim_items(dim) for dim, _ in enumerate(self.shape)]

    def get_dim_label(self, dimension: Literal[0, 1]) -> str | int:
        if dimension not in [0, 1]:
            raise ValueError("Dimension must be 0 (rows) or 1 (columns).")

        dim_label = self.table_headers.get(
            self.shape[dimension])

        return dim_label[0] if isinstance(dim_label, list) else dim_label

    def get_dim_items(self, dimension: Literal[0, 1]) -> List[str]:
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
            specific cvxpy variable)

        Returns:
            Dict: 
                keys: are rows where cvxpy variables values are None;
                values: the names of the sets that identify the variable;
        """
        cvxpy_var_header = constants._CVXPY_VAR_HEADER

        if self.data[cvxpy_var_header][row].value is None:
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
