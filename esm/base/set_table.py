from typing import Any, Dict, Iterator, List, Optional, Tuple
import pandas as pd

from esm.constants import Constants
from esm.log_exc.logger import Logger


class SetTable:
    """
    Represents a set with associated attributes and methods.

    Args:
        logger (Logger): An instance of the Logger class for logging purposes.
        data (pd.DataFrame, optional): DataFrame containing set data. 
            Defaults to None.
        **kwargs: Additional keyword arguments representing attributes of 
            the set.

    Attributes:
        logger (Logger): A Logger instance for logging.
        symbol (str): Symbol representing the set.
        table_name (str): Name of the SQLite table associated with the set.
        table_headers (Dict[str, Any]): Headers of the SQLite table associated 
            with the set.
        set_categories (Dict[str, Any]): Categories of the set.
        split_problem (bool): If True, the set is defining multiple numerical 
            problems.
        data (pd.DataFrame): DataFrame containing set data.

    Methods:
        __repr__: Representation of the Set instance.
        __iter__: Iterator over the Set instance.
    """

    def __init__(
            self,
            logger: Logger,
            data: Optional[pd.DataFrame] = None,
            **kwargs,
    ) -> None:

        self.logger = logger.getChild(__name__)

        self.symbol: str
        self.table_name: str
        self.split_problem: bool = False
        self.table_structure: Dict[str, Any]

        for key, value in kwargs.items():
            setattr(self, key, value)

        self.table_headers: Optional[Dict[str, Any]] = None
        self.table_filters: Optional[Dict[int, Any]] = None
        self.set_categories: Optional[Dict[str, Any]] = None
        self.data = data

        self.fetching_headers_and_filters()

    @property
    def set_name_header(self) -> str | None:
        if self.table_headers is not None:
            return self.table_headers[Constants.get('_STD_NAME_HEADER')][0]
        else:
            return

    @property
    def set_aggregation_header(self) -> str | None:
        if self.table_headers is not None:
            aggregation_key = Constants.get('_STD_AGGREGATION_HEADER')

            if aggregation_key in self.table_headers:
                return self.table_headers[aggregation_key][0]
            else:
                return
        else:
            return

    @property
    def set_excel_file_headers(self) -> List | None:
        if self.table_headers is not None:
            return [
                item[0] for item in list(self.table_headers.values())
            ]
        else:
            return

    @property
    def set_filters_dict(self) -> Dict[str, List[str]] | None:
        if self.table_filters:
            return {
                filter_items['header'][0]: filter_items['values']
                for filter_items in self.table_filters.values()
            }
        else:
            return

    @property
    def set_filters_headers(self) -> Dict[int, str] | None:
        if self.table_filters:
            return {
                key: value['header'][0]
                for key, value in self.table_filters.items()
            }
        else:
            return

    @property
    def set_items(self) -> List[str] | None:
        if self.data is not None:
            return list(self.data[self.set_name_header])
        else:
            return

    def fetching_headers_and_filters(self) -> None:

        name_key = Constants.get('_STD_NAME_HEADER')
        filters_key = Constants.get('_STD_FILTERS_HEADERS')
        aggregation_key = Constants.get('_STD_AGGREGATION_HEADER')

        # Fetching filters
        self.table_filters = self.table_structure.get(filters_key, None)

        # Fetching table headers
        name_header = self.table_structure.get(name_key, None)
        aggregation_header = self.table_structure.get(
            aggregation_key, None)

        filters_headers = {
            'filter_' + str(key): value['header']
            for key, value in self.table_structure.get(filters_key, {}).items()
        }

        self.table_headers = {
            name_key: name_header,
            **filters_headers
        }

        if aggregation_header:
            self.table_headers[aggregation_key] = aggregation_header

    def __repr__(self) -> str:
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
        for key, value in self.__dict__.items():
            if key not in ('data', 'logger'):
                yield key, value
