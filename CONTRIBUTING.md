# Contributing

Thank you for considering contributing to CVXlab! Contributions are welcome from 
everyone.

- [Reporting Bugs and Suggestions](#reporting-bugs-and-suggestions)
- [Contribution Workflow](#contribution-workflow)
- [Development Guidelines](#development-guidelines)
- [Release Process](#release-process)
- [License](#license)


(reporting-bugs-and-suggestions)=
## Reporting Bugs and Suggestions

If you find a bug, please report it by opening an issue on our 
[GitHub Issues](https://github.com/cvxlab/cvxlab/issues) page. 
Include as much detail as possible:
- Operating system and Python version
- CVXlab version
- Minimal code example to reproduce the issue
- Expected vs. actual behavior
- Full error traceback if applicable

We welcome new feature suggestions! Please open an issue on our 
[GitHub Issues](https://github.com/cvxlab/cvxlab/issues) page and describe:
- The feature you would like to see
- Why you need it and what problem it solves
- How it should work (if you have ideas)
- Any relevant examples or references

(contribution-workflow)=
## Contribution Workflow
This section provides guidelines on how to setup development environment, and how 
to contribute to the package as an external contributor or as a core developer.

### Branching Model
All pull requests should target the `dev` branch (not `main`). 
When working on branches, consider the the following branching model:

| Branch | Purpose | Who Uses |
|--------|---------|----------|
| `main` | Stable releases only (v1.0.0, v1.0.1, etc.) | Everyone (read-only) |
| `dev` | Active development and integration | Contributors & Maintainers |
| `feature/*` | Individual features (e.g., `feature/new-solver`) | Contributors |
| `release/*` | Release preparation (e.g., `release/1.1.0`) | Maintainers |
| `hotfix/*` | Urgent fixes to main (e.g., `hotfix/critical-bug`) | Maintainers |

### Development Environment Setup
Regardless of your contribution method, set up a local development environment:

**Update environment** if dependencies change:
```sh
conda env update -f environment.yml --prune
conda env export --no-builds > environment.yml
```

**Reinstall after changes** to `pyproject.toml`:
```sh
python -m pip uninstall cvxlab -y
python -m pip install -e .[dev,docs]
```

### For External Contributors (Fork Workflow)
If you're contributing from outside the core team, follow the fork workflow:

1. **Fork** the repository on GitHub
2. **Clone** your fork locally:
   ```sh
   git clone https://github.com/YOUR_USERNAME/cvxlab.git
   cd cvxlab
   ```
3. **Add upstream** remote:
   ```sh
   git remote add upstream https://github.com/cvxlab/cvxlab.git
   ```
4. **Create a feature branch** from `dev` (see branching rules):
   ```sh
   git checkout dev
   git pull upstream dev
   git checkout -b feature/my-feature
   ```
5. **Make your changes** and commit with clear messages
6. **Push** to your fork:
   ```sh
   git push origin feature/my-feature
   ```
7. **Open a pull request** on GitHub targeting the `dev` branch (not `main`)


### For Core Team Members (Direct Repository Access)
If you have write access to the main repository, work directly on feature branches:

1. **Clone** the repository:
   ```sh
   git clone https://github.com/cvxlab/cvxlab.git
   cd cvxlab
   ```
2. **Create a feature branch** from `dev` (see branching rules):
   ```sh
   git checkout dev
   git pull origin dev
   git checkout -b feature/my-feature
   ```
3. **Set up development environment** using `conda`:
   ```sh
   conda env create -f environment.yml
   conda activate cvxlab_env
   ```
4. **Install CVXlab locally** in editable mode:
   ```sh
   python -m pip uninstall cvxlab -y
   python -m pip install -e .[dev,docs]
   ```
5. **Verify installation**:
   ```sh
   python -c "from importlib.metadata import version; print(version('cvxlab'))"
   ```
6. **Make your changes** and commit with clear messages
7. **Push** to the main repository:
   ```sh
   git push origin feature/my-feature
   ```
8. **Open a pull request** on GitHub targeting the `dev` branch
9. (Optional) **Update environment.yml** if dependencies change:
   ```sh
   conda env update -f environment.yml --prune
   conda env export --no-builds > environment.yml
   ```

(development-guidelines)=
## Development Guidelines
Follow the guidelines below when contributing code to CVXlab.


### Code Style
- **Follow PEP 8**: Use Python's official style guide for clean, readable code
- **Meaningful names**: Use descriptive variable, function, and class names that 
   clearly indicate their purpose
- **Modular design**: Keep functions and methods focused on a single responsibility
- **Type hints**: Add type annotations to function signatures for better code 
   clarity and IDE support

### Documentation
- **Write clear docstrings**: Use **Google style** docstrings for all public 
   functions, classes, and methods
  ```python
  def solve_model(model: Model, solver: str = "ECOS") -> dict:
      """Solve the optimization model using the specified solver.

      Args:
          model: The CVXlab model instance to solve.
          solver: Name of the solver to use (default: "ECOS").

      Returns:
          Dictionary containing solution status, objective value, and variables.

      Raises:
          SolverError: If the solver fails to find a solution.
      """
      ...
  ```
- **Check docstring quality**: Run `pydocstyle` to verify docstring compliance
  ```sh
  python -m pydocstyle cvxlab/
  ```
- **Update documentation**: If your changes affect user-facing functionality, 
   update the relevant pages in `docs/source/`
- **Build and preview docs locally**: Verify documentation builds without 
   errors and renders correctly
  ```sh
  python -m sphinx -b html docs/source docs/_build/html
  # Inspect documentation (Windows)
  start docs/_build/html/index.html
  ```

### Testing
- **Add tests for new features**: Write tests for new functionality in the `tests/` 
   directory
- **Run all tests**: Ensure your changes don't break existing functionality
  ```sh
  pytest
  ```

### Commit Messages
- Use clear, descriptive commit messages
- Start with a verb in present tense: "Add", "Fix", "Update", "Refactor"
- Keep the first line under 72 characters
- Add details in the commit body if needed
  ```
  Add support for quadratic constraints
  
  - Implement QuadraticConstraint class
  - Add tests for quadratic expressions
  - Update documentation with examples
  ```

#### Pull Request Guidelines
- **One feature per PR**: Keep pull requests focused on a single feature or bug fix
- **Reference issues**: Link to related GitHub issues in your PR description
- **Describe changes**: Explain what you changed and why
- **Request reviews**: Tag relevant maintainers for review
- **Respond to feedback**: Address review comments promptly and professionally


(release-process)=
## Release Process

### Version Numbering

CVXlab follows **Semantic Versioning** (SemVer):

```
MAJOR.MINOR.PATCH[pre-release]
  1  .  0  .  0     b1
```

- **MAJOR**: Breaking changes (e.g., 1.0.0 → 2.0.0)
- **MINOR**: New features, backward compatible (e.g., 1.0.0 → 1.1.0)
- **PATCH**: Bug fixes only (e.g., 1.0.0 → 1.0.1)
- **Pre-release**: 
  - `a1, a2, ...` = Alpha (unstable)
  - `b1, b2, ...` = Beta (feature complete, testing)
  - `rc1, rc2, ...` = Release Candidate (final testing)

(license)=
## License

By contributing to CVXlab, you agree that your contributions will be licensed under 
the Apache License 2.0.