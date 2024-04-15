class ModelFolderError(Exception):

    def __init__(self, message='Model folder error.'):
        self.message = message
        super().__init__(self.message)


class ConceptualModelError(Exception):

    def __init__(self, message='Conceptual Model error.'):
        self.message = message
        super().__init__(self.message)


class SettingsError(Exception):

    def __init__(self, message='Settings error.'):
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


class NumericalProblemError(Exception):

    def __init__(self, message='Numerical problem error'):
        self.message = message
        super().__init__(self.message)


class TableNotFoundError(Exception):

    def __init__(self, message='Table not found.'):
        self.message = message
        super().__init__(self.message)
