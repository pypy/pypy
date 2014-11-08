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
from rpython.rlib import rposix, rwin32
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

_CYGWIN = sys.platform == 'cygwin'

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
    if not _WIN32:
        CLOCK_T = platform.SimpleType('clock_t', rffi.INT)

        TMS = platform.Struct(
            'struct tms', [('tms_utime', rffi.INT),
                           ('tms_stime', rffi.INT),
                           ('tms_cutime', rffi.INT),
                           ('tms_cstime', rffi.INT)])

    # For now we require off_t to be the same size as LONGLONG, which is the
    # interface required by callers of functions that thake an argument of type
    # off_t
    OFF_T_SIZE = platform.SizeOf('off_t')

    SEEK_SET = platform.DefinedConstantInteger('SEEK_SET')
    SEEK_CUR = platform.DefinedConstantInteger('SEEK_CUR')
    SEEK_END = platform.DefinedConstantInteger('SEEK_END')

    UTIMBUF = platform.Struct('struct %sutimbuf' % UNDERSCORE_ON_WIN32,
                              [('actime', rffi.INT),
                               ('modtime', rffi.INT)])


class RegisterOs(BaseLazyRegistering):

    def __init__(self):
        self.configure(CConfig)
        if not _WIN32:
            assert self.OFF_T_SIZE == rffi.sizeof(rffi.LONGLONG)

        # we need an indirection via c functions to get macro calls working on llvm XXX still?
        if hasattr(os, 'WCOREDUMP'):
            decl_snippet = """
            %(ret_type)s pypy_macro_wrapper_%(name)s (int status);
            """
            def_snippet = """
            %(ret_type)s pypy_macro_wrapper_%(name)s (int status) {
            return %(name)s(status);
            }
            """
            decls = []
            defs = []
            for name in self.w_star:
                if hasattr(os, name):
                    data = {'ret_type': 'int', 'name': name}
                    decls.append((decl_snippet % data).strip())
                    defs.append((def_snippet % data).strip())

            self.compilation_info = self.compilation_info.merge(
                ExternalCompilationInfo(
                post_include_bits = decls,
                separate_module_sources = ["\n".join(defs)]
            ))

    @registering_if(os, 'kill', sys.platform != 'win32')
    def register_os_kill(self):
        os_kill = self.llexternal('kill', [rffi.PID_T, rffi.INT],
                                  rffi.INT)
        def kill_llimpl(pid, sig):
            res = rffi.cast(lltype.Signed, os_kill(rffi.cast(rffi.PID_T, pid),
                                                   rffi.cast(rffi.INT, sig)))
            if res < 0:
                raise OSError(rposix.get_errno(), "os_kill failed")
        return extdef([int, int], s_None, llimpl=kill_llimpl,
                      export_name="ll_os.ll_os_kill")

    @registering_if(os, 'killpg')
    def register_os_killpg(self):
        os_killpg = self.llexternal('killpg', [rffi.INT, rffi.INT],
                                    rffi.INT)

        def killpg_llimpl(pid, sig):
            res = rffi.cast(lltype.Signed, os_killpg(rffi.cast(rffi.INT, pid),
                                                     rffi.cast(rffi.INT, sig)))
            if res < 0:
                raise OSError(rposix.get_errno(), "os_killpg failed")

        return extdef([int, int], s_None, llimpl=killpg_llimpl,
                      export_name="ll_os.ll_os_killpg")

    @registering_if(os, 'link')
    def register_os_link(self):
        os_link = self.llexternal('link', [rffi.CCHARP, rffi.CCHARP],
                                  rffi.INT)

        def link_llimpl(oldpath, newpath):
            res = rffi.cast(lltype.Signed, os_link(oldpath, newpath))
            if res < 0:
                raise OSError(rposix.get_errno(), "os_link failed")

        return extdef([str0, str0], s_None, llimpl=link_llimpl,
                      export_name="ll_os.ll_os_link")

    @registering_if(os, 'symlink')
    def register_os_symlink(self):
        os_symlink = self.llexternal('symlink', [rffi.CCHARP, rffi.CCHARP],
                                     rffi.INT)

        def symlink_llimpl(oldpath, newpath):
            res = rffi.cast(lltype.Signed, os_symlink(oldpath, newpath))
            if res < 0:
                raise OSError(rposix.get_errno(), "os_symlink failed")

        return extdef([str0, str0], s_None, llimpl=symlink_llimpl,
                      export_name="ll_os.ll_os_symlink")

    @registering(os._exit)
    def register_os__exit(self):
        from rpython.rlib import debug
        os__exit = self.llexternal('_exit', [rffi.INT], lltype.Void)

        def _exit_llimpl(status):
            debug.debug_flush()
            os__exit(rffi.cast(rffi.INT, status))

        return extdef([int], s_None, llimpl=_exit_llimpl,
                      export_name="ll_os.ll_os__exit")

    @registering_if(os, 'nice')
    def register_os_nice(self):
        os_nice = self.llexternal('nice', [rffi.INT], rffi.INT)

        def nice_llimpl(inc):
            # Assume that the system provides a standard-compliant version
            # of nice() that returns the new priority.  Nowadays, FreeBSD
            # might be the last major non-compliant system (xxx check me).
            rposix.set_errno(0)
            res = rffi.cast(lltype.Signed, os_nice(inc))
            if res == -1:
                err = rposix.get_errno()
                if err != 0:
                    raise OSError(err, "os_nice failed")
            return res

        return extdef([int], int, llimpl=nice_llimpl,
                      export_name="ll_os.ll_os_nice")

    @registering_if(os, 'ctermid')
    def register_os_ctermid(self):
        os_ctermid = self.llexternal('ctermid', [rffi.CCHARP], rffi.CCHARP)

        def ctermid_llimpl():
            return rffi.charp2str(os_ctermid(lltype.nullptr(rffi.CCHARP.TO)))

        return extdef([], str, llimpl=ctermid_llimpl,
                      export_name="ll_os.ll_os_ctermid")

    @registering_if(os, 'tmpnam')
    def register_os_tmpnam(self):
        os_tmpnam = self.llexternal('tmpnam', [rffi.CCHARP], rffi.CCHARP)

        def tmpnam_llimpl():
            return rffi.charp2str(os_tmpnam(lltype.nullptr(rffi.CCHARP.TO)))

        return extdef([], str, llimpl=tmpnam_llimpl,
                      export_name="ll_os.ll_os_tmpnam")

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


    # ------------------------------- os.W* ---------------------------------

    w_star = ['WCOREDUMP', 'WIFCONTINUED', 'WIFSTOPPED',
              'WIFSIGNALED', 'WIFEXITED', 'WEXITSTATUS',
              'WSTOPSIG', 'WTERMSIG']
    # last 3 are returning int
    w_star_returning_int = dict.fromkeys(w_star[-3:])



    def declare_new_w_star(self, name):
        """ stupid workaround for the python late-binding
        'feature'
        """

        def fake(status):
            return int(getattr(os, name)(status))
        fake.func_name = 'fake_' + name

        os_c_func = self.llexternal("pypy_macro_wrapper_" + name,
                                    [lltype.Signed], lltype.Signed,
                                    _callable=fake)

        if name in self.w_star_returning_int:
            def llimpl(status):
                return os_c_func(status)
            resulttype = int
        else:
            def llimpl(status):
                return bool(os_c_func(status))
            resulttype = bool
        llimpl.func_name = name + '_llimpl'
        return extdef([int], resulttype, "ll_os." + name,
                      llimpl=llimpl)

    for name in w_star:
        locals()['register_w_' + name] = registering_if(os, name)(
            lambda self, xname=name : self.declare_new_w_star(xname))

    @registering_if(os, 'ttyname')
    def register_os_ttyname(self):
        os_ttyname = self.llexternal('ttyname', [lltype.Signed], rffi.CCHARP, releasegil=False)

        def ttyname_llimpl(fd):
            l_name = os_ttyname(fd)
            if not l_name:
                raise OSError(rposix.get_errno(), "ttyname raised")
            return rffi.charp2str(l_name)

        return extdef([int], str, "ll_os.ttyname",
                      llimpl=ttyname_llimpl)

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
