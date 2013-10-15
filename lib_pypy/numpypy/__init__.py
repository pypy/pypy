from . import core
from .core import *
from . import lib
from .lib import *

from __builtin__ import bool, int, long, float, complex, object, unicode, str

from .core import round, abs, max, min

__version__ = '1.7.0'

import os
def get_include():
    """
    Return the directory that contains the NumPy \\*.h header files.

    Extension modules that need to compile against NumPy should use this
    function to locate the appropriate include directory.

    Notes
    -----
    When using ``distutils``, for example in ``setup.py``.
    ::

        import numpy as np
        ...
        Extension('extension_name', ...
                include_dirs=[np.get_include()])
        ...

    """
    try:
        import numpy
    except:
        # running from pypy source directory
        head, tail = os.path.split(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(head, '../include')
    else:
        # using installed numpy core headers
        import numpy.core as core
        d = os.path.join(os.path.dirname(core.__file__), 'include')
    return d


__all__ = ['__version__', 'get_include']
__all__ += core.__all__
__all__ += lib.__all__

#import sys
#sys.modules.setdefault('numpy', sys.modules['numpypy'])
