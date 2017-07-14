import os

import py
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rtyper.tool import rffi_platform as platform
from rpython.translator import cdir
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rlib import rposix

from pypy.interpreter.error import (
    OperationError, exception_from_saved_errno, oefmt, wrap_oserror)
from pypy.interpreter.gateway import unwrap_spec
from pypy.module.posix.interp_posix import run_fork_hooks

thisdir = py.path.local(__file__).dirpath()

class CConfig:
    _compilation_info_ = ExternalCompilationInfo(
        includes=['unistd.h', 'sys/syscall.h', 'sys/stat.h'])
    HAVE_SYS_SYSCALL_H = platform.Has("syscall")
    HAVE_SYS_STAT_H = platform.Has("stat")
    HAVE_SETSID = platform.Has("setsid")

config = platform.configure(CConfig)

eci = ExternalCompilationInfo(
    includes=[thisdir.join('_posixsubprocess.h')],
    include_dirs=[str(thisdir), cdir],
    separate_module_files=[thisdir.join('_posixsubprocess.c')])

compile_extra = []
if config['HAVE_SYS_SYSCALL_H']:
    compile_extra.append("-DHAVE_SYS_SYSCALL_H")
if config['HAVE_SYS_STAT_H']:
    compile_extra.append("-DHAVE_SYS_STAT_H")
if config['HAVE_SETSID']:
    compile_extra.append("-DHAVE_SETSID")

class CConfig:
    _compilation_info_ = ExternalCompilationInfo(includes=['dirent.h'])
    HAVE_DIRENT_H = platform.Has("opendir")

config = platform.configure(CConfig)

if config['HAVE_DIRENT_H']:
    compile_extra.append("-DHAVE_DIRENT_H")

eci = eci.merge(
    rposix.eci_inheritable,
    ExternalCompilationInfo(
        compile_extra=compile_extra))

c_child_exec = rffi.llexternal(
    'pypy_subprocess_child_exec',
    [rffi.CCHARPP, rffi.CCHARPP, rffi.CCHARPP, rffi.CCHARP,
     rffi.INT, rffi.INT, rffi.INT, rffi.INT, rffi.INT, rffi.INT, 
     rffi.INT, rffi.INT, rffi.INT, rffi.INT, rffi.INT,
     rffi.CArrayPtr(rffi.LONG), lltype.Signed,
     lltype.Ptr(lltype.FuncType([rffi.VOIDP], rffi.INT)), rffi.VOIDP],
    lltype.Void,
    compilation_info=eci,
    releasegil=True)
c_cloexec_pipe = rffi.llexternal(
    'pypy_subprocess_cloexec_pipe',
    [rffi.CArrayPtr(rffi.INT)], rffi.INT,
    compilation_info=eci,
    releasegil=True,
    save_err=rffi.RFFI_SAVE_ERRNO)
c_init = rffi.llexternal(
    'pypy_subprocess_init',
    [], lltype.Void,
    compilation_info=eci,
    releasegil=True)


class PreexecCallback:
    def __init__(self):
        self.space = None
        self.w_preexec_fn = None
    
    @staticmethod
    def run_function(unused):
        self = preexec
        if self.w_preexec_fn:
            try:
                self.space.call_function(self.w_preexec_fn)
            except OperationError:
                return rffi.cast(rffi.INT, 0)
        return rffi.cast(rffi.INT, 1)
preexec = PreexecCallback()


def build_fd_sequence(space, w_fd_list):
    result = [space.int_w(w_fd)
              for w_fd in space.unpackiterable(w_fd_list)]
    prev_fd = -1
    for fd in result:
        if fd < 0 or fd < prev_fd or fd > 1 << 30:
            raise oefmt(space.w_ValueError, "bad value(s) in fds_to_keep")
    return result


def seqstr2charpp(space, w_seqstr):
    """Sequence of bytes -> char**, NULL terminated"""
    w_iter = space.iter(w_seqstr)
    return rffi.liststr2charpp([space.bytes0_w(space.next(w_iter))
                                for i in range(space.len_w(w_seqstr))])


@unwrap_spec(p2cread=int, p2cwrite=int, c2pread=int, c2pwrite=int,
             errread=int, errwrite=int, errpipe_read=int, errpipe_write=int,
             restore_signals=int, call_setsid=int)
def fork_exec(space, w_process_args, w_executable_list,
              w_close_fds, w_fds_to_keep, w_cwd, w_env_list,
              p2cread, p2cwrite, c2pread, c2pwrite,
              errread, errwrite, errpipe_read, errpipe_write,
              restore_signals, call_setsid, w_preexec_fn):
    """\
    fork_exec(args, executable_list, close_fds, cwd, env,
              p2cread, p2cwrite, c2pread, c2pwrite,
              errread, errwrite, errpipe_read, errpipe_write,
              restore_signals, call_setsid, preexec_fn)

    Forks a child process, closes parent file descriptors as appropriate in the
    child and dups the few that are needed before calling exec() in the child
    process.
    
    The preexec_fn, if supplied, will be called immediately before exec.
    WARNING: preexec_fn is NOT SAFE if your application uses threads.
             It may trigger infrequent, difficult to debug deadlocks.
    
    If an error occurs in the child process before the exec, it is
    serialized and written to the errpipe_write fd per subprocess.py.
    
    Returns: the child process's PID.
    
    Raises: Only on an error in the parent process.
    """
    close_fds = space.is_true(w_close_fds)
    if close_fds and errpipe_write < 3:  # precondition
        raise oefmt(space.w_ValueError, "errpipe_write must be >= 3")
    fds_to_keep = build_fd_sequence(space, w_fds_to_keep)

    # No need to disable GC in PyPy:
    # - gc.disable() only disables __del__ anyway.
    # - appelvel __del__ are only called at specific points of the
    #   interpreter.

    l_exec_array = lltype.nullptr(rffi.CCHARPP.TO)
    l_argv = lltype.nullptr(rffi.CCHARPP.TO)
    l_envp = lltype.nullptr(rffi.CCHARPP.TO)
    l_cwd = lltype.nullptr(rffi.CCHARP.TO)
    l_fds_to_keep = lltype.nullptr(rffi.CArrayPtr(rffi.LONG).TO)

    # Convert args and env into appropriate arguments for exec()
    # These conversions are done in the parent process to avoid allocating
    # or freeing memory in the child process.
    try:
        l_exec_array = seqstr2charpp(space, w_executable_list)

        if not space.is_none(w_process_args):
            w_iter = space.iter(w_process_args)
            argv = [space.fsencode_w(space.next(w_iter))
                    for i in range(space.len_w(w_process_args))]
            l_argv = rffi.liststr2charpp(argv)

        if not space.is_none(w_env_list):
            l_envp = seqstr2charpp(space, w_env_list)

        l_fds_to_keep = lltype.malloc(rffi.CArrayPtr(rffi.LONG).TO,
                                      len(fds_to_keep) + 1, flavor='raw')
        for i in range(len(fds_to_keep)):
            l_fds_to_keep[i] = fds_to_keep[i]

        if not space.is_none(w_preexec_fn):
            preexec.space = space
            preexec.w_preexec_fn = w_preexec_fn
        else:
            preexec.w_preexec_fn = None

        if not space.is_none(w_cwd):
            cwd = space.fsencode_w(w_cwd)
            l_cwd = rffi.str2charp(cwd)
            
        run_fork_hooks('before', space)

        try:
            try:
                pid = os.fork()
            except OSError as e:
                raise wrap_oserror(space, e)

            if pid == 0:
                # Child process
                # Code from here to _exit() must only use
                # async-signal-safe functions, listed at `man 7 signal`
                # http://www.opengroup.org/onlinepubs/009695399/functions/xsh_chap02_04.html.
                if not space.is_none(w_preexec_fn):
                    # We'll be calling back into Python later so we need
                    # to do this. This call may not be async-signal-safe
                    # but neither is calling back into Python.  The user
                    # asked us to use hope as a strategy to avoid
                    # deadlock...
                    run_fork_hooks('child', space)

                c_child_exec(
                    l_exec_array, l_argv, l_envp, l_cwd,
                    p2cread, p2cwrite, c2pread, c2pwrite,
                    errread, errwrite, errpipe_read, errpipe_write,
                    close_fds, restore_signals, call_setsid,
                    l_fds_to_keep, len(fds_to_keep),
                    PreexecCallback.run_function, None)
                os._exit(255)
        finally:
            # parent process
            run_fork_hooks('parent', space)

    finally:
        preexec.w_preexec_fn = None

        if l_cwd:
            rffi.free_charp(l_cwd)
        if l_envp:
            rffi.free_charpp(l_envp)
        if l_argv:
            rffi.free_charpp(l_argv)
        if l_exec_array:
            rffi.free_charpp(l_exec_array)
        if l_fds_to_keep:
            lltype.free(l_fds_to_keep, flavor='raw')

    return space.newint(pid)


def cloexec_pipe(space):
    """cloexec_pipe() -> (read_end, write_end)

    Create a pipe whose ends have the cloexec flag set."""

    with lltype.scoped_alloc(rffi.CArrayPtr(rffi.INT).TO, 2) as fds:
        res = c_cloexec_pipe(fds)
        if res != 0:
            raise exception_from_saved_errno(space, space.w_OSError)

        return space.newtuple([space.newint(fds[0]),
                               space.newint(fds[1]),
                               ])
