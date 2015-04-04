"""
Low-level implementations for the external functions of the 'os' module.
"""

# Implementation details about those functions
# might be found in doc/rffi.txt

import os, sys, errno
import py
from rpython.rtyper.module.support import (
    UNDERSCORE_ON_WIN32, _WIN32, StringTraits, UnicodeTraits)
from rpython.tool.sourcetools import func_renamer
from rpython.rlib.rarithmetic import r_longlong
from rpython.rtyper.extfunc import (
    BaseLazyRegistering, register_external)
from rpython.rtyper.extfunc import registering, registering_if, extdef
from rpython.annotator.model import (
    SomeInteger, SomeString, SomeTuple, SomeFloat, s_Str0, s_Unicode0)
from rpython.annotator.model import s_ImpossibleValue, s_None, s_Bool
from rpython.rtyper.lltypesystem import rffi
from rpython.rtyper.lltypesystem import lltype
from rpython.rtyper.tool import rffi_platform as platform
from rpython.rlib import rposix, rwin32, jit
from rpython.translator.tool.cbuild import ExternalCompilationInfo
from rpython.rlib.objectmodel import specialize
from rpython.translator import cdir

str0 = s_Str0
unicode0 = s_Unicode0

def monkeypatch_rposix(posixfunc, unicodefunc, signature):
    func_name = posixfunc.__name__

    if hasattr(signature, '_default_signature_'):
        signature = signature._default_signature_
    arglist = ['arg%d' % (i,) for i in range(len(signature))]
    transformed_arglist = arglist[:]
    for i, arg in enumerate(signature):
        if arg in (unicode, unicode0):
            transformed_arglist[i] = transformed_arglist[i] + '.as_unicode()'

    args = ', '.join(arglist)
    transformed_args = ', '.join(transformed_arglist)
    try:
        main_arg = 'arg%d' % (signature.index(unicode0),)
    except ValueError:
        main_arg = 'arg%d' % (signature.index(unicode),)

    source = py.code.Source("""
    def %(func_name)s(%(args)s):
        if isinstance(%(main_arg)s, str):
            return posixfunc(%(args)s)
        else:
            return unicodefunc(%(transformed_args)s)
    """ % locals())
    miniglobals = {'posixfunc'  : posixfunc,
                   'unicodefunc': unicodefunc,
                   '__name__':    __name__, # for module name propagation
                   }
    exec source.compile() in miniglobals
    new_func = miniglobals[func_name]
    specialized_args = [i for i in range(len(signature))
                        if signature[i] in (unicode, unicode0, None)]
    new_func = specialize.argtype(*specialized_args)(new_func)

    # Monkeypatch the function in rpython.rlib.rposix
    setattr(rposix, func_name, new_func)

def registering_str_unicode(posixfunc, condition=True):
    if not condition or posixfunc is None:
        return registering(None, condition=False)

    func_name = posixfunc.__name__

    def register_posixfunc(self, method):
        val = method(self, StringTraits())
        register_external(posixfunc, *val.def_args, **val.def_kwds)

        if sys.platform == 'win32':
            val = method(self, UnicodeTraits())
            @func_renamer(func_name + "_unicode")
            def unicodefunc(*args):
                return posixfunc(*args)
            register_external(unicodefunc, *val.def_args, **val.def_kwds)
            signature = val.def_args[0]
            monkeypatch_rposix(posixfunc, unicodefunc, signature)

    def decorator(method):
        decorated = lambda self: register_posixfunc(self, method)
        decorated._registering_func = posixfunc
        return decorated
    return decorator

posix = __import__(os.name)

includes = []
if not _WIN32:
    # XXX many of these includes are not portable at all
    includes += ['dirent.h', 'sys/stat.h',
                 'sys/times.h', 'utime.h', 'sys/types.h', 'unistd.h',
                 'signal.h', 'sys/wait.h', 'fcntl.h']
else:
    includes += ['sys/utime.h', 'sys/types.h']

class CConfig:
    """
    Definitions for platform integration.

    Note: this must be processed through platform.configure() to provide
    usable objects.  For example::

        CLOCK_T = platform.configure(CConfig)['CLOCK_T']
        register(function, [CLOCK_T], ...)

    """

    _compilation_info_ = ExternalCompilationInfo(
        includes=includes
    )


class RegisterOs(BaseLazyRegistering):

    def __init__(self):
        self.configure(CConfig)

# --------------------------- os.stat & variants ---------------------------

    @registering(os.fstat)
    def register_os_fstat(self):
        from rpython.rtyper.module import ll_os_stat
        return ll_os_stat.register_stat_variant('fstat', StringTraits())

    @registering_str_unicode(os.stat)
    def register_os_stat(self, traits):
        from rpython.rtyper.module import ll_os_stat
        return ll_os_stat.register_stat_variant('stat', traits)

    @registering_str_unicode(os.lstat)
    def register_os_lstat(self, traits):
        from rpython.rtyper.module import ll_os_stat
        return ll_os_stat.register_stat_variant('lstat', traits)

    @registering_if(os, 'fstatvfs')
    def register_os_fstatvfs(self):
        from rpython.rtyper.module import ll_os_stat
        return ll_os_stat.register_statvfs_variant('fstatvfs', StringTraits())

    if hasattr(os, 'statvfs'):
        @registering_str_unicode(os.statvfs)
        def register_os_statvfs(self, traits):
            from rpython.rtyper.module import ll_os_stat
            return ll_os_stat.register_statvfs_variant('statvfs', traits)


# ____________________________________________________________
# Support for os.environ

# XXX only for systems where os.environ is an instance of _Environ,
# which should cover Unix and Windows at least
assert type(os.environ) is not dict

from rpython.rtyper.controllerentry import ControllerEntryForPrebuilt

class EnvironExtRegistry(ControllerEntryForPrebuilt):
    _about_ = os.environ

    def getcontroller(self):
        from rpython.rtyper.module.ll_os_environ import OsEnvironController
        return OsEnvironController()
