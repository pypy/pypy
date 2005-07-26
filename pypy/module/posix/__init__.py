# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule

import os

class Module(MixedModule):
    appleveldefs = {
    'error'     : 'app_posix.error',
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
    'stat'      : 'interp_posix.stat',
    'dup'       : 'interp_posix.dup',
    '__doc__'   : "space.wrap('Posix module')",
    '__name__'  : "space.wrap('The builtin posix module')",
    }

for constant in ['EX_CANTCREAT', 'EX_CONFIG', 'EX_DATAERR', 'EX_IOERR',
                 'EX_NOHOST', 'EX_NOINPUT', 'EX_NOPERM', 'EX_NOUSER',
                 'EX_OK', 'EX_OSERR', 'EX_OSFILE', 'EX_PROTOCOL',
                 'EX_SOFTWARE', 'EX_TEMPFAIL', 'EX_UNAVAILABLE', 'EX_USAGE',
                 'F_OK', 'NGROUPS_MAX', 'O_APPEND', 'O_CREAT', 'O_DIRECT',
                 'O_DIRECTORY', 'O_DSYNC', 'O_EXCL', 'O_LARGEFILE', 'O_NDELAY',
                 'O_NOCTTY', 'O_NOFOLLOW', 'O_NONBLOCK', 'O_RDONLY', 'O_RDWR',
                 'O_RSYNC', 'O_SYNC', 'O_TRUNC', 'O_WRONLY', 'R_OK', 'TMP_MAX',
                  'W_OK', 'X_OK']:
    try:
        Module.interpleveldefs[constant] = ("space.wrap(%s)" %
                                            (getattr(os, constant), ))
    except AttributeError:
        pass