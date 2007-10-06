from pypy.rpython.tool import rffi_platform
from pypy.rpython.lltypesystem import rffi, lltype, llmemory
from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app
import sys
import os
import platform
import stat

_POSIX = os.name == "posix"
_MS_WINDOWS = os.name == "nt"
_LINUX = "linux" in sys.platform
_64BIT = "64bit" in platform.architecture()[0]

class CConfig:
    _includes_ = ("sys/types.h",'unistd.h')
    _header_ = '#define _GNU_SOURCE\n'
    size_t = rffi_platform.SimpleType("size_t", rffi.LONG)
    off_t = rffi_platform.SimpleType("off_t", rffi.LONG)

constants = {}
if _POSIX:
    CConfig._includes_ += ("sys/mman.h",)
    # constants, look in sys/mman.h and platform docs for the meaning
    # some constants are linux only so they will be correctly exposed outside 
    # depending on the OS
    constant_names = ['MAP_SHARED', 'MAP_PRIVATE',
                      'PROT_READ', 'PROT_WRITE',
                      'MS_SYNC']
    opt_constant_names = ['MAP_ANON', 'MAP_ANONYMOUS',
                          'PROT_EXEC',
                          'MAP_DENYWRITE', 'MAP_EXECUTABLE']
    for name in constant_names:
        setattr(CConfig, name, rffi_platform.ConstantInteger(name))
    for name in opt_constant_names:
        setattr(CConfig, name, rffi_platform.DefinedConstantInteger(name))

    CConfig.MREMAP_MAYMOVE = (
        rffi_platform.DefinedConstantInteger("MREMAP_MAYMOVE"))
    CConfig.has_mremap = rffi_platform.Has('mremap()') # a dirty hack, this
    # is probably a macro

elif _MS_WINDOWS:
    CConfig._includes_ += ("windows.h",)
    constant_names = ['PAGE_READONLY', 'PAGE_READWRITE', 'PAGE_WRITECOPY',
                      'FILE_MAP_READ', 'FILE_MAP_WRITE', 'FILE_MAP_COPY',
                      'DUPLICATE_SAME_ACCESS']
    for name in constant_names:
        setattr(CConfig, name, rffi_platform.ConstantInteger(name))

# export the constants inside and outside. see __init__.py
cConfig = rffi_platform.configure(CConfig)
constants.update(cConfig)

if _POSIX:
    # MAP_ANONYMOUS is not always present but it's always available at CPython level
    if constants["MAP_ANONYMOUS"] is None:
        constants["MAP_ANONYMOUS"] = constants["MAP_ANON"]
    assert constants["MAP_ANONYMOUS"] is not None
    constants["MAP_ANON"] = constants["MAP_ANONYMOUS"]

locals().update(constants)

_ACCESS_DEFAULT, ACCESS_READ, ACCESS_WRITE, ACCESS_COPY = range(4)

def external(name, args, result):
    return rffi.llexternal(name, args, result, includes=CConfig._includes_)

PTR = rffi.VOIDP # XXX?

has_mremap = cConfig['has_mremap']

c_memmove = external('memmove', [PTR, PTR, size_t], lltype.Void)

if _POSIX:
    c_mmap = external('mmap', [PTR, size_t, rffi.INT, rffi.INT,
                               rffi.INT, off_t], PTR)
    c_munmap = external('munmap', [PTR, size_t], rffi.INT)
    c_msync = external('msync', [PTR, size_t, rffi.INT], rffi.INT)
    if has_mremap:
        c_mremap = external('mremap', [PTR, size_t, size_t, rffi.ULONG], PTR)

    _get_page_size = external('getpagesize', [], rffi.INT)

    def _get_error_msg():
        errno = rffi.get_errno()
        return os.strerror(errno)   
elif _MS_WINDOWS:
    XXX
    from ctypes import wintypes
    
    WORD = wintypes.WORD
    DWORD = wintypes.DWORD
    BOOL = wintypes.BOOL
    LONG = wintypes.LONG
    LPVOID = PTR
    LPCVOID = LPVOID
    DWORD_PTR = DWORD
    rffi.INT = wintypes.rffi.INT
    INVALID_c_int_VALUE = c_int(-1).value
    
    class SYSINFO_STRUCT(Structure):
        _fields_ = [("wProcessorArchitecture", WORD),
                    ("wReserved", WORD)]

    class SYSINFO_UNION(Union):
        _fields_ = [("dwOemId", DWORD),
                    ("struct", SYSINFO_STRUCT)]

    class SYSTEM_INFO(Structure):
        _fields_ = [("union", SYSINFO_UNION),
                    ("dwPageSize", DWORD),
                    ("lpMinimumApplicationAddress", LPVOID),
                    ("lpMaximumApplicationAddress", LPVOID),
                    ("dwActiveProcessorMask", DWORD_PTR),
                    ("dwNumberOfProcessors", DWORD),
                    ("dwProcessorType", DWORD),
                    ("dwAllocationGranularity", DWORD),
                    ("wProcessorLevel", WORD),
                    ("wProcessorRevision", WORD)]
    
    windll.kernel32.GetSystemInfo.argtypes = [POINTER(SYSTEM_INFO)]
    GetFileSize = windll.kernel32.GetFileSize
    GetFileSize.argtypes = [rffi.INT, POINTER(rffi.INT)]
    GetFileSize.restype = rffi.INT
    GetCurrentProcess = windll.kernel32.GetCurrentProcess
    GetCurrentProcess.restype = rffi.INT
    DuplicateHandle = windll.kernel32.DuplicateHandle
    DuplicateHandle.argtypes = [rffi.INT, rffi.INT, rffi.INT, POINTER(rffi.INT), DWORD,
                                BOOL, DWORD]
    DuplicateHandle.restype = BOOL
    CreateFileMapping = windll.kernel32.CreateFileMappingA
    CreateFileMapping.argtypes = [rffi.INT, PTR, rffi.INT, rffi.INT, rffi.INT,
                                  c_char_p]
    CreateFileMapping.restype = rffi.INT
    MapViewOfFile = windll.kernel32.MapViewOfFile
    MapViewOfFile.argtypes = [rffi.INT, DWORD,  DWORD, DWORD, DWORD]
    MapViewOfFile.restype = PTR
    CloseHandle = windll.kernel32.CloseHandle
    CloseHandle.argtypes = [rffi.INT]
    CloseHandle.restype = BOOL
    UnmapViewOfFile = windll.kernel32.UnmapViewOfFile
    UnmapViewOfFile.argtypes = [LPCVOID]
    UnmapViewOfFile.restype = BOOL
    FlushViewOfFile = windll.kernel32.FlushViewOfFile
    FlushViewOfFile.argtypes = [LPCVOID, rffi.INT]
    FlushViewOfFile.restype = BOOL
    SetFilePointer = windll.kernel32.SetFilePointer
    SetFilePointer.argtypes = [rffi.INT, rffi.INT, POINTER(rffi.INT), rffi.INT]
    SetEndOfFile = windll.kernel32.SetEndOfFile
    SetEndOfFile.argtypes = [rffi.INT]
    msvcr71 = cdll.LoadLibrary("msvcr71.dll")
    msvcr71._get_osfhandle.argtypes = [rffi.INT]
    msvcr71._get_osfhandle.restype = rffi.INT
    # libc._lseek.argtypes = [rffi.INT, rffi.INT, rffi.INT]
    # libc._lseek.restype = rffi.INT
    
    
    def _get_page_size():
        si = SYSTEM_INFO()
        windll.kernel32.GetSystemInfo(byref(si))
        return int(si.dwPageSize)
    
    def _get_file_size(space, handle):
        # XXX use native Windows types like WORD
        high = rffi.INT(0)
        low = rffi.INT(windll.kernel32.GetFileSize(rffi.INT(handle.value), byref(high)))
        # low might just happen to have the value INVALID_FILE_SIZE
        # so we need to check the last error also
        INVALID_FILE_SIZE = -1
        NO_ERROR = 0
        dwErr = GetLastError()
        if low.value == INVALID_FILE_SIZE and dwErr != NO_ERROR:
            raise OperationError(space.w_EnvironmentError,
                                 space.wrap(os.strerror(dwErr)))
        return low.value, high.value

    def _get_error_msg():
        errno = GetLastError()
        return os.strerror(errno)

PAGESIZE = _get_page_size()
NULL = lltype.nullptr(PTR.TO)
NODATA = lltype.nullptr(PTR.TO)
INVALID_INT_VALUE = -1

# ____________________________________________________________

# XXX the methods should take unsigned int arguments instead of int

class W_MMap(Wrappable):
    def __init__(self, space, access):
        self.space = space
        self.size = 0
        self.pos = 0
        self.access = access

        if _MS_WINDOWS:
            self.map_handle = 0
            self.file_handle = 0
            self.tagname = ""
        elif _POSIX:
            self.fd = -1
            self.closed = False
    
    def check_valid(self):
        if _MS_WINDOWS:
            to_close = self.map_handle.value == INVALID_INT_VALUE
        elif _POSIX:
            to_close = self.closed

        if to_close:
            raise OperationError(self.space.w_ValueError, 
                    self.space.wrap("map closed or invalid"))
    
    def check_writeable(self):
        if not (self.access != ACCESS_READ):
            raise OperationError(self.space.w_TypeError,
                self.space.wrap("mmap can't modify a readonly memory map."))
    
    def check_resizeable(self):
        if not (self.access == ACCESS_WRITE or self.access == _ACCESS_DEFAULT):
            raise OperationError(self.space.w_TypeError,
                self.space.wrap(
                    "mmap can't resize a readonly or copy-on-write memory map."))

    def setdata(self, data, size):
        """Set the internal data and map size from a PTR."""
        assert size >= 0
        self.data = data
        self.size = size
    
    def close(self):
        if _MS_WINDOWS:
            if self.size > 0:
                self.unmapview()
                self.setdata(NODATA, 0)
            if self.map_handle.value != INVALID_rffi.INT_VALUE:
                CloseHandle(self.map_handle)
                self.map_handle.value = INVALID_rffi.INT_VALUE
            if self.file_handle.value != INVALID_rffi.INT_VALUE:
                CloseHandle(self.file_handle)
                self.file_handle.value = INVALID_rffi.INT_VALUE
        elif _POSIX:
            self.closed = True
            if self.fd != -1:
                os.close(self.fd)
                self.fd = -1
            if self.size > 0:
                c_munmap(self.getptr(0), self.size)
                self.setdata(NODATA, 0)
    close.unwrap_spec = ['self']
    
    def unmapview(self):
        UnmapViewOfFile(self.getptr(0))
    
    def read_byte(self):
        self.check_valid()

        if self.pos < self.size:
            value = self.data[self.pos]
            self.pos += 1
            return self.space.wrap(value)
        else:
            raise OperationError(self.space.w_ValueError,
                self.space.wrap("read byte out of range"))
    read_byte.unwrap_spec = ['self']
    
    def readline(self):
        self.check_valid()

        data = self.data
        for pos in xrange(self.pos, self.size):
            if data[pos] == '\n':
                eol = pos + 1 # we're interested in the position after new line
                break
        else: # no '\n' found
            eol = self.size

        res = "".join([data[i] for i in range(self.pos, eol)])
        self.pos += len(res)
        return self.space.wrap(res)
    readline.unwrap_spec = ['self']
    
    def read(self, num=-1):
        self.check_valid()

        if num < 0:
            # read all
            eol = self.size
        else:
            eol = self.pos + num
            # silently adjust out of range requests
            if eol > self.size:
                eol = self.size

        res = [self.data[i] for i in range(self.pos, eol)]
        res = "".join(res)
        self.pos += len(res)
        return self.space.wrap(res)
    read.unwrap_spec = ['self', int]

    def find(self, tofind, start=0):
        self.check_valid()

        # XXX naive! how can we reuse the rstr algorithm?
        if start < 0:
            start += self.size
            if start < 0:
                start = 0
        data = self.data
        for p in xrange(start, self.size - len(tofind) + 1):
            for q in range(len(tofind)):
                if data[p+q] != tofind[q]:
                    break     # position 'p' is not a match
            else:
                # full match
                return self.space.wrap(p)
        # failure
        return self.space.wrap(-1)
    find.unwrap_spec = ['self', str, int]

    def seek(self, pos, whence=0):
        self.check_valid()
        
        dist = pos
        how = whence
        
        if how == 0: # relative to start
            where = dist
        elif how == 1: # relative to current position
            where = self.pos + dist
        elif how == 2: # relative to the end
            where = self.size + dist
        else:
            raise OperationError(self.space.w_ValueError,
                    self.space.wrap("unknown seek type"))

        if not (0 <= where <= self.size):
            raise OperationError(self.space.w_ValueError,
                self.space.wrap("seek out of range"))
        
        self.pos = where
    seek.unwrap_spec = ['self', 'index', int]
    
    def tell(self):
        self.check_valid()
        
        return self.space.wrap(self.pos)
    tell.unwrap_spec = ['self']
    
    def descr_size(self):
        self.check_valid()
        
        size = self.size
        if _MS_WINDOWS:
            if self.file_handle.value != INVALID_rffi.INT_VALUE:
                low, high = _get_file_size(self.space, self.file_handle)
                if not high and low <= sys.maxint:
                    return self.space.wrap(low)
                size = rffi.INT((high << 32) + low).value
        elif _POSIX:
            st = os.fstat(self.fd)
            size = st[stat.ST_SIZE]
            if size > sys.maxint:
                size = sys.maxint
            else:
                size = int(size)
        return self.space.wrap(size)
    descr_size.unwrap_spec = ['self']
    
    def write(self, data):
        self.check_valid()        
        self.check_writeable()
        
        data_len = len(data)
        if self.pos + data_len > self.size:
            raise OperationError(self.space.w_ValueError,
                self.space.wrap("data out of range"))

        internaldata = self.data
        start = self.pos
        for i in range(data_len):
            internaldata[start+i] = data[i]
        self.pos = start + data_len
    write.unwrap_spec = ['self', str]
    
    def write_byte(self, byte):
        self.check_valid()
        
        if len(byte) != 1:
            raise OperationError(self.space.w_TypeError,
                self.space.wrap("write_byte() argument must be char"))
        
        self.check_writeable()
        self.data[self.pos] = byte[0]
        self.pos += 1
    write_byte.unwrap_spec = ['self', str]

    def getptr(self, offset):
        if offset > 0:
            # XXX 64-bit support for pointer arithmetic!
            # is this still valid?
            dataptr = lltype.cast_int_to_ptr(PTR, lltype.cast_ptr_to_int(
                self.data) + offset)
            return dataptr
        else:
            return self.data

    def flush(self, offset=0, size=0):
        self.check_valid()

        if size == 0:
            size = self.size
        if offset < 0 or size < 0 or offset + size > self.size:
            raise OperationError(self.space.w_ValueError,
                self.space.wrap("flush values out of range"))
        else:
            start = self.getptr(offset)
            if _MS_WINDOWS:
                res = FlushViewOfFile(start, size)
                # XXX res == 0 means that an error occurred, but in CPython
                # this is not checked
                return self.space.wrap(res)
            elif _POSIX:
##                XXX why is this code here?  There is no equivalent in CPython
##                if _LINUX:
##                    # alignment of the address
##                    value = cast(self.data, c_void_p).value
##                    aligned_value = value & ~(PAGESIZE - 1)
##                    # the size should be increased too. otherwise the final
##                    # part is not "msynced"
##                    new_size = size + value & (PAGESIZE - 1)
                res = c_msync(start, size, MS_SYNC)
                if res == -1:
                    raise OperationError(self.space.w_EnvironmentError,
                        self.space.wrap(_get_error_msg()))
        
        return self.space.wrap(0)
    flush.unwrap_spec = ['self', int, int]
    
    def move(self, dest, src, count):
        self.check_valid()
        
        self.check_writeable()
        
        # check boundings
        if (src < 0 or dest < 0 or count < 0 or
            src + count > self.size or dest + count > self.size):
            raise OperationError(self.space.w_ValueError,
                self.space.wrap("source or destination out of range"))

        datasrc = self.getptr(src)
        datadest = self.getptr(dest)
        c_memmove(datadest, datasrc, count)
    move.unwrap_spec = ['self', int, int, int]
    
    def resize(self, newsize):
        self.check_valid()
        
        self.check_resizeable()
        
        if _POSIX:
            if not has_mremap:
                msg = "mmap: resizing not available -- no mremap()"
                raise OperationError(self.space.w_EnvironmentError,
                    self.space.wrap(msg))
            
            # resize the underlying file first
            try:
                os.ftruncate(self.fd, newsize)
            except OSError, e:
                raise OperationError(self.space.w_EnvironmentError,
                    self.space.wrap(os.strerror(e.errno)))
                
            # now resize the mmap
            newdata = c_mremap(self.getptr(0), self.size, newsize,
                               MREMAP_MAYMOVE or 0)
            self.setdata(newdata, newsize)
        elif _MS_WINDOWS:
            # disconnect the mapping
            self.unmapview()
            CloseHandle(self.map_handle)

            # move to the desired EOF position
            if _64BIT:
                newsize_high = DWORD(newsize >> 32)
                newsize_low = DWORD(newsize & 0xFFFFFFFF)
            else:
                newsize_high = rffi.INT(0)
                newsize_low = rffi.INT(newsize)

            FILE_BEGIN = rffi.INT(0)
            SetFilePointer(self.file_handle, newsize_low, byref(newsize_high),
                           FILE_BEGIN)
            # resize the file
            SetEndOfFile(self.file_handle)
            # create another mapping object and remap the file view
            res = CreateFileMapping(self.file_handle, NULL, PAGE_READWRITE,
                                 newsize_high, newsize_low, self.tagname)
            self.map_handle = rffi.INT(res)

            dwErrCode = DWORD(0)
            if self.map_handle:
                data = MapViewOfFile(self.map_handle, FILE_MAP_WRITE,
                    0, 0, 0)
                if data:
                    self.setdata(data, newsize)
                    return
                else:
                    dwErrCode = GetLastError()
            else:
                dwErrCode = GetLastError()

            raise OperationError(self.space.w_EnvironmentError,
                                 self.space.wrap(os.strerror(dwErrCode)))
    resize.unwrap_spec = ['self', int]
    
    def __len__(self):
        self.check_valid()
        
        return self.space.wrap(self.size)
    __len__.unwrap_spec = ['self']
    
    def descr_getitem(self, w_index):
        self.check_valid()

        space = self.space
        start, stop, step = space.decode_index(w_index, self.size)
        if step == 0:  # index only
            return space.wrap(self.data[start])
        elif step == 1:
            if 0 <= start <= stop:
                res = "".join([self.data[i] for i in range(start, stop)])
            else:
                res = ''
            return space.wrap(res)
        else:
            raise OperationError(space.w_ValueError,
                space.wrap("mmap object does not support slicing with a step"))
    descr_getitem.unwrap_spec = ['self', W_Root]

    def descr_setitem(self, w_index, value):
        self.check_valid()

        self.check_writeable()

        space = self.space
        start, stop, step = space.decode_index(w_index, self.size)
        if step == 0:  # index only
            if len(value) != 1:
                raise OperationError(space.w_ValueError,
                                     space.wrap("mmap assignment must be "
                                                "single-character string"))
            self.data[start] = value[0]
        elif step == 1:
            length = stop - start
            if start < 0 or length < 0:
                length = 0
            if len(value) != length:
                raise OperationError(space.w_ValueError,
                          space.wrap("mmap slice assignment is wrong size"))
            for i in range(length):
                self.data[start + i] = value[i]
        else:
            raise OperationError(space.w_ValueError,
                space.wrap("mmap object does not support slicing with a step"))
    descr_setitem.unwrap_spec = ['self', W_Root, str]


W_MMap.typedef = TypeDef("mmap",
    close = interp2app(W_MMap.close),
    read_byte = interp2app(W_MMap.read_byte),
    readline = interp2app(W_MMap.readline),
    read = interp2app(W_MMap.read),
    find = interp2app(W_MMap.find),
    seek = interp2app(W_MMap.seek),
    tell = interp2app(W_MMap.tell),
    size = interp2app(W_MMap.descr_size),
    write = interp2app(W_MMap.write),
    write_byte = interp2app(W_MMap.write_byte),
    flush = interp2app(W_MMap.flush),
    move = interp2app(W_MMap.move),
    resize = interp2app(W_MMap.resize),
    __module__ = "mmap",

    __len__ = interp2app(W_MMap.__len__),
    __getitem__ = interp2app(W_MMap.descr_getitem),
    __setitem__ = interp2app(W_MMap.descr_setitem),
)

def _check_map_size(space, size):
    if size < 0:
        raise OperationError(space.w_TypeError,
            space.wrap("memory mapped size must be positive"))
    if rffi.cast(size_t, size) != size:
        raise OperationError(space.w_OverflowError,
            space.wrap("memory mapped size is too large (limited by C int)"))

if _POSIX:
    def mmap(space, fileno, length, flags=MAP_SHARED,
        prot=PROT_WRITE | PROT_READ, access=_ACCESS_DEFAULT):

        fd = fileno

        # check size boundaries
        _check_map_size(space, length)
        map_size = length

        # check access is not there when flags and prot are there
        if access != _ACCESS_DEFAULT and ((flags != MAP_SHARED) or\
                                          (prot != (PROT_WRITE | PROT_READ))):
            raise OperationError(space.w_ValueError,
                space.wrap("mmap can't specify both access and flags, prot."))

        if access == ACCESS_READ:
            flags = MAP_SHARED
            prot = PROT_READ
        elif access == ACCESS_WRITE:
            flags = MAP_SHARED
            prot = PROT_READ | PROT_WRITE
        elif access == ACCESS_COPY:
            flags = MAP_PRIVATE
            prot = PROT_READ | PROT_WRITE
        elif access == _ACCESS_DEFAULT:
            pass
        else:
            raise OperationError(space.w_ValueError,
                space.wrap("mmap invalid access parameter."))

        # check file size
        try:
            st = os.fstat(fd)
        except OSError:
            pass     # ignore errors and trust map_size
        else:
            mode = st[stat.ST_MODE]
            size = st[stat.ST_SIZE]
            if size > sys.maxint:
                size = sys.maxint
            else:
                size = int(size)
            if stat.S_ISREG(mode):
                if map_size == 0:
                    map_size = size
                elif map_size > size:
                    raise OperationError(space.w_ValueError,
                        space.wrap("mmap length is greater than file size"))

        m = W_MMap(space, access)
        if fd == -1:
            # Assume the caller wants to map anonymous memory.
            # This is the same behaviour as Windows.  mmap.mmap(-1, size)
            # on both Windows and Unix map anonymous memory.
            m.fd = -1

            flags |= MAP_ANONYMOUS

        else:
            try:
                m.fd = os.dup(fd)
            except OSError, e:
                raise OperationError(space.w_EnvironmentError,
                                     space.wrap(os.strerror(e.errno)))

        res = c_mmap(NULL, map_size, prot, flags, fd, 0)
        if lltype.cast_ptr_to_int(res) == -1:
            raise OperationError(space.w_EnvironmentError,
                space.wrap(_get_error_msg()))
        
        m.setdata(res, map_size)

        return space.wrap(m)
    mmap.unwrap_spec = [ObjSpace, int, 'index', int, int, int]
elif _MS_WINDOWS:
    def mmap(space, fileno, length, tagname="", access=_ACCESS_DEFAULT):
        # check size boundaries
        _check_map_size(space, length)
        map_size = length
        
        flProtect = 0
        dwDesiredAccess = 0
        fh = 0
        
        if access == ACCESS_READ:
            flProtect = PAGE_READONLY
            dwDesiredAccess = FILE_MAP_READ
        elif access == _ACCESS_DEFAULT or access == ACCESS_WRITE:
            flProtect = PAGE_READWRITE
            dwDesiredAccess = FILE_MAP_WRITE
        elif access == ACCESS_COPY:
            flProtect = PAGE_WRITECOPY
            dwDesiredAccess = FILE_MAP_COPY
        else:
            raise OperationError(space.w_ValueError,
                                 space.wrap("mmap invalid access parameter."))
        
        # assume -1 and 0 both mean invalid file descriptor
        # to 'anonymously' map memory.
        if fileno != -1 and fileno != 0:
            fh = msvcr71._get_osfhandle(fileno)
            if fh == -1:
                raise OperationError(space.w_EnvironmentError,
                                     space.wrap(_get_error_msg()))
            # Win9x appears to need us seeked to zero
            # SEEK_SET = 0
            # libc._lseek(fileno, 0, SEEK_SET)
        
        m = W_MMap(space, access)
        # XXX the following two attributes should be plain RPython ints
        m.file_handle = rffi.INT(INVALID_rffi.INT_VALUE)
        m.map_handle = rffi.INT(INVALID_rffi.INT_VALUE)
        
        if fh:
            # it is necessary to duplicate the handle, so the
            # Python code can close it on us        
            res = DuplicateHandle(GetCurrentProcess(), # source process handle
                                  fh, # handle to be duplicated
                                  GetCurrentProcess(), # target process handle
                                  byref(m.file_handle), # result
                                  0, # access - ignored due to options value
                                  False, # inherited by child procs?
                                  DUPLICATE_SAME_ACCESS) # options
            if not res:
                raise OperationError(space.w_EnvironmentError,
                                     space.wrap(_get_error_msg()))
        
            if not map_size:
                low, high = _get_file_size(space, rffi.INT(fh))
                if _64BIT:
                    map_size = rffi.INT((low << 32) + 1).value
                else:
                    if high:
                        # file is too large to map completely
                        map_size = -1
                    else:
                        map_size = low

        if tagname:
            m.tagname = tagname
        
        # DWORD is a 4-byte int. If int > 4-byte it must be divided
        if _64BIT:
            size_hi = DWORD(map_size >> 32)
            size_lo = DWORD(map_size & 0xFFFFFFFF)
        else:
            size_hi = rffi.INT(0)
            size_lo = rffi.INT(map_size)

        m.map_handle = rffi.INT(CreateFileMapping(m.file_handle, NULL, flProtect,
                                               size_hi, size_lo, m.tagname))

        if m.map_handle:
            res = MapViewOfFile(m.map_handle, dwDesiredAccess,
                                0, 0, 0)
            if res:
                m.setdata(res, map_size)
                return space.wrap(m)
            else:
                dwErr = GetLastError()
        else:
            dwErr = GetLastError()

        raise OperationError(space.w_EnvironmentError,
                             space.wrap(os.strerror(dwErr)))
    mmap.unwrap_spec = [ObjSpace, int, 'index', str, int]
