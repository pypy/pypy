import core
from core import *
import lib
from lib import *

from __builtin__ import bool, int, long, float, complex, object, unicode, str
from core import abs, max, min

__version__ = '1.7.0'

import os
def get_include():
    head, tail = os.path.split(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(head, '../include')


__all__ = ['__version__', 'get_include']
__all__ += core.__all__
__all__ += lib.__all__

#import sys
#sys.modules.setdefault('numpy', sys.modules['numpypy'])


