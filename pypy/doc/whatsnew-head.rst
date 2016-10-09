==========================
What's new in PyPy2.7 5.4+
==========================

.. this is a revision shortly after release-pypy2.7-v5.4
.. startrev: 522736f816dc

.. branch: rpython-resync
Backport rpython changes made directly on the py3k and py3.5 branches.

.. branch: buffer-interface
Implement PyObject_GetBuffer, PyMemoryView_GET_BUFFER, and handles memoryviews
in numpypy

.. branch: force-virtual-state
Improve merging of virtual states in the JIT in order to avoid jumping to the
preamble. Accomplished by allocating virtual objects where non-virtuals are
expected.

.. branch: conditional_call_value_3
JIT residual calls: if the called function starts with a fast-path
like "if x.foo != 0: return x.foo", then inline the check before
doing the CALL.  For now, string hashing is about the only case.

.. branch: search-path-from-libpypy

The compiled pypy now looks for its lib-python/lib_pypy path starting
from the location of the *libpypy-c* instead of the executable. This is
arguably more consistent, and also it is what occurs anyway if you're
embedding pypy.  Linux distribution packagers, take note!  At a minimum,
the ``libpypy-c.so`` must really be inside the path containing
``lib-python`` and ``lib_pypy``.  Of course, you can put a symlink to it
from somewhere else.  You no longer have to do the same with the
``pypy`` executable, as long as it finds its ``libpypy-c.so`` library.

.. branch: _warnings

CPython allows warning.warn(('something', 1), Warning), on PyPy this
produced a "expected a readable buffer object" error. Test and fix.

.. branch: stricter-strip

CPython rejects 'a'.strip(buffer(' ')); only None, str or unicode are
allowed as arguments. Test and fix for str and unicode

.. branch: faulthandler

Port the 'faulthandler' module to PyPy default.  This module is standard
in Python 3.3 but can also be installed from CPython >= 2.6 from PyPI.

.. branch: test-cpyext

Refactor cpyext testing to be more pypy3-friendly.

.. branch: better-error-missing-self

Improve the error message when the user forgot the "self" argument of a method.


.. fb6bb835369e
Change the ``timeit`` module: it now prints the average time and the standard
deviation over 7 runs by default, instead of the minimum. The minimum is often
misleading.

.. branch: stdlib-2.7.11

Update stdlib to version 2.7.11

.. branch: vendor/stdlib
.. branch: stdlib-2.7.12

Update stdlib to version 2.7.12
