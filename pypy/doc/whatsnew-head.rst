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

.. branch: issue2444

Fix ``PyObject_GetBuffer`` and ``PyMemoryView_GET_BUFFER``, which leaked
memory and held references. Add a finalizer to CPyBuffer, add a
PyMemoryViewObject with a PyBuffer attached so that the call to 
``PyMemoryView_GET_BUFFER`` does not leak a PyBuffer-sized piece of memory.
Properly call ``bf_releasebuffer`` when not ``NULL``.

.. branch: boehm-rawrefcount

Support translations of cpyext with the Boehm GC (for special cases like
revdb).

.. branch: strbuf-as-buffer

Implement StringBuffer.get_raw_address (missing feature for the buffer protocol).
More generally it is now possible to obtain the address of any object (if it
is readonly) without pinning it.

.. branch: cpyext-cleanup
.. branch: api_func-refactor

Refactor cpyext initialisation.

.. branch: cpyext-from2

Fix a test failure introduced by strbuf-as-buffer

.. branch: cpyext-FromBuffer

Do not recreate the object in PyMemoryView_FromBuffer, rather pass it to
the returned PyMemoryViewObject, to take ownership of it. Fixes a ref leak.

.. branch: issue2464

Give (almost?) all GetSetProperties a valid __objclass__.

.. branch: TreeStain/fixed-typo-line-29-mostly-to-most-1484469416419
.. branch: TreeStain/main-lines-changed-in-l77-l83-made-para-1484471558033

.. branch: missing-tp_new

Improve mixing app-level classes in c-extensions, especially if the app-level
class has a ``tp_new`` or ``tp_dealloc``. The issue is that c-extensions expect
all the method slots to be filled with a function pointer, where app-level will
search up the mro for an appropriate function at runtime. With this branch we
now fill many more slots in the c-extenion type objects.
Also fix for c-extension type that calls ``tp_hash`` during initialization
(str, unicode types), and fix instantiating c-extension types from built-in
classes by enforcing an order of instaniation.

.. branch: rffi-parser-2

rffi structures in cpyext can now be created by parsing simple C headers.
Additionally, the cts object that holds the parsed information can act like
cffi's ffi objects, with the methods cts.cast() and cts.gettype().
