==========================
What's new in PyPy2.7 6.0+
==========================

.. this is a revision shortly after release-pypy-6.0.0
.. startrev: 2e04adf1b89f

.. branch: cpyext-subclass-setattr

Fix for python-level classes that inherit from C-API types, previously the
`w_obj` was not necessarily preserved throughout the lifetime of the `pyobj`
which led to cases where instance attributes were lost. Fixes issue #2793
