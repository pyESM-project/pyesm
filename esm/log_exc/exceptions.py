"""
exceptions.py 

@author: Matteo V. Rocco
@institution: Politecnico di Milano

This module includes all the exceptions classes necessary to clearly identify
exceptions in executing the package.
"""


class ModelFolderError(Exception):
    """
    Exception raised when there is an issue with the model folder, such as 
    the absence of essential setup files or input data files.

    Attributes:
        message (str): Explanation of the error.
    """

    def __init__(self, message='Model folder error.'):
        self.message = message
        super().__init__(self.message)


class ConceptualModelError(Exception):
    """
    Exception raised for errors in the conceptual model: errors in the logic
    adopted to define sets, variables and model expressions.

    Attributes:
        message (str): Explanation of the error.
    """

    def __init__(self, message='Conceptual Model error.'):
        self.message = message
        super().__init__(self.message)


class SettingsError(Exception):
    """
    Exception raised for errors related to settings configurations.

    Attributes:
        message (str): Explanation of the error.
    """

    def __init__(self, message='Settings error.'):
        self.message = message
        super().__init__(self.message)


class MissingDataError(Exception):
    """
    Exception raised when expected data is missing.

    Attributes:
        message (str): Explanation of the error.
    """

    def __init__(self, message='Missing data error.'):
        self.message = message
        super().__init__(self.message)


class OperationalError(Exception):
    """
    Exception raised for errors that occur during the operation of the package,
    related to generic operation of classes and related methods.

    Attributes:
        message (str): Explanation of the error.
    """

    def __init__(self, message='Operational error.'):
        self.message = message
        super().__init__(self.message)


class IntegrityError(Exception):
    """
    It mirrors the integrity error of sqlite3 in handling sqlite databases.

    Attributes:
        message (str): Explanation of the error.
    """

    def __init__(self, message='Integrity error'):
        self.message = message
        super().__init__(self.message)


class NumericalProblemError(Exception):
    """
    Exception raised for errors arising from numerical solution of the problem.

    Attributes:
        message (str): Explanation of the error.
    """

    def __init__(self, message='Numerical problem error'):
        self.message = message
        super().__init__(self.message)


class TableNotFoundError(Exception):
    """
    Exception raised when a specified table cannot be found.

    Attributes:
        message (str): Explanation of the error.
    """

    def __init__(self, message='Table not found.'):
        self.message = message
        super().__init__(self.message)
