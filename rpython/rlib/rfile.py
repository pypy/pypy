""" This file makes open() and friends RPython. Note that RFile should not
be used directly and instead it's magically appearing each time you call
python builtin open()
"""

import os, stat, errno
from rpython.rlib import rposix
from rpython.rlib.rarithmetic import intmask
from rpython.rlib.rstring import StringBuilder
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rtyper.tool import rffi_platform as platform
from rpython.translator.tool.cbuild import ExternalCompilationInfo

includes = ['stdio.h', 'sys/types.h']
if os.name == "posix":
    includes += ['unistd.h']
    ftruncate = 'ftruncate'
    fileno = 'fileno'
else:
    ftruncate = '_chsize'
    fileno = '_fileno'
eci = ExternalCompilationInfo(includes=includes)


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

BASE_BUF_SIZE = 4096
BASE_LINE_SIZE = 100


def llexternal(*args, **kwargs):
    return rffi.llexternal(*args, compilation_info=eci, **kwargs)

c_fopen = llexternal('fopen', [rffi.CCHARP, rffi.CCHARP], FILEP)
c_fclose = llexternal('fclose', [FILEP], rffi.INT, releasegil=False)
c_fwrite = llexternal('fwrite', [rffi.CCHARP, rffi.SIZE_T, rffi.SIZE_T,
                                 FILEP], rffi.SIZE_T)
c_fread = llexternal('fread', [rffi.CCHARP, rffi.SIZE_T, rffi.SIZE_T,
                               FILEP], rffi.SIZE_T)
c_feof = llexternal('feof', [FILEP], rffi.INT)
c_ferror = llexternal('ferror', [FILEP], rffi.INT)
c_clearerr = llexternal('clearerr', [FILEP], lltype.Void)
c_fseek = llexternal('fseek', [FILEP, rffi.LONG, rffi.INT],
                     rffi.INT)
c_tmpfile = llexternal('tmpfile', [], FILEP)
c_fileno = llexternal(fileno, [FILEP], rffi.INT)
c_fdopen = llexternal(('_' if os.name == 'nt' else '') + 'fdopen',
                      [rffi.INT, rffi.CCHARP], FILEP)
c_ftell = llexternal('ftell', [FILEP], rffi.LONG)
c_fflush = llexternal('fflush', [FILEP], rffi.INT)
c_ftruncate = llexternal(ftruncate, [rffi.INT, OFF_T], rffi.INT, macro=True)

c_getc = llexternal('getc', [FILEP], rffi.INT, macro=True)
c_fgets = llexternal('fgets', [rffi.CCHARP, rffi.INT, FILEP],
                     rffi.CCHARP)

c_popen = llexternal('popen', [rffi.CCHARP, rffi.CCHARP], FILEP)
c_pclose = llexternal('pclose', [FILEP], rffi.INT, releasegil=False)
c_setvbuf = llexternal('setvbuf', [FILEP, rffi.CCHARP, rffi.INT, rffi.SIZE_T], rffi.INT)


def _error(ll_file):
    err = c_ferror(ll_file)
    c_clearerr(ll_file)
    raise OSError(err, os.strerror(err))


def _dircheck(ll_file):
    try:
        st = os.fstat(c_fileno(ll_file))
    except OSError:
        pass
    else:
        if stat.S_ISDIR(st[0]):
            err = errno.EISDIR
            raise OSError(err, os.strerror(err))


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
    mode = _sanitize_mode(mode)
    ll_name = rffi.str2charp(filename)
    try:
        ll_mode = rffi.str2charp(mode)
        try:
            ll_f = c_fopen(ll_name, ll_mode)
            if not ll_f:
                errno = rposix.get_errno()
                raise OSError(errno, os.strerror(errno))
        finally:
            lltype.free(ll_mode, flavor='raw')
    finally:
        lltype.free(ll_name, flavor='raw')
    _dircheck(ll_f)
    if buffering >= 0:
        if buffering == 0:
            c_setvbuf(ll_f, lltype.nullptr(rffi.CCHARP.TO), _IONBF, 0)
        elif buffering == 1:
            c_setvbuf(ll_f, lltype.nullptr(rffi.CCHARP.TO), _IOLBF, BUFSIZ)
        else:
            c_setvbuf(ll_f, lltype.nullptr(rffi.CCHARP.TO), _IOFBF, buffering)
    return RFile(ll_f)


def create_temp_rfile():
    res = c_tmpfile()
    if not res:
        errno = rposix.get_errno()
        raise OSError(errno, os.strerror(errno))
    return RFile(res)


def create_fdopen_rfile(fd, mode="r"):
    mode = _sanitize_mode(mode)
    ll_mode = rffi.str2charp(mode)
    try:
        ll_f = c_fdopen(rffi.cast(rffi.INT, fd), ll_mode)
        if not ll_f:
            errno = rposix.get_errno()
            raise OSError(errno, os.strerror(errno))
    finally:
        lltype.free(ll_mode, flavor='raw')
    _dircheck(ll_f)
    return RFile(ll_f)


def create_popen_file(command, type):
    ll_command = rffi.str2charp(command)
    try:
        ll_type = rffi.str2charp(type)
        try:
            ll_f = c_popen(ll_command, ll_type)
            if not ll_f:
                errno = rposix.get_errno()
                raise OSError(errno, os.strerror(errno))
        finally:
            lltype.free(ll_type, flavor='raw')
    finally:
        lltype.free(ll_command, flavor='raw')
    return RPopenFile(ll_f)


class RFile(object):
    def __init__(self, ll_file):
        self.ll_file = ll_file

    def _check_closed(self):
        if not self.ll_file:
            raise ValueError("I/O operation on closed file")

    def write(self, value):
        self._check_closed()
        assert value is not None
        ll_value = rffi.get_nonmovingbuffer(value)
        try:
            # note that since we got a nonmoving buffer, it is either raw
            # or already cannot move, so the arithmetics below are fine
            length = len(value)
            bytes = c_fwrite(ll_value, 1, length, self.ll_file)
            if bytes != length:
                errno = rposix.get_errno()
                raise OSError(errno, os.strerror(errno))
        finally:
            rffi.free_nonmovingbuffer(value, ll_value)

    def close(self):
        """Closes the described file.

        Attention! Unlike Python semantics, `close' does not return `None' upon
        success but `0', to be able to return an exit code for popen'ed files.

        The actual return value may be determined with os.WEXITSTATUS.
        """
        res = 0
        ll_file = self.ll_file
        if ll_file:
            # double close is allowed
            self.ll_file = lltype.nullptr(FILEP.TO)
            res = self._do_close(ll_file)
            if res == -1:
                errno = rposix.get_errno()
                raise OSError(errno, os.strerror(errno))
        return res

    _do_close = staticmethod(c_fclose)    # overridden in RPopenFile

    def read(self, size=-1):
        # XXX CPython uses a more delicate logic here
        self._check_closed()
        ll_file = self.ll_file
        if size == 0:
            return ""
        elif size < 0:
            # read the entire contents
            buf = lltype.malloc(rffi.CCHARP.TO, BASE_BUF_SIZE, flavor='raw')
            try:
                s = StringBuilder()
                while True:
                    returned_size = c_fread(buf, 1, BASE_BUF_SIZE, ll_file)
                    returned_size = intmask(returned_size)  # is between 0 and BASE_BUF_SIZE
                    if returned_size == 0:
                        if c_feof(ll_file):
                            # ok, finished
                            return s.build()
                        raise _error(ll_file)
                    s.append_charpsize(buf, returned_size)
            finally:
                lltype.free(buf, flavor='raw')
        else:  # size > 0
            with rffi.scoped_alloc_buffer(size) as buf:
                returned_size = c_fread(buf.raw, 1, size, ll_file)
                returned_size = intmask(returned_size)  # is between 0 and size
                if returned_size == 0:
                    if not c_feof(ll_file):
                        raise _error(ll_file)
                s = buf.str(returned_size)
            return s

    def seek(self, pos, whence=0):
        self._check_closed()
        res = c_fseek(self.ll_file, pos, whence)
        if res == -1:
            errno = rposix.get_errno()
            raise OSError(errno, os.strerror(errno))

    def fileno(self):
        self._check_closed()
        return intmask(c_fileno(self.ll_file))

    def tell(self):
        self._check_closed()
        res = intmask(c_ftell(self.ll_file))
        if res == -1:
            errno = rposix.get_errno()
            raise OSError(errno, os.strerror(errno))
        return res

    def flush(self):
        self._check_closed()
        res = c_fflush(self.ll_file)
        if res != 0:
            errno = rposix.get_errno()
            raise OSError(errno, os.strerror(errno))

    def truncate(self, arg=-1):
        self._check_closed()
        if arg == -1:
            arg = self.tell()
        self.flush()
        res = c_ftruncate(self.fileno(), arg)
        if res == -1:
            errno = rposix.get_errno()
            raise OSError(errno, os.strerror(errno))

    def __del__(self):
        self.close()

    def _readline1(self, raw_buf):
        ll_file = self.ll_file
        for i in range(BASE_LINE_SIZE):
            raw_buf[i] = '\n'

        result = c_fgets(raw_buf, BASE_LINE_SIZE, ll_file)
        if not result:
            if c_feof(ll_file):   # ok
                return 0
            raise _error(ll_file)

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

    def readline(self, size=-1):
        self._check_closed()
        if size == 0:
            return ""
        elif size < 0:
            with rffi.scoped_alloc_buffer(BASE_LINE_SIZE) as buf:
                c = self._readline1(buf.raw)
                if c >= 0:
                    return buf.str(c)

                # this is the rare case: the line is longer than BASE_LINE_SIZE
                s = StringBuilder()
                while True:
                    s.append_charpsize(buf.raw, BASE_LINE_SIZE - 1)
                    c = self._readline1(buf.raw)
                    if c >= 0:
                        break
                s.append_charpsize(buf.raw, c)
            return s.build()
        else:  # size > 0
            ll_file = self.ll_file
            s = StringBuilder()
            while s.getlength() < size:
                c = c_getc(ll_file)
                if c == EOF:
                    if c_ferror(ll_file):
                        raise _error(ll_file)
                    break
                c = chr(c)
                s.append(c)
                if c == '\n':
                    break
            return s.build()


class RPopenFile(RFile):
    _do_close = staticmethod(c_pclose)
