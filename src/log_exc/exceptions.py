from sqlite3 import OperationalError


class MissingDataError(Exception):

    def __init__(self, message='Missing data error.'):
        self.message = message
        super().__init__(self.message)
