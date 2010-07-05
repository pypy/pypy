# This __init__.py shows up in PyPy's app-level standard library.
# Let's try to prevent that confusion.
# Without this check, you would be able to do 'import __init__' from a pypy
# prompt

import sys; print sys.path
if __name__ != 'lib_pypy':
    raise ImportError, '__init__'
