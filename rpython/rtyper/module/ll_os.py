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
from rpython.rlib import rposix
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

    # a simple, yet useful factory
    def extdef_for_os_function_returning_int(self, name, **kwds):
        c_func = self.llexternal(name, [], rffi.INT, **kwds)
        def c_func_llimpl():
            res = rffi.cast(rffi.SIGNED, c_func())
            if res == -1:
                raise OSError(rposix.get_errno(), "%s failed" % name)
            return res
        c_func_llimpl.func_name = name + '_llimpl'

        return extdef([], int, llimpl=c_func_llimpl,
                      export_name='ll_os.ll_os_' + name)

    def extdef_for_os_function_accepting_int(self, name, **kwds):
        c_func = self.llexternal(name, [rffi.INT], rffi.INT, **kwds)
        def c_func_llimpl(arg):
            res = rffi.cast(rffi.SIGNED, c_func(arg))
            if res == -1:
                raise OSError(rposix.get_errno(), "%s failed" % name)

        c_func_llimpl.func_name = name + '_llimpl'

        return extdef([int], None, llimpl=c_func_llimpl,
                      export_name='ll_os.ll_os_' + name)

    def extdef_for_os_function_accepting_2int(self, name, **kwds):
        c_func = self.llexternal(name, [rffi.INT, rffi.INT], rffi.INT, **kwds)
        def c_func_llimpl(arg, arg2):
            res = rffi.cast(rffi.SIGNED, c_func(arg, arg2))
            if res == -1:
                raise OSError(rposix.get_errno(), "%s failed" % name)

        c_func_llimpl.func_name = name + '_llimpl'

        return extdef([int, int], None, llimpl=c_func_llimpl,
                      export_name='ll_os.ll_os_' + name)

    def extdef_for_os_function_accepting_0int(self, name, **kwds):
        c_func = self.llexternal(name, [], rffi.INT, **kwds)
        def c_func_llimpl():
            res = rffi.cast(rffi.SIGNED, c_func())
            if res == -1:
                raise OSError(rposix.get_errno(), "%s failed" % name)

        c_func_llimpl.func_name = name + '_llimpl'

        return extdef([], None, llimpl=c_func_llimpl,
                      export_name='ll_os.ll_os_' + name)

    def extdef_for_os_function_int_to_int(self, name, **kwds):
        c_func = self.llexternal(name, [rffi.INT], rffi.INT, **kwds)
        def c_func_llimpl(arg):
            res = rffi.cast(rffi.SIGNED, c_func(arg))
            if res == -1:
                raise OSError(rposix.get_errno(), "%s failed" % name)
            return res

        c_func_llimpl.func_name = name + '_llimpl'

        return extdef([int], int, llimpl=c_func_llimpl,
                      export_name='ll_os.ll_os_' + name)

# ------------------------------- os.read -------------------------------

    @registering(os.read)
    def register_os_read(self):
        os_read = self.llexternal(UNDERSCORE_ON_WIN32 + 'read',
                                  [rffi.INT, rffi.VOIDP, rffi.SIZE_T],
                                  rffi.SIZE_T)

        def os_read_llimpl(fd, count):
            if count < 0:
                raise OSError(errno.EINVAL, None)
            rposix.validate_fd(fd)
            with rffi.scoped_alloc_buffer(count) as buf:
                void_buf = rffi.cast(rffi.VOIDP, buf.raw)
                got = rffi.cast(lltype.Signed, os_read(fd, void_buf, count))
                if got < 0:
                    raise OSError(rposix.get_errno(), "os_read failed")
                return buf.str(got)

        return extdef([int, int], SomeString(can_be_None=True),
                      "ll_os.ll_os_read", llimpl=os_read_llimpl)

    @registering(os.write)
    def register_os_write(self):
        os_write = self.llexternal(UNDERSCORE_ON_WIN32 + 'write',
                                   [rffi.INT, rffi.VOIDP, rffi.SIZE_T],
                                   rffi.SIZE_T)

        def os_write_llimpl(fd, data):
            count = len(data)
            rposix.validate_fd(fd)
            with rffi.scoped_nonmovingbuffer(data) as buf:
                written = rffi.cast(lltype.Signed, os_write(
                    rffi.cast(rffi.INT, fd),
                    buf, rffi.cast(rffi.SIZE_T, count)))
                if written < 0:
                    raise OSError(rposix.get_errno(), "os_write failed")
            return written

        return extdef([int, str], SomeInteger(nonneg=True),
                      "ll_os.ll_os_write", llimpl=os_write_llimpl)

    @registering(os.close)
    def register_os_close(self):
        os_close = self.llexternal(UNDERSCORE_ON_WIN32 + 'close', [rffi.INT],
                                   rffi.INT, releasegil=False)

        def close_llimpl(fd):
            rposix.validate_fd(fd)
            error = rffi.cast(lltype.Signed, os_close(rffi.cast(rffi.INT, fd)))
            if error == -1:
                raise OSError(rposix.get_errno(), "close failed")

        return extdef([int], s_None, llimpl=close_llimpl,
                      export_name="ll_os.ll_os_close")

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
                                   rffi.LONGLONG, macro=True)

        def lseek_llimpl(fd, pos, how):
            rposix.validate_fd(fd)
            how = fix_seek_arg(how)
            res = os_lseek(rffi.cast(rffi.INT,      fd),
                           rffi.cast(rffi.LONGLONG, pos),
                           rffi.cast(rffi.INT,      how))
            res = rffi.cast(lltype.SignedLongLong, res)
            if res < 0:
                raise OSError(rposix.get_errno(), "os_lseek failed")
            return res

        return extdef([int, r_longlong, int],
                      r_longlong,
                      llimpl = lseek_llimpl,
                      export_name = "ll_os.ll_os_lseek")

    @registering_if(os, 'ftruncate')
    def register_os_ftruncate(self):
        os_ftruncate = self.llexternal('ftruncate',
                                       [rffi.INT, rffi.LONGLONG], rffi.INT, macro=True)

        def ftruncate_llimpl(fd, length):
            rposix.validate_fd(fd)
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
            rposix.validate_fd(fd)
            res = rffi.cast(rffi.SIGNED, os_fsync(rffi.cast(rffi.INT, fd)))
            if res < 0:
                raise OSError(rposix.get_errno(), "fsync failed")
        return extdef([int], s_None,
                      llimpl=fsync_llimpl,
                      export_name="ll_os.ll_os_fsync")

    @registering_if(os, 'fdatasync')
    def register_os_fdatasync(self):
        os_fdatasync = self.llexternal('fdatasync', [rffi.INT], rffi.INT)

        def fdatasync_llimpl(fd):
            rposix.validate_fd(fd)
            res = rffi.cast(rffi.SIGNED, os_fdatasync(rffi.cast(rffi.INT, fd)))
            if res < 0:
                raise OSError(rposix.get_errno(), "fdatasync failed")
        return extdef([int], s_None,
                      llimpl=fdatasync_llimpl,
                      export_name="ll_os.ll_os_fdatasync")

    @registering_if(os, 'fchdir')
    def register_os_fchdir(self):
        os_fchdir = self.llexternal('fchdir', [rffi.INT], rffi.INT)

        def fchdir_llimpl(fd):
            rposix.validate_fd(fd)
            res = rffi.cast(rffi.SIGNED, os_fchdir(rffi.cast(rffi.INT, fd)))
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

        return extdef([traits.str0, int], s_Bool, llimpl=access_llimpl,
                      export_name=traits.ll_os_name("access"))

    @registering_str_unicode(getattr(posix, '_getfullpathname', None),
                             condition=sys.platform=='win32')
    def register_posix__getfullpathname(self, traits):
        # this nt function is not exposed via os, but needed
        # to get a correct implementation of os.path.abspath
        from rpython.rtyper.module.ll_win32file import make_getfullpathname_impl
        getfullpathname_llimpl = make_getfullpathname_impl(traits)

        return extdef([traits.str0],  # a single argument which is a str
                      traits.str0,    # returns a string
                      traits.ll_os_name('_getfullpathname'),
                      llimpl=getfullpathname_llimpl)

    @registering(os.getcwd)
    def register_os_getcwd(self):
        os_getcwd = self.llexternal(UNDERSCORE_ON_WIN32 + 'getcwd',
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

        return extdef([], str0,
                      "ll_os.ll_os_getcwd", llimpl=os_getcwd_llimpl)

    @registering(os.getcwdu, condition=sys.platform=='win32')
    def register_os_getcwdu(self):
        os_wgetcwd = self.llexternal(UNDERSCORE_ON_WIN32 + 'wgetcwd',
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
            from rpython.rtyper.module.ll_win32file import make_listdir_impl
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
            # XXX macro=True is hack to make sure we get the correct kind of
            # dirent struct (which depends on defines)
            os_readdir = self.llexternal('readdir', [DIRP], DIRENTP,
                                         compilation_info=compilation_info,
                                         macro=True)
            os_closedir = self.llexternal('closedir', [DIRP], rffi.INT,
                                          compilation_info=compilation_info)

            def os_listdir_llimpl(path):
                dirp = os_opendir(path)
                if not dirp:
                    raise OSError(rposix.get_errno(), "os_opendir failed")
                result = []
                while True:
                    rposix.set_errno(0)
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

        return extdef([traits.str0],  # a single argument which is a str
                      [traits.str0],  # returns a list of strings
                      traits.ll_os_name('listdir'),
                      llimpl=os_listdir_llimpl)

    @registering(os.pipe)
    def register_os_pipe(self):
        # we need a different approach on Windows and on Posix
        if sys.platform.startswith('win'):
            from rpython.rlib import rwin32
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

        return extdef([str0, int, int], None, "ll_os.ll_os_chown",
                      llimpl=os_chown_llimpl)

    @registering_if(os, 'lchown')
    def register_os_lchown(self):
        os_lchown = self.llexternal('lchown',[rffi.CCHARP, rffi.INT, rffi.INT],
                                    rffi.INT)

        def os_lchown_llimpl(path, uid, gid):
            res = os_lchown(path, uid, gid)
            if res == -1:
                raise OSError(rposix.get_errno(), "os_lchown failed")

        return extdef([str0, int, int], None, "ll_os.ll_os_lchown",
                      llimpl=os_lchown_llimpl)

    @registering_if(os, 'fchown')
    def register_os_fchown(self):
        os_fchown = self.llexternal('fchown',[rffi.INT, rffi.INT, rffi.INT],
                                    rffi.INT)

        def os_fchown_llimpl(fd, uid, gid):
            res = os_fchown(fd, uid, gid)
            if res == -1:
                raise OSError(rposix.get_errno(), "os_fchown failed")

        return extdef([int, int, int], None, "ll_os.ll_os_fchown",
                      llimpl=os_fchown_llimpl)

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
            result = rffi.charp2strn(buf, res)
            lltype.free(buf, flavor='raw')
            return result

        return extdef([str0], str0,
                      "ll_os.ll_os_readlink",
                      llimpl=os_readlink_llimpl)

    @registering(os.isatty)
    def register_os_isatty(self):
        os_isatty = self.llexternal(UNDERSCORE_ON_WIN32 + 'isatty',
                                    [rffi.INT], rffi.INT)

        def isatty_llimpl(fd):
            if not rposix.is_valid_fd(fd):
                return False
            res = rffi.cast(lltype.Signed, os_isatty(rffi.cast(rffi.INT, fd)))
            return res != 0

        return extdef([int], bool, llimpl=isatty_llimpl,
                      export_name="ll_os.ll_os_isatty")

    @registering(os.strerror)
    def register_os_strerror(self):
        os_strerror = self.llexternal('strerror', [rffi.INT], rffi.CCHARP, releasegil=False)

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

        return extdef([str0], int, llimpl=system_llimpl,
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
            from rpython.rlib.rwin32file import make_win32_traits
            win32traits = make_win32_traits(traits)

            @func_renamer('unlink_llimpl_%s' % traits.str.__name__)
            def unlink_llimpl(path):
                if not win32traits.DeleteFile(path):
                    raise rwin32.lastWindowsError()

        return extdef([traits.str0], s_None, llimpl=unlink_llimpl,
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
            from rpython.rtyper.module.ll_win32file import make_chdir_impl
            os_chdir_llimpl = make_chdir_impl(traits)

        return extdef([traits.str0], s_None, llimpl=os_chdir_llimpl,
                      export_name=traits.ll_os_name('chdir'))

    @registering_str_unicode(os.mkdir)
    def register_os_mkdir(self, traits):
        os_mkdir = self.llexternal(traits.posix_function_name('mkdir'),
                                   [traits.CCHARP, rffi.MODE_T], rffi.INT)

        if sys.platform == 'win32':
            from rpython.rlib.rwin32file import make_win32_traits
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

        return extdef([traits.str0, int], s_None, llimpl=os_mkdir_llimpl,
                      export_name=traits.ll_os_name('mkdir'))

    @registering_str_unicode(os.rmdir)
    def register_os_rmdir(self, traits):
        os_rmdir = self.llexternal(traits.posix_function_name('rmdir'),
                                   [traits.CCHARP], rffi.INT)

        def rmdir_llimpl(pathname):
            res = rffi.cast(lltype.Signed, os_rmdir(pathname))
            if res < 0:
                raise OSError(rposix.get_errno(), "os_rmdir failed")

        return extdef([traits.str0], s_None, llimpl=rmdir_llimpl,
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
            from rpython.rtyper.module.ll_win32file import make_chmod_impl
            chmod_llimpl = make_chmod_impl(traits)

        return extdef([traits.str0, int], s_None, llimpl=chmod_llimpl,
                      export_name=traits.ll_os_name('chmod'))

    @registering_if(os, 'fchmod')
    def register_os_fchmod(self):
        os_fchmod = self.llexternal('fchmod', [rffi.INT, rffi.MODE_T],
                                    rffi.INT)

        def fchmod_llimpl(fd, mode):
            mode = rffi.cast(rffi.MODE_T, mode)
            res = rffi.cast(lltype.Signed, os_fchmod(fd, mode))
            if res < 0:
                raise OSError(rposix.get_errno(), "os_fchmod failed")

        return extdef([int, int], s_None, "ll_os.ll_os_fchmod",
                      llimpl=fchmod_llimpl)

    @registering_str_unicode(os.rename)
    def register_os_rename(self, traits):
        os_rename = self.llexternal(traits.posix_function_name('rename'),
                                    [traits.CCHARP, traits.CCHARP], rffi.INT)

        def rename_llimpl(oldpath, newpath):
            res = rffi.cast(lltype.Signed, os_rename(oldpath, newpath))
            if res < 0:
                raise OSError(rposix.get_errno(), "os_rename failed")

        if sys.platform == 'win32':
            from rpython.rlib.rwin32file import make_win32_traits
            win32traits = make_win32_traits(traits)

            @func_renamer('rename_llimpl_%s' % traits.str.__name__)
            def rename_llimpl(oldpath, newpath):
                if not win32traits.MoveFile(oldpath, newpath):
                    raise rwin32.lastWindowsError()

        return extdef([traits.str0, traits.str0], s_None, llimpl=rename_llimpl,
                      export_name=traits.ll_os_name('rename'))

    @registering_str_unicode(getattr(os, 'mkfifo', None))
    def register_os_mkfifo(self, traits):
        os_mkfifo = self.llexternal(traits.posix_function_name('mkfifo'),
                                    [traits.CCHARP, rffi.MODE_T], rffi.INT)

        def mkfifo_llimpl(path, mode):
            res = rffi.cast(lltype.Signed, os_mkfifo(path, mode))
            if res < 0:
                raise OSError(rposix.get_errno(), "os_mkfifo failed")

        return extdef([traits.str0, int], s_None, llimpl=mkfifo_llimpl,
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

        return extdef([traits.str0, int, int], s_None, llimpl=mknod_llimpl,
                      export_name=traits.ll_os_name('mknod'))

    @registering(os.umask)
    def register_os_umask(self):
        os_umask = self.llexternal(UNDERSCORE_ON_WIN32 + 'umask',
                                   [rffi.MODE_T], rffi.MODE_T)

        def umask_llimpl(newmask):
            res = os_umask(rffi.cast(rffi.MODE_T, newmask))
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
