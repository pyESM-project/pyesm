from pathlib import Path
from re import A
from types import NoneType
from typing import Literal, Union, Dict, List

import pandas as pd

from src.log_exc.logger import Logger
from src.log_exc import exceptions as exc
from src.constants import constants
from src.support.file_manager import FileManager
from src.support import util


class BaseItem:
    def __init__(self, **kwargs) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self) -> str:
        output = ''
        for key, value in self.__dict__.items():
            if key in ['data', 'table']:
                pass
            elif key != 'values':
                output += f'\n{key}: {value}'
            else:
                output += f'\n{key}: \n{value}'
        return output


class Set(BaseItem):
    def __init__(
            self,
            data: pd.DataFrame = None,
            **kwargs,
    ) -> None:

        self.symbol = None
        self.table_name = None
        self.table_headers = None
        self.set_categories = None
        self.split_problem = None

        super().__init__(**kwargs)

        self.data = data


class Variable(BaseItem):
    def __init__(
            self,
            **kwargs,
    ) -> None:

        self.symbol = None
        self.name = None
        self.type = None
        self.coordinates_info = {}
        self.shape = []

        super().__init__(**kwargs)

        self.coordinates_fields = {}
        self.table_headers = {}
        self.coordinates = {}
        self.foreign_keys = {}
        self.sets_parsing_hierarchy = {}
        self.data = {}

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

    def get_dim_label(self, dimension: Literal[0, 1]) -> Union[str, int]:
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


class Index:

    def __init__(
            self,
            files: FileManager,
            logger: Logger,
            paths: Dict,
    ) -> None:

        self.logger = logger.getChild(__name__)
        self.logger.info(f"'{self}' object initialization...")

        self.files = files
        self.paths = paths

        self.sets = self.load_sets()
        self.variables = self.load_variables()

        self.load_vars_coordinates_fields()
        self.load_vars_table_headers()
        self.load_vars_sets_parsing_hierarchy()

        self.logger.info(f"'{self}' object initialized.")

    def __repr__(self):
        class_name = type(self).__name__
        return f'{class_name}'

    @property
    def list_sets(self) -> Dict[str, str]:
        return {
            key: value.table_headers[constants._STD_TABLE_HEADER_KEY][0]
            for key, value in self.sets.items()
        }

    @property
    def list_sets_split_problem(self) -> Dict[str, str]:
        list_sets_split_problem = {
            key: value.table_headers[constants._STD_TABLE_HEADER_KEY][0]
            for key, value in self.sets.items()
            if getattr(value, 'split_problem', False)
        }

        if not list_sets_split_problem:
            msg = "At least one Set must identify a problem. " \
                f"Check 'split_problem' properties in 'sets_structure.yml'"
            self.logger.error(msg)
            raise exc.NumericalProblemError(msg)

        return list_sets_split_problem

    def load_sets(self) -> util.DotDict[str, Set]:

        sets_data = self.files.load_file(
            file_name=constants._SETUP_FILES['sets_structure'],
            dir_path=self.paths['model_dir'],
        )

        return util.DotDict({
            key: Set(**value)
            for key, value in sets_data.items()
        })

    def load_variables(self) -> Dict[str, Variable]:
        variables_data = self.files.load_file(
            file_name=constants._SETUP_FILES['variables'],
            dir_path=self.paths['model_dir'],
        )
        return util.DotDict({
            key: Variable(**value)
            for key, value in variables_data.items()
        })

    def load_vars_coordinates_fields(self) -> None:

        self.logger.debug(
            f"Loading 'variables_fields' to Index.")

        for variable in self.variables.values():
            set_headers_key = constants._STD_TABLE_HEADER_KEY

            for set_key in variable.coordinates_info.keys():
                set_headers = self.sets[set_key].table_headers[set_headers_key]
                variable.coordinates_fields[set_key] = set_headers

    def load_vars_table_headers(self) -> None:

        self.logger.debug("Loading variables 'table_headers' to Index.")

        for var_key, variable in self.variables.items():
            if variable.coordinates_fields is None:
                error = f"'variable_fields' is empty for variable '{var_key}'."
                self.logger.error(error)
                raise ValueError(error)

            variable.table_headers = variable.coordinates_fields.copy()
            variable.table_headers = util.add_item_to_dict(
                dictionary=variable.table_headers,
                item=constants._STD_ID_FIELD,
                position=0,
            )

    def load_foreign_keys_to_vars_index(self) -> None:

        self.logger.debug(f"Loading tables 'foreign_keys' to Index.")

        for variable in self.variables.values():
            for set_key, set_header in variable.coordinates_fields.items():
                variable.foreign_keys[set_header[0]] = \
                    (set_header[0], self.sets[set_key].table_name)

    def load_vars_sets_parsing_hierarchy(self) -> None:

        self.logger.debug(
            f"Loading variables 'sets_parsing_hierarchy' to Index.")

        for variable in self.variables.values():
            sets_parsing_hierarchy = {
                key: value[0]
                for key, value in variable.coordinates_fields.items()
                if key not in variable.shape
            }

            if not sets_parsing_hierarchy:
                variable.sets_parsing_hierarchy = None
            else:
                variable.sets_parsing_hierarchy = sets_parsing_hierarchy

    def load_sets_to_index(
            self,
            excel_file_name: str,
            excel_file_dir_path: Path | str,
            empty_data_fill='',
    ) -> None:

        if all(
            set_instance.data is None
            for set_instance in self.sets.values()
        ):
            self.logger.info(f"'{self}' object: loading new Sets to Index.")
        else:
            self.logger.warning(
                f"'{self}' object: Sets tables already "
                "defined for at least one Set in Index.")
            user_input = input("Overwrite Sets? (y/[n]): ")
            if user_input.lower() != 'y':
                self.logger.info(
                    f"'{self}' object: Sets tables not overwritten.")
                return
            else:
                self.logger.info(
                    f"'{self}' object: overwriting Sets to Index.")

        sets_values = self.files.excel_to_dataframes_dict(
            excel_file_name=excel_file_name,
            excel_file_dir_path=excel_file_dir_path,
            empty_data_fill=empty_data_fill,
            dtype=str
        )

        for set_instance in self.sets.values():
            table_name = set_instance.table_name
            if table_name in sets_values.keys():
                set_instance.data = sets_values[table_name]

    def load_vars_coordinates_to_index(self) -> None:

        self.logger.debug(f"Loading variables 'coordinates' to Index.")

        for variable in self.variables.values():

            for set_key, set_filter in variable.coordinates_info.items():

                set_header = variable.coordinates_fields[set_key][0]

                if set_filter is None:
                    set_values = list(self.sets[set_key].data[set_header])

                elif isinstance(set_filter, dict):

                    if 'set_categories' in set_filter and \
                            set_filter['set_categories'] is not None:

                        category_filter_id = set_filter['set_categories']
                        category_filter = self.sets[set_key].set_categories[category_filter_id]
                        category_header_name = self.sets[set_key].table_headers['category'][0]

                        set_filtered = self.sets[set_key].data.query(
                            f'{category_header_name} == "{category_filter}"'
                        ).copy()

                    if 'aggregation_key' in set_filter and \
                            set_filter['aggregation_key'] is not None:

                        aggregation_key = set_filter['aggregation_key']
                        aggregation_key_name = self.sets[set_key].table_headers[aggregation_key][0]

                        set_filtered.loc[
                            set_filtered[aggregation_key_name] != '', set_header
                        ] = set_filtered[aggregation_key_name]

                    set_values = list(set(set_filtered[set_header]))

                else:
                    error_msg = f"Missing or wrong data in 'constants/_VARIABLES'."
                    self.logger.error(error_msg)
                    raise exc.MissingDataError(error_msg)

                variable.coordinates[set_header] = set_values
