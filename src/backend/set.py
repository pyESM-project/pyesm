from typing import Any, Dict
import pandas as pd


class Set:

    def __init__(
            self,
            data: pd.DataFrame = None,
            **kwargs,
    ) -> None:

        self.symbol: str = None
        self.table_name: str = None
        self.table_headers: Dict[str, Any] = None
        self.set_categories: Dict[str, Any] = None
        self.split_problem: bool = False
        self.data = data

        for key, value in kwargs.items():
            setattr(self, key, value)

    def __repr__(self) -> str:
        output = ''
        for key, value in self.__dict__.items():
            if key == 'data':
                pass
            elif key != 'values':
                output += f'\n{key}: {value}'
            else:
                output += f'\n{key}: \n{value}'
        return output
