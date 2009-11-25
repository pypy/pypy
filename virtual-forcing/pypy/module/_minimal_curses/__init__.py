try:
    import _curses
except ImportError:
    import _minimal_curses as _curses   # when running on top of pypy-c

from pypy.interpreter.mixedmodule import MixedModule
from pypy.module._minimal_curses import fficurses
from pypy.module._minimal_curses import interp_curses
from pypy.rlib.nonconst import NonConstant


class Module(MixedModule):
    """ Low-level interface for curses module,
    not meant to be used directly
    """

    appleveldefs = {
        'error'          : 'app_curses.error',
    }
    
    interpleveldefs = {
        'setupterm'      : 'interp_curses.setupterm',
        'tigetstr'       : 'interp_curses.tigetstr',
        'tparm'          : 'interp_curses.tparm',
    }

for i in dir(_curses):
    val = getattr(_curses, i)
    if i.isupper() and type(val) is int:
        Module.interpleveldefs[i] = "space.wrap(%s)" % val
