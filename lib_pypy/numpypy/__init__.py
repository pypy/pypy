from _numpypy import *
from .core import *

import sys
sys.modules.setdefault('numpy', sys.modules['numpypy'])
