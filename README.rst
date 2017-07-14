=====================================
PyPy: Python in Python Implementation
=====================================

Welcome to PyPy!

PyPy is both an implementation of the Python programming language, and
an extensive compiler framework for dynamic language implementations.
You can build self-contained Python implementations which execute
independently from CPython.

The home page is:

    http://pypy.org/

If you want to help developing PyPy, this document might help you:

    http://doc.pypy.org/

It will also point you to the rest of the documentation which is generated
from files in the pypy/doc directory within the source repositories. Enjoy
and send us feedback!

    the pypy-dev team <pypy-dev@python.org>


Building
========

First switch to or download the correct branch.  The basic choices are
``default`` for Python 2.7 and, for Python 3.X, the corresponding py3.X
branch (e.g. ``py3.5``).

Build with:

.. code-block:: console

    $ rpython/bin/rpython -Ojit pypy/goal/targetpypystandalone.py

This ends up with a ``pypy-c`` or ``pypy3-c`` binary in the main pypy
directory.  We suggest to use virtualenv with the resulting
pypy-c/pypy3-c as the interpreter; you can find more details about
various installation schemes here:

    http://doc.pypy.org/en/latest/install.html
