=========================
What's new in PyPy 5.0.+
=========================

.. this is a revision shortly after release-5.0.0
.. startrev: 6d13e55b962a

.. branch: memop-simplify3

Simplification of zero_array. Start and end index are scaled using res ops (or cpu scaling) rather than doing it manually.

.. branch: s390x-backend

The jit compiler backend implementation for the s390x architecutre.
