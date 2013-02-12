# Package initialisation
from pypy.interpreter.mixedmodule import MixedModule
from rpython.rtyper.module.ll_os import RegisterOs

import os, sys
exec 'import %s as posix' % os.name

# this is the list of function which is *not* present in the posix module of
# IronPython 2.6, and that we want to ignore for now
lltype_only_defs = [
    'chown', 'chroot', 'closerange', 'confstr', 'confstr_names', 'ctermid', 'dup',
    'dup2', 'execv', 'execve', 'fchdir', 'fchmod', 'fchown', 'fdatasync', 'fork',
    'forkpty', 'fpathconf', 'fstatvfs', 'fsync', 'ftruncate', 'getegid', 'geteuid',
    'getgid', 'getgroups', 'getloadavg', 'getlogin', 'getpgid', 'getpgrp', 'getppid',
    'getsid', 'getuid', 'kill', 'killpg', 'lchown', 'link', 'lseek', 'major',
    'makedev', 'minor', 'mkfifo', 'mknod', 'nice', 'openpty', 'pathconf', 'pathconf_names',
    'pipe', 'readlink', 'setegid', 'seteuid', 'setgid', 'setgroups', 'setpgid', 'setpgrp',
    'setregid', 'setreuid', 'setsid', 'setuid', 'stat_float_times', 'statvfs',
    'statvfs_result', 'symlink', 'sysconf', 'sysconf_names', 'tcgetpgrp', 'tcsetpgrp',
    'ttyname', 'uname', 'wait', 'wait3', 'wait4'
    ]

# the Win32 urandom implementation isn't going to translate on JVM or CLI so
# we have to remove it
lltype_only_defs.append('urandom')

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
        'tmpnam'     : 'app_posix.tmpnam',
        'tempnam'    : 'app_posix.tempnam',
    }
    if os.name == 'nt':
        appleveldefs.update({
                'popen2' : 'app_posix.popen2',
                'popen3' : 'app_posix.popen3',
                'popen4' : 'app_posix.popen4',
                })
    if hasattr(posix, 'wait'):
        appleveldefs['wait'] = 'app_posix.wait'
    if hasattr(posix, 'wait3'):
        appleveldefs['wait3'] = 'app_posix.wait3'
    if hasattr(posix, 'wait4'):
        appleveldefs['wait4'] = 'app_posix.wait4'
        
    # Functions implemented on all platforms
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
        'getcwdu'   : 'interp_posix.getcwdu',
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
        'kill'      : 'interp_posix.kill',
        'abort'     : 'interp_posix.abort',
        'urandom'   : 'interp_posix.urandom',
        }

    for name in '''
            wait wait3 wait4 chown lchown fchown fchmod ftruncate
            fsync fdatasync fchdir putenv unsetenv killpg getpid
            link symlink readlink
            fork openpty forkpty waitpid execv execve uname sysconf fpathconf
            ttyname getloadavg makedev major minor mkfifo mknod nice getlogin
            getsid getuid geteuid getgid getegid getpgrp getpgid
            setsid setuid seteuid setgid setegid setpgrp setpgid
            getppid getgroups setreuid setregid chroot
            _getfullpathname
            '''.split():
        if hasattr(posix, name):
            interpleveldefs[name] = 'interp_posix.%s' % (name,)

    for constant in '''
            F_OK R_OK W_OK X_OK NGROUPS_MAX TMP_MAX
            WNOHANG WCONTINUED WUNTRACED
            O_RDONLY O_WRONLY O_RDWR O_NDELAY O_NONBLOCK O_APPEND
            O_DSYNC O_RSYNC O_SYNC O_NOCTTY O_CREAT O_EXCL O_TRUNC
            O_BINARY O_TEXT O_LARGEFILE O_SHLOCK O_EXLOCK
            O_NOINHERIT O_TEMPORARY O_RANDOM O_SEQUENTIAL
            O_ASYNC O_DIRECT O_DIRECTORY O_NOFOLLOW O_NOATIME 
            EX_OK EX_USAGE EX_DATAERR EX_NOINPUT EX_NOUSER EX_NOHOST
            EX_UNAVAILABLE EX_SOFTWARE EX_OSERR EX_OSFILE EX_CANTCREAT
            EX_IOERR EX_TEMPFAIL EX_PROTOCOL EX_NOPERM EX_CONFIG EX_NOTFOUND
            '''.split():
        if hasattr(posix, constant):
            value = getattr(posix, constant)
            interpleveldefs[constant] = "space.wrap(%s)" % value

    # XXX don't use the os module here
    if 'sysconf' in interpleveldefs:
        interpleveldefs['sysconf_names'] = 'space.wrap(os.sysconf_names)'
    if 'fpathconf' in interpleveldefs:
        interpleveldefs['pathconf_names'] = 'space.wrap(os.pathconf_names)'

    # Macros for process exit statuses: WIFEXITED &co
    for name in RegisterOs.w_star:
        if hasattr(posix, name):
            interpleveldefs[name] = 'interp_posix.' + name

    def __init__(self, space, w_name):
        # if it's an ootype translation, remove all the defs that are lltype
        # only
        backend = space.config.translation.backend
        if backend == 'cli' or backend == 'jvm':
            for name in lltype_only_defs:
                self.interpleveldefs.pop(name, None)
        MixedModule.__init__(self, space, w_name)

    def startup(self, space):
        from pypy.module.posix import interp_posix
        interp_posix.get(space).startup(space)
