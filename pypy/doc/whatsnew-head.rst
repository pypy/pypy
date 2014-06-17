=======================
What's new in PyPy 2.4+
=======================

.. this is a revision shortly after release-2.3.x
.. startrev: ca9b7cf02cf4

.. branch: fix-bytearray-complexity
Bytearray operations no longer copy the bytearray unnecessarily

Added support for ``__getitem__``, ``__setitem__``, ``__getslice__``,
``__setslice__``,  and ``__len__`` to RPython

.. branch: stringbuilder2-perf
Give the StringBuilder a more flexible internal structure, with a
chained list of strings instead of just one string. This make it
more efficient when building large strings, e.g. with cStringIO().

Also, use systematically jit.conditional_call() instead of regular
branches. This lets the JIT make more linear code, at the cost of
forcing a bit more data (to be passed as arguments to
conditional_calls). I would expect the net result to be a slight
slow-down on some simple benchmarks and a speed-up on bigger
programs.
