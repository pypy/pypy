==========================
What's new in PyPy2.7 6.0+
==========================

.. this is a revision shortly after release-pypy-6.0.0
.. startrev: f22145c34985


.. branch: issue2752

Fix a rare GC bug that was introduced more than one year ago, but was
not diagnosed before issue #2752.

.. branch: gc-hooks

Introduce GC hooks, as documented in doc/gc_info.rst
