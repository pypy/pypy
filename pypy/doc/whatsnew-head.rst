=======================
What's new in PyPy 2.6+
=======================

.. this is a revision shortly after release-2.6.0
.. startrev: 91904d5c5188

.. branch: use_min_scalar
Correctly resolve the output dtype of ufunc(array, scalar) calls.

.. branch: stdlib-2.7.10

Update stdlib to version 2.7.10

.. branch: issue2062

.. branch: disable-unroll-for-short-loops
The JIT no longer performs loop unrolling if the loop compiles to too much code.
