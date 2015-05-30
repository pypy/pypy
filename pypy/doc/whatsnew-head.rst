=======================
What's new in PyPy 2.6+
=======================

.. this is a revision shortly after release-2.6.0
.. startrev: 2ac87a870acf562301840cace411e34c1b96589c

.. branch: fix-result-types

branch fix-result-types:
* Refactor dtype casting and promotion rules for consistency and compatibility
with CNumPy.
* Refactor ufunc creation.
* Implement np.promote_types().
