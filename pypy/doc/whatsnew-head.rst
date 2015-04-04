=======================
What's new in PyPy 2.5+
=======================

.. this is a revision shortly after release-2.5.1
.. startrev: cb01edcb59414d9d93056e54ed060673d24e67c1

.. branch: gc-incminimark-pinning-improve
Object Pinning is now used in `bz2` and `rzlib` (therefore also affects
Python's `zlib`). In case the data to compress/decompress is inside the nursery
(incminimark) it no longer needs to create a non-moving copy of it. This saves
one `malloc` and copying the data.  Additionally a new GC environment variable
is introduced (`PYPY_GC_MAX_PINNED`) primarily for debugging purposes.
