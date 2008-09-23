"""
Low-level implementations for the external functions of the 'os' module.
"""

# Implementation details about those functions
# might be found in doc/rffi.txt

import os, sys, errno
from pypy.rpython.module.support import ll_strcpy, OOSupport
from pypy.tool.sourcetools import func_with_new_name
from pypy.rlib.rarithmetic import r_longlong
from pypy.rpython.extfunc import BaseLazyRegistering
from pypy.rpython.extfunc import registering, registering_if, extdef
from pypy.annotation.model import SomeInteger, SomeString, SomeTuple, SomeFloat
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
from pypy.rlib.objectmodel import keepalive_until_here

posix = __import__(os.name)

if sys.platform.startswith('win'):
    underscore_on_windows = '_'
else:
    underscore_on_windows = ''

includes = []
if not sys.platform.startswith('win'):
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
    if not sys.platform.startswith('win'):
        CLOCK_T = platform.SimpleType('clock_t', rffi.INT)

        TMS = platform.Struct(
            'struct tms', [('tms_utime', rffi.INT),
                           ('tms_stime', rffi.INT),
                           ('tms_cutime', rffi.INT),
                           ('tms_cstime', rffi.INT)])

    SEEK_SET = platform.DefinedConstantInteger('SEEK_SET')
    SEEK_CUR = platform.DefinedConstantInteger('SEEK_CUR')
    SEEK_END = platform.DefinedConstantInteger('SEEK_END')

    UTIMBUF     = platform.Struct('struct '+underscore_on_windows+'utimbuf',
                                  [('actime', rffi.INT),
                                   ('modtime', rffi.INT)])


class RegisterOs(BaseLazyRegistering):

    def __init__(self):
        self.configure(CConfig)

        # we need an indirection via c functions to get macro calls working on llvm
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

    # a simple, yet usefull factory
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

    def extdef_for_function_int_to_int(self, name, **kwds):
        c_func = self.llexternal(name, [rffi.INT], rffi.INT, **kwds)
        def c_func_llimpl(arg):
            res = rffi.cast(rffi.LONG, c_func(arg))
            if res == -1:
                raise OSError(rposix.get_errno(), "%s failed" % name)
        
        c_func_llimpl.func_name = name + '_llimpl'

        return extdef([int], None, llimpl=c_func_llimpl,
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

    @registering(os.utime)
    def register_os_utime(self):
        UTIMBUFP = lltype.Ptr(self.UTIMBUF)
        os_utime = self.llexternal('utime', [rffi.CCHARP, UTIMBUFP], rffi.INT)

        class CConfig:
            _compilation_info_ = ExternalCompilationInfo(
                includes=['sys/time.h']
            )
            HAVE_UTIMES = platform.Has('utimes')
        config = platform.configure(CConfig)

        if config['HAVE_UTIMES']:
            class CConfig:
                _compilation_info_ = ExternalCompilationInfo(
                    includes = ['sys/time.h']
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
                l_times[0].c_tv_sec = int(intpart)
                l_times[0].c_tv_usec = int(fracpart * 1E6)
                fracpart, intpart = math.modf(modtime)
                l_times[1].c_tv_sec = int(intpart)
                l_times[1].c_tv_usec = int(fracpart * 1E6)
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

        def os_utime_llimpl(path, tp):
            # NB. this function is specialized; we get one version where
            # tp is known to be None, and one version where it is known
            # to be a tuple of 2 floats.
            if tp is None:
                error = os_utime(path, lltype.nullptr(UTIMBUFP.TO))
            else:
                actime, modtime = tp
                error = os_utime_platform(path, actime, modtime)
            error = rffi.cast(lltype.Signed, error)
            if error == -1:
                raise OSError(rposix.get_errno(), "os_utime failed")
        os_utime_llimpl._annspecialcase_ = 'specialize:argtype(1)'

        s_string = SomeString()
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

        return extdef(os_utime_normalize_args, s_None,
                      "ll_os.ll_os_utime",
                      llimpl=os_utime_llimpl)


    @registering(os.times)
    def register_os_times(self):
        if sys.platform.startswith('win'):
            HANDLE = rffi.ULONG
            FILETIME = rffi.CStruct('_FILETIME', ('dwLowDateTime', rffi.LONG),
                                                 ('dwHighDateTime', rffi.LONG))
            GetCurrentProcess = self.llexternal('GetCurrentProcess', [],
                                                HANDLE)
            GetProcessTimes = self.llexternal('GetProcessTimes',
                                              [HANDLE,
                                               lltype.Ptr(FILETIME),
                                               lltype.Ptr(FILETIME),
                                               lltype.Ptr(FILETIME),
                                               lltype.Ptr(FILETIME)],
                                              lltype.Bool)

            def times_lltypeimpl():
                pcreate = lltype.malloc(FILETIME, flavor='raw')
                pexit   = lltype.malloc(FILETIME, flavor='raw')
                pkernel = lltype.malloc(FILETIME, flavor='raw')
                puser   = lltype.malloc(FILETIME, flavor='raw')
                hProc = GetCurrentProcess()
                GetProcessTimes(hProc, pcreate, pexit, pkernel, puser)
                # The fields of a FILETIME structure are the hi and lo parts
                # of a 64-bit value expressed in 100 nanosecond units
                # (of course).
                result = (pkernel.c_dwHighDateTime*429.4967296 +
                          pkernel.c_dwLowDateTime*1E-7,
                          puser.c_dwHighDateTime*429.4967296 +
                          puser.c_dwLowDateTime*1E-7,
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
                if result == rffi.cast(self.CLOCK_T, -1):
                    raise OSError(rposix.get_errno(), "times failed")
                return (
                    l_tmsbuf.c_tms_utime / CLOCK_TICKS_PER_SECOND,
                    l_tmsbuf.c_tms_stime / CLOCK_TICKS_PER_SECOND,
                    l_tmsbuf.c_tms_cutime / CLOCK_TICKS_PER_SECOND,
                    l_tmsbuf.c_tms_cstime / CLOCK_TICKS_PER_SECOND,
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
            return c_sysconf(i)
        return extdef([int], int, "ll_os.ll_sysconf", llimpl=sysconf_llimpl)

    @registering_if(os, 'getuid')
    def register_os_getuid(self):
        return self.extdef_for_os_function_returning_int('getuid')

    @registering_if(os, 'geteuid')
    def register_os_geteuid(self):
        return self.extdef_for_os_function_returning_int('geteuid')

    @registering_if(os, 'setuid')
    def register_os_setuid(self):
        return self.extdef_for_function_int_to_int('setuid')

    @registering_if(os, 'seteuid')
    def register_os_seteuid(self):
        return self.extdef_for_function_int_to_int('seteuid')

    @registering_if(os, 'setgid')
    def register_os_setgid(self):
        return self.extdef_for_function_int_to_int('setgid')

    @registering_if(os, 'setegid')
    def register_os_setegid(self):
        return self.extdef_for_function_int_to_int('setegid')

    @registering_if(os, 'getpid')
    def register_os_getpid(self):
        return self.extdef_for_os_function_returning_int('getpid')

    @registering_if(os, 'getgid')
    def register_os_getgid(self):
        return self.extdef_for_os_function_returning_int('getgid')

    @registering_if(os, 'getegid')
    def register_os_getegid(self):
        return self.extdef_for_os_function_returning_int('getegid')
    

    @registering(os.open)
    def register_os_open(self):
        os_open = self.llexternal(underscore_on_windows+'open',
                                  [rffi.CCHARP, rffi.INT, rffi.MODE_T],
                                  rffi.INT)

        def os_open_llimpl(path, flags, mode):
            result = rffi.cast(rffi.LONG, os_open(path, flags, mode))
            if result == -1:
                raise OSError(rposix.get_errno(), "os_open failed")
            return result

        def os_open_oofakeimpl(o_path, flags, mode):
            return os.open(o_path._str, flags, mode)

        return extdef([str, int, int], int, "ll_os.ll_os_open",
                      llimpl=os_open_llimpl, oofakeimpl=os_open_oofakeimpl)

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

        return extdef([int, int], str, "ll_os.ll_os_read",
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
        os_close = self.llexternal(underscore_on_windows+'close', [rffi.INT], rffi.INT)
        
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
                raise OSError(rposix.get_errno(), "os_lseek failed")

        return extdef([int, r_longlong], s_None,
                      llimpl = ftruncate_llimpl,
                      export_name = "ll_os.ll_os_ftruncate")

    @registering(os.access)
    def register_os_access(self):
        os_access = self.llexternal(underscore_on_windows + 'access',
                                    [rffi.CCHARP, rffi.INT],
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

        return extdef([str, int], s_Bool, llimpl=access_llimpl,
                      export_name="ll_os.ll_os_access",
                      oofakeimpl=os_access_oofakeimpl)

    @registering_if(posix, '_getfullpathname')
    def register_posix__getfullpathname(self):
        # this nt function is not exposed via os, but needed
        # to get a correct implementation of os.abspath
        # XXX why do we ignore WINAPI conventions everywhere?
        class CConfig:
            _compilation_info_ = ExternalCompilationInfo(
                includes = ['Windows.h']
            )
            MAX_PATH = platform.ConstantInteger('MAX_PATH')
            DWORD    = platform.SimpleType("DWORD", rffi.ULONG)
            LPCTSTR  = platform.SimpleType("LPCTSTR", rffi.CCHARP)
            LPTSTR   = platform.SimpleType("LPTSTR", rffi.CCHARP)
            LPTSTRP  = platform.SimpleType("LPTSTR*", rffi.CCHARPP)

        config = platform.configure(CConfig)
        MAX_PATH = config['MAX_PATH']
        DWORD    = config['DWORD']
        LPCTSTR  = config['LPCTSTR']
        LPTSTR   = config['LPTSTR']
        LPTSTRP  = config['LPTSTRP']
        # XXX unicode?
        GetFullPathName = self.llexternal('GetFullPathNameA',
                         [LPCTSTR, DWORD, LPTSTR, LPTSTRP], DWORD)
        GetLastError = self.llexternal('GetLastError', [], DWORD)
        ##DWORD WINAPI GetFullPathName(
        ##  __in          LPCTSTR lpFileName,
        ##  __in          DWORD nBufferLength,
        ##  __out         LPTSTR lpBuffer,
        ##  __out         LPTSTR* lpFilePart
        ##);

        def _getfullpathname_llimpl(lpFileName):
            nBufferLength = MAX_PATH + 1
            lpBuffer = lltype.malloc(LPTSTR.TO, nBufferLength, flavor='raw')
            try:
                res = GetFullPathName(
                    lpFileName, rffi.cast(DWORD, nBufferLength),
                    lpBuffer, lltype.nullptr(LPTSTRP.TO))
                if res == 0:
                    error = GetLastError()
                    raise OSError(error, "_getfullpathname failed")
                # XXX ntpath expects WindowsError :-(
                result = rffi.charp2str(lpBuffer)
                return result
            finally:
                lltype.free(lpBuffer, flavor='raw')

        return extdef([str],  # a single argument which is a str
                      str,    # returns a string
                      "ll_os.posix__getfullpathname",
                      llimpl=_getfullpathname_llimpl)

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

    @registering(os.listdir)
    def register_os_listdir(self):
        # we need a different approach on Windows and on Posix
        if sys.platform.startswith('win'):
            class CConfig:
                _compilation_info_ = ExternalCompilationInfo(
                    includes = ['windows.h']
                )
                WIN32_FIND_DATA = platform.Struct('struct _WIN32_FIND_DATAA',
                    [('cFileName', lltype.FixedSizeArray(rffi.CHAR, 1))])
                INVALID_HANDLE_VALUE = platform.ConstantInteger(
                    'INVALID_HANDLE_VALUE')
                ERROR_FILE_NOT_FOUND = platform.ConstantInteger(
                    'ERROR_FILE_NOT_FOUND')
                ERROR_NO_MORE_FILES = platform.ConstantInteger(
                    'ERROR_NO_MORE_FILES')

            config = platform.configure(CConfig)
            WIN32_FIND_DATA      = config['WIN32_FIND_DATA']
            INVALID_HANDLE_VALUE = config['INVALID_HANDLE_VALUE']
            ERROR_FILE_NOT_FOUND = config['ERROR_FILE_NOT_FOUND']
            ERROR_NO_MORE_FILES  = config['ERROR_NO_MORE_FILES']
            LPWIN32_FIND_DATA    = lltype.Ptr(WIN32_FIND_DATA)
            HANDLE               = rffi.ULONG
            #MAX_PATH = WIN32_FIND_DATA.c_cFileName.length

            GetLastError = self.llexternal('GetLastError', [], lltype.Signed)
            FindFirstFile = self.llexternal('FindFirstFile',
                                            [rffi.CCHARP, LPWIN32_FIND_DATA],
                                            HANDLE)
            FindNextFile = self.llexternal('FindNextFile',
                                           [HANDLE, LPWIN32_FIND_DATA],
                                           rffi.INT)
            FindClose = self.llexternal('FindClose',
                                        [HANDLE],
                                        rffi.INT)

            def os_listdir_llimpl(path):
                if path and path[-1] not in ('/', '\\', ':'):
                    path += '/'
                path += '*.*'
                filedata = lltype.malloc(WIN32_FIND_DATA, flavor='raw')
                try:
                    result = []
                    hFindFile = FindFirstFile(path, filedata)
                    if hFindFile == INVALID_HANDLE_VALUE:
                        error = GetLastError()
                        if error == ERROR_FILE_NOT_FOUND:
                            return result
                        else:
                            # XXX guess error code :-(
                            raise OSError(errno.ENOENT, "FindFirstFile failed")
                    while True:
                        name = rffi.charp2str(rffi.cast(rffi.CCHARP,
                                                        filedata.c_cFileName))
                        if name != "." and name != "..":   # skip these
                            result.append(name)
                        if not FindNextFile(hFindFile, filedata):
                            break
                    # FindNextFile sets error to ERROR_NO_MORE_FILES if
                    # it got to the end of the directory
                    error = GetLastError()
                    FindClose(hFindFile)
                    if error == ERROR_NO_MORE_FILES:
                        return result
                    else:
                        # XXX guess error code :-(
                        raise OSError(errno.EIO, "FindNextFile failed")
                finally:
                    lltype.free(filedata, flavor='raw')

        else:
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

        return extdef([str],  # a single argument which is a str
                      [str],  # returns a list of strings
                      "ll_os.ll_os_listdir",
                      llimpl=os_listdir_llimpl)

    @registering(os.pipe)
    def register_os_pipe(self):
        # we need a different approach on Windows and on Posix
        if sys.platform.startswith('win'):
            HANDLE = rffi.ULONG
            HANDLEP = lltype.Ptr(lltype.FixedSizeArray(HANDLE, 1))
            CreatePipe = self.llexternal('CreatePipe', [HANDLEP,
                                                        HANDLEP,
                                                        rffi.VOIDP,
                                                        rffi.ULONG],
                                         rffi.INT)
            _open_osfhandle = self.llexternal('_open_osfhandle', [rffi.ULONG,
                                                                  rffi.INT],
                                              rffi.INT)
            null = lltype.nullptr(rffi.VOIDP.TO)

            def os_pipe_llimpl():
                pread  = lltype.malloc(HANDLEP.TO, flavor='raw')
                pwrite = lltype.malloc(HANDLEP.TO, flavor='raw')
                ok = CreatePipe(pread, pwrite, null, 0)
                hread = pread[0]
                hwrite = pwrite[0]
                lltype.free(pwrite, flavor='raw')
                lltype.free(pread, flavor='raw')
                if not ok:    # XXX guess the error, can't use GetLastError()
                    raise OSError(errno.EMFILE, "os_pipe failed")
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
            res = rffi.cast(rffi.LONG, os_isatty(rffi.cast(rffi.INT, fd)))
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

    @registering(os.unlink)
    def register_os_unlink(self):
        os_unlink = self.llexternal(underscore_on_windows+'unlink', [rffi.CCHARP], rffi.INT)

        def unlink_llimpl(pathname):
            res = rffi.cast(lltype.Signed, os_unlink(pathname))
            if res < 0:
                raise OSError(rposix.get_errno(), "os_unlink failed")

        return extdef([str], s_None, llimpl=unlink_llimpl,
                      export_name="ll_os.ll_os_unlink")

    @registering(os.chdir)
    def register_os_chdir(self):
        os_chdir = self.llexternal(underscore_on_windows+'chdir', [rffi.CCHARP], rffi.INT)

        def chdir_llimpl(path):
            res = rffi.cast(lltype.Signed, os_chdir(path))
            if res < 0:
                raise OSError(rposix.get_errno(), "os_chdir failed")

        return extdef([str], s_None, llimpl=chdir_llimpl,
                      export_name="ll_os.ll_os_chdir")

    @registering(os.mkdir)
    def register_os_mkdir(self):
        if os.name == 'nt':
            ARG2 = []         # no 'mode' argument on Windows - just ignored
        else:
            ARG2 = [rffi.MODE_T]
        os_mkdir = self.llexternal(underscore_on_windows+'mkdir',
                                   [rffi.CCHARP]+ARG2, rffi.INT)
        IGNORE_MODE = len(ARG2) == 0

        def mkdir_llimpl(pathname, mode):
            if IGNORE_MODE:
                res = os_mkdir(pathname)
            else:
                res = os_mkdir(pathname, mode)
            res = rffi.cast(lltype.Signed, res)
            if res < 0:
                raise OSError(rposix.get_errno(), "os_mkdir failed")

        return extdef([str, int], s_None, llimpl=mkdir_llimpl,
                      export_name="ll_os.ll_os_mkdir")

    @registering(os.rmdir)
    def register_os_rmdir(self):
        os_rmdir = self.llexternal(underscore_on_windows+'rmdir', [rffi.CCHARP], rffi.INT)

        def rmdir_llimpl(pathname):
            res = rffi.cast(lltype.Signed, os_rmdir(pathname))
            if res < 0:
                raise OSError(rposix.get_errno(), "os_rmdir failed")

        return extdef([str], s_None, llimpl=rmdir_llimpl,
                      export_name="ll_os.ll_os_rmdir")

    @registering(os.chmod)
    def register_os_chmod(self):
        os_chmod = self.llexternal(underscore_on_windows+'chmod', [rffi.CCHARP, rffi.MODE_T],
                                   rffi.INT)

        def chmod_llimpl(path, mode):
            res = rffi.cast(lltype.Signed, os_chmod(path, rffi.cast(rffi.MODE_T, mode)))
            if res < 0:
                raise OSError(rposix.get_errno(), "os_chmod failed")

        return extdef([str, int], s_None, llimpl=chmod_llimpl,
                      export_name="ll_os.ll_os_chmod")

    @registering(os.rename)
    def register_os_rename(self):
        os_rename = self.llexternal('rename', [rffi.CCHARP, rffi.CCHARP],
                                    rffi.INT)

        def rename_llimpl(oldpath, newpath):
            res = rffi.cast(lltype.Signed, os_rename(oldpath, newpath))
            if res < 0:
                raise OSError(rposix.get_errno(), "os_rename failed")

        return extdef([str, str], s_None, llimpl=rename_llimpl,
                      export_name="ll_os.ll_os_rename")

    @registering(os.umask)
    def register_os_umask(self):
        os_umask = self.llexternal(underscore_on_windows+'umask', [rffi.MODE_T], rffi.MODE_T)

        def umask_llimpl(fd):
            res = os_umask(rffi.cast(rffi.MODE_T, fd))
            return rffi.cast(lltype.Signed, res)

        return extdef([int], int, llimpl=umask_llimpl,
                      export_name="ll_os.ll_os_umask")

    @registering_if(os, 'kill')
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
        eci = self.gcc_profiling_bug_workaround('pid_t _noprof_fork(void)',
                                                'return fork();')
        os_fork = self.llexternal('_noprof_fork', [], rffi.PID_T,
                                  compilation_info = eci)

        def fork_llimpl():
            childpid = rffi.cast(lltype.Signed, os_fork())
            if childpid == -1:
                raise OSError(rposix.get_errno(), "os_fork failed")
            return rffi.cast(lltype.Signed, childpid)

        return extdef([], int, llimpl=fork_llimpl,
                      export_name="ll_os.ll_os_fork")

    @registering(os._exit)
    def register_os__exit(self):
        os__exit = self.llexternal('_exit', [rffi.INT], lltype.Void)

        def _exit_llimpl(status):
            os__exit(rffi.cast(rffi.INT, status))

        return extdef([int], s_None, llimpl=_exit_llimpl,
                      export_name="ll_os.ll_os__exit")

# --------------------------- os.stat & variants ---------------------------

    @registering(os.fstat)
    def register_os_fstat(self):
        from pypy.rpython.module import ll_os_stat
        ll_os_stat.register_stat_variant('fstat')

    @registering(os.stat)
    def register_os_stat(self):
        from pypy.rpython.module import ll_os_stat
        ll_os_stat.register_stat_variant('stat')

    @registering(os.lstat)
    def register_os_lstat(self):
        from pypy.rpython.module import ll_os_stat
        ll_os_stat.register_stat_variant('lstat')

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
