=======================
What's new in PyPy 2.5+
=======================

.. this is a revision shortly after release-2.5.1
.. startrev: cb01edcb59414d9d93056e54ed060673d24e67c1

Issue #2017: on non-Linux-x86 platforms, reduced the memory impact of
creating a lot of greenlets/tasklets.  Particularly useful on Win32 and
on ARM, where you used to get a MemoryError after only 2500-5000
greenlets (the 32-bit address space is exhausted).

.. branch: gc-incminimark-pinning-improve
Object Pinning is now used in `bz2` and `rzlib` (therefore also affects
Python's `zlib`). In case the data to compress/decompress is inside the nursery
(incminimark) it no longer needs to create a non-moving copy of it. This saves
one `malloc` and copying the data.  Additionally a new GC environment variable
is introduced (`PYPY_GC_MAX_PINNED`) primarily for debugging purposes.

.. branch: refactor-pycall
Make `*`-unpacking in RPython function calls completely equivalent to passing
the tuple's elements as arguments. In other words, `f(*(a, b))` now behaves 
exactly like `f(a, b)`.
