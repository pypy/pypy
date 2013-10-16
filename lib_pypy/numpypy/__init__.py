from . import core
from .core import *
from . import lib
from .lib import *

from __builtin__ import bool, int, long, float, complex, object, unicode, str

from .core import round, abs, max, min

__version__ = '1.7.0'

__all__ = ['__version__']
__all__ += core.__all__
__all__ += lib.__all__

#import sys
#sys.modules.setdefault('numpy', sys.modules['numpypy'])
