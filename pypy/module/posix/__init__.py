# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule
    
class Module(MixedModule):
    appleveldefs = {
    }
    interpleveldefs = {
    'open'      : 'interp_posix.open',
    'lseek'     : 'interp_posix.lseek',
    'write'     : 'interp_posix.write',
    'isatty'    : 'interp_posix.isatty',
    'read'      : 'interp_posix.read',
    'close'     : 'interp_posix.close',
    'ftruncate' : 'interp_posix.ftruncate',
    'fstat'     : 'interp_posix.fstat',
    'dup'       : 'interp_posix.dup'
    '__doc__'   : "space.wrap('Posix module')"
    }
