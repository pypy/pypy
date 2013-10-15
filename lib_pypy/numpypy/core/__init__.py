from __future__ import division, absolute_import, print_function

from . import multiarray
from . import umath
from . import numeric
from .numeric import *
from . import fromnumeric
from .fromnumeric import *
from . import shape_base
from .shape_base import *

from .fromnumeric import amax as max, amin as min, \
    round_ as round
from .numeric import absolute as abs

__all__ = []
__all__ += numeric.__all__
__all__ += fromnumeric.__all__
__all__ += shape_base.__all__
