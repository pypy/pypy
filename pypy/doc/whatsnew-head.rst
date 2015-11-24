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
