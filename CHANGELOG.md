# Changelog

All notable changes to CVXlab will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.1] - 11 June 2026

### Added
- **Frontend CLI** (`cvxlab.frontend.run()`): interactive menu-driven interface for
  model setup and execution. Modules: `interface`, `session`, `actions`, `display`.
- **User-defined constants and operators**: template modules
  (`user_defined_constants.py`, `user_defined_operators.py`) for custom symbolic
  extensions; auto-imported when present in the model directory (issue #109).
- **CSV input data support**: models can now use CSV files as input data sources
  (issue #103).
- **`Model.update_sets_tables()`**: update set definitions in an existing SQLite
  database without full regeneration.
- **`skip_tables` argument** in `Model.run_model()` / `Core.solve_integrated_problems()`:
  selectively exclude tables from convergence checks.

### Changed
- **Python ≥ 3.11 required**: bumped `requires-python`; removed
  `from __future__ import annotations` across the codebase.
- **Integrated-solving convergence refactored**: reworked algorithm in
  `Core.solve_integrated_problems()`.
- **Centralized `Defaults.LiteralTypes`**: shared `Literal` type aliases consolidated,
  replacing scattered definitions.
- **Identity matrix constant**: now accepts a single set as dimensional argument
  (issue #101).
- `description` columns in data structures are no longer processed, allowing free
  text (issue #105).
- Removed `CRITICAL` log level from `Logger`.
- Pinned `pandas==2.3.3`; removed deprecated `errors='ignore'` arguments (pandas 3.0
  compatibility).

### Fixed
- `util.normalize_dataframe()`: improved NaN handling and blank-fill logic.
- `SQLManager.dataframe_to_table()`: string-type conversion and batch flag reset.
- `Database.load_data_input_files_to_database()`: input directory path reference and
  NaN replacement before SQLite export.
- `Database.generate_blank_data_input_files()`: corrected `excel_dir_path` argument.
- `Model.run_model()`: selected solver now correctly logged.
- `util.pivot_dataframe_to_data_structure()`: handle missing primary key column in
  Excel setup files.
- Various error-catching improvements for symbolic expression validation and settings
  inconsistencies (issues #102, #104, #106, #107, #108).

### Documentation
- Tutorials merged into `resources` page; standalone `tutorials.rst` removed.
- Added production planning (non-linear) tutorial.
- Added Models gallery and Publications sections to resources page.
- Restructured `index.rst`: workflow figure promoted, navigation table updated.

## [1.0.1b1] - 17 December 2025

### Fixed
- Bug fix following 1.0.0b1 (incremented beta to 1.0.1b1)

## [1.0.0b1] - 14 November 2025

### Added
- `Model` class for optimization problem management
- SQLite-backed data management via `Database` and `SQLManager`
- CVXPY integration for convex optimization solving
- Support for independent and integrated (coupled) problem solving
- Excel and YAML-based model settings definition
- Symbolic expression parsing and validation
- Initial set of built-in operators and constants
- Basic logging and error handling framework

### Documentation
- Initial user guide with workflow steps
- API reference documentation
- Tutorial: Simple model example
- Installation guide
- Contributing guidelines

### Known Limitations
- Documentation under active development
- API subject to change before 1.0.0 stable
- Limited tutorial coverage
- Limited test converage
