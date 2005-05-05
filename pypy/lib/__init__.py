# This __init__.py shows up in PyPy's app-level standard library.
# Let's try to prevent that confusion...
if __name__ != 'pypy.lib':
    raise ImportError, '__init__'
