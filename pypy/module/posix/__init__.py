# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule

import os
exec 'import %s as posix' % os.name

class Module(MixedModule):
    """This module provides access to operating system functionality that is
standardized by the C Standard and the POSIX standard (a thinly
disguised Unix interface).  Refer to the library manual and
corresponding Unix manual entries for more information on calls."""

    applevel_name = os.name

    appleveldefs = {
    'error'      : 'app_posix.error',
    'stat_result': 'app_posix.stat_result',
    'fdopen'     : 'app_posix.fdopen',
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
    'lstat'     : 'interp_posix.lstat',
    'dup'       : 'interp_posix.dup',
    'dup2'      : 'interp_posix.dup2',
    'system'    : 'interp_posix.system',
    'unlink'    : 'interp_posix.unlink',
    'remove'    : 'interp_posix.remove',
    'getcwd'    : 'interp_posix.getcwd',
    'getcwdu'    : 'interp_posix.getcwdu',
    'chdir'     : 'interp_posix.chdir',
    'mkdir'     : 'interp_posix.mkdir',
    'rmdir'     : 'interp_posix.rmdir',
    'environ'   : 'interp_posix.get(space).w_environ',
    'listdir'   : 'interp_posix.listdir',
    'strerror'  : 'interp_posix.strerror',
    'pipe'      : 'interp_posix.pipe',
    'chmod'     : 'interp_posix.chmod',
    'rename'    : 'interp_posix.rename',
    '_exit'     : 'interp_posix._exit',
    'abort'     : 'interp_posix.abort',
    'access'    : 'interp_posix.access',
    }
    if hasattr(os, 'ftruncate'):
        interpleveldefs['ftruncate'] = 'interp_posix.ftruncate'
    if hasattr(os, 'putenv'):
        interpleveldefs['putenv'] = 'interp_posix.putenv'
    if hasattr(posix, 'unsetenv'): # note: emulated in os
        interpleveldefs['unsetenv'] = 'interp_posix.unsetenv'
    if hasattr(os, 'getpid'):
        interpleveldefs['getpid'] = 'interp_posix.getpid'
    if hasattr(os, 'link'):
        interpleveldefs['link'] = 'interp_posix.link'
    if hasattr(os, 'symlink'):
        interpleveldefs['symlink'] = 'interp_posix.symlink'
    if hasattr(os, 'readlink'):
        interpleveldefs['readlink'] = 'interp_posix.readlink'
    if hasattr(os, 'fork'):
        interpleveldefs['fork'] = 'interp_posix.fork'
    if hasattr(os, 'waitpid'):
        interpleveldefs['waitpid'] = 'interp_posix.waitpid'
    if hasattr(os, 'chown'):
        interpleveldefs['chown'] = 'interp_posix.chown'
    if hasattr(os, 'chroot'):
        interpleveldefs['chroot'] = 'interp_posix.chroot'
    if hasattr(os, 'confstr'):
        interpleveldefs['confstr'] = 'interp_posix.confstr'
    if hasattr(os, 'ctermid'):
        interpleveldefs['ctermid'] = 'interp_posix.ctermid'
    if hasattr(os, 'fchdir'):
        interpleveldefs['fchdir'] = 'interp_posix.fchdir'
    if hasattr(os, 'fpathconf'):
        interpleveldefs['fpathconf'] = 'interp_posix.fpathconf'
    if hasattr(os, 'getegid'):
        interpleveldefs['getegid'] = 'interp_posix.getegid'
    if hasattr(os, 'geteuid'):
        interpleveldefs['geteuid'] = 'interp_posix.geteuid'
    if hasattr(os, 'getgid'):
        interpleveldefs['getgid'] = 'interp_posix.getgid'
    if hasattr(os, 'getuid'):
        interpleveldefs['getuid'] = 'interp_posix.getuid'    
    if hasattr(os, 'getpgid'):
        interpleveldefs['getpgid'] = 'interp_posix.getpgid'
    if hasattr(os, 'getpid'):
        interpleveldefs['getpid'] = 'interp_posix.getpid'
    if hasattr(os, 'getppid'):
        interpleveldefs['getppid'] = 'interp_posix.getppid'
    if hasattr(os, 'getpgrp'):
        interpleveldefs['getpgrp'] = 'interp_posix.getpgrp'
    if hasattr(os, 'getsid'):
        interpleveldefs['getsid'] = 'interp_posix.getsid'
    if hasattr(os, 'getlogin'):
        interpleveldefs['getlogin'] = 'interp_posix.getlogin'
    if hasattr(os, 'getgroups'):
        interpleveldefs['getgroups'] = 'interp_posix.getgroups'
    if hasattr(os, 'getloadavg'):
        interpleveldefs['getloadavg'] = 'interp_posix.getloadavg'
    

for constant in dir(os):
    value = getattr(os, constant)
    if constant.isupper() and type(value) is int:
        Module.interpleveldefs[constant] = "space.wrap(%s)" % value
if hasattr(os, 'confstr_names'):
    Module.interpleveldefs['confstr_names'] = "space.wrap(%s)" % os.confstr_names
if hasattr(os, 'pathconf_names'):
    Module.interpleveldefs['pathconf_names'] = "space.wrap(%s)" % os.pathconf_names
