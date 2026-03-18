API reference
=============

.. note::
  CVXlab is currently in **beta** (|version|). The package is functional but APIs 
  may change before the stable 1.0.1 release.
   

CVXlab is designed to be intuitive enough so that it may be used without diving 
into APIs structures. Reading :ref:`User Guide <user_guide>`, practicing with the 
tutorial notebook available in the :ref:`Tutorials <tutorials>` section, and  
looking at existing models in :ref:`Models gallery <models_gallery>` will suffice 
in acquainting you with the package. Nonetheless, API reference are here included 
for those who are comfortable reading technical documentation. 

The classes and functions documented in this section are those imported into the 
*CVXlab* namespace. The documentation is grouped the following sections:

- :ref:`Model <api_model>` documents the main package class cvxlab.Model, embedding 
  all the main package APIs necessary to generate, handle and solve the numerical model. 
- :ref:`Utility functions <api_utility_functions>` section documents various utility 
  functions available in the package, including the guided interactive interface 
  (:py:func:`cvxlab.run`) and functions for initializing model directory and handling 
  model class instances. 
- :ref:`Symbolic operators <api_symbolic_operators>` documents built-in symbolic
  operators available in CVXlab, including standard arithmetic operations, matrix
  operations, and various mathematical functions. Provides guidelines on how to
  create new or add built-in symbolic operators to the package.
- :ref:`Constants <api_constants_types>` documents the various built-in constants 
  data types available in CVXlab, necessary to assign numerical values to constants 
  in numerical problems. Provides guidelines on how to create new or add built-in 
  constant data types to the package.
- :ref:`Templates <api_templates>` documents the template modules included in the 
  CVXlab package, including user-defined symbolic operators and user-defined constants.
- :ref:`Defaults <api_defaults>` documents the cvxlab.constants module, which 
  includes various default settings used throughout the package that may be customized
  by the developer.


.. toctree::
   :hidden:
   :maxdepth: 1

   apidocs/model
   apidocs/utility_functions
   apidocs/symbolic_operators
   apidocs/constants_types
   apidocs/templates
   apidocs/defaults