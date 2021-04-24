============================
What's new in PyPy3.7 7.3.4+
============================

.. this is a revision shortly after release-pypy-7.3.4
.. startrev: 9c11d242d78c

.. branch: hpy

Merge latest hpy


.. branch: py3.7-errormsg-improvements

Produce better error messages for IndentationErrors (showing statement and line
that opened the block that is missing), AttributeErrors and NameErrors (showing
suggestions which name could have been meant instead in case of typos). This
follows the upcoming CPython 3.10 features.
