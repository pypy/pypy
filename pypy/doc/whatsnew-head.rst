=========================
What's new in PyPy 4.1.+
=========================

.. this is a revision shortly after release-4.0.1
.. startrev: 4b5c840d0da2

.. branch: numpy-1.10

Fix tests to run cleanly with -A and start to fix micronumpy for upstream numpy
which is now 1.10.2

.. branch: osx-flat-namespace

Fix the cpyext tests on OSX by linking with -flat_namespace

.. branch: anntype

Refactor and improve exception analysis in the annotator.

.. branch: posita/2193-datetime-timedelta-integrals

Fix issue #2193. ``isinstance(..., int)`` => ``isinstance(..., numbers.Integral)`` 
to allow for alternate ``int``-like implementations (e.g., ``future.types.newint``)

.. branch: faster-rstruct

Improve the performace of struct.unpack, which now directly reads inside the
string buffer and directly casts the bytes to the appropriate type, when
allowed. Unpacking of floats and doubles is about 15 times faster now, while
for integer types it's up to ~50% faster for 64bit integers.

.. branch: wrap-specialisation

Remove unnecessary special handling of space.wrap().

.. branch: compress-numbering

Improve the memory signature of numbering instances in the JIT.

.. branch: fix-trace-too-long-heuristic

Improve the heuristic when disable trace-too-long

.. branch: fix-setslice-can-resize

Make rpython setslice able to resize the destination list & use that to
refactor list use by interp-level code. Fixes #2196 & #2198

.. branch: anntype2

A somewhat random bunch of changes and fixes following up on branch 'anntype'. Highlights:

- Implement @doubledispatch decorator and use it for intersection() and difference().

- Turn isinstance into a SpaceOperation

- Create a few direct tests of the fundamental annotation invariant in test_model.py

- Remove bookkeeper attribute from DictDef and ListDef.

.. branch: cffi-static-callback

.. branch: vecopt-absvalue

- Enhancement. Removed vector fields from AbstractValue.

.. branch: memop-simplify2

Simplification. Backends implement too many loading instructions, only having a slightly different interface.
Four new operations (gc_load/gc_load_indexed, gc_store/gc_store_indexed) replace all the
commonly known loading operations

.. branch: more-rposix

Move wrappers for OS functions from `rpython/rtyper` to `rpython/rlib` and 
turn them into regular RPython functions. Most RPython-compatible `os.*` 
functions are now directly accessible as `rpython.rposix.*`.
