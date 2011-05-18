========================================================================
                          JIT documentation
========================================================================

:abstract:

    When PyPy is translated into an executable such as ``pypy-c``, the
    executable contains a full virtual machine that can optionally
    include a Just-In-Time compiler.  This JIT compiler is **generated
    automatically from the interpreter** that we wrote in RPython.

    This JIT Compiler Generator can be applied on interpreters for any
    language, as long as the interpreter itself is written in RPython
    and contains a few hints to guide the JIT Compiler Generator.


Content
------------------------------------------------------------

- Overview_: motivating our approach

- Notes_ about the current work in PyPy


.. _Overview: overview.html
.. _Notes: pyjitpl5.html
