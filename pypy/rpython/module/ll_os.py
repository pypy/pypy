"""
Low-level implementations for the external functions of the 'os' module.
"""

# Implementation details about those functions
# might be found in doc/rffi.txt

import os, sys, errno
import py
from pypy.rpython.module.support import ll_strcpy, OOSupport
from pypy.tool.sourcetools import func_with_new_name, func_renamer
from pypy.rlib.rarithmetic import r_longlong
from pypy.rpython.extfunc import (
    BaseLazyRegistering, lazy_register, register_external)
from pypy.rpython.extfunc import registering, registering_if, extdef
from pypy.annotation.model import (
    SomeInteger, SomeString, SomeTuple, SomeFloat, SomeUnicodeString)
from pypy.annotation.model import s_ImpossibleValue, s_None, s_Bool
from pypy.rpython.lltypesystem import rffi
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.tool import rffi_platform as platform
from pypy.rlib import rposix
from pypy.tool.udir import udir
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rpython.lltypesystem.rstr import mallocstr
from pypy.rpython.annlowlevel import llstr
from pypy.rpython.lltypesystem.llmemory import sizeof,\
     itemoffsetof, cast_ptr_to_adr, cast_adr_to_ptr, offsetof
from pypy.rpython.lltypesystem.rstr import STR
from pypy.rpython.annlowlevel import llstr
from pypy.rlib import rgc
from pypy.rlib.objectmodel import specialize

def monkeypatch_rposix(posixfunc, unicodefunc, signature):
    func_name = posixfunc.__name__

    if hasattr(signature, '_default_signature_'):
        signature = signature._default_signature_
    arglist = ['arg%d' % (i,) for i in range(len(signature))]
    transformed_arglist = arglist[:]
    for i, arg in enumerate(signature):
        if arg is unicode:
            transformed_arglist[i] = transformed_arglist[i] + '.as_unicode()'

    args = ', '.join(arglist)
    transformed_args = ', '.join(transformed_arglist)
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
                        if signature[i] in (unicode, None)]
    new_func = specialize.argtype(*specialized_args)(new_func)

    # Monkeypatch the function in pypy.rlib.rposix
    setattr(rposix, func_name, new_func)

class StringTraits:
    str = str
    CHAR = rffi.CHAR
    CCHARP = rffi.CCHARP
    charp2str = staticmethod(rffi.charp2str)
    str2charp = staticmethod(rffi.str2charp)
    free_charp = staticmethod(rffi.free_charp)
    scoped_alloc_buffer = staticmethod(rffi.scoped_alloc_buffer)

    @staticmethod
    def posix_function_name(name):
        return underscore_on_windows + name

    @staticmethod
    def ll_os_name(name):
        return 'll_os.ll_os_' + name

class UnicodeTraits:
    str = unicode
    CHAR = rffi.WCHAR_T
    CCHARP = rffi.CWCHARP
    charp2str = staticmethod(rffi.wcharp2unicode)
    str2charp = staticmethod(rffi.unicode2wcharp)
    free_charp = staticmethod(rffi.free_wcharp)
    scoped_alloc_buffer = staticmethod(rffi.scoped_alloc_unicodebuffer)

    @staticmethod
    def posix_function_name(name):
        return underscore_on_windows + 'w' + name

    @staticmethod
    def ll_os_name(name):
        return 'll_os.ll_os_w' + name

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

if sys.platform.startswith('win'):
    _WIN32 = True
else:
    _WIN32 = False

if _WIN32:
    underscore_on_windows = '_'
else:
    underscore_on_windows = ''

includes = []
if not _WIN32:
    # XXX many of these includes are not portable at all
    includes += ['dirent.h', 'sys/stat.h',
                 'sys/times.h', 'utime.h', 'sys/types.h', 'unistd.h',
                 'signal.h', 'sys/wait.h', 'fcntl.h']
else:
    includes += ['sys/utime.h']


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

        GID_T = platform.SimpleType('gid_t',rffi.INT)
        #TODO right now is used only in getgroups, may need to update other
        #functions like setgid

    SEEK_SET = platform.DefinedConstantInteger('SEEK_SET')
    SEEK_CUR = platform.DefinedConstantInteger('SEEK_CUR')
    SEEK_END = platform.DefinedConstantInteger('SEEK_END')

    UTIMBUF     = platform.Struct('struct '+underscore_on_windows+'utimbuf',
                                  [('actime', rffi.INT),
                                   ('modtime', rffi.INT)])


class RegisterOs(BaseLazyRegistering):

    def __init__(self):
        self.configure(CConfig)

        if hasattr(os, 'getpgrp'):
            self.GETPGRP_HAVE_ARG = platform.checkcompiles(
                "getpgrp(0)",
                '#include <unistd.h>',
                [])

        if hasattr(os, 'setpgrp'):
            self.SETPGRP_HAVE_ARG = platform.checkcompiles(
                "setpgrp(0,0)",
                '#include <unistd.h>',
                [])

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
                data = {'ret_type': 'int', 'name': name}
                decls.append((decl_snippet % data).strip())
                defs.append((def_snippet % data).strip())

            self.compilation_info = self.compilation_info.merge(
                ExternalCompilationInfo(
                post_include_bits = decls,
                separate_module_sources = ["\n".join(defs)]
            ))

    # a simple, yet useful factory
    def extdef_for_os_function_returning_int(self, name, **kwds):
        c_func = self.llexternal(name, [], rffi.INT, **kwds)
        def c_func_llimpl():
            res = rffi.cast(rffi.LONG, c_func())
            if res == -1:
                raise OSError(rposix.get_errno(), "%s failed" % name)
            return res
        c_func_llimpl.func_name = name + '_llimpl'

        return extdef([], int, llimpl=c_func_llimpl,
                      export_name='ll_os.ll_os_' + name)

    def extdef_for_os_function_accepting_int(self, name, **kwds):
        c_func = self.llexternal(name, [rffi.INT], rffi.INT, **kwds)
        def c_func_llimpl(arg):
            res = rffi.cast(rffi.LONG, c_func(arg))
            if res == -1:
                raise OSError(rposix.get_errno(), "%s failed" % name)
        
        c_func_llimpl.func_name = name + '_llimpl'

        return extdef([int], None, llimpl=c_func_llimpl,
                      export_name='ll_os.ll_os_' + name)

    def extdef_for_os_function_accepting_2int(self, name, **kwds):
        c_func = self.llexternal(name, [rffi.INT, rffi.INT], rffi.INT, **kwds)
        def c_func_llimpl(arg, arg2):
            res = rffi.cast(rffi.LONG, c_func(arg, arg2))
            if res == -1:
                raise OSError(rposix.get_errno(), "%s failed" % name)
        
        c_func_llimpl.func_name = name + '_llimpl'

        return extdef([int, int], None, llimpl=c_func_llimpl,
                      export_name='ll_os.ll_os_' + name)        

    def extdef_for_os_function_accepting_0int(self, name, **kwds):
        c_func = self.llexternal(name, [], rffi.INT, **kwds)
        def c_func_llimpl():
            res = rffi.cast(rffi.LONG, c_func())
            if res == -1:
                raise OSError(rposix.get_errno(), "%s failed" % name)
        
        c_func_llimpl.func_name = name + '_llimpl'

        return extdef([], None, llimpl=c_func_llimpl,
                      export_name='ll_os.ll_os_' + name)        

    def extdef_for_os_function_int_to_int(self, name, **kwds):
        c_func = self.llexternal(name, [rffi.INT], rffi.INT, **kwds)
        def c_func_llimpl(arg):
            res = rffi.cast(rffi.LONG, c_func(arg))
            if res == -1:
                raise OSError(rposix.get_errno(), "%s failed" % name)
            return res
        
        c_func_llimpl.func_name = name + '_llimpl'

        return extdef([int], int, llimpl=c_func_llimpl,
                      export_name='ll_os.ll_os_' + name)

    @registering_if(os, 'execv')
    def register_os_execv(self):
        eci = self.gcc_profiling_bug_workaround(
            'int _noprof_execv(char *path, char *argv[])',
            'return execv(path, argv);')
        os_execv = self.llexternal('_noprof_execv',
                                   [rffi.CCHARP, rffi.CCHARPP],
                                   rffi.INT, compilation_info = eci)

        def execv_llimpl(path, args):
            l_args = rffi.liststr2charpp(args)
            os_execv(path, l_args)
            rffi.free_charpp(l_args)
            raise OSError(rposix.get_errno(), "execv failed")

        return extdef([str, [str]], s_ImpossibleValue, llimpl=execv_llimpl,
                      export_name="ll_os.ll_os_execv")


    @registering_if(os, 'execve')
    def register_os_execve(self):
        eci = self.gcc_profiling_bug_workaround(
            'int _noprof_execve(char *filename, char *argv[], char *envp[])',
            'return execve(filename, argv, envp);')
        os_execve = self.llexternal(
            '_noprof_execve', [rffi.CCHARP, rffi.CCHARPP, rffi.CCHARPP],
            rffi.INT, compilation_info = eci)

        def execve_llimpl(path, args, env):
            # XXX Check path, args, env for \0 and raise TypeErrors as
            # appropriate
            envstrs = []
            for item in env.iteritems():
                envstrs.append("%s=%s" % item)

            l_args = rffi.liststr2charpp(args)
            l_env = rffi.liststr2charpp(envstrs)
            os_execve(path, l_args, l_env)

            # XXX untested
            rffi.free_charpp(l_env)
            rffi.free_charpp(l_args)

            raise OSError(rposix.get_errno(), "execve failed")

        return extdef(
            [str, [str], {str: str}],
            s_ImpossibleValue,
            llimpl=execve_llimpl,
            export_name="ll_os.ll_os_execve")


    @registering_if(posix, 'spawnv')
    def register_os_spawnv(self):
        os_spawnv = self.llexternal('spawnv',
                                    [rffi.INT, rffi.CCHARP, rffi.CCHARPP],
                                    rffi.INT)

        def spawnv_llimpl(mode, path, args):
            mode = rffi.cast(rffi.INT, mode)
            l_args = rffi.liststr2charpp(args)
            childpid = os_spawnv(mode, path, l_args)
            rffi.free_charpp(l_args)
            if childpid == -1:
                raise OSError(rposix.get_errno(), "os_spawnv failed")
            return rffi.cast(lltype.Signed, childpid)

        return extdef([int, str, [str]], int, llimpl=spawnv_llimpl,
                      export_name="ll_os.ll_os_spawnv")

    @registering(os.dup)
    def register_os_dup(self):
        os_dup = self.llexternal(underscore_on_windows+'dup', [rffi.INT], rffi.INT)

        def dup_llimpl(fd):
            newfd = rffi.cast(lltype.Signed, os_dup(rffi.cast(rffi.INT, fd)))
            if newfd == -1:
                raise OSError(rposix.get_errno(), "dup failed")
            return newfd
        
        return extdef([int], int, llimpl=dup_llimpl,
                      export_name="ll_os.ll_os_dup", oofakeimpl=os.dup)

    @registering(os.dup2)
    def register_os_dup2(self):
        os_dup2 = self.llexternal(underscore_on_windows+'dup2',
                                  [rffi.INT, rffi.INT], rffi.INT)

        def dup2_llimpl(fd, newfd):
            error = rffi.cast(lltype.Signed, os_dup2(rffi.cast(rffi.INT, fd),
                                             rffi.cast(rffi.INT, newfd)))
            if error == -1:
                raise OSError(rposix.get_errno(), "dup2 failed")

        return extdef([int, int], s_None, llimpl=dup2_llimpl,
                      export_name="ll_os.ll_os_dup2")

    @registering_if(os, "getlogin", condition=not _WIN32)
    def register_os_getlogin(self):
        os_getlogin = self.llexternal('getlogin', [], rffi.CCHARP)

        def getlogin_llimpl():
            result = os_getlogin()
            if not result:
                raise OSError(rposix.get_errno(), "getlogin failed")

            return rffi.charp2str(result)

        return extdef([], str, llimpl=getlogin_llimpl,
                      export_name="ll_os.ll_os_getlogin")

    @registering_str_unicode(os.utime)
    def register_os_utime(self, traits):
        UTIMBUFP = lltype.Ptr(self.UTIMBUF)
        os_utime = self.llexternal('utime', [rffi.CCHARP, UTIMBUFP], rffi.INT)

        if not _WIN32:
            includes = ['sys/time.h']
        else:
            includes = ['time.h']
        class CConfig:
            _compilation_info_ = ExternalCompilationInfo(
                includes=includes
            )
            HAVE_UTIMES = platform.Has('utimes')
        config = platform.configure(CConfig)

        # XXX note that on Windows, calls to os.utime() are ignored on
        # directories.  Remove that hack over there once it's fixed here!

        if config['HAVE_UTIMES']:
            class CConfig:
                if not _WIN32:
                    _compilation_info_ = ExternalCompilationInfo(
                        includes = ['sys/time.h']
                    )
                else:
                    _compilation_info_ = ExternalCompilationInfo(
                        includes = ['time.h']
                    )
                TIMEVAL = platform.Struct('struct timeval', [('tv_sec', rffi.LONG),
                                                             ('tv_usec', rffi.LONG)])
            config = platform.configure(CConfig)
            TIMEVAL = config['TIMEVAL']
            TIMEVAL2P = rffi.CArrayPtr(TIMEVAL)
            os_utimes = self.llexternal('utimes', [rffi.CCHARP, TIMEVAL2P],
                                        rffi.INT, compilation_info=CConfig._compilation_info_)

            def os_utime_platform(path, actime, modtime):
                import math
                l_times = lltype.malloc(TIMEVAL2P.TO, 2, flavor='raw')
                fracpart, intpart = math.modf(actime)
                rffi.setintfield(l_times[0], 'c_tv_sec', int(intpart))
                rffi.setintfield(l_times[0], 'c_tv_usec', int(fracpart * 1E6))
                fracpart, intpart = math.modf(modtime)
                rffi.setintfield(l_times[1], 'c_tv_sec', int(intpart))
                rffi.setintfield(l_times[1], 'c_tv_usec', int(fracpart * 1E6))
                error = os_utimes(path, l_times)
                lltype.free(l_times, flavor='raw')
                return error
        else:
            # we only have utime(), which does not allow sub-second resolution
            def os_utime_platform(path, actime, modtime):
                l_utimbuf = lltype.malloc(UTIMBUFP.TO, flavor='raw')
                l_utimbuf.c_actime  = rffi.r_time_t(actime)
                l_utimbuf.c_modtime = rffi.r_time_t(modtime)
                error = os_utime(path, l_utimbuf)
                lltype.free(l_utimbuf, flavor='raw')
                return error

        # NB. this function is specialized; we get one version where
        # tp is known to be None, and one version where it is known
        # to be a tuple of 2 floats.
        if not _WIN32:
            assert traits.str is str

            @specialize.argtype(1)
            def os_utime_llimpl(path, tp):
                if tp is None:
                    error = os_utime(path, lltype.nullptr(UTIMBUFP.TO))
                else:
                    actime, modtime = tp
                    error = os_utime_platform(path, actime, modtime)
                    error = rffi.cast(lltype.Signed, error)
                if error == -1:
                    raise OSError(rposix.get_errno(), "os_utime failed")
        else:
            from pypy.rpython.module.ll_win32file import make_utime_impl
            os_utime_llimpl = make_utime_impl(traits)

        if traits.str is str:
            s_string = SomeString()
        else:
            s_string = SomeUnicodeString()
        s_tuple_of_2_floats = SomeTuple([SomeFloat(), SomeFloat()])

        def os_utime_normalize_args(s_path, s_times):
            # special handling of the arguments: they can be either
            # [str, (float, float)] or [str, s_None], and get normalized
            # to exactly one of these two.
            if not s_string.contains(s_path):
                raise Exception("os.utime() arg 1 must be a string, got %s" % (
                    s_path,))
            case1 = s_None.contains(s_times)
            case2 = s_tuple_of_2_floats.contains(s_times)
            if case1 and case2:
                return [s_string, s_ImpossibleValue] #don't know which case yet
            elif case1:
                return [s_string, s_None]
            elif case2:
                return [s_string, s_tuple_of_2_floats]
            else:
                raise Exception("os.utime() arg 2 must be None or a tuple of "
                                "2 floats, got %s" % (s_times,))
        os_utime_normalize_args._default_signature_ = [traits.str, None]

        return extdef(os_utime_normalize_args, s_None,
                      "ll_os.ll_os_utime",
                      llimpl=os_utime_llimpl)

    @registering(os.times)
    def register_os_times(self):
        if sys.platform.startswith('win'):
            from pypy.rlib import rwin32
            GetCurrentProcess = self.llexternal('GetCurrentProcess', [],
                                                rwin32.HANDLE)
            GetProcessTimes = self.llexternal('GetProcessTimes',
                                              [rwin32.HANDLE,
                                               lltype.Ptr(rwin32.FILETIME),
                                               lltype.Ptr(rwin32.FILETIME),
                                               lltype.Ptr(rwin32.FILETIME),
                                               lltype.Ptr(rwin32.FILETIME)],
                                              rwin32.BOOL)

            def times_lltypeimpl():
                pcreate = lltype.malloc(rwin32.FILETIME, flavor='raw')
                pexit   = lltype.malloc(rwin32.FILETIME, flavor='raw')
                pkernel = lltype.malloc(rwin32.FILETIME, flavor='raw')
                puser   = lltype.malloc(rwin32.FILETIME, flavor='raw')
                hProc = GetCurrentProcess()
                GetProcessTimes(hProc, pcreate, pexit, pkernel, puser)
                # The fields of a FILETIME structure are the hi and lo parts
                # of a 64-bit value expressed in 100 nanosecond units
                # (of course).
                result = (rffi.cast(lltype.Signed, pkernel.c_dwHighDateTime) * 429.4967296 +
                          rffi.cast(lltype.Signed, pkernel.c_dwLowDateTime) * 1E-7,
                          rffi.cast(lltype.Signed, puser.c_dwHighDateTime) * 429.4967296 +
                          rffi.cast(lltype.Signed, puser.c_dwLowDateTime) * 1E-7,
                          0, 0, 0)
                lltype.free(puser,   flavor='raw')
                lltype.free(pkernel, flavor='raw')
                lltype.free(pexit,   flavor='raw')
                lltype.free(pcreate, flavor='raw')
                return result
            self.register(os.times, [], (float, float, float, float, float),
                          "ll_os.ll_times", llimpl=times_lltypeimpl)
            return            

        TMSP = lltype.Ptr(self.TMS)
        os_times = self.llexternal('times', [TMSP], self.CLOCK_T)

        # Here is a random extra platform parameter which is important.
        # Strictly speaking, this should probably be retrieved at runtime, not
        # at translation time.
        CLOCK_TICKS_PER_SECOND = float(os.sysconf('SC_CLK_TCK'))

        def times_lltypeimpl():
            l_tmsbuf = lltype.malloc(TMSP.TO, flavor='raw')
            try:
                result = os_times(l_tmsbuf)
                result = rffi.cast(lltype.Signed, result)
                if result == -1:
                    raise OSError(rposix.get_errno(), "times failed")
                return (
                    rffi.cast(lltype.Signed, l_tmsbuf.c_tms_utime)
                                                   / CLOCK_TICKS_PER_SECOND,
                    rffi.cast(lltype.Signed, l_tmsbuf.c_tms_stime)
                                                   / CLOCK_TICKS_PER_SECOND,
                    rffi.cast(lltype.Signed, l_tmsbuf.c_tms_cutime)
                                                   / CLOCK_TICKS_PER_SECOND,
                    rffi.cast(lltype.Signed, l_tmsbuf.c_tms_cstime)
                                                   / CLOCK_TICKS_PER_SECOND,
                    result / CLOCK_TICKS_PER_SECOND)
            finally:
                lltype.free(l_tmsbuf, flavor='raw')
        self.register(os.times, [], (float, float, float, float, float),
                      "ll_os.ll_times", llimpl=times_lltypeimpl)


    @registering_if(os, 'setsid')
    def register_os_setsid(self):
        os_setsid = self.llexternal('setsid', [], rffi.PID_T)
        def setsid_llimpl():
            result = rffi.cast(lltype.Signed, os_setsid())
            if result == -1:
                raise OSError(rposix.get_errno(), "os_setsid failed")
            return result

        return extdef([], int, export_name="ll_os.ll_os_setsid",
                      llimpl=setsid_llimpl)

    @registering_if(os, 'chroot')
    def register_os_chroot(self):
        os_chroot = self.llexternal('chroot', [rffi.CCHARP], rffi.INT)
        def chroot_llimpl(arg):
            result = os_chroot(arg)
            if result == -1:
                raise OSError(rposix.get_errno(), "os_chroot failed")

        return extdef([str], None, export_name="ll_os.ll_os_chroot",
                      llimpl=chroot_llimpl)

    @registering_if(os, 'uname')
    def register_os_uname(self):
        CHARARRAY = lltype.FixedSizeArray(lltype.Char, 1)
        class CConfig:
            _compilation_info_ = ExternalCompilationInfo(
                includes = ['sys/utsname.h']
            )
            UTSNAME = platform.Struct('struct utsname', [
                ('sysname',  CHARARRAY),
                ('nodename', CHARARRAY),
                ('release',  CHARARRAY),
                ('version',  CHARARRAY),
                ('machine',  CHARARRAY)])
        config = platform.configure(CConfig)
        UTSNAMEP = lltype.Ptr(config['UTSNAME'])

        os_uname = self.llexternal('uname', [UTSNAMEP], rffi.INT,
                                   compilation_info=CConfig._compilation_info_)

        def uname_llimpl():
            l_utsbuf = lltype.malloc(UTSNAMEP.TO, flavor='raw')
            result = os_uname(l_utsbuf)
            if result == -1:
                raise OSError(rposix.get_errno(), "os_uname failed")
            retval = (
                rffi.charp2str(rffi.cast(rffi.CCHARP, l_utsbuf.c_sysname)),
                rffi.charp2str(rffi.cast(rffi.CCHARP, l_utsbuf.c_nodename)),
                rffi.charp2str(rffi.cast(rffi.CCHARP, l_utsbuf.c_release)),
                rffi.charp2str(rffi.cast(rffi.CCHARP, l_utsbuf.c_version)),
                rffi.charp2str(rffi.cast(rffi.CCHARP, l_utsbuf.c_machine)),
                )
            lltype.free(l_utsbuf, flavor='raw')
            return retval

        return extdef([], (str, str, str, str, str),
                      "ll_os.ll_uname", llimpl=uname_llimpl)

    @registering_if(os, 'sysconf')
    def register_os_sysconf(self):
        c_sysconf = self.llexternal('sysconf', [rffi.INT], rffi.LONG)

        def sysconf_llimpl(i):
            rposix.set_errno(0)
            res = c_sysconf(i)
            if res == -1:
                errno = rposix.get_errno()
                if errno != 0:
                    raise OSError(errno, "sysconf failed")
            return res
        return extdef([int], int, "ll_os.ll_sysconf", llimpl=sysconf_llimpl)

    @registering_if(os, 'fpathconf')
    def register_os_fpathconf(self):
        c_fpathconf = self.llexternal('fpathconf',
                                      [rffi.INT, rffi.INT], rffi.LONG)

        def fpathconf_llimpl(fd, i):
            rposix.set_errno(0)
            res = c_fpathconf(fd, i)
            if res == -1:
                errno = rposix.get_errno()
                if errno != 0:
                    raise OSError(errno, "fpathconf failed")
            return res
        return extdef([int, int], int, "ll_os.ll_fpathconf",
                      llimpl=fpathconf_llimpl)

    @registering_if(os, 'getuid')
    def register_os_getuid(self):
        return self.extdef_for_os_function_returning_int('getuid')

    @registering_if(os, 'geteuid')
    def register_os_geteuid(self):
        return self.extdef_for_os_function_returning_int('geteuid')

    @registering_if(os, 'setuid')
    def register_os_setuid(self):
        return self.extdef_for_os_function_accepting_int('setuid')

    @registering_if(os, 'seteuid')
    def register_os_seteuid(self):
        return self.extdef_for_os_function_accepting_int('seteuid')

    @registering_if(os, 'setgid')
    def register_os_setgid(self):
        return self.extdef_for_os_function_accepting_int('setgid')

    @registering_if(os, 'setegid')
    def register_os_setegid(self):
        return self.extdef_for_os_function_accepting_int('setegid')

    @registering_if(os, 'getpid')
    def register_os_getpid(self):
        return self.extdef_for_os_function_returning_int('getpid')

    @registering_if(os, 'getgid')
    def register_os_getgid(self):
        return self.extdef_for_os_function_returning_int('getgid')

    @registering_if(os, 'getegid')
    def register_os_getegid(self):
        return self.extdef_for_os_function_returning_int('getegid')

    @registering_if(os, 'getgroups')
    def register_os_getgroups(self):
        GP = rffi.CArrayPtr(self.GID_T)
        c_getgroups = self.llexternal('getgroups', [rffi.INT, GP], rffi.INT)

        def getgroups_llimpl():
            n = c_getgroups(0, lltype.nullptr(GP.TO))
            if n >= 0:
                groups = lltype.malloc(GP.TO, n, flavor='raw')
                try:
                    n = c_getgroups(n, groups)
                    result = [groups[i] for i in range(n)]
                finally:
                    lltype.free(groups, flavor='raw')
                if n >= 0:
                    return result
            raise OSError(rposix.get_errno(), "os_getgroups failed")

        return extdef([], [self.GID_T], llimpl=getgroups_llimpl,
                      export_name="ll_os.ll_getgroups")

    @registering_if(os, 'getpgrp')
    def register_os_getpgrp(self):
        name = 'getpgrp'
        if self.GETPGRP_HAVE_ARG:
            c_func = self.llexternal(name, [rffi.INT], rffi.INT)
            def c_func_llimpl():
                res = rffi.cast(rffi.LONG, c_func(0))
                if res == -1:
                    raise OSError(rposix.get_errno(), "%s failed" % name)
                return res

            c_func_llimpl.func_name = name + '_llimpl'

            return extdef([], int, llimpl=c_func_llimpl,
                          export_name='ll_os.ll_os_' + name)
        else:
            return self.extdef_for_os_function_returning_int('getpgrp')

    @registering_if(os, 'setpgrp')
    def register_os_setpgrp(self):
        name = 'setpgrp'
        if self.SETPGRP_HAVE_ARG:
            c_func = self.llexternal(name, [rffi.INT, rffi.INT], rffi.INT)
            def c_func_llimpl():
                res = rffi.cast(rffi.LONG, c_func(0, 0))
                if res == -1:
                    raise OSError(rposix.get_errno(), "%s failed" % name)

            c_func_llimpl.func_name = name + '_llimpl'

            return extdef([], None, llimpl=c_func_llimpl,
                          export_name='ll_os.ll_os_' + name)
        else:
            return self.extdef_for_os_function_accepting_0int(name)

    @registering_if(os, 'getppid')
    def register_os_getppid(self):
        return self.extdef_for_os_function_returning_int('getppid')

    @registering_if(os, 'getpgid')
    def register_os_getpgid(self):
        return self.extdef_for_os_function_int_to_int('getpgid')

    @registering_if(os, 'setpgid')
    def register_os_setpgid(self):
        return self.extdef_for_os_function_accepting_2int('setpgid')

    @registering_if(os, 'setreuid')
    def register_os_setreuid(self):
        return self.extdef_for_os_function_accepting_2int('setreuid')

    @registering_if(os, 'setregid')
    def register_os_setregid(self):
        return self.extdef_for_os_function_accepting_2int('setregid')

    @registering_if(os, 'getsid')
    def register_os_getsid(self):
        return self.extdef_for_os_function_int_to_int('getsid')

    @registering_if(os, 'setsid')
    def register_os_setsid(self):
        return self.extdef_for_os_function_returning_int('setsid')

    @registering_str_unicode(os.open)
    def register_os_open(self, traits):
        os_open = self.llexternal(traits.posix_function_name('open'),
                                  [traits.CCHARP, rffi.INT, rffi.MODE_T],
                                  rffi.INT)
        def os_open_llimpl(path, flags, mode):
            result = rffi.cast(lltype.Signed, os_open(path, flags, mode))
            if result == -1:
                raise OSError(rposix.get_errno(), "os_open failed")
            return result

        def os_open_oofakeimpl(path, flags, mode):
            return os.open(OOSupport.from_rstr(path), flags, mode)

        return extdef([traits.str, int, int], int, traits.ll_os_name('open'),
                      llimpl=os_open_llimpl, oofakeimpl=os_open_oofakeimpl)

    @registering_if(os, 'getloadavg')
    def register_os_getloadavg(self):
        AP = rffi.CArrayPtr(lltype.Float)
        c_getloadavg = self.llexternal('getloadavg', [AP, rffi.INT], rffi.INT)

        def getloadavg_llimpl():
            load = lltype.malloc(AP.TO, 3, flavor='raw')
            r = c_getloadavg(load, 3)
            result_tuple = load[0], load[1], load[2]
            lltype.free(load, flavor='raw')
            if r != 3:
                raise OSError
            return result_tuple
        return extdef([], (float, float, float),
                      "ll_os.ll_getloadavg", llimpl=getloadavg_llimpl)

    @registering_if(os, 'makedev')
    def register_os_makedev(self):
        c_makedev = self.llexternal('makedev', [rffi.INT, rffi.INT], rffi.INT)
        def makedev_llimpl(maj, min):
            return c_makedev(maj, min)
        return extdef([int, int], int,
                      "ll_os.ll_makedev", llimpl=makedev_llimpl)

    @registering_if(os, 'major')
    def register_os_major(self):
        c_major = self.llexternal('major', [rffi.INT], rffi.INT)
        def major_llimpl(dev):
            return c_major(dev)
        return extdef([int], int,
                      "ll_os.ll_major", llimpl=major_llimpl)

    @registering_if(os, 'minor')
    def register_os_minor(self):
        c_minor = self.llexternal('minor', [rffi.INT], rffi.INT)
        def minor_llimpl(dev):
            return c_minor(dev)
        return extdef([int], int,
                      "ll_os.ll_minor", llimpl=minor_llimpl)

# ------------------------------- os.read -------------------------------

    @registering(os.read)
    def register_os_read(self):
        os_read = self.llexternal(underscore_on_windows+'read',
                                  [rffi.INT, rffi.VOIDP, rffi.SIZE_T],
                                  rffi.SIZE_T)

        offset = offsetof(STR, 'chars') + itemoffsetof(STR.chars, 0)

        def os_read_llimpl(fd, count):
            if count < 0:
                raise OSError(errno.EINVAL, None)
            raw_buf, gc_buf = rffi.alloc_buffer(count)
            try:
                void_buf = rffi.cast(rffi.VOIDP, raw_buf)
                got = rffi.cast(lltype.Signed, os_read(fd, void_buf, count))
                if got < 0:
                    raise OSError(rposix.get_errno(), "os_read failed")
                return rffi.str_from_buffer(raw_buf, gc_buf, count, got)
            finally:
                rffi.keep_buffer_alive_until_here(raw_buf, gc_buf)
            
        def os_read_oofakeimpl(fd, count):
            return OOSupport.to_rstr(os.read(fd, count))

        return extdef([int, int], SomeString(can_be_None=True),
                      "ll_os.ll_os_read",
                      llimpl=os_read_llimpl, oofakeimpl=os_read_oofakeimpl)

    @registering(os.write)
    def register_os_write(self):
        os_write = self.llexternal(underscore_on_windows+'write',
                                   [rffi.INT, rffi.VOIDP, rffi.SIZE_T],
                                   rffi.SIZE_T)

        def os_write_llimpl(fd, data):
            count = len(data)
            buf = rffi.get_nonmovingbuffer(data)
            try:
                written = rffi.cast(lltype.Signed, os_write(
                    rffi.cast(rffi.INT, fd),
                    buf, rffi.cast(rffi.SIZE_T, count)))
                if written < 0:
                    raise OSError(rposix.get_errno(), "os_write failed")
            finally:
                rffi.free_nonmovingbuffer(data, buf)
            return written

        def os_write_oofakeimpl(fd, data):
            return os.write(fd, OOSupport.from_rstr(data))

        return extdef([int, str], SomeInteger(nonneg=True),
                      "ll_os.ll_os_write", llimpl=os_write_llimpl,
                      oofakeimpl=os_write_oofakeimpl)

    @registering(os.close)
    def register_os_close(self):
        os_close = self.llexternal(underscore_on_windows+'close', [rffi.INT],
                                   rffi.INT, threadsafe=False)
        
        def close_llimpl(fd):
            error = rffi.cast(lltype.Signed, os_close(rffi.cast(rffi.INT, fd)))
            if error == -1:
                raise OSError(rposix.get_errno(), "close failed")

        return extdef([int], s_None, llimpl=close_llimpl,
                      export_name="ll_os.ll_os_close", oofakeimpl=os.close)

    @registering(os.lseek)
    def register_os_lseek(self):
        if sys.platform.startswith('win'):
            funcname = '_lseeki64'
        else:
            funcname = 'lseek'
        if self.SEEK_SET is not None:
            SEEK_SET = self.SEEK_SET
            SEEK_CUR = self.SEEK_CUR
            SEEK_END = self.SEEK_END
        else:
            SEEK_SET, SEEK_CUR, SEEK_END = 0, 1, 2
        if (SEEK_SET, SEEK_CUR, SEEK_END) != (0, 1, 2):
            # Turn 0, 1, 2 into SEEK_{SET,CUR,END}
            def fix_seek_arg(n):
                if n == 0: return SEEK_SET
                if n == 1: return SEEK_CUR
                if n == 2: return SEEK_END
                return n
        else:
            def fix_seek_arg(n):
                return n

        os_lseek = self.llexternal(funcname,
                                   [rffi.INT, rffi.LONGLONG, rffi.INT],
                                   rffi.LONGLONG)

        def lseek_llimpl(fd, pos, how):
            how = fix_seek_arg(how)
            res = os_lseek(rffi.cast(rffi.INT,      fd),
                           rffi.cast(rffi.LONGLONG, pos),
                           rffi.cast(rffi.INT,      how))
            res = rffi.cast(lltype.SignedLongLong, res)
            if res < 0:
                raise OSError(rposix.get_errno(), "os_lseek failed")
            return res

        def os_lseek_oofakeimpl(fd, pos, how):
            res = os.lseek(fd, pos, how)
            return r_longlong(res)

        return extdef([int, r_longlong, int],
                      r_longlong,
                      llimpl = lseek_llimpl,
                      export_name = "ll_os.ll_os_lseek",
                      oofakeimpl = os_lseek_oofakeimpl)

    @registering_if(os, 'ftruncate')
    def register_os_ftruncate(self):
        os_ftruncate = self.llexternal('ftruncate',
                                       [rffi.INT, rffi.LONGLONG], rffi.INT)

        def ftruncate_llimpl(fd, length):
            res = rffi.cast(rffi.LONG,
                            os_ftruncate(rffi.cast(rffi.INT, fd),
                                         rffi.cast(rffi.LONGLONG, length)))
            if res < 0:
                raise OSError(rposix.get_errno(), "os_ftruncate failed")

        return extdef([int, r_longlong], s_None,
                      llimpl = ftruncate_llimpl,
                      export_name = "ll_os.ll_os_ftruncate")

    @registering_if(os, 'fsync')
    def register_os_fsync(self):
        if not _WIN32:
            os_fsync = self.llexternal('fsync', [rffi.INT], rffi.INT)
        else:
            os_fsync = self.llexternal('_commit', [rffi.INT], rffi.INT)

        def fsync_llimpl(fd):
            res = rffi.cast(rffi.LONG, os_fsync(rffi.cast(rffi.INT, fd)))
            if res < 0:
                raise OSError(rposix.get_errno(), "fsync failed")
        return extdef([int], s_None,
                      llimpl=fsync_llimpl,
                      export_name="ll_os.ll_os_fsync")

    @registering_if(os, 'fdatasync')
    def register_os_fdatasync(self):
        os_fdatasync = self.llexternal('fdatasync', [rffi.INT], rffi.INT)

        def fdatasync_llimpl(fd):
            res = rffi.cast(rffi.LONG, os_fdatasync(rffi.cast(rffi.INT, fd)))
            if res < 0:
                raise OSError(rposix.get_errno(), "fdatasync failed")
        return extdef([int], s_None,
                      llimpl=fdatasync_llimpl,
                      export_name="ll_os.ll_os_fdatasync")

    @registering_if(os, 'fchdir')
    def register_os_fchdir(self):
        os_fchdir = self.llexternal('fchdir', [rffi.INT], rffi.INT)

        def fchdir_llimpl(fd):
            res = rffi.cast(rffi.LONG, os_fchdir(rffi.cast(rffi.INT, fd)))
            if res < 0:
                raise OSError(rposix.get_errno(), "fchdir failed")
        return extdef([int], s_None,
                      llimpl=fchdir_llimpl,
                      export_name="ll_os.ll_os_fchdir")

    @registering_str_unicode(os.access)
    def register_os_access(self, traits):
        os_access = self.llexternal(traits.posix_function_name('access'),
                                    [traits.CCHARP, rffi.INT],
                                    rffi.INT)

        if sys.platform.startswith('win'):
            # All files are executable on Windows
            def access_llimpl(path, mode):
                mode = mode & ~os.X_OK
                error = rffi.cast(lltype.Signed, os_access(path, mode))
                return error == 0
        else:
            def access_llimpl(path, mode):
                error = rffi.cast(lltype.Signed, os_access(path, mode))
                return error == 0

        def os_access_oofakeimpl(path, mode):
            return os.access(OOSupport.from_rstr(path), mode)

        return extdef([traits.str, int], s_Bool, llimpl=access_llimpl,
                      export_name=traits.ll_os_name("access"),
                      oofakeimpl=os_access_oofakeimpl)

    @registering_str_unicode(getattr(posix, '_getfullpathname', None),
                             condition=sys.platform=='win32')
    def register_posix__getfullpathname(self, traits):
        # this nt function is not exposed via os, but needed
        # to get a correct implementation of os.abspath
        from pypy.rpython.module.ll_win32file import make_getfullpathname_impl
        getfullpathname_llimpl = make_getfullpathname_impl(traits)

        return extdef([traits.str],  # a single argument which is a str
                      traits.str,    # returns a string
                      traits.ll_os_name('_getfullpathname'),
                      llimpl=getfullpathname_llimpl)

    @registering(os.getcwd)
    def register_os_getcwd(self):
        os_getcwd = self.llexternal(underscore_on_windows + 'getcwd',
                                    [rffi.CCHARP, rffi.SIZE_T],
                                    rffi.CCHARP)

        def os_getcwd_llimpl():
            bufsize = 256
            while True:
                buf = lltype.malloc(rffi.CCHARP.TO, bufsize, flavor='raw')
                res = os_getcwd(buf, rffi.cast(rffi.SIZE_T, bufsize))
                if res:
                    break   # ok
                error = rposix.get_errno()
                lltype.free(buf, flavor='raw')
                if error != errno.ERANGE:
                    raise OSError(error, "getcwd failed")
                # else try again with a larger buffer, up to some sane limit
                bufsize *= 4
                if bufsize > 1024*1024:  # xxx hard-coded upper limit
                    raise OSError(error, "getcwd result too large")
            result = rffi.charp2str(res)
            lltype.free(buf, flavor='raw')
            return result

        def os_getcwd_oofakeimpl():
            return OOSupport.to_rstr(os.getcwd())

        return extdef([], str,
                      "ll_os.ll_os_getcwd", llimpl=os_getcwd_llimpl,
                      oofakeimpl=os_getcwd_oofakeimpl)

    @registering(os.getcwdu, condition=sys.platform=='win32')
    def register_os_getcwdu(self):
        os_wgetcwd = self.llexternal(underscore_on_windows + 'wgetcwd',
                                     [rffi.CWCHARP, rffi.SIZE_T],
                                     rffi.CWCHARP)

        def os_getcwd_llimpl():
            bufsize = 256
            while True:
                buf = lltype.malloc(rffi.CWCHARP.TO, bufsize, flavor='raw')
                res = os_wgetcwd(buf, rffi.cast(rffi.SIZE_T, bufsize))
                if res:
                    break   # ok
                error = rposix.get_errno()
                lltype.free(buf, flavor='raw')
                if error != errno.ERANGE:
                    raise OSError(error, "getcwd failed")
                # else try again with a larger buffer, up to some sane limit
                bufsize *= 4
                if bufsize > 1024*1024:  # xxx hard-coded upper limit
                    raise OSError(error, "getcwd result too large")
            result = rffi.wcharp2unicode(res)
            lltype.free(buf, flavor='raw')
            return result

        return extdef([], unicode,
                      "ll_os.ll_os_wgetcwd", llimpl=os_getcwd_llimpl)

    @registering_str_unicode(os.listdir)
    def register_os_listdir(self, traits):
        # we need a different approach on Windows and on Posix
        if sys.platform.startswith('win'):
            from pypy.rpython.module.ll_win32file import make_listdir_impl
            os_listdir_llimpl = make_listdir_impl(traits)
        else:
            assert traits.str is str
            compilation_info = ExternalCompilationInfo(
                includes = ['sys/types.h', 'dirent.h']
            )
            class CConfig:
                _compilation_info_ = compilation_info
                DIRENT = platform.Struct('struct dirent',
                    [('d_name', lltype.FixedSizeArray(rffi.CHAR, 1))])

            DIRP = rffi.COpaquePtr('DIR')
            config = platform.configure(CConfig)
            DIRENT = config['DIRENT']
            DIRENTP = lltype.Ptr(DIRENT)
            os_opendir = self.llexternal('opendir', [rffi.CCHARP], DIRP,
                                         compilation_info=compilation_info)
            os_readdir = self.llexternal('readdir', [DIRP], DIRENTP,
                                         compilation_info=compilation_info)
            os_closedir = self.llexternal('closedir', [DIRP], rffi.INT,
                                          compilation_info=compilation_info)

            def os_listdir_llimpl(path):
                dirp = os_opendir(path)
                if not dirp:
                    raise OSError(rposix.get_errno(), "os_opendir failed")
                rposix.set_errno(0)
                result = []
                while True:
                    direntp = os_readdir(dirp)
                    if not direntp:
                        error = rposix.get_errno()
                        break
                    namep = rffi.cast(rffi.CCHARP, direntp.c_d_name)
                    name = rffi.charp2str(namep)
                    if name != '.' and name != '..':
                        result.append(name)
                os_closedir(dirp)
                if error:
                    raise OSError(error, "os_readdir failed")
                return result

        return extdef([traits.str],  # a single argument which is a str
                      [traits.str],  # returns a list of strings
                      traits.ll_os_name('listdir'),
                      llimpl=os_listdir_llimpl)

    @registering(os.pipe)
    def register_os_pipe(self):
        # we need a different approach on Windows and on Posix
        if sys.platform.startswith('win'):
            from pypy.rlib import rwin32
            CreatePipe = self.llexternal('CreatePipe', [rwin32.LPHANDLE,
                                                        rwin32.LPHANDLE,
                                                        rffi.VOIDP,
                                                        rwin32.DWORD],
                                         rwin32.BOOL)
            _open_osfhandle = self.llexternal('_open_osfhandle', [rffi.INTPTR_T,
                                                                  rffi.INT],
                                              rffi.INT)
            null = lltype.nullptr(rffi.VOIDP.TO)

            def os_pipe_llimpl():
                pread  = lltype.malloc(rwin32.LPHANDLE.TO, 1, flavor='raw')
                pwrite = lltype.malloc(rwin32.LPHANDLE.TO, 1, flavor='raw')
                ok = CreatePipe(pread, pwrite, null, 0)
                if ok:
                    error = 0
                else:
                    error = rwin32.GetLastError()
                hread = rffi.cast(rffi.INTPTR_T, pread[0])
                hwrite = rffi.cast(rffi.INTPTR_T, pwrite[0])
                lltype.free(pwrite, flavor='raw')
                lltype.free(pread, flavor='raw')
                if error:
                    raise WindowsError(error, "os_pipe failed")
                fdread = _open_osfhandle(hread, 0)
                fdwrite = _open_osfhandle(hwrite, 1)
                return (fdread, fdwrite)

        else:
            INT_ARRAY_P = rffi.CArrayPtr(rffi.INT)
            os_pipe = self.llexternal('pipe', [INT_ARRAY_P], rffi.INT)

            def os_pipe_llimpl():
                filedes = lltype.malloc(INT_ARRAY_P.TO, 2, flavor='raw')
                error = rffi.cast(lltype.Signed, os_pipe(filedes))
                read_fd = filedes[0]
                write_fd = filedes[1]
                lltype.free(filedes, flavor='raw')
                if error != 0:
                    raise OSError(rposix.get_errno(), "os_pipe failed")
                return (rffi.cast(lltype.Signed, read_fd),
                        rffi.cast(lltype.Signed, write_fd))

        return extdef([], (int, int),
                      "ll_os.ll_os_pipe",
                      llimpl=os_pipe_llimpl)

    @registering_if(os, 'chown')
    def register_os_chown(self):
        os_chown = self.llexternal('chown', [rffi.CCHARP, rffi.INT, rffi.INT],
                                   rffi.INT)

        def os_chown_llimpl(path, uid, gid):
            res = os_chown(path, uid, gid)
            if res == -1:
                raise OSError(rposix.get_errno(), "os_chown failed")

        return extdef([str, int, int], None, "ll_os.ll_os_chown",
                      llimpl=os_chown_llimpl)

    @registering_if(os, 'lchown')
    def register_os_lchown(self):
        os_lchown = self.llexternal('lchown',[rffi.CCHARP, rffi.INT, rffi.INT],
                                    rffi.INT)

        def os_lchown_llimpl(path, uid, gid):
            res = os_lchown(path, uid, gid)
            if res == -1:
                raise OSError(rposix.get_errno(), "os_lchown failed")

        return extdef([str, int, int], None, "ll_os.ll_os_lchown",
                      llimpl=os_lchown_llimpl)

    @registering_if(os, 'readlink')
    def register_os_readlink(self):
        os_readlink = self.llexternal('readlink',
                                   [rffi.CCHARP, rffi.CCHARP, rffi.SIZE_T],
                                   rffi.INT)
        # XXX SSIZE_T in POSIX.1-2001

        def os_readlink_llimpl(path):
            bufsize = 1023
            while True:
                l_path = rffi.str2charp(path)
                buf = lltype.malloc(rffi.CCHARP.TO, bufsize,
                                    flavor='raw')
                res = rffi.cast(lltype.Signed, os_readlink(l_path, buf, bufsize))
                lltype.free(l_path, flavor='raw')
                if res < 0:
                    error = rposix.get_errno()    # failed
                    lltype.free(buf, flavor='raw')
                    raise OSError(error, "readlink failed")
                elif res < bufsize:
                    break                       # ok
                else:
                    # buf too small, try again with a larger buffer
                    lltype.free(buf, flavor='raw')
                    bufsize *= 4
            # convert the result to a string
            l = [buf[i] for i in range(res)]
            result = ''.join(l)
            lltype.free(buf, flavor='raw')
            return result

        return extdef([str], str,
                      "ll_os.ll_os_readlink",
                      llimpl=os_readlink_llimpl)

    @registering(os.waitpid)
    def register_os_waitpid(self):
        if sys.platform.startswith('win'):
            # emulate waitpid() with the _cwait() of Microsoft's compiler
            os__cwait = self.llexternal('_cwait',
                                        [rffi.INTP, rffi.PID_T, rffi.INT],
                                        rffi.PID_T)
            def os_waitpid(pid, status_p, options):
                result = os__cwait(status_p, pid, options)
                # shift the status left a byte so this is more
                # like the POSIX waitpid
                status_p[0] <<= 8
                return result
        else:
            # Posix
            os_waitpid = self.llexternal('waitpid',
                                         [rffi.PID_T, rffi.INTP, rffi.INT],
                                         rffi.PID_T)

        def os_waitpid_llimpl(pid, options):
            status_p = lltype.malloc(rffi.INTP.TO, 1, flavor='raw')
            status_p[0] = rffi.cast(rffi.INT, 0)
            result = os_waitpid(rffi.cast(rffi.PID_T, pid),
                                status_p,
                                rffi.cast(rffi.INT, options))
            result = rffi.cast(lltype.Signed, result)
            status = status_p[0]
            lltype.free(status_p, flavor='raw')
            if result == -1:
                raise OSError(rposix.get_errno(), "os_waitpid failed")
            return (rffi.cast(lltype.Signed, result),
                    rffi.cast(lltype.Signed, status))

        return extdef([int, int], (int, int),
                      "ll_os.ll_os_waitpid",
                      llimpl=os_waitpid_llimpl)

    @registering(os.isatty)
    def register_os_isatty(self):
        os_isatty = self.llexternal(underscore_on_windows+'isatty', [rffi.INT], rffi.INT)

        def isatty_llimpl(fd):
            res = rffi.cast(lltype.Signed, os_isatty(rffi.cast(rffi.INT, fd)))
            return res != 0

        return extdef([int], bool, llimpl=isatty_llimpl,
                      export_name="ll_os.ll_os_isatty")

    @registering(os.strerror)
    def register_os_strerror(self):
        os_strerror = self.llexternal('strerror', [rffi.INT], rffi.CCHARP)

        def strerror_llimpl(errnum):
            res = os_strerror(rffi.cast(rffi.INT, errnum))
            if not res:
                raise ValueError("os_strerror failed")
            return rffi.charp2str(res)

        return extdef([int], str, llimpl=strerror_llimpl,
                      export_name="ll_os.ll_os_strerror")

    @registering(os.system)
    def register_os_system(self):
        os_system = self.llexternal('system', [rffi.CCHARP], rffi.INT)

        def system_llimpl(command):
            res = os_system(command)
            return rffi.cast(lltype.Signed, res)

        return extdef([str], int, llimpl=system_llimpl,
                      export_name="ll_os.ll_os_system")

    @registering_str_unicode(os.unlink)
    def register_os_unlink(self, traits):
        os_unlink = self.llexternal(traits.posix_function_name('unlink'),
                                    [traits.CCHARP], rffi.INT)

        def unlink_llimpl(pathname):
            res = rffi.cast(lltype.Signed, os_unlink(pathname))
            if res < 0:
                raise OSError(rposix.get_errno(), "os_unlink failed")

        if sys.platform == 'win32':
            from pypy.rpython.module.ll_win32file import make_win32_traits
            win32traits = make_win32_traits(traits)

            @func_renamer('unlink_llimpl_%s' % traits.str.__name__)
            def unlink_llimpl(path):
                if not win32traits.DeleteFile(path):
                    raise rwin32.lastWindowsError()

        return extdef([traits.str], s_None, llimpl=unlink_llimpl,
                      export_name=traits.ll_os_name('unlink'))

    @registering_str_unicode(os.chdir)
    def register_os_chdir(self, traits):
        os_chdir = self.llexternal(traits.posix_function_name('chdir'),
                                   [traits.CCHARP], rffi.INT)

        def os_chdir_llimpl(path):
            res = rffi.cast(lltype.Signed, os_chdir(path))
            if res < 0:
                raise OSError(rposix.get_errno(), "os_chdir failed")

        # On Windows, use an implementation that will produce Win32 errors
        if sys.platform == 'win32':
            from pypy.rpython.module.ll_win32file import make_chdir_impl
            os_chdir_llimpl = make_chdir_impl(traits)

        return extdef([traits.str], s_None, llimpl=os_chdir_llimpl,
                      export_name=traits.ll_os_name('chdir'))

    @registering_str_unicode(os.mkdir)
    def register_os_mkdir(self, traits):
        os_mkdir = self.llexternal(traits.posix_function_name('mkdir'),
                                   [traits.CCHARP, rffi.MODE_T], rffi.INT)

        if sys.platform == 'win32':
            from pypy.rpython.module.ll_win32file import make_win32_traits
            win32traits = make_win32_traits(traits)

            @func_renamer('mkdir_llimpl_%s' % traits.str.__name__)
            def os_mkdir_llimpl(path, mode):
                if not win32traits.CreateDirectory(path, None):
                    raise rwin32.lastWindowsError()
        else:
            def os_mkdir_llimpl(pathname, mode):
                res = os_mkdir(pathname, mode)
                res = rffi.cast(lltype.Signed, res)
                if res < 0:
                    raise OSError(rposix.get_errno(), "os_mkdir failed")

        return extdef([traits.str, int], s_None, llimpl=os_mkdir_llimpl,
                      export_name=traits.ll_os_name('mkdir'))

    @registering_str_unicode(os.rmdir)
    def register_os_rmdir(self, traits):
        os_rmdir = self.llexternal(traits.posix_function_name('rmdir'),
                                   [traits.CCHARP], rffi.INT)

        def rmdir_llimpl(pathname):
            res = rffi.cast(lltype.Signed, os_rmdir(pathname))
            if res < 0:
                raise OSError(rposix.get_errno(), "os_rmdir failed")

        return extdef([traits.str], s_None, llimpl=rmdir_llimpl,
                      export_name=traits.ll_os_name('rmdir'))

    @registering_str_unicode(os.chmod)
    def register_os_chmod(self, traits):
        os_chmod = self.llexternal(traits.posix_function_name('chmod'),
                                   [traits.CCHARP, rffi.MODE_T], rffi.INT)

        def chmod_llimpl(path, mode):
            res = rffi.cast(lltype.Signed, os_chmod(path, rffi.cast(rffi.MODE_T, mode)))
            if res < 0:
                raise OSError(rposix.get_errno(), "os_chmod failed")

        if sys.platform == 'win32':
            from pypy.rpython.module.ll_win32file import make_chmod_impl
            chmod_llimpl = make_chmod_impl(traits)

        return extdef([traits.str, int], s_None, llimpl=chmod_llimpl,
                      export_name=traits.ll_os_name('chmod'))

    @registering_str_unicode(os.rename)
    def register_os_rename(self, traits):
        os_rename = self.llexternal(traits.posix_function_name('rename'),
                                    [traits.CCHARP, traits.CCHARP], rffi.INT)

        def rename_llimpl(oldpath, newpath):
            res = rffi.cast(lltype.Signed, os_rename(oldpath, newpath))
            if res < 0:
                raise OSError(rposix.get_errno(), "os_rename failed")

        if sys.platform == 'win32':
            from pypy.rpython.module.ll_win32file import make_win32_traits
            win32traits = make_win32_traits(traits)

            @func_renamer('rename_llimpl_%s' % traits.str.__name__)
            def rename_llimpl(oldpath, newpath):
                if not win32traits.MoveFile(oldpath, newpath):
                    raise rwin32.lastWindowsError()

        return extdef([traits.str, traits.str], s_None, llimpl=rename_llimpl,
                      export_name=traits.ll_os_name('rename'))

    @registering_str_unicode(getattr(os, 'mkfifo', None))
    def register_os_mkfifo(self, traits):
        os_mkfifo = self.llexternal(traits.posix_function_name('mkfifo'),
                                    [traits.CCHARP, rffi.MODE_T], rffi.INT)

        def mkfifo_llimpl(path, mode):
            res = rffi.cast(lltype.Signed, os_mkfifo(path, mode))
            if res < 0:
                raise OSError(rposix.get_errno(), "os_mkfifo failed")

        return extdef([traits.str, int], s_None, llimpl=mkfifo_llimpl,
                      export_name=traits.ll_os_name('mkfifo'))

    @registering_str_unicode(getattr(os, 'mknod', None))
    def register_os_mknod(self, traits):
        os_mknod = self.llexternal(traits.posix_function_name('mknod'),
                                   [traits.CCHARP, rffi.MODE_T, rffi.INT],
                                   rffi.INT)      # xxx: actually ^^^ dev_t

        def mknod_llimpl(path, mode, dev):
            res = rffi.cast(lltype.Signed, os_mknod(path, mode, dev))
            if res < 0:
                raise OSError(rposix.get_errno(), "os_mknod failed")

        return extdef([traits.str, int, int], s_None, llimpl=mknod_llimpl,
                      export_name=traits.ll_os_name('mknod'))

    @registering(os.umask)
    def register_os_umask(self):
        os_umask = self.llexternal(underscore_on_windows+'umask', [rffi.MODE_T], rffi.MODE_T)

        def umask_llimpl(fd):
            res = os_umask(rffi.cast(rffi.MODE_T, fd))
            return rffi.cast(lltype.Signed, res)

        return extdef([int], int, llimpl=umask_llimpl,
                      export_name="ll_os.ll_os_umask")

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

        return extdef([str, str], s_None, llimpl=link_llimpl,
                      export_name="ll_os.ll_os_link")

    @registering_if(os, 'symlink')
    def register_os_symlink(self):
        os_symlink = self.llexternal('symlink', [rffi.CCHARP, rffi.CCHARP],
                                     rffi.INT)

        def symlink_llimpl(oldpath, newpath):
            res = rffi.cast(lltype.Signed, os_symlink(oldpath, newpath))
            if res < 0:
                raise OSError(rposix.get_errno(), "os_symlink failed")

        return extdef([str, str], s_None, llimpl=symlink_llimpl,
                      export_name="ll_os.ll_os_symlink")

    @registering_if(os, 'fork')
    def register_os_fork(self):
        from pypy.module.thread import ll_thread
        eci = self.gcc_profiling_bug_workaround('pid_t _noprof_fork(void)',
                                                'return fork();')
        os_fork = self.llexternal('_noprof_fork', [], rffi.PID_T,
                                  compilation_info = eci,
                                  _nowrapper = True)

        def fork_llimpl():
            opaqueaddr = ll_thread.gc_thread_before_fork()
            childpid = rffi.cast(lltype.Signed, os_fork())
            ll_thread.gc_thread_after_fork(childpid, opaqueaddr)
            if childpid == -1:
                raise OSError(rposix.get_errno(), "os_fork failed")
            return rffi.cast(lltype.Signed, childpid)

        return extdef([], int, llimpl=fork_llimpl,
                      export_name="ll_os.ll_os_fork")

    @registering_if(os, 'openpty')
    def register_os_openpty(self):
        os_openpty = self.llexternal(
            'openpty',
            [rffi.INTP, rffi.INTP, rffi.VOIDP, rffi.VOIDP, rffi.VOIDP],
            rffi.INT,
            compilation_info=ExternalCompilationInfo(libraries=['util']))
        def openpty_llimpl():
            master_p = lltype.malloc(rffi.INTP.TO, 1, flavor='raw')
            slave_p = lltype.malloc(rffi.INTP.TO, 1, flavor='raw')
            result = os_openpty(master_p, slave_p, None, None, None)
            master_fd = master_p[0]
            slave_fd = slave_p[0]
            lltype.free(master_p, flavor='raw')
            lltype.free(slave_p, flavor='raw')
            if result == -1:
                raise OSError(rposix.get_errno(), "os_openpty failed")
            return (rffi.cast(lltype.Signed, master_fd),
                    rffi.cast(lltype.Signed, slave_fd))

        return extdef([], (int, int), "ll_os.ll_os_openpty",
                      llimpl=openpty_llimpl)

    @registering_if(os, 'forkpty')
    def register_os_forkpty(self):
        os_forkpty = self.llexternal(
            'forkpty',
            [rffi.INTP, rffi.VOIDP, rffi.VOIDP, rffi.VOIDP],
            rffi.PID_T,
            compilation_info=ExternalCompilationInfo(libraries=['util']))
        def forkpty_llimpl():
            master_p = lltype.malloc(rffi.INTP.TO, 1, flavor='raw')
            childpid = os_forkpty(master_p, None, None, None)
            master_fd = master_p[0]
            lltype.free(master_p, flavor='raw')
            if childpid == -1:
                raise OSError(rposix.get_errno(), "os_forkpty failed")
            return (rffi.cast(lltype.Signed, childpid),
                    rffi.cast(lltype.Signed, master_fd))

        return extdef([], (int, int), "ll_os.ll_os_forkpty",
                      llimpl=forkpty_llimpl)

    @registering(os._exit)
    def register_os__exit(self):
        os__exit = self.llexternal('_exit', [rffi.INT], lltype.Void)

        def _exit_llimpl(status):
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

# --------------------------- os.stat & variants ---------------------------

    @registering(os.fstat)
    def register_os_fstat(self):
        from pypy.rpython.module import ll_os_stat
        return ll_os_stat.register_stat_variant('fstat', StringTraits())

    @registering_str_unicode(os.stat)
    def register_os_stat(self, traits):
        from pypy.rpython.module import ll_os_stat
        return ll_os_stat.register_stat_variant('stat', traits)

    @registering_str_unicode(os.lstat)
    def register_os_lstat(self, traits):
        from pypy.rpython.module import ll_os_stat
        return ll_os_stat.register_stat_variant('lstat', traits)

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
        os_ttyname = self.llexternal('ttyname', [lltype.Signed], rffi.CCHARP)

        def ttyname_llimpl(fd):
            l_name = os_ttyname(fd)
            if not l_name:
                raise OSError(rposix.get_errno(), "ttyname raised")
            return rffi.charp2str(l_name)

        return extdef([int], str, "ll_os.ttyname",
                      llimpl=ttyname_llimpl)

    # ____________________________________________________________
    # XXX horrible workaround for a bug of profiling in gcc on
    # OS X with functions containing a direct call to some system calls
    # like fork(), execv(), execve()
    def gcc_profiling_bug_workaround(self, decl, body):
        body = ('/*--no-profiling-for-this-file!--*/\n'
                '%s {\n'
                '\t%s\n'
                '}\n' % (decl, body,))
        return ExternalCompilationInfo(
            post_include_bits = [decl + ';'],
            separate_module_sources = [body])

# ____________________________________________________________
# Support for os.environ

# XXX only for systems where os.environ is an instance of _Environ,
# which should cover Unix and Windows at least
assert type(os.environ) is not dict

from pypy.rpython.controllerentry import ControllerEntryForPrebuilt

class EnvironExtRegistry(ControllerEntryForPrebuilt):
    _about_ = os.environ

    def getcontroller(self):
        from pypy.rpython.module.ll_os_environ import OsEnvironController
        return OsEnvironController()

# ____________________________________________________________
# Support for the WindowsError exception

if sys.platform == 'win32':
    from pypy.rlib import rwin32

    class RegisterFormatError(BaseLazyRegistering):
        def __init__(self):
            pass

        @registering(rwin32.FormatError)
        def register_rwin32_FormatError(self):
            return extdef([rwin32.DWORD], str,
                          "rwin32_FormatError",
                          llimpl=rwin32.llimpl_FormatError,
                          ooimpl=rwin32.fake_FormatError)
