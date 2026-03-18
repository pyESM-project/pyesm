# Changelog

All notable changes to CVXlab will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **Python ≥ 3.11 required**: bumped `requires-python` from `>=3.8`; removed `from __future__ import annotations` across the codebase.
- **Frontend package added**: new `frontend/` package providing a guided CLI for model setup and interaction. Public entry point is `cvxlab.frontend.run()`, which accepts all `Model.__init__`, solver, and frontend-only parameters, partitions them into typed groups, and drives an interactive menu loop. Key modules: `interface` (entry point and menu engine), `session` (`SessionConfig` / `ModelState` dataclasses), `actions` (decorator-based `@menu_action` registry building `MAIN_MENU`), and `display` (terminal UI helpers).
- **Centralized `Defaults.LiteralTypes`**: shared `Literal` type aliases consolidated into `Defaults.LiteralTypes`, replacing scattered definitions across modules.
- **Integrated-solving convergence refactored**: reworked convergence algorithm in `Core.solve_integrated_problems()` with new `skip_tables` argument for selectively excluding tables from convergence checks.
- **User-defined constants and operators**: new template modules (`user_defined_constants.py`, `user_defined_operators.py`) enabling custom symbolic extensions (GitHub issue #109).
- **DataFrame / SQLite data-handling fixes**: improved `util.normalize_dataframe()` for NaN handling, fixed CSV reading for missing values, and corrected `SQLManager.dataframe_to_table()` string-type conversion.
- **Pandas 2.3 compatibility**: pinned `pandas==2.3.3`, removed deprecated `errors='ignore'` arguments, fixed boolean-import issues introduced by pandas 3.0.

### Planned
- Stable 1.0.1 release.
- API stabilization.
- Complete documentation coverage.
- First interface function to ease user interaction.

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
