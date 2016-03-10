=========================
What's new in PyPy 5.0.+
=========================

.. this is a revision shortly after release-5.0
.. startrev: b238b48f9138

.. branch: memop-simplify3

Simplification of zero_array. Start and end index are scaled using res ops (or cpu scaling) rather than doing it manually.

.. branch: s390x-backend

The jit compiler backend implementation for the s390x architecutre.

.. branch: s390x-enhance-speed

Refactoring to only store 64-bit values in the literal pool of the assembly. Generated machine code uses less space and runs faster.

