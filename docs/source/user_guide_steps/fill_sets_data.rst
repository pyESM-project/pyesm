.. _fill-sets-data:

Fill sets data (model coordinates)
==================================

In this step, the user fills the sets data, defined as the model *coordinates*. 

Based on the Sets structure defined by the user in previous steps, according to 
the notation and conventions defined in :ref:`sets_definition`, the blank file 
``sets.xlsx`` (with a structure automatically generated) is now filled with the 
corresponding data.


Generic file structure
----------------------

**Excel** has been chosen as the sole coordinates input format, due to the fact 
that models are usually defined by several Sets, each characterized by many 
coordinates and filters/aggregations categories. Using tabular format allows to 
easily visualize and manage the data, and to use Excel functionalities (e.g., 
lookup functions, etc.).

Below, an example of the generic ``sets.xlsx`` file structure is shown.


.. list-table:: Generic structure of each set tab in ``sets.xlsx`` file.
   :header-rows: 1
   :widths: 20 20 20 10

   * - <set_name>_Name
     - <set_name>_<filter_name_#>
     - <set_name>_<aggregation_name_#>
     - ...
   * - <str>
     - <str>
     - <str>
     - <str>
   * - ...
     - ...
     - ...
     - ...


.. rubric:: Fields description and conventions

Each Excel **tab** corresponds to a specific set defined in the model. Each set 
tab is named as ``_set_<SET_NAME>``, where ``<SET_NAME>`` is the capitalized name 
of the set, as defined in the model settings. This naming convention allows to 
easily identify the Set tables in the SQLite database. The ``_set_`` prefix 
(as well as other prefixes conventionally adopted elsewhere) are defined and 
customizable in :class:`cvxlab.defaults.Defaults.Labels`.

In each ``_set_<SET_NAME>`` tab, user fill Sets coordinates in the table above, 
structured as follows: 

- ``<set_name>_Name`` column corresponds to the Set coordinates names. This 
  column is **mandatory**, and must be filled with the actual coordinates of 
  the set.
- ``<set_name>_<filter_name_#>`` column corresponds to filters of the Set. 
  Only present in case the model includes filters for the set, and it is 
  optional to be filled by the user.
- ``<set_name>_<aggregation_name_#>`` column corresponds to aggregation categories 
  of the Set. Only present in case the model includes aggregation categories 
  for the set, and it is optional to be filled by the user.


Notes
-----

- There is no distinction between **Inter-problem sets** and **Dimensions sets** 
  in the ``sets.xlsx`` file. However, tabs for Inter-problem sets are expected to 
  present only the first column (i.e., the coordinates column), since this Set is 
  not expected to be filtered nor aggregatd.
- In running CVXlab models, it may be useful to update the sets data. Two potential 
  cases may occur:

  - In case of major updates, such as adding new sets or new coordinates may 
    affect other model settings (e.g. how variable are defined or shaped). This may 
    require the SQLite database and input files to be re-generated to reflect the new 
    model structure. 
  
  - In case *aggregation* categories need to be added, without changing Sets and 
    related coordinates or filters, the Sets can be updated, reflecting changes in 
    SQLite databases, without re-generating the database and input files. This 
    can be achieved by relying on the API method :py:meth:`~cvxlab.Model.update_sets_tables`, 
    which allows to update the sets data, without changing the model structure.


