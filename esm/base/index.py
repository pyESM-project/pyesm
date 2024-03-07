from pathlib import Path
from typing import Dict

from esm.base.set import Set
from esm.base.variable import Variable
from esm.log_exc.logger import Logger
from esm.log_exc import exceptions as exc
from esm import constants
from esm.support.file_manager import FileManager
from esm.support.dotdict import DotDict
from esm.support import util


class Index:

    def __init__(
            self,
            logger: Logger,
            files: FileManager,
            paths: Dict[str, str],
    ) -> None:

        self.logger = logger.getChild(__name__)
        self.logger.info(f"'{self}' object initialization...")

        self.files = files
        self.paths = paths

        self.sets: DotDict[str, Set] = self.load_sets()
        self.variables: DotDict[str, Variable] = self.load_variables()

        self.load_vars_coordinates_fields()
        self.load_vars_table_headers()
        self.load_vars_sets_parsing_hierarchy()
        self.load_sets_intra_problem()

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

    def load_sets(self) -> DotDict[str, Set]:

        sets_data = self.files.load_file(
            file_name=constants._SETUP_FILES['sets_structure'],
            dir_path=self.paths['model_dir'],
        )

        if util.validate_dict_structure(
            dictionary=sets_data,
            validation_structure=constants._SET_DEFAULT_STRUCTURE,
        ):
            return DotDict({
                key: Set(logger=self.logger, **value)
                for key, value in sets_data.items()
            })
        else:
            msg = "Sets data validation not successful. " \
                "Set input data must comply with default structure."
            self.logger.error(msg)
            raise exc.SettingsError(msg)

    def load_sets_intra_problem(self) -> None:
        for variable in self.variables.values():
            if variable.type != 'constant':
                variable.sets_intra_problem = {
                    key: value
                    for key, value in variable.sets_parsing_hierarchy.items()
                    if key not in self.list_sets_split_problem
                }

    def load_variables(self) -> DotDict[str, Variable]:

        variables_data = self.files.load_file(
            file_name=constants._SETUP_FILES['variables'],
            dir_path=self.paths['model_dir'],
        )

        if util.validate_dict_structure(
            dictionary=variables_data,
            validation_structure=constants._VARIABLE_DEFAULT_STRUCTURE,
        ):
            return DotDict({
                key: Variable(logger=self.logger, **value)
                for key, value in variables_data.items()
            })
        else:
            msg = "Variables data validation not successful. " \
                "Variable input data must comply with default structure."
            self.logger.error(msg)
            raise exc.SettingsError(msg)

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

                # partire da qui per cambiare gli headers degli attributi
                # di sets e variables.
                # set_header = set_key

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
