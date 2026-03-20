.. _api_utility_functions:

Utility functions
=================

The following utility functions are available in CVXlab:


Guided interface
----------------

CVXlab provides a guided interactive interface that walks through the entire 
modeling workflow via a menu-driven session. This is the simplest way to get 
started with CVXlab, requiring no prior knowledge of the package APIs.

.. autofunction:: cvxlab.run


Model directory and instance management
---------------------------------------

.. autofunction:: cvxlab.create_model_dir
.. autofunction:: cvxlab.copy_user_defined_templates
.. autofunction:: cvxlab.transfer_setup_info_xlsx
.. autofunction:: cvxlab.handle_model_instance