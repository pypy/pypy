"""
A Python library to execute and communicate with a subprocess that
was translated from RPython code with --sandbox.  This library is
for the outer process, which can run CPython or PyPy.
"""

import py
import marshal, sys, os, posixpath, errno, stat
from pypy.rpython.module.ll_os_stat import s_StatResult
from pypy.tool.ansi_print import AnsiLog
from pypy.rlib.rarithmetic import r_longlong
from py.compat import subprocess

class MyAnsiLog(AnsiLog):
    KW_TO_COLOR = {
        'call': ((34,), False),
        'result': ((34,), False),
        'exception': ((34,), False),
        'vpath': ((35,), False),
        }

log = py.log.Producer("sandlib")
py.log.setconsumer("sandlib", MyAnsiLog())


def read_message(f, timeout=None):
    # warning: 'timeout' is not really reliable and should only be used
    # for testing.  Also, it doesn't work if the file f does any buffering.
    if timeout is not None:
        import select
        iwtd, owtd, ewtd = select.select([f], [], [], timeout)
        if not iwtd:
            raise EOFError("timed out waiting for data")
    return marshal.load(f)

def write_message(g, msg, resulttype=None):
    if resulttype is None:
        if sys.version_info < (2, 4):
            marshal.dump(msg, g)
        else:
            marshal.dump(msg, g, 0)
    else:
        # use the exact result type for encoding
        from pypy.rlib.rmarshal import get_marshaller
        buf = []
        get_marshaller(resulttype)(buf, msg)
        g.write(''.join(buf))
    g.flush()

# keep the table in sync with rsandbox.reraise_error()
EXCEPTION_TABLE = [
    (1, OSError),
    (2, IOError),
    (3, OverflowError),
    (4, ValueError),
    (5, ZeroDivisionError),
    (6, MemoryError),
    (7, KeyError),
    (8, IndexError),
    (9, RuntimeError),
    ]

def write_exception(g, exception, tb=None):
    for i, excclass in EXCEPTION_TABLE:
        if isinstance(exception, excclass):
            write_message(g, i)
            if excclass is OSError:
                error = exception.errno
                if error is None:
                    error = errno.EPERM
                write_message(g, error)
            break
    else:
        # just re-raise the exception
        raise exception.__class__, exception, tb

def shortrepr(x):
    r = repr(x)
    if len(r) >= 80:
        r = r[:20] + '...' + r[-8:]
    return r

def signal_name(n):
    import signal
    for key, value in signal.__dict__.items():
        if key.startswith('SIG') and not key.startswith('SIG_') and value == n:
            return key
    return 'signal %d' % (n,)


class SandboxedProc(object):
    """Base class to control a sandboxed subprocess.
    Inherit from this class and implement all the do_xxx() methods
    for the external functions xxx that you want to support.
    """
    debug = False
    os_level_sandboxing = False   # Linux only: /proc/PID/seccomp

    def __init__(self, args, executable=None):
        """'args' should a sequence of argument for the subprocess,
        starting with the full path of the executable.
        """
        self.popen = subprocess.Popen(args, executable=executable,
                                      bufsize=-1,
                                      stdin=subprocess.PIPE,
                                      stdout=subprocess.PIPE,
                                      close_fds=True,
                                      env={})

    def poll(self):
        return self.popen.poll()

    def wait(self):
        return self.popen.wait()

    def handle_forever(self):
        returncode = self.handle_until_return()
        if returncode != 0:
            raise OSError("the sandboxed subprocess exited with code %d" % (
                returncode,))

    def handle_until_return(self):
        if self.os_level_sandboxing and sys.platform.startswith('linux2'):
            # rationale: we wait until the child process started completely,
            # letting the C library do any system calls it wants for
            # initialization.  When the RPython code starts up, it quickly
            # does its first system call.  At this point we turn seccomp on.
            import select
            select.select([self.popen.stdout], [], [])
            f = open('/proc/%d/seccomp' % self.popen.pid, 'w')
            print >> f, 1
            f.close()
        while True:
            try:
                fnname = read_message(self.popen.stdout)
                args   = read_message(self.popen.stdout)
            except EOFError, e:
                break
            if self.debug:
                log.call('%s(%s)' % (fnname,
                                     ', '.join([shortrepr(x) for x in args])))
            try:
                answer, resulttype = self.handle_message(fnname, *args)
            except Exception, e:
                tb = sys.exc_info()[2]
                write_exception(self.popen.stdin, e, tb)
                if self.debug:
                    if str(e):
                        log.exception('%s: %s' % (e.__class__.__name__, e))
                    else:
                        log.exception('%s' % (e.__class__.__name__,))
            else:
                if self.debug:
                    log.result(shortrepr(answer))
                write_message(self.popen.stdin, 0)  # error code - 0 for ok
                write_message(self.popen.stdin, answer, resulttype)
        returncode = self.popen.wait()
        return returncode

    def handle_message(self, fnname, *args):
        if '__' in fnname:
            raise ValueError("unsafe fnname")
        handler = getattr(self, 'do_' + fnname.replace('.', '__'))
        resulttype = getattr(handler, 'resulttype', None)
        return handler(*args), resulttype


class SimpleIOSandboxedProc(SandboxedProc):
    """Control a sandboxed subprocess which is only allowed to read from
    its stdin and write to its stdout and stderr.
    """
    _input = None
    _output = None
    _error = None

    def communicate(self, input=None):
        """Send data to stdin. Read data from stdout and stderr,
        until end-of-file is reached. Wait for process to terminate.
        """
        import cStringIO
        if input:
            if isinstance(input, str):
                input = cStringIO.StringIO(input)
            self._input = input
        self._output = cStringIO.StringIO()
        self._error = cStringIO.StringIO()
        self.handle_forever()
        output = self._output.getvalue()
        self._output = None
        error = self._error.getvalue()
        self._error = None
        return (output, error)

    def interact(self, stdin=None, stdout=None, stderr=None):
        """Interact with the subprocess.  By default, stdin, stdout and
        stderr are set to the ones from 'sys'."""
        import sys
        self._input  = stdin  or sys.stdin
        self._output = stdout or sys.stdout
        self._error  = stderr or sys.stderr
        returncode = self.handle_until_return()
        if returncode != 0:
            if os.name == 'posix' and returncode < 0:
                print >> self._error, "[Subprocess killed by %s]" % (
                    signal_name(-returncode),)
            else:
                print >> self._error, "[Subprocess exit code: %d]" % (
                    returncode,)
        self._input = None
        self._output = None
        self._error = None

    def do_ll_os__ll_os_read(self, fd, size):
        if fd == 0:
            if self._input is None:
                return ""
            elif self._input.isatty():
                # don't wait for all 'size' chars if reading from a tty,
                # to avoid blocking.  Instead, stop after reading a line.
                return self._input.readline(size)
            else:
                return self._input.read(size)
        raise OSError("trying to read from fd %d" % (fd,))

    def do_ll_os__ll_os_write(self, fd, data):
        if fd == 1:
            self._output.write(data)
            return len(data)
        if fd == 2:
            self._error.write(data)
            return len(data)
        raise OSError("trying to write to fd %d" % (fd,))


class VirtualizedSandboxedProc(SandboxedProc):
    """Control a virtualized sandboxed process, which is given a custom
    view on the filesystem and a custom environment.
    """
    virtual_env = {}
    virtual_cwd = '/tmp'
    virtual_console_isatty = False
    virtual_fd_range = range(3, 50)

    def __init__(self, virtual_root, *args, **kwds):
        super(VirtualizedSandboxedProc, self).__init__(*args, **kwds)
        self.virtual_root = virtual_root
        self.open_fds = {}   # {virtual_fd: real_file_object}

    def do_ll_os__ll_os_envitems(self):
        return self.virtual_env.items()

    def do_ll_os__ll_os_getenv(self, name):
        return self.virtual_env.get(name)

    def translate_path(self, vpath):
        # XXX this assumes posix vpaths for now, but os-specific real paths
        vpath = posixpath.normpath(posixpath.join(self.virtual_cwd, vpath))
        dirnode = self.virtual_root
        components = [component for component in vpath.split('/')]
        for component in components[:-1]:
            if component:
                dirnode = dirnode.join(component)
                if dirnode.kind != stat.S_IFDIR:
                    raise OSError(errno.ENOTDIR, component)
        return dirnode, components[-1]

    def get_node(self, vpath):
        dirnode, name = self.translate_path(vpath)
        if name:
            node = dirnode.join(name)
        else:
            node = dirnode
        log.vpath('%r => %r' % (vpath, node))
        return node

    def do_ll_os__ll_os_stat(self, vpathname):
        node = self.get_node(vpathname)
        return node.stat()
    do_ll_os__ll_os_stat.resulttype = s_StatResult

    do_ll_os__ll_os_lstat = do_ll_os__ll_os_stat

    def do_ll_os__ll_os_isatty(self, fd):
        return self.virtual_console_isatty and fd in (0, 1, 2)

    def allocate_fd(self, f):
        for fd in self.virtual_fd_range:
            if fd not in self.open_fds:
                self.open_fds[fd] = f
                return fd
        else:
            raise OSError(errno.EMFILE, "trying to open too many files")

    def get_file(self, fd):
        try:
            return self.open_fds[fd]
        except KeyError:
            raise OSError(errno.EBADF, "bad file descriptor")

    def do_ll_os__ll_os_open(self, vpathname, flags, mode):
        node = self.get_node(vpathname)
        if flags & (os.O_RDONLY|os.O_WRONLY|os.O_RDWR) != os.O_RDONLY:
            raise OSError(errno.EPERM, "write access denied")
        # all other flags are ignored
        f = node.open()
        return self.allocate_fd(f)

    def do_ll_os__ll_os_close(self, fd):
        f = self.get_file(fd)
        del self.open_fds[fd]
        f.close()

    def do_ll_os__ll_os_read(self, fd, size):
        try:
            f = self.open_fds[fd]
        except KeyError:
            return super(VirtualizedSandboxedProc, self).do_ll_os__ll_os_read(
                fd, size)
        else:
            if not (0 <= size <= sys.maxint):
                raise OSError(errno.EINVAL, "invalid read size")
            # don't try to read more than 256KB at once here
            return f.read(min(size, 256*1024))

    def do_ll_os__ll_os_lseek(self, fd, pos, how):
        f = self.get_file(fd)
        f.seek(pos, how)
        return f.tell()
    do_ll_os__ll_os_lseek.resulttype = r_longlong

    def do_ll_os__ll_os_getcwd(self):
        return self.virtual_cwd

    def do_ll_os__ll_os_strerror(self, errnum):
        # unsure if this shouldn't be considered safeboxsafe
        return os.strerror(errnum) or ('Unknown error %d' % (errnum,))

    def do_ll_os__ll_os_listdir(self, vpathname):
        node = self.get_node(vpathname)
        return node.keys()
