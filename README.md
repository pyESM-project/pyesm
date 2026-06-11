![CVXlab Logo](https://raw.githubusercontent.com/cvxlab/cvxlab/main/docs/source/_static/CVXlab_logo_dark.png)

[![PyPI version](https://img.shields.io/pypi/v/cvxlab?label=PyPI&logo=pypi)](https://pypi.org/project/cvxlab/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/cvxlab)](https://pypi.org/project/cvxlab/)
[![Documentation Status](https://readthedocs.org/projects/cvxlab/badge/?version=latest)](https://cvxlab.readthedocs.io/en/latest/?badge=latest)
[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.20644006.svg)](https://doi.org/10.5281/zenodo.20644006)

CVXlab is an open-source Python laboratory for modeling and solving convex optimization problems. 
It extends [cvxpy](https://www.cvxpy.org/) with user-friendly interfaces, integrated data 
management and support for multiple, interconnected optimization models.

## Table of Contents
- [Installation](#installation)
- [Quick Overview](#quick-overview)
- [Guided Interface](#guided-interface)
- [Documentation](#documentation)
- [Changelog](#changelog)
- [Contributing](#contributing)
- [Community & Support](#community--support)
- [License](#license)
- [Citing](#citing)

## Installation
**From PyPI**
```bash
pip install cvxlab
```
**From source (for development):**
```bash
git clone https://github.com/cvxlab/cvxlab.git
cd cvxlab
pip install -e .[dev]
```
See the [Installation Guide](https://cvxlab.readthedocs.io/en/latest/installation.html) 
for detailed instructions.

## Quick Overview
CVXlab allows you to define optimization problems using:
- **General-purpose model generator**: Model problems as you would mathematically, without restrictive solver forms.
- **Almost no-code required**: Build models using Excel or YAML—no coding required.
- **Centralized data management**: Centralized data input/output via SQLite database.
- **Multi-Model Support**: Generate and solve multiple integrated or decomposed optimization problems.
- **Powerful engine embedded**: Built on cvxpy package, leveraging its extensive solver support.

**Typical workflow:**

The figure below provides a synthetic and simplified overview of the CVXlab modeling 
process.

![CVXlab workflow](https://raw.githubusercontent.com/cvxlab/cvxlab/main/docs/source/_static/CVXlab_nutshell.png)

In generating and handling a CVXlab model, the user must follow the five fundamental
activities summarized below:

- The user **defines the model settings** and the related structure: model scope, 
  structure of variables, and list of mathematical expressions, including equalities,
  inequalities and (eventually) objective function. This activity requires almost no
  coding, as model definition can be performed via Excel files or YAML configuration 
  files.
- The user proceeds by **generating a CVXlab Model object**, consisting in a *Python* 
  class instance embedding all the model settings and the methods useful to manage 
  the model. At the same time, other items are generated, including the **SQLite 
  database file** (to store all model data), and the Excel files serving as blank 
  templates for collecting exogenous data from the user. 
- The user **feeds input data** to SQLite database through blank Excel template 
  files. Specifically, user defines the data input required to characterize exogenous 
  model variables.
- The **numerical problem is generated**, exogenous data fetched from the database, 
  and the problem is solved through CVXPY engine.
- If problem is successfuly solved, **results are finally exported** to the database.
  Due to the structure of the relational database, it can be easily linked and 
  inspected via Excel or SQL queries, or imported into Business Intelligence tools 
  (such as *PowerBI* or *Tableau*) for more elaborated data visualization and analysis.

## Guided Interface
CVXlab provides an interactive guided interface that walks you through the full 
modeling workflow — from directory setup to solving — via a terminal menu. 
Launch it with `cvxlab.frontend.run()`:

```python
import cvxlab

cvxlab.run(
    model_dir_name='my_model',
    main_dir_path='/path/to/models',
)
```

The `run()` signature mirrors the parameters of `Model.__init__()` and 
`Model.run_model()`, with additional frontend-only options such as 
`model_structure_file` and `template_file_type`.
All parameters are optional; when omitted, the backend applies its own defaults 
or the interactive prompt asks for specific instructions.

## Documentation
Full documentation is available at [cvxlab.readthedocs.io](https://cvxlab.readthedocs.io/en/latest/).
You can also browse the source documentation in the [docs/source](docs/source) directory.

## Changelog
See [CHANGELOG.md](CHANGELOG.md) for a detailed history of changes.

## Contributing
We welcome contributions from the community! Please see [CONTRIBUTING.md](CONTRIBUTING.md) 
for guidelines.

## Community & Support
Submit issues and ideas for improvements in GitHub [GitHub Issues](https://github.com/cvxlab/cvxlab/issues)

## License
Licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.

## Citing
If you use CVXlab in academic work, please cite the software as follows.

**APA**
> Rocco, M. V. (2026). *CVXlab* (Version 1.0.1) [Software]. Zenodo. https://doi.org/10.5281/zenodo.20644006

**BibTeX**
```bibtex
@software{rocco_cvxlab_2026,
  author    = {Rocco, Matteo V.},
  title     = {{CVXlab}},
  version   = {1.0.1},
  year      = {2026},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.20644006},
  url       = {https://doi.org/10.5281/zenodo.20644006}
}
```

For industry or non-academic use, we'd love to hear your feedback — reach out via
email at matteovincenzo.rocco@polimi.it.