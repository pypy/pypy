.. _jit:

JIT documentation
=================

:abstract:

    When a interpreter written in RPython is translated into an executable, the
    executable contains a full virtual machine that can optionally
    include a Just-In-Time compiler.  This JIT compiler is **generated
    automatically from the interpreter** that we wrote in RPython.

    This JIT Compiler Generator can be applied on interpreters for any
    language, as long as the interpreter itself is written in RPython
    and contains a few hints to guide the JIT Compiler Generator.


Content
-------

.. toctree::
   :hidden:

   overview
   pyjitpl5
   virtualizable

- :doc:`Overview <overview>`: motivating our approach

- :doc:`Notes <pyjitpl5>` about the current work in PyPy

- :doc:`Virtulizable <virtualizable>` how virtualizables work and what they are
  (in other words how to make frames more efficient).
