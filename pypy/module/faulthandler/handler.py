import os
from rpython.rtyper.lltypesystem import rffi
from rpython.rlib.rposix import is_valid_fd

from pypy.interpreter.error import oefmt, exception_from_saved_errno
from pypy.interpreter.gateway import unwrap_spec
from pypy.module.faulthandler import cintf


class Handler(object):
    def __init__(self, space):
        self.space = space
        self._cleanup_()

    def _cleanup_(self):
        self.is_initialized = False
        self.fatal_error_w_file = None

    def check_err(self, p_err):
        if p_err:
            raise oefmt(self.space.w_RuntimeError, 'faulthandler: %8',
                        rffi.charp2str(p_err))

    def get_fileno_and_file(self, w_file):
        space = self.space
        if space.is_none(w_file):
            w_file = space.sys.get('stderr')
            if space.is_none(w_file):
                raise oefmt(space.w_RuntimeError, "sys.stderr is None")
        elif space.isinstance_w(w_file, space.w_int):
            fd = space.int_w(w_file)
            if fd < 0 or not is_valid_fd(fd):
                raise oefmt(space.w_ValueError,
                            "file is not a valid file descriptor")
            return fd, None

        fd = space.int_w(space.call_method(w_file, 'fileno'))
        try:
            space.call_method(w_file, 'flush')
        except OperationError as e:
            if e.async(space):
                raise
            pass   # ignore flush() error
        return fd, w_file

    def enable(self, w_file, all_threads):
        fileno, w_file = self.get_fileno_and_file(w_file)
        if not self.is_initialized:
            self.check_err(cintf.pypy_faulthandler_setup())
            self.is_initialized = True

        self.fatal_error_w_file = w_file
        err = cintf.pypy_faulthandler_enable(fileno, all_threads)
        if err:
            space = self.space
            raise exception_from_saved_errno(space, space.w_RuntimeError)

    def disable(self):
        cintf.pypy_faulthandler_disable()
        self.fatal_error_w_file = None

    def is_enabled(self):
        return (self.is_initialized and
                bool(cintf.pypy_faulthandler_is_enabled()))

    def finish(self):
        if self.is_initialized:
            cintf.pypy_faulthandler_teardown()
        self._cleanup_()


def startup(space):
    """Initialize the faulthandler logic when the space is starting
    (this is called from baseobjspace.py)"""
    #
    # Call faulthandler.enable() if the PYTHONFAULTHANDLER environment variable
    # is defined, or if sys._xoptions has a 'faulthandler' key.
    if not os.environ.get('PYTHONFAULTHANDLER'):
        w_options = space.sys.get('_xoptions')
        if not space.contains(w_options, space.wrap('faulthandler')):
            return
    #
    # Like CPython.  Why not just call enable(space)?  Maybe the goal is
    # to let the user override the 'faulthandler' module.  Maybe someone
    # mis-uses ``"faulthandler" in sys.modules'' as a way to check if it
    # was started by checking if it was imported at all.
    space.appexec([], """
        import faulthandler
        faulthandler.enable()
    """)

def finish(space):
    """Finalize the faulthandler logic (called from baseobjspace.py)"""
    space.fromcache(Handler).finish()


@unwrap_spec(all_threads=int)
def enable(space, w_file=None, all_threads=0):
    "enable(file=sys.stderr, all_threads=True): enable the fault handler"
    space.fromcache(Handler).enable(w_file, all_threads)

def disable(space):
    "disable(): disable the fault handler"
    space.fromcache(Handler).disable()

def is_enabled(space):
    "is_enabled()->bool: check if the handler is enabled"
    return space.wrap(space.fromcache(Handler).is_enabled())
