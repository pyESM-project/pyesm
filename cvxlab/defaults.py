"""Module collecting all fundamental default settings of the package.

Defaults of the package are useful for simplifying renaming package labels,
defining templates for fundamental package objects (sets, data tables, variables, ...)
for validation purposes, defining fundamental numerical settings and template 
text messages.
"""
from typing import Literal, Union

import cvxpy as cp
import numpy as np
import pandas as pd

from cvxlab.support import util_constants, util_operators


class Defaults:
    """Centralized repository for default settings of the package.

    Defaults are grouped into meaningful categories (sub-classes) for clarity and 
    ease of access. Supports direct attribute access of default settings using '__getattr__' method.

    Subgroups:

    - LiteralTypes: Shared Literal type aliases for validating settings and type hints.
    - ConfigFiles: Defaults related to configuration and file management.
    - Labels: Standard headers and field names.
    - DefaultStructures: Default structures for data validation.
    - SymbolicDefinitions: Allowed constants and operators for symbolic problem definitions.
    - NumericalSettings: Settings for numerical solvers and tolerances.
    - TextNotes: Text notes and messages for user.

    Usage:: 

        # Attributes of sub-groups can be accessed directly
        Defaults.ConfigFiles.SETUP_FILES
    """

    _SUBGROUPS = []

    class LiteralTypes:
        """Shared Literal type aliases (single source of truth).

        To be used to validate settings and for type hints across the package. 
        Changing these aliases will change the allowed values for settings across 
        the package.
        """
        SettingsSource = Literal['yml', 'xlsx']
        DataFileType = Literal['xlsx', 'csv']
        LogLevel = Literal['info', 'debug', 'warning', 'error']
        LogFormat = Literal['standard', 'detailed']
        NormType = Literal['max_relative', 'max_absolute', 'l1', 'l2', 'linf']
        SetUpdateMode = Literal['all', 'filters', 'aggregations']
        HybridVarType = Literal['endogenous', 'exogenous']
        TransferUpdate = Literal['settings', 'sets', 'all']
        ConvergenceTables = Literal['all_endogenous', 'hybrid_only']
        HandleModelInstance = Literal['save', 'load']
        ExcelEngine = Literal['openpyxl', 'xlsxwriter']
        TableHandling = Literal['update', 'overwrite']

    class ConfigFiles:
        """Defaults related to configuration and file management.

        - SETUP_INFO: Dictionary mapping setup information groups.
        - SETUP_XLSX_FILE: Default name of the setup Excel file.
        - SETS_FILE: Default name of the sets Excel file.
        - AVAILABLE_SETUP_SOURCES: List of possible formats for input data sources.
        - INPUT_DATA_DIR: Default name for input data directory.
        - INPUT_DATA_FILE_NAME: Default name for the input data file (for single input data file).
        - AVAILABLE_DATA_FILES_EXTENSIONS: Default extensions for data file/s.
        - SQLITE_DATABASE_FILE: Default name for the SQLite database file.
        - SQLITE_DATABASE_FILE_BKP: Default name for the SQLite database backup file.
        - SQLITE_DATABASE_FILE_TEST: Default name for the SQLite database test file.
        - INSTANCES_DIR: Default name for the directory containing saved Model instances.

        """

        SETUP_INFO = {
            0: 'structure_sets',
            1: 'structure_variables',
            2: 'problem'
        }
        SETUP_XLSX_FILE = 'model_settings.xlsx'
        SETS_FILE = 'sets.xlsx'
        AVAILABLE_SETUP_SOURCES = ['yml', 'xlsx']
        AVAILABLE_DATA_FILES_EXTENSIONS = ['xlsx', 'csv']
        INPUT_DATA_DIR = 'input_data'
        INPUT_DATA_FILE_NAME = 'input_data'
        SQLITE_DATABASE_FILE = 'database.db'
        SQLITE_DATABASE_FILE_BKP = 'database_bkp.db'
        SQLITE_DATABASE_FILE_TEST = 'database_expected.db'
        TEMPLATES_DIR_PATH = r'cvxlab/templates'
        INSTANCES_DIR = 'instances'
        CUSTOM_OPERATORS_FILE_NAME = 'user_defined_operators.py'
        CUSTOM_CONSTANTS_FILE_NAME = 'user_defined_constants.py'

    class Labels:
        """Default labels and field names for dictionary keys and dataframes.

        Dictionary keys default labels:

        - NAME: key related to the name of the data table object.
        - FILTERS: key related to set and data tables filters.
        - SET: key related to the set key of the set table.
        - DIM: key related to the dimension of the set.
        - AGGREGATIONS: key related to set tables aggregations.
        - CVXPY_VAR: key related to cvxpy variables.
        - COORDINATES_KEY: key related to the coordinates of the data table.
        - VARIABLES_INFO_KEY: key related to the variables information.
        - VALUE_KEY: key related to the type for variable of type constants.
        - BLANK_FILL_KEY: key related to the value used to fill blank.
        - NONNEG_KEY: key related to the non-negativity sign of endogenous variables.

        Dataframe columns default labels:

        - SUB_PROBLEM_KEY: column representing sub-problem keys.
        - FILTER_DICT_KEY: column representing filter dictionaries.
        - PROBLEM: column representing problem names.
        - SCENARIO_COORDINATES: column representing scenario coordinates.
        - PROBLEM_STATUS: column representing problem status.
        - OBJECTIVE: column representing the objective of the problem.
        - EXPRESSIONS: column representing expressions in the problem.
        - RMS_TABLES: column representing label for RMS reporting monitor for 
            integrated problems solving.

        Default field types for SQLite data tables:

        - GENERIC_FIELD_TYPE: default field type for text.
        - VALUES_FIELD: default structure and type for numeric values.
        - ID_FIELD: default structure and type for IDs.

        Default suffixes and prefixes for SQLite tables:

        - SET_TABLE_NAME_PREFIX: prefix for set table names.
        - COLUMN_NAME_SUFFIX: suffix for column names.
        - COLUMN_AGGREGATION_SUFFIX: suffix for aggregation columns.
        """

        NAME = 'name'
        FILTERS = 'filters'
        SET = 'set'
        DIM = 'dim'
        AGGREGATIONS = 'aggregations'
        CVXPY_VAR = 'variable'
        COORDINATES_KEY = 'coordinates'
        VARIABLES_INFO_KEY = 'variables_info'
        VALUE_KEY = 'value'
        BLANK_FILL_KEY = 'blank_fill'
        NONNEG_KEY = 'nonneg'

        SUB_PROBLEM_KEY = 'sub_problem_key'
        FILTER_DICT_KEY = 'filter'
        PROBLEM = 'problem'
        SCENARIO_COORDINATES = 'info'
        PROBLEM_STATUS = 'status'
        OBJECTIVE = 'objective'
        EXPRESSIONS = 'expressions'

        GENERIC_FIELD_TYPE = 'TEXT'
        VALUES_FIELD = {'values': ['values', 'REAL']}
        ID_FIELD = {'id': ['id', 'INTEGER PRIMARY KEY']}

        SET_TABLE_NAME_PREFIX = '_set_'
        COLUMN_NAME_SUFFIX = '_Name'
        COLUMN_AGGREGATION_SUFFIX = '_agg_'

    class DefaultStructures:
        """Default structures for data validation and for generating templates.

        Changing these structures will change the way data is validated and
        how templates are generated.

        SET_STRUCTURE: Structure for defining sets with metadata and filters. 
        Sets are defined as the dimensions of the numerical problem. 

        Properties of a SET:

        - set_key: 
            name of the set, used as name of the set in the SQLite data 
            table. Since SQLite tables names are case insensitive, the set_key
            is case insensitive (e.g., 'e' and 'E' are the same set). This is 
            the sole set information that is required to define a set.
        - description: 
            (Optional) information of the set provided by the modeler.
        - split_problem: 
            (Optional) if the set items defines independent numerical 
            sub-problems. In case more sets are defined, the number of sub-problems
            is equal to the linear combination of the items of the sets.
        - copy_from: 
            (Optional) key of another set to copy the data from. If a set is 
            defined with this key, it will copy the data from the set with
            the key defined in this field, and it is not necessary to provide the
            related data in the sets file.
        - filters: 
            (Optional) dictionary with keys as the filters name and values
            as the list of filter values. Filters are used to define variables 
            as part of data tables.
        - aggregations: 
            (Optional) list of set aggregations useful to aggregate data for 
            visualization. Not recalled in operating with numerical problem.


        DATA_TABLE_STRUCTURE: Structure for defining data tables with variables 
        and their properties. Data tables correspond to SQLite tables and are 
        used to generate variables in the numerical problem. 

        Properties of a DATA TABLE:

        - table_key: 
            name of the data table, used as name of the table in the SQLite data 
            table. Since SQLite tables names are case insensitive, the
            table_key is case insensitive (e.g., 'e' and 'E' are the same table).
        - description: 
            (Optional) information of the data table provided by the modeler.
        - type: 
            type of the data table, can be one of VARIABLE_TYPES or a dictionary 
            with keys as problem name and corresponding values as allowed types.
        - integer: 
            (Optional) if variables of the table are integers (default: False).
        - coordinates: 
            list of table coordinates (set_key symbols) that define the dimensions 
            of the data table.
        - variables_info: 
            definition of the variables based on the same data table. It is a 
            dictionary with keys as variables names and values as dict with
            variable info. Variables are case sensitive.

            - value: 
                (Optional) ALLOWED_CONSTANTS (only for constants!).
            - blank_fill: 
                (Optional) numerical value that will be used to fill variables
                in case of blank or nan values.
            - nonneg: 
                (Optional) defines whether an endogenous variable is expected to 
                be non-negative. This will result in an implicit non-negativity 
                constraint defined in the model. In case of integrated models,
                this constraint is useful to check if endogenous variables values 
                are exchanged with the correct sign, to avoid numerical inconsistencies.
            - set_key: 
                (Optional) dictionary with keys as set_key symbols and values
                defining the dimension and filters for the set.

                - dim: 
                    (Optional) DIMENSIONS (included in 'coordinates').
                - filters: 
                    (Optional) dictionary with keys as the filters key of the set
                    and values as the list of values to filter.


        PROBLEM_STRUCTURE: Structure for defining problems with objectives and 
        expressions.

        Properties of a PROBLEM:

        - problem_key: 
            (Optional) name of the problem, used to define multiple problems
            in the same model. If not defined, the problem is considered as the 
            main problem.
        - objective: 
            (Optional) list of expressions defining the objective of the problem.
            It can be a single expression or a list of expressions. The objective is
            defined as a scalar that can be minimized or maximized. If not defined,
            the problem is solved as a system of equations.
        - expressions: 
            list of expressions defining the problem constraints. Each expression
            can be an equality or inequality. The expressions are defined as a list of
            cvxpy expressions. At least one expression is required to define a problem.
        - description: 
            (Optional) list of strings with the problem description provided
            by the modeler. It is used to provide additional information about the problem.

        XLSX_PIVOT_KEYS and XLSX_TEMPLATE_COLUMNS: Keys and columns used to pivot 
        data for generating Excel template files for sets, variables, and problems.

        ALLOWED_BOOL: Dictionary mapping common boolean representations to Python 
        boolean values. This is used to validate boolean values in the data files.
        """

        OPTIONAL = object()
        ANY = object()
        METADATA = 'description'

        SET_STRUCTURE = (
            'set_key:',
            {
                METADATA: (OPTIONAL, str),
                'split_problem': (OPTIONAL, bool),
                'copy_from': (OPTIONAL, str),
                'filters': (OPTIONAL, {ANY: list}),
                'aggregations': (OPTIONAL, Union[int, str, list]),
            }
        )

        DATA_TABLE_STRUCTURE = (
            'table_key:',
            {
                METADATA: (OPTIONAL, str),
                'type': (str, dict),
                'integer': (OPTIONAL, bool),
                'coordinates': (str, list),
                'variables_info': {
                    ANY: {
                        'value': (OPTIONAL, str),
                        'blank_fill': (OPTIONAL, Union[int, float]),
                        'nonneg': (OPTIONAL, bool),
                        ANY: (OPTIONAL, {
                            'dim': (OPTIONAL, str),
                            'filters': (OPTIONAL, dict),
                        })
                    }
                }
            }
        )

        PROBLEM_STRUCTURE = (
            'problem_key: # optional',
            {
                'objective': (OPTIONAL, list),
                'expressions': list,
                METADATA: (OPTIONAL, list),
            }
        )

        XLSX_PIVOT_KEYS = {
            'structure_sets': ('set_key', None),
            'structure_variables': ('table_key', 'variables_info'),
            'problem': ('problem_key', None),
        }

        XLSX_TEMPLATE_COLUMNS = {
            'structure_sets': [
                'set_key',
                *SET_STRUCTURE[1].keys()
            ],
            'structure_variables': [
                'table_key',
                *DATA_TABLE_STRUCTURE[1].keys(),
                'value',
                'blank_fill',
                'set_keys ...'
            ],
            'problem': [
                'problem_key',
                *PROBLEM_STRUCTURE[1].keys()
            ],
        }

        ALLOWED_BOOL = {
            'true': True, 'True': True, 'TRUE': True,
            'false': False, 'False': False, 'FALSE': False,
        }

    class SymbolicDefinitions:
        """Allowed constants and operators for symbolic problem definitions.

        - TOKEN_PATTERNS: 
            Dictionary of regex patterns for token types (text, 
            numbers, operators, parentheses). Determines how the symbolic
            expressions are parsed and validated.
        - NONE_SYMBOLS: 
            List of symbols considered as None or empty.
        - STD_TEXT_DATA_FILL: 
            Standard text used to fill blank text fields in SQLite sets or data tables.
        - DIMENSIONS: 
            Dict of allowed dimensions of variables, where coordinates can be defined.
        - VARIABLE_TYPES: 
            Dict of allowed variable types for data tables.
        - ALLOWED_CONSTANTS: 
            Dictionary of user-defined constants. These are defined within the 
            dictionary values (complex constants are defined in util_constants module), 
            are used to define variables (see 'value' field in data tables). 
            Constants are be built with exogenous data only. 
        - ALLOWED_OPERATORS: 
            Dictionary of user-defined operators. Keys of operators can be directly 
            used in symbolic expressions. These are defined within the dictionary 
            values (complex operators are defined in util_operators module). 
            Operators are built with exogenous data only. 

        """

        TOKEN_PATTERNS = {
            'text': r"\b[a-zA-Z_][a-zA-Z0-9_]*\b",
            'numbers': r"\b(?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?\b",
            'operators': [
                r"==", r">=", r"<=",
                r"\+", r"-", r"\*", r"/", r"@", f",",
            ],
            'parentheses': [r"\(", r"\)"],
        }

        NONE_VARIANTS = [
            pd.NA, np.nan, None, float('nan'),
            'nan', 'NaN', 'NA', 'na', 'N/A', '<NA>', '<N/A>', 'None', 'null', '',
        ]
        STD_TEXT_DATA_FILL = ''

        DIMENSIONS = {
            'ROWS': 'rows',
            'COLS': 'cols',
            'INTRA': 'intra',
            'INTER': 'inter',
        }

        VARIABLE_TYPES = {
            'CONSTANT': 'constant',
            'EXOGENOUS': 'exogenous',
            'ENDOGENOUS': 'endogenous',
        }

        ALLOWED_CONSTANTS = util_constants.CONSTANTS
        ALLOWED_OPERATORS = util_operators.OPERATORS

    class NumericalSettings:
        """Settings for numerical solvers and tolerances.

        - STD_VALUES_TYPE: 
            Type of standard numerical values.
        - ALLOWED_VALUES_TYPES: 
            Tuple of allowed numerical types for values. Useful to recognize and 
            homogenize numerical values provided by user in input data files.
        - ALLOWED_TEXT_TYPE: 
            Type of allowed text values.
        - ALLOWED_SOLVERS:
            List of allowed solvers installed in the current CVXPY version.
        - TOLERANCE_TESTS_RESULTS_CHECK: 
            Tolerance for checking results of tests. It is a relative difference 
            (0.02 means 2% of maximum allowed difference between the resulting 
            database and the test databases).
        - ROUNDING_DIGITS_RELATIVE_DIFFERENCE_DB: 
            Number of digits to round the relative difference between the values 
            of the database and the test database. It is used to avoid numerical 
            issues in case of very small differences between the values of the 
            database and the test database.
        - SPARSE_MATRIX_ZEROS_THRESHOLD: 
            Threshold for considering a matrix as sparse. (0.3 means 30% of zeros 
            in the matrix). If the percentage of zeros in the matrix is higher 
            than this threshold, the matrix is considered as sparse and stored 
            in a sparse format to save memory.
        - SQL_BATCH_SIZE: 
            Batch size for SQL operations. It is used to limit the number of rows 
            processed in a single SQL operation to avoid memory issues and speed 
            up database operations.
        - SQL_MAX_BATCH_MEMORY_MB:
            Maximum memory (in MB) allocated for SQL batch operations. It is used
            to dynamically adjust the batch size based on the available memory.
        - SQL_BATCH_SIZE_MIN:
            Minimum batch size for SQL operations.
        - SQL_BATCH_SIZE_MAX:
            Maximum batch size for SQL operations.
        - CVXPY_DEFAULT_SETTINGS:
            Default settings for CVXPY solver. It includes the default solver, 
            canon backend, and whether to ignore DPP.
        - MODEL_COUPLING_SETTINGS:
            Settings for model coupling. It includes:
                allowed norms for convergence (max_relative, max_absolute, l1, l2, linf),
                numerical tolerance for convergence for each table (absolute value),
                numerical tolerance for convergence for all tables (RMS, absolute value), 
                maximum number of iterations.
        """

        STD_VALUES_TYPE = float
        ALLOWED_VALUES_TYPES = (
            int, float, np.dtype('float64'), np.dtype('int64'))
        ALLOWED_TEXT_TYPE = str
        ALLOWED_SOLVERS = cp.installed_solvers()
        TOLERANCE_TESTS_RESULTS_CHECK = 0.02
        ROUNDING_DIGITS_RELATIVE_DIFFERENCE_DB = 5
        SPARSE_MATRIX_ZEROS_THRESHOLD = 0.3
        SQL_BATCH_SIZE = 1000
        SQL_MAX_BATCH_MEMORY_MB = 10
        SQL_BATCH_SIZE_MIN = 100
        SQL_BATCH_SIZE_MAX = 10000
        CVXPY_DEFAULT_SETTINGS = {
            'solver': 'SCIPY',
            'canon_backend': cp.SCIPY_CANON_BACKEND,
            'ignore_dpp': True,
        }
        MODEL_COUPLING_SETTINGS = {
            'allowed_norms': ['max_relative', 'max_absolute', 'l1', 'l2', 'linf'],
            # Per-table RELATIVE tolerance
            'relative_tolerance': 0.01,
            # Per-table ABSOLUTE minimum tolerance (minimum guard value)
            'absolute_minimum_guard_tolerance': 0.001,
            'max_iterations': 20,
        }

    _SUBGROUPS = [
        LiteralTypes,
        ConfigFiles,
        Labels,
        DefaultStructures,
        SymbolicDefinitions,
        NumericalSettings,
    ]

    @classmethod
    def __getattr__(cls, name):
        """Provide direct access to default settings by searching nested groups.

        Args:
            name (str): The name of the attribute to retrieve.

        Returns:
            Any: The requested constant or attribute.

        Raises:
            AttributeError: If the attribute is not found.
        """
        for subgroup in cls._SUBGROUPS:
            if hasattr(subgroup, name):
                return getattr(subgroup, name)
        raise AttributeError(
            f"Constant '{name}' not found in {cls.__name__}.")
