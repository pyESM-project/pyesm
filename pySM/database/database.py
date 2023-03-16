from pySM.database import constants as c
from pySM.database import util as u


class Database:
    """Defining and managing the data structure for the model"""
    sets = c._SETS

    @classmethod
    def print_sets(cls):
        u.prettify(cls.sets)


if __name__ == '__main__':

    d1 = Database()
    d1.print_sets()
