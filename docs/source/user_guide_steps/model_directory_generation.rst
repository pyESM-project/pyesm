.. _generation-of-model-directory:

Generation of model directory
-----------------------------

This step initializes a new model workspace by creating a dedicated directory 
containing all the necessary configuration template files required to create and
handle a CVXlab model.
This function is typically executed once at the beginning of the modeling process,
in the case of :ref:`model generation from scratch <model_generation_from_scratch>`.

**Overview**

- All files related to the model instance will be stored in this directory (settings 
  files, data input files, database, etc.).
- It is possible to choose between YAML (*.yml*) or Excel (*.xlsx*) templates for 
  setup files, depending on user's workflow preferences.
- Template files for user-defined symbolic operators and constants types can be 
  optionally included to facilitate their definition and integration into the model 
  without modifying the CVXlab repository.

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

**What's Generated**

- A new directory named *my_model* in the specified *../parent* path.
- Setup file/s in the chosen format:
    - case of YAML: *structure_sets.yml*, *structure_variables.yml*, *problem.yml*.
    - case of Excel: *model_settings.xlsx* (with the above information organized in three tabs).
- Optionally, template files for user-defined symbolic operators and constants types.
