import warnings

warnings.warn(
    "The 'numpy' module of PyPy is in-development and not complete. "
    "To avoid this warning, write 'import numpypy as numpy'. ")

from numpypy import *

import os

__version__ = '1.7'

def get_include():
    head, tail = os.path.split(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(head, 'include')

