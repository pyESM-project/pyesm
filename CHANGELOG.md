# Changelog

All notable changes to CVXlab will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **`variable_domain` field for data tables**: replaces the old boolean `integer` field.
  Accepted values: `integer` (integer variables, $\mathbb{Z}$) or `boolean` (binary
  variables, $\{0,1\}$). Omitting the field keeps the default continuous domain.
  The deprecated `integer: true` syntax is still accepted with a warning and
  automatically migrated to `domain: integer`.
- Installation docs: new *Install from Dev Branch* section with `git+https` install
  instructions for users who want the latest unreleased features.
- Possibility to **run only a selection of scenarios** from Model.run_model() method, 
  by specifying the `scenario_idx` attribute as integer or list of integers 
  corresponding to the index of scenarios in the `Model.scenarios` property.
- Per-problem solver and solver-settings routing for multi-problem runs (backend: 
  `core.py`, `problem.py`, `database.py`).
- Centralized backward-compatibility helpers: added `cvxlab.backward_compat.BackwardCompat`
  to host short-lived translation helpers for deprecated public API (e.g., mapping
  `integrated_problems` → `solution_mode`). This keeps core modules clean and makes
  deprecation removal straightforward in future releases.
- **Sequential solution mode** (`solution_mode='sequential'` in `Model.run_model()`):
  multiple numerical sub-problems can now be solved in a user-defined order via the
  `sequential_solution_chain` argument. After each sub-problem is solved, endogenous
  results are exported to the SQLite database and hybrid variables are automatically
  passed downstream to subsequent problems in the chain.
- **`RunSettings` class** (`backend/run_settings.py`): centralizes collection and
  validation of all `run_model()` arguments (solution mode, solver, solver settings,
  scenario selection, sequential chain, integrated-solver tolerances). Removes scattered
  argument validation from `Core` and `Model`.
- **`ModelSettings` and `ModelPaths` classes** (`backend/model_settings.py`): replace
  `DotDict`-based settings and path containers with dedicated typed objects that
  validate eagerly on construction and expose attributes instead of dict keys.
  All backend modules (`core.py`, `database.py`, `index.py`, `problem.py`) updated
  to use attribute access.
- Added `cyipopt>=1.1.0` to the `solvers` optional extra in `pyproject.toml` for
  IPOPT support via pip (note: source-only on PyPI; Windows users should use
  `conda install -c conda-forge cyipopt`).

### Changed
- Reorganized backend solve flow; moved database comparison/cleanup into dedicated 
  helpers (`backend/database.py`, `backend/core.py`).
- Split nonlinear tutorial assets into separate `model_nonlinear` and `model_decomposition` 
  sets under `docs/source/tutorials/production_planning_nonlinear`.
- Bumped minimum `cvxpy` version to `>=1.9.1` (see `pyproject.toml`).
- Adjusted numerical default: `Defaults.NumericalSettings.SPARSE_MATRIX_ZEROS_THRESHOLD` 
  changed from `0.3` to `0.7` (`defaults.py`).
- Integration tests now run directly against tutorial model directories instead of
  isolated fixtures; the `sequential_problems` test key renamed to
  `production_planning_sequential` with an updated `sequential_solution_chain`
  (`data_calibration` → `planning_model`).
- Tutorial gallery: replaced `products_footprints_sequential` with a new
  `production_planning_sequential` tutorial (sequential calibration + planning
  workflow); renamed gallery entries "Production planning (non-linear)" →
  "Handling non-linearities" and "Production planning (decomposition)" →
  "Problem decomposition".

### Fixed
- **Backward-compatibility migration for `integer` field**: the migration block that
  converts `integer: true` → `domain: integer`.
  - Added backward-compatibility mapping for `integrated_problems` → `solution_mode`.
- README images now use absolute raw GitHub URLs so they render correctly on PyPI.
- Corrected GitHub organization URL (`cvxgrp` → `cvxlab`) throughout installation docs.
- Replaced unsupported `tab-set`/`tab-item` directives (sphinx-design) with plain RST
  in the citation section of the resources page.
- Integration tests and CI: integration tests now run across tutorial models and were 
  updated to cover solver routing and tutorial assets (`tests/integration/test_integration.py`).
- **Windows: hardened SQLite cleanup and DB restore** in sequential and integrated
  solver flows (`backend/core.py`, `support/sql_manager.py`, `support/file_manager.py`):
  explicitly close cursor and connection before file operations; use atomic
  `os.replace` in `FileManager.rename_file` (`force_overwrite` flag); emit a warning
  instead of crashing when a temp iteration DB is locked and cannot be deleted.

### Documentation
- Added package structure diagram (`_static/package_structure.png`) to
  `api_reference.rst` with a description of the class hierarchy
  (`Model` → `Core` → `Index` / `Database` / `Problem`, settings, support utilities).
- Added PyPI icon link to the Sphinx navbar (`conf.py`).
- Updated `index.rst` homepage: expanded description to mention parallel, sequential,
  and integrated solution modes; added "Linked-model orchestration" feature bullet;
  added GitHub Discussions link.
- Added `.. _installation:` cross-reference anchor to `installation.rst`.
- Updated user guide steps: conceptual model definition, data structures
  initialization, and numerical problem run pages revised; solution mode figure added.


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
