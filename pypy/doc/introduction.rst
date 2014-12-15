What is PyPy?
=============

In common parlance, PyPy has been used to mean two things.  The first is the
:ref:`RPython translation toolchain <rpython:index>`, which is a framework for generating
dynamic programming language implementations.  And the second is one
particular implementation that is so generated --
an implementation of the Python_ programming language written in
Python itself.  It is designed to be flexible and easy to experiment with.

This double usage has proven to be confusing, and we are trying to move
away from using the word PyPy to mean both things.  From now on we will
try to use PyPy to only mean the Python implementation, and say the
:ref:`RPython translation toolchain <rpython:index>` when we mean the framework.

Some older documents, presentations, papers and videos will still have the old
usage.  You are hereby warned.

We target a large variety of platforms, small and large, by providing a
compiler toolsuite that can produce custom Python versions.  Platform, memory
and threading models, as well as the JIT compiler itself, are aspects of the
translation process - as opposed to encoding low level details into the
language implementation itself.

For more details, have a look at our :doc:`architecture overview <architecture>`.

.. _Python: http://python.org
.. _
