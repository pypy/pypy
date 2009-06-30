
from pypy.interpreter.mixedmodule import MixedModule
import termios
from pypy.rlib.nonconst import NonConstant

class Module(MixedModule):
    "This module provides an interface to the Posix calls for tty I/O control.\n\
    For a complete description of these calls, see the Posix or Unix manual\n\
    pages. It is only available for those Unix versions that support Posix\n\
    termios style tty I/O control.\n\
    \n\
    All functions in this module take a file descriptor fd as their first\n\
    argument. This can be an integer file descriptor, such as returned by\n\
    sys.stdin.fileno(), or a file object, such as sys.stdin itself."

    appleveldefs = {
        'error'       : 'app_termios.error',
    }
    
    interpleveldefs = {
        'tcdrain'     : 'interp_termios.tcdrain',
        'tcflow'      : 'interp_termios.tcflow',
        'tcflush'     : 'interp_termios.tcflush',
        'tcgetattr'   : 'interp_termios.tcgetattr',
        'tcsendbreak' : 'interp_termios.tcsendbreak',
        'tcsetattr'   : 'interp_termios.tcsetattr',
    }

import termios
from pypy.module.termios import interp_termios

# XXX this is extremaly not-portable, but how to prevent this?

for i in dir(termios):
    val = getattr(termios, i)
    if i.isupper() and type(val) is int:
        Module.interpleveldefs[i] = "space.wrap(%s)" % val

