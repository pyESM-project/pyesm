.. _api_constants_types:

Constant data types
===================

CVXlab supports a variety of built-in constants data types (see next section). 
In defining models, it may be necessary to define other constants. This can be 
accomplished the following two ways:

1. **Local user-defined constants**. Ideal for model users, whihc can define custom 
   constants in local model directory by defining the related function in the 
   *user_defined_constants.py* module, that will be automatically loaded in 
   generating Model class instance. This way, users can extend the package with 
   their own custom constants without modifying the package code (ideal for model 
   users). See :ref:`user defined constants template <api_user_defined_constants>` 
   for detailed instructions on how to define and use local user-defined constants.

2. **Adding new built-in constant**. Adding a new constant directly in the current 
   package module ``cvxlab.support.util_constants`` simply defines a new function 
   in this module, that will be embedded in the package as a built-in constant. 
   This approach is ideal **only in case** a constant is expected to be widely used across 
   different models and users.


.. _built-in-constants-types-reference:

Built-in constants types reference
----------------------------------

.. automodule:: cvxlab.support.util_constants
  :members:
  :undoc-members: 
  :show-inheritance:
  :exclude-members: 
