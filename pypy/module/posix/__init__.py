# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule
from pypy.rpython.module.ll_os import RegisterOs

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
    'tmpfile'    : 'app_posix.tmpfile',
    'popen'      : 'app_posix.popen',
    }
    if os.name == 'nt':
        appleveldefs.update({
                'popen2' : 'app_posix.popen2',
                'popen3' : 'app_posix.popen3',
                'popen4' : 'app_posix.popen4',
                })

    if hasattr(os, 'wait'):
        appleveldefs['wait'] = 'app_posix.wait'
        
    interpleveldefs = {
    'open'      : 'interp_posix.open',
    'lseek'     : 'interp_posix.lseek',
    'write'     : 'interp_posix.write',
    'isatty'    : 'interp_posix.isatty',
    'read'      : 'interp_posix.read',
    'close'     : 'interp_posix.close',
    'closerange': 'interp_posix.closerange',
    'fstat'     : 'interp_posix.fstat',
    'stat'      : 'interp_posix.stat',
    'lstat'     : 'interp_posix.lstat',
    'stat_float_times' : 'interp_posix.stat_float_times',
    'dup'       : 'interp_posix.dup',
    'dup2'      : 'interp_posix.dup2',
    'access'    : 'interp_posix.access',
    'times'     : 'interp_posix.times',
    'system'    : 'interp_posix.system',
    'unlink'    : 'interp_posix.unlink',
    'remove'    : 'interp_posix.remove',
    'getcwd'    : 'interp_posix.getcwd',
    'chdir'     : 'interp_posix.chdir',
    'mkdir'     : 'interp_posix.mkdir',
    'rmdir'     : 'interp_posix.rmdir',
    'environ'   : 'interp_posix.get(space).w_environ',
    'listdir'   : 'interp_posix.listdir',
    'strerror'  : 'interp_posix.strerror',
    'pipe'      : 'interp_posix.pipe',
    'chmod'     : 'interp_posix.chmod',
    'rename'    : 'interp_posix.rename',
    'umask'     : 'interp_posix.umask',
    '_exit'     : 'interp_posix._exit',
    'utime'     : 'interp_posix.utime',
    '_statfields': 'interp_posix.getstatfields(space)',
    }

    if os.name == 'nt':
        interpleveldefs['urandom'] = 'interp_posix.win32_urandom'

    if hasattr(os, 'chown'):
        interpleveldefs['chown'] = 'interp_posix.chown'
    if hasattr(os, 'ftruncate'):
        interpleveldefs['ftruncate'] = 'interp_posix.ftruncate'
    if hasattr(os, 'fsync'):
        interpleveldefs['fsync'] = 'interp_posix.fsync'
    if hasattr(os, 'fdatasync'):
        interpleveldefs['fdatasync'] = 'interp_posix.fdatasync'
    if hasattr(os, 'putenv'):
        interpleveldefs['putenv'] = 'interp_posix.putenv'
    if hasattr(posix, 'unsetenv'): # note: emulated in os
        interpleveldefs['unsetenv'] = 'interp_posix.unsetenv'
    if hasattr(os, 'kill'):
        interpleveldefs['kill'] = 'interp_posix.kill'
        interpleveldefs['abort'] = 'interp_posix.abort'
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
    if hasattr(os, 'openpty'):
        interpleveldefs['openpty'] = 'interp_posix.openpty'
    if hasattr(os, 'waitpid'):
        interpleveldefs['waitpid'] = 'interp_posix.waitpid'
    if hasattr(os, 'execv'):
        interpleveldefs['execv'] = 'interp_posix.execv'
    if hasattr(os, 'execve'):
        interpleveldefs['execve'] = 'interp_posix.execve'
    if hasattr(os, 'uname'):
        interpleveldefs['uname'] = 'interp_posix.uname'
    if hasattr(os, 'sysconf'):
        interpleveldefs['sysconf'] = 'interp_posix.sysconf'
        interpleveldefs['sysconf_names'] = 'space.wrap(os.sysconf_names)'
    if hasattr(os, 'ttyname'):
        interpleveldefs['ttyname'] = 'interp_posix.ttyname'

    for name in ['setsid', 'getuid', 'geteuid', 'getgid', 'getegid', 'setuid',
                 'seteuid', 'setgid', 'setegid', 'getpgrp', 'setpgrp',
                 'getppid', 'getpgid', 'setpgid', 'setreuid', 'setregid',
                 'getsid', 'setsid']:
        if hasattr(os, name):
            interpleveldefs[name] = 'interp_posix.%s' % (name,)
    # not visible via os, inconsistency in nt:
    if hasattr(posix, '_getfullpathname'):
        interpleveldefs['_getfullpathname'] = 'interp_posix._getfullpathname'
    if hasattr(os, 'chroot'):
        interpleveldefs['chroot'] = 'interp_posix.chroot'
    
    for name in RegisterOs.w_star:
        if hasattr(os, name):
            interpleveldefs[name] = 'interp_posix.' + name

    def __init__(self, space, w_name):
        backend = space.config.translation.backend
        # the Win32 urandom implementation isn't going to translate on JVM or CLI
        # so we have to remove it
        if 'urandom' in self.interpleveldefs and (backend == 'cli' or backend == 'jvm'):
            del self.interpleveldefs['urandom']
        MixedModule.__init__(self, space, w_name)

    def startup(self, space):
        from pypy.module.posix import interp_posix
        interp_posix.get(space).startup(space)
        
for constant in dir(os):
    value = getattr(os, constant)
    if constant.isupper() and type(value) is int:
        Module.interpleveldefs[constant] = "space.wrap(%s)" % value
