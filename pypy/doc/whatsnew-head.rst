=========================
What's new in PyPy2.7 5.3+
=========================

.. this is a revision shortly after release-pypy2.7-v5.3
.. startrev: 873218a739f1

.. 418b05f95db5
Improve CPython compatibility for ``is``. Now code like ``if x is ():``
works the same way as it does on CPython.  See http://pypy.readthedocs.io/en/latest/cpython_differences.html#object-identity-of-primitive-values-is-and-id .

.. pull request #455
Add sys.{get,set}dlopenflags, for cpyext extensions.

.. branch: fix-gen-dfa

Resolves an issue with the generator script to build the dfa for Python syntax.

.. branch: z196-support

Fixes a critical issue in the register allocator and extends support on s390x.
PyPy runs and translates on the s390x revisions z10 (released February 2008, experimental)
and z196 (released August 2010) in addition to zEC12 and z13.
To target e.g. z196 on a zEC12 machine supply CFLAGS="-march=z196" to your shell environment.

.. branch: s390x-5.3-catchup

Implement the backend related changes for s390x.

.. branch: incminimark-ll_assert
.. branch: vmprof-openbsd

.. branch: testing-cleanup

Simplify handling of interp-level tests and make it more forward-
compatible.

