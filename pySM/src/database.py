from pySM.src.constants import _SETS
from pySM.src.util import prettify


class Database:
    """Defining and managing the data structure for the model"""
    sets = _SETS

    @classmethod
    def print_sets(cls):
        prettify(cls.sets)


if __name__ == '__main__':

    d1 = Database()
    d1.print_sets()
