from _numpypy import *
from .core import *
from .lib import *

import _numpypy
__all__ = _numpypy.__all__

import sys
sys.modules.setdefault('numpy', sys.modules['numpypy'])
