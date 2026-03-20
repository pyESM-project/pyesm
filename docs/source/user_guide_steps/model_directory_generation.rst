.. _generation-of-model-directory:

Generation of model directory
-----------------------------

This step initializes a new model workspace by creating a dedicated directory 
containing the necessary configuration template files required to create and
handle a CVXlab model.
This function is typically executed once at the beginning of the modeling process,
in the case of :ref:`model generation from scratch <model_generation_from_scratch>`.


**Overview**

- Creates a new directory to store all files related to a CVXlab model instance 
  (settings, input data, database, etc.).
- Supports both YAML (*.yml*) and Excel (*.xlsx*) templates for setup files, 
  depending on workflow preference.
- Optionally includes template files for user-defined symbolic operators and 
  constants, allowing customization without modifying the CVXlab repository.

API: :py:func:`cvxlab.create_model_dir`


**Typical Usage**

.. code-block:: python

    import cvxlab

    cvxlab.create_model_dir(
        model_dir_name="my_model",
        main_dir_path="path/to/parent",
        template_file_type="yml",  # or "xlsx"
        include_user_operators_template=False,
        include_user_constants_template=False,
    )


**Parameter descriptions:**

All arguments are optional and have sensible defaults. You can customize the 
directory creation as follows:

- ``model_dir_name``: Name of the model directory to create. Defaults to *model*.
- ``main_dir_path``: Path to the parent directory where the model directory will 
  be created. Defaults to the current working directory if not specified.
- ``template_file_type``: Format of the setup files, either *yml* or *xlsx*. 
  Defaults to *yml*.
- ``include_user_operators_template``: If *True*, includes a template file for 
  user-defined symbolic operators in the model directory. Defaults to *False*.
- ``include_user_constants_template``: If *True*, includes a template file for 
  user-defined constants types in the model directory. Defaults to *False*.
- ``force_overwrite``: If *True*, overwrites the directory if it already exists 
  without confirmation. Defaults to *False*.


**Workflow**

When :py:func:`cvxlab.create_model_dir` is called:

- The target directory is created at ``main_dir_path/model_dir_name``. If it already 
  exists, it is erased if ``force_overwrite`` is set, otherwise user confirmation 
  is required.

- Setup template files are generated in the chosen format:

  - If ``template_file_type`` is *yml*: three YAML files are created for sets, 
    variables, and problem structure.
  - If ``template_file_type`` is *xlsx*: a single Excel file is created with 
    three sheets for *sets*, *variables*, and *problem*.

- Optionally, template files for user-defined symbolic operators and constants 
  are copied into the directory if requested.

- The directory is ready for subsequent modeling steps.


**Generated files**

- Directory: *my_model* (or specified name) in the chosen parent path.
- Setup files:

  - YAML: *structure_sets.yml*, *structure_variables.yml*, *problem.yml*.
  - Excel: *model_settings.xlsx* (with three sheets: sets, variables, problem).

- Optional templates:

  - *user_defined_operators.py*: Template for custom symbolic operators.
  - *user_defined_constants.py*: Template for custom constants types.

These files provide the basic structure for defining sets, variables, and the 
symbolic problem, and can be edited as needed before proceeding to model 
initialization and data input.
