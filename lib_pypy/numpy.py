import warnings
import sys
if 'numpypy' not in sys.modules:
    warnings.warn(
        "The 'numpy' module of PyPy is in-development and not complete. "
        "To avoid this warning, write 'import numpypy as numpy'. ",
        UserWarning) # XXX is this the best warning type?

from numpypy import *
import numpypy
__all__ = numpypy.__all__
del numpypy
