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

build with::

  rpython/bin/rpython -Ojit pypy/goal/targetpypystandalone.py

This ends up with ``pypy-c`` binary in the main pypy directory. We suggest
to use virtualenv with the resulting pypy-c as the interpreter, you can
find more details about various installation schemes here:

http://doc.pypy.org/en/latest/getting-started.html#installing-pypy
