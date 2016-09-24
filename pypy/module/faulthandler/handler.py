import os
from rpython.rtyper.lltypesystem import rffi
from rpython.rlib.rposix import is_valid_fd
from rpython.rlib.rarithmetic import widen
from rpython.rlib.objectmodel import keepalive_until_here
from rpython.rtyper.annlowlevel import llhelper

from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.error import exception_from_saved_errno
from pypy.interpreter.gateway import unwrap_spec
from pypy.module.faulthandler import cintf, dumper


class Handler(object):
    def __init__(self, space):
        "NOT_RPYTHON"
        self.space = space
        self._cleanup_()

    def _cleanup_(self):
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
            fd = space.c_int_w(w_file)
            if fd < 0 or not is_valid_fd(fd):
                raise oefmt(space.w_ValueError,
                            "file is not a valid file descriptor")
            return fd, None

        fd = space.c_int_w(space.call_method(w_file, 'fileno'))
        try:
            space.call_method(w_file, 'flush')
        except OperationError as e:
            if e.async(space):
                raise
            pass   # ignore flush() error
        return fd, w_file

    def enable(self, w_file, all_threads):
        fileno, w_file = self.get_fileno_and_file(w_file)
        #
        dump_callback = llhelper(cintf.DUMP_CALLBACK, dumper._dump_callback)
        self.check_err(cintf.pypy_faulthandler_setup(dump_callback))
        #
        self.fatal_error_w_file = w_file
        self.check_err(cintf.pypy_faulthandler_enable(
            rffi.cast(rffi.INT, fileno),
            rffi.cast(rffi.INT, all_threads)))

    def disable(self):
        cintf.pypy_faulthandler_disable()
        self.fatal_error_w_file = None

    def is_enabled(self):
        return bool(widen(cintf.pypy_faulthandler_is_enabled()))

    def dump_traceback(self, w_file, all_threads):
        fileno, w_file = self.get_fileno_and_file(w_file)
        #
        dump_callback = llhelper(cintf.DUMP_CALLBACK, dumper._dump_callback)
        self.check_err(cintf.pypy_faulthandler_setup(dump_callback))
        #
        cintf.pypy_faulthandler_dump_traceback(
            rffi.cast(rffi.INT, fileno),
            rffi.cast(rffi.INT, all_threads))
        keepalive_until_here(w_file)

    def finish(self):
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
        if not space.is_true(space.contains(w_options,
                                            space.wrap('faulthandler'))):
            return
    #
    # Like CPython.  Why not just call enable(space)?  Maybe someone
    # mis-uses ``"faulthandler" in sys.modules'' as a way to check if it
    # was started by checking if it was imported at all.
    space.appexec([], """():
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

@unwrap_spec(all_threads=int)
def dump_traceback(space, w_file=None, all_threads=0):
   """dump the traceback of the current thread into file
   including all threads if all_threads is True"""
   space.fromcache(Handler).dump_traceback(w_file, all_threads)

# for tests...

@unwrap_spec(release_gil=bool)
def read_null(space, release_gil):
    if release_gil:
        cintf.pypy_faulthandler_read_null_releasegil()
    else:
        cintf.pypy_faulthandler_read_null()
