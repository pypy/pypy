=========================
What's new in PyPy 5.0.+
=========================

.. this is a revision shortly after release-5.0
.. startrev: b238b48f9138

.. branch: s390x-backend

The jit compiler backend implementation for the s390x architecutre.
The backend manages 64-bit values in the literal pool of the assembly instead of loading them as immediates.
It includes a simplification for the operation 'zero_array'. Start and length parameters are bytes instead of size.

