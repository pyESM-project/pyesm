from pySM.database.database import Database


class Model:
    """Definition and solution of the numerical model."""

    def __init__(self):
        self.database = Database()


if __name__ == '__main__':

    m1 = Model()
    m1.database.print_sets()
