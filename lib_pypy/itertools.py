try:
    from __builtin_itertools import *
    from __builtin_itertools import __doc__
except ImportError:
    from _itertools import *
    from _itertools import __doc__
