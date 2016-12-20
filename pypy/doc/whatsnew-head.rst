==========================
What's new in PyPy2.7 5.6+
==========================

.. this is a revision shortly after release-pypy2.7-v5.6
.. startrev: 7e9787939641


Since a while now, PyPy preserves the order of dictionaries and sets.
However, the set literal syntax ``{x, y, z}`` would by mistake build a
set with the opposite order: ``set([z, y, x])``.  This has been fixed.
Note that CPython is inconsistent too: in 2.7.12, ``{5, 5.0}`` would be
``set([5.0])``, but in 2.7.trunk it is ``set([5])``.  PyPy's behavior
changed in exactly the same way because of this fix.


.. branch: mappingproxy
.. branch: py3k-finish_time
.. branch: py3k-kwonly-builtin
.. branch: py3k_add_terminal_size
.. branch: testing-cleanup-py3k

.. branch: rpython-resync
Backport rpython changes made directly on the py3k and py3.5 branches.

.. branch: rpython-error-to-systemerror

Any uncaught RPython exception (from a PyPy bug) is turned into an
app-level SystemError.  This should improve the lot of users hitting an
uncaught RPython error.

.. branch: union-side-effects-2

Try to improve the consistency of RPython annotation unions.

.. branch: pytest-2.9.2

.. branch: clean-exported-state

Clean-ups in the jit optimizeopt

.. branch: conditional_call_value_4

Add jit.conditional_call_elidable(), a way to tell the JIT "conditonally
call this function" returning a result.

.. branch: desc-specialize

Refactor FunctionDesc.specialize() and related code (RPython annotator).

.. branch: raw-calloc

.. branch: issue2446

Assign ``tp_doc`` to the new TypeObject's type dictionary ``__doc__`` key
so it will be picked up by app-level objects of that type

.. branch: cling-support

Module cppyy now uses cling as its backend (Reflex has been removed). The
user-facing interface and main developer tools (genreflex, selection files,
class loader, etc.) remain the same.  A libcppyy_backend.so library is still
needed but is now available through PyPI with pip: PyPy-cppyy-backend.

The Cling-backend brings support for modern C++ (11, 14, etc.), dynamic
template instantations, and improved integration with CFFI for better
performance.  It also provides interactive C++ (and bindings to that).

.. branch: better-PyDict_Next

Improve the performance of ``PyDict_Next``. When trying ``PyDict_Next`` on a
typedef dict, the test exposed a problem converting a ``GetSetProperty`` to a
``PyGetSetDescrObject``. The other direction seem to be fully implemented.
This branch made a minimal effort to convert the basic fields to avoid
segfaults, but trying to use the ``PyGetSetDescrObject`` will probably fail.

.. branch: stdlib-2.7.13

Updated the implementation to match CPython 2.7.13 instead of 2.7.13.
