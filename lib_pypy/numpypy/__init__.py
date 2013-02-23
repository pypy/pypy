from _numpypy import *
from .core import *
from .lib import *

from __builtin__ import bool, int, long, float, complex, object, unicode, str

import _numpypy
__all__ = _numpypy.__all__

import sys
sys.modules.setdefault('numpy', sys.modules['numpypy'])
