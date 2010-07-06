# This __init__.py shows up in PyPy's app-level standard library.
# Let's try to prevent that confusion...
import sys; print sys.path
if __name__ != 'lib_pypy':
    raise ImportError, '__init__'
