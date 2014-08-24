import os
import py

from pypy.interpreter.gateway import interp2app, unwrap_spec, WrappedDefault
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from pypy.interpreter.error import OperationError, oefmt

cwd = py.path.local(__file__).dirpath()
eci = ExternalCompilationInfo(
    includes=[cwd.join('faulthandler.h')],
    include_dirs=[str(cwd)],
    separate_module_files=[cwd.join('faulthandler.c')],
    export_symbols=['pypy_faulthandler_read_null',
                    'pypy_faulthandler_sigsegv',
                    'pypy_faulthandler_sigfpe',
                    'pypy_faulthandler_sigabrt',
                    'pypy_faulthandler_sigbus',
                    'pypy_faulthandler_sigill',
                    ])

def llexternal(*args, **kwargs):
    kwargs.setdefault('releasegil', False)
    kwargs.setdefault('compilation_info', eci)
    return rffi.llexternal(*args, **kwargs)

pypy_faulthandler_read_null = llexternal(
    'pypy_faulthandler_read_null', [], lltype.Void)
pypy_faulthandler_read_null_nogil = llexternal(
    'pypy_faulthandler_read_null', [], lltype.Void,
    releasegil=True)
pypy_faulthandler_sigsegv = llexternal(
    'pypy_faulthandler_sigsegv', [], lltype.Void)
pypy_faulthandler_sigfpe = llexternal(
    'pypy_faulthandler_sigfpe', [], lltype.Void)
pypy_faulthandler_sigabrt = llexternal(
    'pypy_faulthandler_sigabrt', [], lltype.Void)
pypy_faulthandler_sigbus = llexternal(
    'pypy_faulthandler_sigbus', [], lltype.Void)
pypy_faulthandler_sigill = llexternal(
    'pypy_faulthandler_sigill', [], lltype.Void)

class FatalErrorState(object):
    def __init__(self, space):
        self.enabled = False

def enable(space):
    space.fromcache(FatalErrorState).enabled = True

def disable(space):
    space.fromcache(FatalErrorState).enabled = False

def is_enabled(space):
    return space.wrap(space.fromcache(FatalErrorState).enabled)

def register(space, __args__):
    pass


@unwrap_spec(w_file=WrappedDefault(None),
             w_all_threads=WrappedDefault(True))
def dump_traceback(space, w_file, w_all_threads):
    ec = space.getexecutioncontext()
    ecs = space.threadlocals.getallvalues()

    if space.is_none(w_file):
        w_file = space.sys.get('stderr')
    fd = space.c_filedescriptor_w(w_file)

    frame = ec.gettopframe()
    while frame:
        code = frame.pycode
        lineno = frame.get_last_lineno()
        if code:
            os.write(fd, "File \"%s\", line %s in %s\n" % (
                    code.co_filename, lineno, code.co_name))
        else:
            os.write(fd, "File ???, line %s in ???\n" % (
                    lineno,))

        frame = frame.f_backref()
 

@unwrap_spec(w_release_gil=WrappedDefault(False))
def read_null(space, w_release_gil):
    if space.is_true(w_release_gil):
        pypy_faulthandler_read_null_nogil()
    else:
        pypy_faulthandler_read_null()

def sigsegv():
    pypy_faulthandler_sigsegv()

def sigfpe():
    pypy_faulthandler_sigfpe()

def sigabrt():
    pypy_faulthandler_sigabrt()

def sigbus():
    pypy_faulthandler_sigbus()

def sigill():
    pypy_faulthandler_sigill()
