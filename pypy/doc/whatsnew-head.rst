==========================
What's new in PyPy2.7 5.8+
==========================

.. this is a revision shortly after release-pypy2.7-v5.7.0
.. startrev: 44f31f6dd39f

Add cpyext interfaces for ``PyModule_New``

Correctly handle `dict.pop`` where the ``pop``
key is not the same type as the ``dict``'s and ``pop``
is called with a default (will be part of release 5.7.1)
Make rpython setslice able to resize the destination list.
Fixes issue #2196.

.. branch: fix-2198

Use the new resizing setslice to refactor list use by interp-level code.
Fixes issue #2198.


.. branch: issue2522

Fix missing tp_new on w_object called through multiple inheritance
(will be part of release 5.7.1)

.. branch: lstrip_to_empty_string

