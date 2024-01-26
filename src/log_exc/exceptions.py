class ModelFolderError(Exception):

    def __init__(self, message='Model folder error.'):
        self.message = message
        super().__init__(self.message)


class MissingDataError(Exception):

    def __init__(self, message='Missing data error.'):
        self.message = message
        super().__init__(self.message)


class OperationalError(Exception):

    def __init__(self, message='Operational error.'):
        self.message = message
        super().__init__(self.message)


class IntegrityError(Exception):

    def __init__(self, message='Integrity error'):
        self.message = message
        super().__init__(self.message)


class TableNotFoundError(Exception):
    pass
