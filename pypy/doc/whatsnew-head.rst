=========================
What's new in PyPy 5.1+
=========================

.. this is a revision shortly after release-5.1
.. startrev: aa60332382a1

.. branch: techtonik/introductionrst-simplify-explanation-abo-1460879168046

.. branch: gcheader-decl

Reduce the size of generated C sources.


.. branch: remove-objspace-options

Remove a number of options from the build process that were never tested and
never set. Fix a performance bug in the method cache.

.. branch: bitstring

JIT: use bitstrings to compress the lists of read or written descrs
that we attach to EffectInfo.  Fixes a problem we had in
remove-objspace-options.

.. branch: cpyext-for-merge

Update cpyext C-API support After this branch, we are almost able to support 
upstream numpy via cpyext, so we created (yet another) fork of numpy at 
github.com/pypy/numpy with the needed changes. Among the significant changes 
to cpyext:
  - allow c-snippet tests to be run with -A so we can verify we are compatible
  - fix many edge cases exposed by fixing tests to run with -A
  - issequence() logic matches cpython
  - make PyStringObject and PyUnicodeObject field names compatible with cpython
  - add prelminary support for PyDateTime_*
  - support PyComplexObject, PyFloatObject, PyDict_Merge, PyDictProxy,
    PyMemoryView_*, _Py_HashDouble, PyFile_AsFile, PyFile_FromFile,
  - PyAnySet_CheckExact, PyUnicode_Concat
  - improve support for PyGILState_Ensure, PyGILState_Release, and thread
    primitives, also find a case where CPython will allow thread creation
    before PyEval_InitThreads is run, dissallow on PyPy 
  - create a PyObject-specific list strategy
  - rewrite slot assignment for typeobjects
  - improve tracking of PyObject to rpython object mapping
  - support tp_as_{number, sequence, mapping, buffer} slots

(makes the pypy-c bigger; this was fixed subsequently by the
share-cpyext-cpython-api branch)

.. branch: share-mapdict-methods-2

Reduce generated code for subclasses by using the same function objects in all
generated subclasses.

.. branch: share-cpyext-cpython-api

.. branch: cpyext-auto-gil

CPyExt tweak: instead of "GIL not held when a CPython C extension module
calls PyXxx", we now silently acquire/release the GIL.  Helps with
CPython C extension modules that call some PyXxx() functions without
holding the GIL (arguably, they are theorically buggy).
