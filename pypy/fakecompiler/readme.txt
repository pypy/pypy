Attention!

This folder's purpose is to support testing using the compiled PyPy.
At the moment, our applevel compiler is a bit slow to make this
useful. Therefore, this folder exists.

If the compiled pypy's current directory has a file named
"fakecompiler.py", like this folder, then every compilation
that is either "exec" or "eval" gets compiled using CPython.

Requirements:

- this folder must be writable
- there must be a file named "pythonname" which contains the
  complete filename of a Python 1.4.2 compatible binary.
  Please, add this by hand for your installation.
