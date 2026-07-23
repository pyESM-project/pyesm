"""Module defining the SetTable class.

This module provides the SetTable class for handling and manipulating Set tables 
in a structured format. It allows for managing Set tables with detailed logging 
and interaction with a SQLite database.
"""
from typing import Any, Dict, Iterator, List, Optional, Tuple

import pandas as pd

from cvxlab.defaults import Defaults
from cvxlab.log_exc.logger import Logger


class SetTable:
    """Generate and manipulate a Set tables with specific attributes and methods.

    This class encapsulates operations related to Set tables, such as fetching 
    headers, filters, and related data. It integrates with a logger for activity
    logging and uses a pandas DataFrame to handle the Set's data.

    Attributes:

    - logger (Logger): Logger object for logging information, warnings, and errors.
    - name (Optional[str]): The name of the Set.
    - table_name (Optional[str]): The name of the associated SQLite table.
    - split_problem (bool): Indicates whether the Set defines multiple 
        numerical problems (i.e. inter-problem set defining model Scenarios).
    - description (Optional[str]): Description metadata for the Set.
    - copy_from (Optional[str]): Name of another Set to copy values from.
    - table_structure (Dict[str, Any]): Structure of the SQLite table for 
        data handling.
    - table_headers (Dict[str, List[str]]): Headers of the SQLite table.
    - table_filters (Dict[int, Any]): Filters applicable to the table.
    - set_categories (Dict[str, Any]): Categories applicable to the Set. Not 
        directly employed in model activity, used for data visualization and
        aggregation of categories.
    - data (Optional[pd.DataFrame]): DataFrame containing the Set's data.

    """

    def __init__(
            self,
            logger: Logger,
            key_name: str,
            **set_info,
    ):
        """Initialize a new instance of the SetTable class.

        This constructor sets up the SetTable instance with a logger, a key name,
        and various attributes defined in the set_info dictionary.
        This constructor automatically calls methods to fetch names, attributes,
        and table headers based on the provided information.

        Args:
            logger (Logger): Logger instance for logging activities.
            key_name (str): The key/name of the set.
            **set_info: key-value pairs embedding set information.
        """
        self.logger = logger.get_child(__name__)

        self.name: Optional[str] = None
        self.table_name: Optional[str] = None

        self.split_problem: bool = False
        self.description: Optional[str] = None
        self.copy_from: Optional[str] = None

        self.table_structure: Dict[str, Any] = {}
        self.table_headers: Dict[str, List[str]] = {}
        self.table_filters: Dict[int, Any] = {}
        self.table_aggregations: Dict[int, Any] = {}
        self.set_categories: Dict[str, Any] = {}
        self.data: Optional[pd.DataFrame] = None

        self.fetch_names(key_name)
        self.fetch_attributes(set_info)
        self.fetch_tables_headers()

    @property
    def set_name_header(self) -> str | None:
        """Return the default set table name header.

        Returns:
            Optional[str]: The standard name header if available, otherwise None.
        """
        if self.table_headers is not None:
            return self.table_headers[Defaults.Labels.NAME][0]
        return None

    @property
    def set_excel_file_headers(self) -> List | None:
        """Return a list of formatted headers for Excel files usage.

        Returns:
            Optional[List]: List of headers suitable for Excel, or None 
                if not defined.
        """
        if self.table_headers is not None:
            return [item[0] for item in list(self.table_headers.values())]
        return None

    @property
    def set_filters_dict(self) -> Dict[str, List[str]] | None:
        """Return a dictionary of filter keys with their corresponding values.

        Returns:
            Optional[Dict[str, List[str]]]: Dictionary where keys are filter 
                headers and values are lists of filter criteria, or None if not set.
        """
        if self.table_filters:
            return {
                filter_items['header']: filter_items['values']
                for filter_items in self.table_filters.values()
            }
        return None

    @property
    def set_filters_headers(self) -> Dict[int, str] | None:
        """Return a mapping from filter index to their corresponding keys.

        Returns:
            Optional[Dict[int, str]]: Dictionary mapping filter indices to 
                related keys, or None if not defined.
        """
        if self.table_filters:
            return {
                key: value['header']
                for key, value in self.table_filters.items()
            }
        return None

    @property
    def set_aggregations_headers(self) -> Dict[int, str] | None:
        """Return a mapping from aggregation index to their corresponding keys.

        Returns:
            Optional[Dict[int, str]]: Dictionary mapping aggregation indices 
                to related keys, or None if not defined.
        """
        if self.table_aggregations:
            return {
                key: value['header']
                for key, value in self.table_aggregations.items()
            }
        return None

    @property
    def set_items(self) -> List[str] | None:
        """Return a list of items in the set.

        Returns:
            Optional[List[str]]: List of item names from the set, or None 
                if data is empty or header is undefined.
        """
        if self.data is not None:
            return list(self.data[self.set_name_header])
        return None

    def fetch_names(self, set_key: str) -> None:
        """Fetch name and SQLite table name of the set based on the provided key.

        The method constructs the table name by appending a predefined prefix
        to the uppercase version of the provided set key.

        Args:
            set_key (str): The key of the set.
        """
        prefix = Defaults.Labels.SET_TABLE_NAME_PREFIX
        self.name = set_key
        self.table_name = prefix+set_key.upper()

    def fetch_attributes(self, set_info: dict) -> None:
        """Define table_structure attribute from the provided set information.

        The method get attributes on the instance from the information dictionary, 
        and defines the structure of the SQLite table of the set.

        Args:
            set_info (dict): Dictionary of attributes for the set.
        """
        col_name_suffix = Defaults.Labels.COLUMN_NAME_SUFFIX
        filters_header = Defaults.Labels.FILTERS
        aggregations_header = Defaults.Labels.AGGREGATIONS
        aggregations_suffix = Defaults.Labels.COLUMN_AGGREGATION_SUFFIX
        name_header = Defaults.Labels.NAME

        # set all attributes except filters and aggregations
        for key, value in set_info.items():
            if key not in (filters_header, aggregations_header) and \
                    value is not None:
                setattr(self, key, value)

        # column with name of set entries
        self.table_structure[name_header] = self.name + col_name_suffix

        # column with filter values
        if filters_header in set_info:
            filters_info = set_info[filters_header] or {}
            self.table_structure[filters_header] = {}

            for filter_key, filter_values in filters_info.items():
                self.table_structure[filters_header][filter_key] = {
                    'header': f"{self.name}_{filter_key}",
                    'values': filter_values
                }

        # column with aggregations categories (always converted to str)
        if aggregations_header in set_info:
            agg_items = set_info[aggregations_header]
            if not isinstance(agg_items, list):
                agg_items = [agg_items]
            self.table_structure[aggregations_header] = {}

            for item in agg_items:
                self.table_structure[aggregations_header][item] = {
                    'header': f"{self.name}{aggregations_suffix}{item}",
                }

    def fetch_tables_headers(self) -> None:
        """Define table headers based on the table structure.

        This method updates the instance's table_headers and table_filters attributes
        based on configuration defaults. It extracts specific headers for name, filters,
        and aggregation from the table's structural definition, and sets them up for
        easy access throughout the class's methods.
        """
        name_key = Defaults.Labels.NAME
        filters_key = Defaults.Labels.FILTERS
        aggregations_key = Defaults.Labels.AGGREGATIONS
        generic_field_type = Defaults.Labels.GENERIC_FIELD_TYPE

        # Fetching filters and aggregations
        self.table_filters = self.table_structure.get(filters_key, {})
        self.table_aggregations = self.table_structure.get(
            aggregations_key, {})

        # Fetching table headers
        name_header = self.table_structure.get(name_key, None)
        filters_headers = {
            'filter_' + str(key): value['header']
            for key, value in self.table_structure.get(filters_key, {}).items()
        }

        aggregations_headers = {
            'aggregation_' + str(key): value['header']
            for key, value in self.table_structure.get(aggregations_key, {}).items()
        }

        self.table_headers = {
            key: [value, generic_field_type]
            for key, value in {
                name_key: name_header,
                **filters_headers,
                **aggregations_headers,
            }.items()
        }

    def __repr__(self) -> str:
        """Return a string representation of the SetTable instance."""
        output = ''
        for key, value in self.__dict__.items():
            if key in ('data', 'logger'):
                pass
            elif key != 'values':
                output += f'\n{key}: {value}'
            else:
                output += f'\n{key}: \n{value}'
        return output

    def __iter__(self) -> Iterator[Tuple[Any, Any]]:
        """Iterate over the instance's attributes, excluding data and logger."""
        for key, value in self.__dict__.items():
            if key not in ('data', 'logger'):
                yield key, value
