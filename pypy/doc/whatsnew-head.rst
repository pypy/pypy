==========================
What's new in PyPy2.7 7.0+
==========================

.. this is a revision shortly after release-pypy-7.0.0
.. startrev: 481c69f7d81f

.. branch: zlib-copying-third-time-a-charm

Make sure zlib decompressobjs have their streams deallocated immediately
on flush.

.. branch: zlib-copying-redux

Fix calling copy on already-flushed compressobjs.

.. branch: zlib-copying

The zlib module's compressobj and decompressobj now expose copy methods
as they do on CPython.


.. branch: math-improvements

Improve performance of long operations where one of the operands fits into
an int.

.. branch: regalloc-playgrounds

Improve register allocation in the JIT.

.. branch: unicode-utf8

Use utf8 internally to represent unicode, with the goal of never using rpython-level unicode
