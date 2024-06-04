"""
dotdict.py 

@author: Matteo V. Rocco
@institution: Politecnico di Milano

This module defines a custom dictionary class, DotDict, which allows 
access to values using both key-based indexing (e.g., dict_instance['key']) 
and dot notation (e.g., dict_instance.key).
The class inherits all methods of a standard dictionary.
"""

from typing import Any


class DotDict(dict[Any, Any]):
    """
    This class generates a dictionary where values can be accessed either
    by key (example: dict_instance['key']) and by dot notation (example:
    dict_instance.key). The class inherits all methods of a standard dictionary.
    """

    def __getattr__(self, name: str) -> Any:
        """
        Retrieve the value associated with the given attribute name.

        Args:
            name (str): The name of the attribute to retrieve.

        Returns:
            Any: The value associated with the attribute.

        Raises:
            AttributeError: If the attribute does not exist.
        """
        try:
            return self[name]
        except KeyError as error:
            raise AttributeError(f"No such attribute: {name}") from error

    def __setattr__(self, name: str, value: Any) -> None:
        """
        Set the value associated with the given attribute name.

        Args:
            name (str): The name of the attribute to set.
            value (Any): The value to associate with the attribute.
        """
        self[name] = value

    def __delattr__(self, name: str) -> None:
        """
        Delete the attribute with the given name.

        Args:
            name (str): The name of the attribute to delete.

        Raises:
            AttributeError: If the attribute does not exist.
        """
        try:
            del self[name]
        except KeyError as error:
            raise AttributeError(f"No such attribute: {name}") from error
