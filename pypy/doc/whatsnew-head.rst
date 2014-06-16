=======================
What's new in PyPy 2.4+
=======================

.. this is a revision shortly after release-2.3.x
.. startrev: ca9b7cf02cf4

.. branch: fix-bytearray-complexity
Bytearray operations no longer copy the bytearray unnecessarily

Added support for ``__getitem__``, ``__setitem__``, ``__getslice__``,
``__setslice__``,  and ``__len__`` to RPython
