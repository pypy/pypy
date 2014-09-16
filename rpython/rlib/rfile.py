""" This file makes open() and friends RPython. Note that RFile should not
be used directly and instead it's magically appearing each time you call
python builtin open()
"""

import os, sys, stat, errno
from rpython.rlib import rposix
from rpython.rlib.objectmodel import enforceargs
from rpython.rlib.rarithmetic import intmask
from rpython.rlib.rstring import StringBuilder
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rtyper.tool import rffi_platform as platform
from rpython.translator.tool.cbuild import ExternalCompilationInfo

MS_WINDOWS = os.name == 'nt'
if MS_WINDOWS:
    from rpython.rlib.rwin32 import _get_osfhandle, SetEndOfFile, INVALID_HANDLE_VALUE

includes = ['stdio.h', 'sys/types.h']
if os.name == "posix":
    includes += ['unistd.h']

stdio_streams = ['stdin', 'stdout', 'stderr']
separate_module_sources = ['\n'.join('FILE* get_%s() { return %s; }' % (s, s)
                                     for s in stdio_streams)]
post_include_bits = ['FILE* get_%s();' % s for s in stdio_streams]
export_symbols = ['get_%s' % s for s in stdio_streams]

eci = ExternalCompilationInfo(includes=includes,
                              separate_module_sources=separate_module_sources,
                              post_include_bits=post_include_bits,
                              export_symbols=export_symbols)


class CConfig(object):
    _compilation_info_ = eci

    off_t = platform.SimpleType('off_t')

    _IONBF = platform.DefinedConstantInteger('_IONBF')
    _IOLBF = platform.DefinedConstantInteger('_IOLBF')
    _IOFBF = platform.DefinedConstantInteger('_IOFBF')
    BUFSIZ = platform.DefinedConstantInteger('BUFSIZ')
    EOF = platform.DefinedConstantInteger('EOF')

config = platform.configure(CConfig)

FILEP = rffi.COpaquePtr("FILE")
OFF_T = config['off_t']

_IONBF = config['_IONBF']
_IOLBF = config['_IOLBF']
_IOFBF = config['_IOFBF']
BUFSIZ = config['BUFSIZ']
EOF = config['EOF']

BASE_LINE_SIZE = 100

NEWLINE_UNKNOWN = 0
NEWLINE_CR = 1
NEWLINE_LF = 2
NEWLINE_CRLF = 4


def llexternal(*args, **kwargs):
    return rffi.llexternal(*args, compilation_info=eci, **kwargs)

_fdopen = ('_' if MS_WINDOWS else '') + 'fdopen'
_fileno = ('_' if MS_WINDOWS else '') + 'fileno'

c_fopen = llexternal('fopen', [rffi.CCHARP, rffi.CCHARP], FILEP, macro=True)
c_popen = llexternal('popen', [rffi.CCHARP, rffi.CCHARP], FILEP)
c_fdopen = llexternal(_fdopen, [rffi.INT, rffi.CCHARP], FILEP)
c_tmpfile = llexternal('tmpfile', [], FILEP)

# Note: the following functions are called from __del__ methods,
# so must be 'releasegil=False'.  Otherwise, a program using both
# threads and the RFile class cannot translate.  See c684bf704d1f
_fflush = ('fflush', [FILEP], rffi.INT)
c_fflush, c_fflush_nogil = (llexternal(*_fflush),
                            llexternal(*_fflush, releasegil=False))
_fclose = ('fclose', [FILEP], rffi.INT)
c_fclose, c_fclose_nogil = (llexternal(*_fclose),
                            llexternal(*_fclose, releasegil=False))
_pclose = ('pclose', [FILEP], rffi.INT)
c_pclose, c_pclose_nogil = (llexternal(*_pclose),
                            llexternal(*_pclose, releasegil=False))

_fclose2 = (c_fclose, c_fclose_nogil)
_pclose2 = (c_pclose, c_pclose_nogil)

c_flockfile = llexternal('flockfile', [FILEP], lltype.Void)
c_funlockfile = llexternal('funlockfile', [FILEP], lltype.Void)

c_getc = llexternal('getc', [FILEP], rffi.INT)
c_getc_unlocked = llexternal('getc_unlocked', [FILEP], rffi.INT)
c_ungetc = llexternal('ungetc', [rffi.INT, FILEP], rffi.INT)

if MS_WINDOWS:
    c_flockfile = lambda ll_file: None
    c_funlockfile = lambda ll_file: None
    c_getc_unlocked = c_getc
    USE_FGETS_IN_GETLINE = True
else:
    USE_FGETS_IN_GETLINE = False

c_fgets = llexternal('fgets', [rffi.CCHARP, rffi.INT, FILEP], rffi.CCHARP)
c_fread = llexternal('fread', [rffi.CCHARP, rffi.SIZE_T, rffi.SIZE_T, FILEP],
                     rffi.SIZE_T)
c_fwrite = llexternal('fwrite', [rffi.CCHARP, rffi.SIZE_T, rffi.SIZE_T, FILEP],
                      rffi.SIZE_T)

if not MS_WINDOWS:
    assert rffi.sizeof(OFF_T) == 8
    if sys.platform.startswith('linux'):
        c_ftruncate = llexternal('ftruncate64', [rffi.INT, OFF_T], rffi.INT)
        c_fseek = llexternal('fseeko64', [FILEP, OFF_T, rffi.INT], rffi.INT)
        c_ftell = llexternal('ftello64', [FILEP], OFF_T)
    else:
        c_ftruncate = llexternal('ftruncate', [rffi.INT, OFF_T], rffi.INT)
        c_fseek = llexternal('fseeko', [FILEP, OFF_T, rffi.INT], rffi.INT)
        c_ftell = llexternal('ftello', [FILEP], OFF_T)
else:
    c_ftruncate = llexternal('_chsize', [rffi.INT, OFF_T], rffi.INT)
    c_fseek = llexternal('_fseeki64', [FILEP, rffi.LONGLONG, rffi.INT], rffi.INT)
    c_ftell = llexternal('_ftelli64', [FILEP], rffi.LONGLONG)

c_fileno = llexternal(_fileno, [FILEP], rffi.INT, releasegil=False)
c_feof = llexternal('feof', [FILEP], rffi.INT, releasegil=False)
c_ferror = llexternal('ferror', [FILEP], rffi.INT, releasegil=False)
c_clearerr = llexternal('clearerr', [FILEP], lltype.Void, releasegil=False)

c_setvbuf = llexternal('setvbuf', [FILEP, rffi.CCHARP, rffi.INT, rffi.SIZE_T],
                       rffi.INT, releasegil=False)

c_stdin = llexternal('get_stdin', [], FILEP, _nowrapper=True)
c_stdout = llexternal('get_stdout', [], FILEP, _nowrapper=True)
c_stderr = llexternal('get_stderr', [], FILEP, _nowrapper=True)


def _from_errno(exc):
    err = rposix.get_errno()
    return exc(err, os.strerror(err))


def _dircheck(ll_file):
    try:
        st = os.fstat(c_fileno(ll_file))
    except OSError:
        pass
    else:
        if stat.S_ISDIR(st[0]):
            err = errno.EISDIR
            raise IOError(err, os.strerror(err))


def _sanitize_mode(mode):
    if len(mode) == 0:
        raise ValueError("empty mode string")
    upos = mode.find('U')
    if upos >= 0:
        mode = mode[:upos] + mode[upos+1:]
        first = mode[0:1]
        if first == 'w' or first == 'a':
            raise ValueError("universal newline mode can only be used with "
                             "modes starting with 'r'")
        if first != 'r':
            mode = 'r' + mode
        if 'b' not in mode:
            mode = mode[0] + 'b' + mode[1:]
    elif mode[0] != 'r' and mode[0] != 'w' and mode[0] != 'a':
        raise ValueError("mode string must begin with one of 'r', 'w', 'a' "
                         "or 'U', not '%s'" % mode)
    return mode


def create_file(filename, mode="r", buffering=-1):
    newmode = _sanitize_mode(mode)
    ll_name = rffi.str2charp(filename)
    try:
        ll_mode = rffi.str2charp(newmode)
        try:
            ll_file = c_fopen(ll_name, ll_mode)
            if not ll_file:
                raise _from_errno(IOError)
        finally:
            lltype.free(ll_mode, flavor='raw')
    finally:
        lltype.free(ll_name, flavor='raw')
    _dircheck(ll_file)
    f = RFile(ll_file, mode)
    f._setbufsize(buffering)
    return f


def create_fdopen_rfile(fd, mode="r", buffering=-1):
    newmode = _sanitize_mode(mode)
    fd = rffi.cast(rffi.INT, fd)
    rposix.validate_fd(fd)
    ll_mode = rffi.str2charp(newmode)
    try:
        ll_file = c_fdopen(fd, ll_mode)
        if not ll_file:
            raise _from_errno(OSError)
    finally:
        lltype.free(ll_mode, flavor='raw')
    _dircheck(ll_file)
    f = RFile(ll_file, mode)
    f._setbufsize(buffering)
    return f


def create_temp_rfile():
    res = c_tmpfile()
    if not res:
        raise _from_errno(OSError)
    return RFile(res)


def create_popen_file(command, type):
    ll_command = rffi.str2charp(command)
    try:
        ll_type = rffi.str2charp(type)
        try:
            ll_file = c_popen(ll_command, ll_type)
            if not ll_file:
                raise _from_errno(OSError)
        finally:
            lltype.free(ll_type, flavor='raw')
    finally:
        lltype.free(ll_command, flavor='raw')
    return RFile(ll_file, close2=_pclose2)


def _check_and_flush(ll_file):
    prev_fail = c_ferror(ll_file)
    return c_fflush(ll_file) or (EOF if prev_fail else 0)


def create_stdio():
    close2 = (_check_and_flush, c_fflush_nogil)
    stdin = RFile(c_stdin(), close2=(None, None))
    stdout = RFile(c_stdout(), close2=close2)
    stderr = RFile(c_stderr(), close2=close2)
    return stdin, stdout, stderr


class RFile(object):
    _signal_checker = None
    _readable = True
    _writable = True
    _setbuf = lltype.nullptr(rffi.CCHARP.TO)
    _univ_newline = False
    _newlinetypes = NEWLINE_UNKNOWN
    _skipnextlf = False

    def __init__(self, ll_file, mode=None, close2=_fclose2):
        self._ll_file = ll_file
        if mode is not None:
            self._univ_newline = 'U' in mode
            self._readable = self._writable = False
            if 'r' in mode or self._univ_newline:
                self._readable = True
            if 'w' in mode or 'a' in mode:
                self._writable = True
            if '+' in mode:
                self._readable = self._writable = True
        self._close2 = close2

    def _setbufsize(self, bufsize):
        if bufsize >= 0:
            if bufsize == 0:
                mode = _IONBF
            elif bufsize == 1:
                mode = _IOLBF
                bufsize = BUFSIZ
            else:
                mode = _IOFBF
            c_fflush_nogil(self._ll_file)
            if self._setbuf:
                lltype.free(self._setbuf, flavor='raw')
            if mode == _IONBF:
                self._setbuf = lltype.nullptr(rffi.CCHARP.TO)
            else:
                self._setbuf = lltype.malloc(rffi.CCHARP.TO, bufsize, flavor='raw')
            c_setvbuf(self._ll_file, self._setbuf, mode, bufsize)

    def __del__(self):
        """Closes the described file when the object's last reference
        goes away.  Unlike an explicit call to close(), this is meant
        as a last-resort solution and cannot release the GIL or return
        an error code."""
        ll_file = self._ll_file
        if ll_file:
            do_close = self._close2[1]
            if do_close:
                do_close(ll_file)       # return value ignored
            if self._setbuf:
                lltype.free(self._setbuf, flavor='raw')

    def close(self):
        """Closes the described file.

        Attention! Unlike Python semantics, `close' does not return `None' upon
        success but `0', to be able to return an exit code for popen'ed files.

        The actual return value may be determined with os.WEXITSTATUS.
        """
        res = 0
        ll_file = self._ll_file
        if ll_file:
            # double close is allowed
            self._ll_file = lltype.nullptr(FILEP.TO)
            do_close = self._close2[0]
            try:
                if do_close:
                    res = do_close(ll_file)
                    if res == -1:
                        raise _from_errno(IOError)
            finally:
                if self._setbuf:
                    lltype.free(self._setbuf, flavor='raw')
                    self._setbuf = lltype.nullptr(rffi.CCHARP.TO)
        return res

    def _cleanup_(self):
        self._ll_file = lltype.nullptr(FILEP.TO)

    def _check_closed(self):
        if not self._ll_file:
            raise ValueError("I/O operation on closed file")

    def _check_readable(self):
        if not self._readable:
            raise IOError("File not open for reading")

    def _check_writable(self):
        if not self._writable:
            raise IOError("File not open for writing")

    def _fread(self, buf, n, stream):
        if not self._univ_newline:
            return c_fread(buf, 1, n, stream)

        i = 0
        newlinetypes = self._newlinetypes
        skipnextlf = self._skipnextlf
        assert n >= 0
        while n:
            dst = rffi.ptradd(buf, i)
            nread = c_fread(dst, 1, n, stream)
            assert nread <= n
            if nread == 0:
                break

            j = 0
            n -= nread
            shortread = n != 0
            while nread:
                nread -= 1
                c = dst[j]
                j += 1
                if c == '\r':
                    buf[i] = '\n'
                    i += 1
                    skipnextlf = True
                elif skipnextlf and c == '\n':
                    skipnextlf = False
                    newlinetypes |= NEWLINE_CRLF
                    n += 1
                else:
                    if c == '\n':
                        newlinetypes |= NEWLINE_LF
                    elif skipnextlf:
                        newlinetypes |= NEWLINE_CR
                    buf[i] = c
                    i += 1
                    skipnextlf = False
            if shortread:
                if skipnextlf and c_feof(stream):
                    newlinetypes |= NEWLINE_CR
                break
        self._newlinetypes = newlinetypes
        self._skipnextlf = skipnextlf
        return i

    def _new_buffersize(self, currentsize):
        ll_file = self._ll_file
        try:
            st = os.fstat(c_fileno(ll_file))
        except OSError:
            pass
        else:
            end = st.st_size
            try:
                pos = os.lseek(c_fileno(ll_file), 0, os.SEEK_CUR)
            except OSError:
                c_clearerr(ll_file)
            else:
                pos = c_ftell(ll_file)
                if end > pos and pos >= 0:
                    return intmask(currentsize + end - pos + 1)
        # fstat didn't work
        return currentsize + (currentsize >> 3) + 6

    def read(self, size=-1):
        self._check_closed()
        self._check_readable()
        ll_file = self._ll_file

        s = StringBuilder()
        buffersize = size if size >= 0 else self._new_buffersize(0)
        remainsize = buffersize
        raw_buf, gc_buf = rffi.alloc_buffer(remainsize)
        try:
            while True:
                chunksize = intmask(self._fread(raw_buf, remainsize, ll_file))
                interrupted = (c_ferror(ll_file) and
                               rposix.get_errno() == errno.EINTR)
                if interrupted:
                    c_clearerr(ll_file)
                    if self._signal_checker is not None:
                        self._signal_checker()
                if chunksize == 0:
                    if interrupted:
                        continue
                    if not c_ferror(ll_file):
                        break
                    c_clearerr(ll_file)
                    if s.getlength() > 0 and rposix.get_errno() == errno.EAGAIN:
                        break
                    raise _from_errno(IOError)
                elif chunksize == size:
                    # we read everything in one call, try to avoid copy
                    # (remainsize == size if chunksize == size)
                    return rffi.str_from_buffer(raw_buf, gc_buf, remainsize, size)
                s.append_charpsize(raw_buf, chunksize)
                if chunksize < remainsize and not interrupted:
                    c_clearerr(ll_file)
                    break
                if size >= 0:
                    break
                buffersize = self._new_buffersize(buffersize)
                remainsize = buffersize - s.getlength()
                rffi.keep_buffer_alive_until_here(raw_buf, gc_buf)
                raw_buf, gc_buf = rffi.alloc_buffer(remainsize)
        finally:
            rffi.keep_buffer_alive_until_here(raw_buf, gc_buf)
        return s.build()

    def _get_line_fgets_single(self, raw_buf):
        ll_file = self._ll_file
        for i in range(BASE_LINE_SIZE):
            raw_buf[i] = '\n'

        result = c_fgets(raw_buf, BASE_LINE_SIZE, ll_file)
        if not result:
            c_clearerr(ll_file)
            if self._signal_checker is not None:
                self._signal_checker()
            return 0

        # Assume that fgets() works as documented, and additionally
        # never writes beyond the final \0, which the CPython
        # fileobject.c says appears to be the case everywhere.
        # The only case where the buffer was not big enough is the
        # case where the buffer is full, ends with \0, and doesn't
        # end with \n\0.

        p = 0
        while raw_buf[p] != '\n':
            p += 1
            if p == BASE_LINE_SIZE:
                # fgets read whole buffer without finding newline
                return -1
        # p points to first \n

        if p + 1 < BASE_LINE_SIZE and raw_buf[p + 1] == '\0':
            # \n followed by \0, fgets read and found newline
            return p + 1
        else:
            # \n not followed by \0, fgets read but didnt find newline
            assert p > 0 and raw_buf[p - 1] == '\0'
            return p - 1

    def _get_line_fgets(self):
        # XXX use buffer size logic from cpython
        with rffi.scoped_alloc_buffer(BASE_LINE_SIZE) as buf:
            c = self._get_line_fgets_single(buf.raw)
            if c >= 0:
                return buf.str(c)

            # this is the rare case: the line is longer than BASE_LINE_SIZE
            s = StringBuilder()
            while True:
                s.append_charpsize(buf.raw, BASE_LINE_SIZE - 1)
                c = self._get_line_fgets_single(buf.raw)
                if c >= 0:
                    break
            s.append_charpsize(buf.raw, c)
        return s.build()

    def _get_line(self, size):
        if USE_FGETS_IN_GETLINE and size < 0 and not self._univ_newline:
            return self._get_line_fgets()

        ll_file = self._ll_file
        newlinetypes = self._newlinetypes
        skipnextlf = self._skipnextlf
        c = 0
        s = StringBuilder()
        while True:
            # XXX release gil for all of this rather than each getc
            c_flockfile(ll_file)
            if self._univ_newline:
                while size < 0 or s.getlength() < size:
                    c = c_getc_unlocked(ll_file)
                    if c == EOF:
                        break
                    if skipnextlf:
                        skipnextlf = False
                        if c == ord('\n'):
                            newlinetypes |= NEWLINE_CRLF
                            c = c_getc_unlocked(ll_file)
                            if c == EOF:
                                break
                        else:
                            newlinetypes |= NEWLINE_CR
                    if c == ord('\r'):
                        skipnextlf = True
                        c = ord('\n')
                    elif c == ord('\n'):
                        newlinetypes |= NEWLINE_LF
                    s.append(chr(c))
                    if c == ord('\n'):
                        break
                if c == EOF:
                    if c_ferror(ll_file) and rposix.get_errno() == errno.EINTR:
                        c_funlockfile(ll_file)
                        self._newlinetypes = newlinetypes
                        self._skipnextlf = skipnextlf
                        if self._signal_checker is not None:
                            self._signal_checker()
                        c_clearerr(ll_file)
                        continue
                    if skipnextlf:
                        newlinetypes |= NEWLINE_CR
            else:
                while size < 0 or s.getlength() < size:
                    c = c_getc_unlocked(ll_file)
                    if c == EOF:
                        break
                    s.append(chr(c))
                    if c == ord('\n'):
                        break
            c_funlockfile(ll_file)
            self._newlinetypes = newlinetypes
            self._skipnextlf = skipnextlf
            if c == ord('\n'):
                break
            elif c == EOF:
                if c_ferror(ll_file):
                    if rposix.get_errno() == errno.EINTR:
                        if self._signal_checker is not None:
                            self._signal_checker()
                        c_clearerr(ll_file)
                        continue
                    c_clearerr(ll_file)
                    raise _from_errno(IOError)
                c_clearerr(ll_file)
                if self._signal_checker is not None:
                    self._signal_checker()
                break
            else:
                assert s.getlength() == size
                break
        return s.build()

    def readline(self, size=-1):
        self._check_closed()
        self._check_readable()
        if size == 0:
            return ""
        return self._get_line(size)

    @enforceargs(None, str)
    def write(self, value):
        self._check_closed()
        self._check_writable()
        ll_file = self._ll_file
        ll_value = rffi.get_nonmovingbuffer(value)
        try:
            # note that since we got a nonmoving buffer, it is either raw
            # or already cannot move, so the arithmetics below are fine
            n = len(value)
            n2 = c_fwrite(ll_value, 1, n, ll_file)
            if n2 != n or c_ferror(ll_file):
                c_clearerr(ll_file)
                raise _from_errno(IOError)
        finally:
            rffi.free_nonmovingbuffer(value, ll_value)

    def truncate(self, arg=-1):
        self._check_closed()
        self._check_writable()
        ll_file = self._ll_file
        pos = c_ftell(ll_file)
        if pos == -1:
            c_clearerr(ll_file)
            raise _from_errno(IOError)
        if arg == -1:
            arg = pos
        res = c_fflush(ll_file)
        if res != 0:
            c_clearerr(ll_file)
            raise _from_errno(IOError)
        if MS_WINDOWS:
            ret = c_fseek(ll_file, arg, os.SEEK_SET)
            if ret:
                c_clearerr(ll_file)
                raise _from_errno(IOError)
            handle = _get_osfhandle(c_fileno(ll_file))
            ret = handle == INVALID_HANDLE_VALUE
            if ret == 0:
                ret = SetEndOfFile(handle) == 0
                if ret:
                    rposix.set_errno(errno.EACCES)
            if ret:
                c_clearerr(ll_file)
                raise _from_errno(IOError)
        else:
            ret = c_ftruncate(c_fileno(ll_file), arg)
            if ret != 0:
                c_clearerr(ll_file)
                raise _from_errno(IOError)
        res = c_fseek(ll_file, pos, os.SEEK_SET)
        if res != 0:
            c_clearerr(ll_file)
            raise _from_errno(IOError)

    def flush(self):
        self._check_closed()
        res = c_fflush(self._ll_file)
        if res != 0:
            c_clearerr(self._ll_file)
            raise _from_errno(IOError)

    def seek(self, pos, whence=0):
        self._check_closed()
        res = c_fseek(self._ll_file, pos, whence)
        if res != 0:
            c_clearerr(self._ll_file)
            raise _from_errno(IOError)
        self._skipnextlf = False

    def tell(self):
        self._check_closed()
        res = c_ftell(self._ll_file)
        if res == -1:
            c_clearerr(self._ll_file)
            raise _from_errno(IOError)
        if self._skipnextlf:
            c = c_getc(self._ll_file)
            if c == ord('\n'):
                self._newlinetypes |= NEWLINE_CRLF
                res += 1
                self._skipnextlf = False
            elif c != EOF:
                c_ungetc(c, self._ll_file)
        return res

    def fileno(self):
        self._check_closed()
        return c_fileno(self._ll_file)

    def isatty(self):
        self._check_closed()
        return os.isatty(c_fileno(self._ll_file))
