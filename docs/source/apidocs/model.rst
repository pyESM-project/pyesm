.. _api_model:

Model
=====

The cvxlab.Model class includes all the main package APIs necessary to
generate, handle and solve the numerical model.

.. autoclass:: cvxlab.Model
   :no-members:
   :no-undoc-members:


Model initialization and setup
------------------------------

.. automethod:: cvxlab.Model.__init__
.. automethod:: cvxlab.Model.initialize_model_environment
.. automethod:: cvxlab.Model.refresh_database_and_initialize_problem
.. automethod:: cvxlab.Model.run_model


Model data management methods
-----------------------------

.. automethod:: cvxlab.Model.generate_input_data_files
.. automethod:: cvxlab.Model.load_results_to_database
.. automethod:: cvxlab.Model.reinitialize_sqlite_database
.. automethod:: cvxlab.Model.update_sets_tables


Attributes and properties
-------------------------

.. autoattribute:: cvxlab.Model.sets
.. autoattribute:: cvxlab.Model.data_tables
.. autoattribute:: cvxlab.Model.variables
.. autoattribute:: cvxlab.Model.scenarios
.. autoattribute:: cvxlab.Model.is_problem_solved


Helper methods
--------------

.. automethod:: cvxlab.Model.set
.. automethod:: cvxlab.Model.variable
.. automethod:: cvxlab.Model.check_model_results