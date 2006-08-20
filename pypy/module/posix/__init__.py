# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule

import os
exec 'import %s as posix' % os.name

class Module(MixedModule):
    """This module provides access to operating system functionality that is
standardized by the C Standard and the POSIX standard (a thinly
disguised Unix interface).  Refer to the library manual and
corresponding Unix manual entries for more information on calls."""

    appleveldefs = {
        'error': 'app_posix.error',
        'stat_result': 'app_posix.stat_result',
        'fdopen': 'app_posix.fdopen',
    }
    
    interpleveldefs = {
        'environ': 'interp_posix.get(space).w_environ'
    }
    
    for func_name in ['ftruncate', 'putenv', 'unsetenv', 'getpid', 'link',
        'symlink', 'readlink', 'fork', 'waitpid', 'chown', 'chroot',
        'confstr', 'ctermid', 'fchdir', 'fpathconf', 'getegid', 'geteuid',
        'getgid', 'getuid', 'getpgid', 'getpid', 'getppid', 'getpgrp',
        'getsid', 'getlogin', 'getgroups', 'getloadavg', 'lchown', 'pathconf',
        'minor', 'major', 'access', 'abort', '_exit', 'rename', 'chmod',
        'pipe', 'strerror', 'listdir', 'rmdir', 'mkdir', 'chdir', 'getcwdu',
        'getcwd', 'remove', 'unlink', 'system', 'dup2', 'dup', 'lstat',
        'stat', 'fstat', 'close', 'read', 'write', 'isatty', 'lseek', 'open',
        'sysconf', 'wait', 'uname', 'umask', 'ttyname']:
        if hasattr(os, func_name):
            interpleveldefs[func_name] = 'interp_posix.%s' % func_name
    
for constant in dir(os):
    value = getattr(os, constant)
    if constant.isupper() and type(value) is int:
        Module.interpleveldefs[constant] = "space.wrap(%s)" % value
for const in ['confstr_names', 'pathconf_names', 'sysconf_names']:
    if hasattr(os, const):
        Module.interpleveldefs[const] = "space.wrap(%s)" % getattr(os, const)
