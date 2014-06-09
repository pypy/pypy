=======================
What's new in PyPy 2.4+
=======================

.. this is a revision shortly after release-2.3.x
.. startrev: b2cc67adbaad

Added support for the stdlib gdbm module via cffi

Annotator cleanups

.. branch: release-2.3.x

.. branch: unify-call-ops

.. branch: fix-bytearray-complexity
Bytearray operations no longer copy the bytearray unnecessarily

Added support for ``__getitem__``, ``__setitem__``, ``__getslice__``,
``__setslice__``,  and ``__len__`` to RPython
