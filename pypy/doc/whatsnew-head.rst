=======================
What's new in PyPy 2.6+
=======================

.. this is a revision shortly after release-2.6.0
.. startrev: 91904d5c5188

.. branch: use_min_scalar
Correctly resolve the output dtype of ufunc(array, scalar) calls.

.. branch: stdlib-2.7.10

Update stdlib to version 2.7.10

.. branch: issue2062

.. branch: disable-unroll-for-short-loops
The JIT no longer performs loop unrolling if the loop compiles to too much code.

.. branch: run-create_cffi_imports

Build cffi import libraries as part of translation by monkey-patching an 
additional task into translation

.. branch: int-float-list-strategy

Use a compact strategy for Python lists that mix integers and floats,
at least if the integers fit inside 32 bits.  These lists are now
stored as an array of floats, like lists that contain only floats; the
difference is that integers are stored as tagged NaNs.  (This should
have no visible effect!  After ``lst = [42, 42.5]``, the value of
``lst[0]`` is still *not* the float ``42.0`` but the integer ``42``.)

.. branch: cffi-callback-onerror
.. branch: cffi-new-allocator

.. branch: unicode-dtype

Partial implementation of unicode dtype and unicode scalars.

.. branch: dtypes-compatibility

Improve compatibility with numpy dtypes; handle offsets to create unions,
fix str() and repr(), allow specifying itemsize, metadata and titles, add flags,
allow subclassing dtype
