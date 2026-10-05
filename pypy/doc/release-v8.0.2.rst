===============================================================
PyPy v8.0.2: release of python 2.7 and 3.12 released 2026-XX-XX
===============================================================

.. note::
   This is a pre-release announcement. When the release actually happens, it
   will be announced on the PyPy blog_

..
  updated to e68dc64be52

Changelog
=========


For all versions
----------------

- Make flaky tests more reliable
- Make RPython more python3-friendly (:issue:`5601`)
- Use vmprof 0.6.0 version profiles, which include a timestamp (:issue:`5598`).
- Fix a bug in the revdb symbolic parser, which is also used by vmprof (:issue:`5593`)


Bugfixes
~~~~~~~~

- Use shared argument types when specializing JIT markers (:issue:`5606`)
  A ``can_enter_jit`` argument can be a *subclass* of the corresponding
  ``jit_merge_point`` argument. This can then produce wrong pointer types on
  the C level. More recent gccs reject those as errors (they were warnings
  before). Instead, use the shared argument repr to insert the correct cast


Speedups and enhancements
~~~~~~~~~~~~~~~~~~~~~~~~~

- Speed up ``rsre_jit::RSreJitDriver::repr`` for tests
- Add more simplification rules for int operations (:issue:`5587`)
  This also adds a check to prevent redundant rules


Python 3.12
-----------

- Fix failing tests for windows64

Bugfixes including missing compatibility with CPython 3.12
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Implement ``PY_VECTORCALL_ARGUMENTS_OFFSET`` protocol in ``PyObject_VectorcallDict``
