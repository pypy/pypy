# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule

import os

class Module(MixedModule):
    """This module provides access to operating system functionality that is
standardized by the C Standard and the POSIX standard (a thinly
disguised Unix interface).  Refer to the library manual and
corresponding Unix manual entries for more information on calls."""

    appleveldefs = {
    'error'      : 'app_posix.error',
    'stat_result': 'app_posix.stat_result',
    }
    
    interpleveldefs = {
    'open'      : 'interp_posix.open',
    'lseek'     : 'interp_posix.lseek',
    'write'     : 'interp_posix.write',
    'isatty'    : 'interp_posix.isatty',
    'read'      : 'interp_posix.read',
    'close'     : 'interp_posix.close',
    'fstat'     : 'interp_posix.fstat',
    'stat'      : 'interp_posix.stat',
    'dup'       : 'interp_posix.dup',
    'system'    : 'interp_posix.system',
    }
    if hasattr(os, 'ftruncate'):
        interpleveldefs['ftruncate'] = 'interp_posix.ftruncate'


for constant in ['EX_CANTCREAT', 'EX_CONFIG', 'EX_DATAERR', 'EX_IOERR',
                 'EX_NOHOST', 'EX_NOINPUT', 'EX_NOPERM', 'EX_NOUSER',
                 'EX_OK', 'EX_OSERR', 'EX_OSFILE', 'EX_PROTOCOL',
                 'EX_SOFTWARE', 'EX_TEMPFAIL', 'EX_UNAVAILABLE', 'EX_USAGE',
                 'F_OK', 'NGROUPS_MAX', 'O_APPEND', 'O_CREAT', 'O_DIRECT',
                 'O_DIRECTORY', 'O_DSYNC', 'O_EXCL', 'O_LARGEFILE', 'O_NDELAY',
                 'O_NOCTTY', 'O_NOFOLLOW', 'O_NONBLOCK', 'O_RDONLY', 'O_RDWR',
                 'O_RSYNC', 'O_SYNC', 'O_TRUNC', 'O_WRONLY', 'R_OK', 'TMP_MAX',
                 'WCONTINUED', 'WNOHANG', 'WUNTRACED', 'W_OK', 'X_OK']:
    try:
        Module.interpleveldefs[constant] = ("space.wrap(%s)" %
                                            (getattr(os, constant), ))
    except AttributeError:
        pass
