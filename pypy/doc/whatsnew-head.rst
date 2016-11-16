==========================
What's new in PyPy2.7 5.6+
==========================

.. this is a revision shortly after release-pypy2.7-v5.6
.. startrev: 7e9787939641

.. branch: mappingproxy
.. branch: py3k-finish_time
.. branch: py3k-kwonly-builtin
.. branch: py3k_add_terminal_size
.. branch: testing-cleanup-py3k

.. branch: rpython-resync
Backport rpython changes made directly on the py3k and py3.5 branches.

.. branch: rpython-error-to-systemerror

Any uncaught RPython exception (from a PyPy bug) is turned into an
app-level SystemError.  This should improve the lot of users hitting an
uncaught RPython error.

.. branch: union-side-effects-2

Try to improve the consistency of RPython annotation unions.
