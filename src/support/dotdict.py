from typing import Any, Dict


class DotDict(dict):
    """This class generates a dictionary where values can be accessed either
    by key (example: dict_instance['key']) and by dot notation (example:
    dict_instance.key). The class inherits all methods of standard dict.
    """

    def __getattr__(self, name: str) -> Any:
        if name in self:
            return self[name]
        else:
            error = f"No such attribute: {name}"
            raise AttributeError(error)

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value

    def __iter__(self) -> Dict[str, Any]:
        return iter(self.items())
