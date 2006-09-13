from pypy.rpython.rctypes.tool import ctypes_platform
from pypy.rpython.rctypes.tool.libc import libc
import pypy.rpython.rctypes.implementation # this defines rctypes magic
from pypy.rpython.rctypes.aerrno import geterrno
from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app
from ctypes import *
import sys
import os
import platform
import stat

_POSIX = os.name == "posix"
_MS_WINDOWS = os.name == "nt"
_LINUX = "linux" in sys.platform
_64BIT = "64bit" in platform.architecture()[0]


class CConfig:
    _includes_ = ("sys/types.h",)
    size_t = ctypes_platform.SimpleType("size_t", c_long)
    off_t = ctypes_platform.SimpleType("off_t", c_long)

constants = {}
if _POSIX:
    CConfig._includes_ += ("sys/mman.h",)
    # constants, look in sys/mman.h and platform docs for the meaning
    # some constants are linux only so they will be correctly exposed outside 
    # depending on the OS
    constant_names = ['MAP_SHARED', 'MAP_PRIVATE', 'MAP_ANON', 'MAP_ANONYMOUS',
                      'PROT_READ', 'PROT_WRITE', 'PROT_EXEC', 'MAP_DENYWRITE', 'MAP_EXECUTABLE',
                      'MS_SYNC']
    for name in constant_names:
        setattr(CConfig, name, ctypes_platform.DefinedConstantInteger(name))
elif _MS_WINDOWS:
    CConfig._includes_ += ("windows.h",)
    constant_names = ['PAGE_READONLY', 'PAGE_READWRITE', 'PAGE_WRITECOPY',
                      'FILE_MAP_READ', 'FILE_MAP_WRITE', 'FILE_MAP_COPY',
                      'DUPLICATE_SAME_ACCESS']
    for name in constant_names:
        setattr(CConfig, name, ctypes_platform.ConstantInteger(name))
    
class cConfig:
    pass

cConfig.__dict__.update(ctypes_platform.configure(CConfig))

# needed to export the constants inside and outside. see __init__.py
for name in constant_names:
    value = getattr(cConfig, name)
    if value is not None:
        constants[name] = value

if _POSIX:
    # MAP_ANONYMOUS is not always present but it's always available at CPython level
    if cConfig.MAP_ANONYMOUS is None:
        cConfig.MAP_ANONYMOUS = cConfig.MAP_ANON
        constants["MAP_ANONYMOUS"] = cConfig.MAP_ANON

locals().update(constants)
    

_ACCESS_DEFAULT, ACCESS_READ, ACCESS_WRITE, ACCESS_COPY = range(4)

PTR = POINTER(c_char)    # cannot use c_void_p as return value of functions :-(

size_t = cConfig.size_t
off_t = cConfig.off_t
libc.strerror.restype = c_char_p
libc.strerror.argtypes = [c_int]

if _POSIX:
    libc.mmap.argtypes = [PTR, size_t, c_int, c_int, c_int, off_t]
    libc.mmap.restype = PTR
    libc.mmap.includes = ("sys/mman.h",)
    libc.close.argtypes = [c_int]
    libc.close.restype = c_int
    libc.munmap.argtypes = [PTR, size_t]
    libc.munmap.restype = c_int
    libc.munmap.includes = ("sys/mman.h",)
    libc.msync.argtypes = [PTR, size_t, c_int]
    libc.msync.restype = c_int
    libc.msync.includes = ("sys/mman.h",)
    
    has_mremap = False
    if hasattr(libc, "mremap"):
        libc.mremap.argtypes = [PTR, size_t, size_t, c_ulong]
        libc.mremap.restype = PTR
        libc.mremap.includes = ("sys/mman.h",)
        has_mremap = True
    libc.ftruncate.argtypes = [c_int, off_t]
    libc.ftruncate.restype = c_int

    def _get_page_size():
        return libc.getpagesize()

    def _get_error_msg():
        errno = geterrno()
        return libc.strerror(errno)   
elif _MS_WINDOWS:
    from ctypes import wintypes
    
    WORD = wintypes.WORD
    DWORD = wintypes.DWORD
    BOOL = wintypes.BOOL
    LONG = wintypes.LONG
    LPVOID = PTR
    LPCVOID = LPVOID
    DWORD_PTR = DWORD
    c_int = wintypes.c_int
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
    GetFileSize.argtypes = [c_int, POINTER(c_int)]
    GetFileSize.restype = c_int
    GetCurrentProcess = windll.kernel32.GetCurrentProcess
    GetCurrentProcess.restype = c_int
    DuplicateHandle = windll.kernel32.DuplicateHandle
    DuplicateHandle.argtypes = [c_int, c_int, c_int, POINTER(c_int), DWORD,
                                BOOL, DWORD]
    DuplicateHandle.restype = BOOL
    CreateFileMapping = windll.kernel32.CreateFileMappingA
    CreateFileMapping.argtypes = [c_int, PTR, c_int, c_int, c_int,
                                  c_char_p]
    CreateFileMapping.restype = c_int
    MapViewOfFile = windll.kernel32.MapViewOfFile
    MapViewOfFile.argtypes = [c_int, DWORD,  DWORD, DWORD, DWORD]
    MapViewOfFile.restype = PTR
    CloseHandle = windll.kernel32.CloseHandle
    CloseHandle.argtypes = [c_int]
    CloseHandle.restype = BOOL
    UnmapViewOfFile = windll.kernel32.UnmapViewOfFile
    UnmapViewOfFile.argtypes = [LPCVOID]
    UnmapViewOfFile.restype = BOOL
    FlushViewOfFile = windll.kernel32.FlushViewOfFile
    FlushViewOfFile.argtypes = [LPCVOID, c_int]
    FlushViewOfFile.restype = BOOL
    SetFilePointer = windll.kernel32.SetFilePointer
    SetFilePointer.argtypes = [c_int, c_int, POINTER(c_int), c_int]
    SetEndOfFile = windll.kernel32.SetEndOfFile
    SetEndOfFile.argtypes = [c_int]
    msvcr71 = cdll.LoadLibrary("msvcr71.dll")
    msvcr71._get_osfhandle.argtypes = [c_int]
    msvcr71._get_osfhandle.restype = c_int
    # libc._lseek.argtypes = [c_int, c_int, c_int]
    # libc._lseek.restype = c_int
    
    
    def _get_page_size():
        si = SYSTEM_INFO()
        windll.kernel32.GetSystemInfo(byref(si))
        return int(si.dwPageSize)
    
    def _get_file_size(space, handle):
        # XXX use native Windows types like WORD
        high = c_int(0)
        low = c_int(windll.kernel32.GetFileSize(c_int(handle.value), byref(high)))
        # low might just happen to have the value INVALID_FILE_SIZE
        # so we need to check the last error also
        INVALID_FILE_SIZE = -1
        NO_ERROR = 0
        dwErr = GetLastError()
        if low.value == INVALID_FILE_SIZE and dwErr != NO_ERROR:
            raise OperationError(space.w_EnvironmentError,
                                 space.wrap(_get_error_msg(dwErr)))
        return low.value, high.value

    def _get_error_msg(errno=0):
        if not errno:
            errno = GetLastError()
        return libc.strerror(errno)

PAGESIZE = _get_page_size()
NULL = PTR()

# ____________________________________________________________

class W_MMap(Wrappable):
    def __init__(self, space, access):
        self.space = space
        self.size = 0
        self.pos = 0
        self.access = access

        if _MS_WINDOWS:
            self.map_handle = wintypes.c_int()
            self.file_handle = wintypes.c_int()
            self.tagname = ""
        elif _POSIX:
            self.fd = -1
            self.closed = False
    
##    def to_str(self):
##        return "".join([self.data[i] for i in range(self.size)])
    
    def check_valid(self):
        if _MS_WINDOWS:
            to_close = self.map_handle.value == INVALID_c_int_VALUE
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
        arraytype = c_char * size
        self.data = cast(data, POINTER(arraytype))
        self.size = size
    
    def close(self):
        if _MS_WINDOWS:
            if self.data:
                self.unmapview()
                self.setdata(NULL, 0)
            if self.map_handle.value != INVALID_c_int_VALUE:
                CloseHandle(self.map_handle)
                self.map_handle.value = INVALID_c_int_VALUE
            if self.file_handle.value != INVALID_c_int_VALUE:
                CloseHandle(self.file_handle)
                self.file_handle.value = INVALID_c_int_VALUE
        elif _POSIX:
            self.closed = True
            if self.fd != -1:
                libc.close(self.fd)
                self.fd = -1
            if self.data:
                libc.munmap(self.data, self.size)
                self.setdata(NULL, 0)
    close.unwrap_spec = ['self']
    
    def unmapview(self):
        data = cast(self.data, PTR)
        UnmapViewOfFile(data)
    
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

        for pos in xrange(self.pos, self.size):
            if self.data[pos] == '\n':
                eol = pos + 1 # we're interested in the position after new line
                break
        else: # no '\n' found
            eol = self.size

        res = self.data[self.pos:eol]
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

        res = self.data[self.pos:eol]
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
        for p in xrange(start, self.size):
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
    seek.unwrap_spec = ['self', int, int]
    
    def tell(self):
        self.check_valid()
        
        return self.space.wrap(self.pos)
    tell.unwrap_spec = ['self']
    
    def size(self):
        self.check_valid()
        
        size = self.size
        if _MS_WINDOWS:
            if self.file_handle.value != INVALID_c_int_VALUE:
                low, high = _get_file_size(self.space, self.file_handle)
                if not high and low <= sys.maxint:
                    return self.space.wrap(low)
                size = c_int((high << 32) + low).value
        elif _POSIX:
            st = os.fstat(self.fd)
            size = st[stat.ST_SIZE]
        return self.space.wrap(size)
    size.unwrap_spec = ['self']
    
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
        
        if len(byte) > 1:
            raise OperationError(self.space.w_TypeError,
                self.space.wrap("write_byte() argument must be char"))
        
        self.check_writeable()
        self.data[self.pos] = byte
        self.pos += 1
    write_byte.unwrap_spec = ['self', str]
    
    def flush(self, offset=0, size=0):
        self.check_valid()

        if size == 0:
            size = self.size
        if offset < 0 or size < 0 or offset + size > self.size:
            raise OperationError(self.space.w_ValueError,
                self.space.wrap("flush values out of range"))
        else:
            # XXX 64-bit support for pointer arithmetic!
            start = cast(self.data, c_void_p)
            if offset > 0:
                start = c_void_p(start.value + offset)
            start = cast(start, PTR)
            if _MS_WINDOWS:
                res = FlushViewOfFile(start, size)
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
                res = libc.msync(start, size, MS_SYNC)
                if res == -1:
                    raise OperationError(self.space.w_EnvironmentError,
                        self.space.wrap(_get_error_msg()))
        
        return self.space.wrap(0)
    flush.unwrap_spec = ['self', int, int]
    
    def move(self, dest, src, count):
        self.check_valid()
        
        self.check_writeable()
        
        # check boundings
        assert src >= 0; assert dest >= 0; assert count >= 0; assert self.size >= 0
        if (src + count > self.size) or (dest + count > self.size):
            raise OperationError(self.space.w_ValueError,
                self.space.wrap("source or destination out of range"))

        XXXXXXX
        data_dest = c_char_p("".join([self.data[i] for i in range(dest, self.size)]))
        data_src = c_char_p("".join([self.data[i] for i in range(src, src+count)]))
        libc.memmove XXX (data_dest, data_src, size_t(count))
        
        assert dest >= 0
        str_left = self.space.str_w(self.to_str())[0:dest]
        final_str = "%s%s" % (str_left, data_dest.value)
        
        p = c_char_p(final_str)
        libc.memcpy(self.data, p, len(final_str))
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
            res = libc.ftruncate(self.fd, newsize)
            if res == -1:
                raise OperationError(self.space.w_EnvironmentError,
                    self.space.wrap(_get_error_msg()))
                
            # now resize the mmap
            MREMAP_MAYMOVE = 1
            libc.mremap(self.data, self.size, newsize, MREMAP_MAYMOVE)
            self.size = newsize
        elif _MS_WINDOWS:
            # disconnect the mapping
            self.unmapview()
            CloseHandle(self.map_handle)

            # move to the desired EOF position
            if _64BIT:
                newsize_high = DWORD(newsize >> 32)
                newsize_low = DWORD(newsize & 0xFFFFFFFF)
            else:
                newsize_high = c_int(0)
                newsize_low = c_int(newsize)

            FILE_BEGIN = c_int(0)
            SetFilePointer(self.file_handle, newsize_low, byref(newsize_high),
                           FILE_BEGIN)
            # resize the file
            SetEndOfFile(self.file_handle)
            # create another mapping object and remap the file view
            res = CreateFileMapping(self.file_handle, NULL, PAGE_READWRITE,
                                 newsize_high, newsize_low, self.tagname)
            self.map_handle = c_int(res)

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
                                 self.space.wrap(_get_error_msg(dwErrCode)))
    resize.unwrap_spec = ['self', int]
    
    def __len__(self):
        self.check_valid()
        
        return self.space.wrap(self.size)
    __len__.unwrap_spec = ['self']
    
    def __getitem__(self, index):
        self.check_valid()

        # XXX this does not support slice() instances

        try:
            return self.space.wrap(self.space.str_w(self.to_str())[index])
        except IndexError:
            raise OperationError(self.space.w_IndexError,
                self.space.wrap("mmap index out of range"))
    __getitem__.unwrap_spec = ['self', int]
    
    def __setitem__(self, index, value):
        self.check_valid()
        self.check_writeable()
        
        # XXX this does not support slice() instances
        
        if len(value) != 1:
            raise OperationError(self.space.w_IndexError,
                self.space.wrap("mmap assignment must be single-character string"))

        str_data = ""
        try:
            str_data = self.space.str_w(self.to_str())
            str_data_lst = [i for i in str_data] 
            str_data_lst[index] = value
            str_data = "".join(str_data_lst)
        except IndexError:
            raise OperationError(self.space.w_IndexError,
                self.space.wrap("mmap index out of range"))

        XXXXXXXXXX
        p = c_char_p(str_data)
        libc.memcpy(self.data, p, len(str_data))
    __setitem__.unwrap_spec = ['self', int, str]
    
    def __delitem__(self, index):
        self.check_valid()
        
        # XXX this does not support slice() instances (does it matter?)
        
        raise OperationError(self.space.w_TypeError,
            self.space.wrap("mmap object doesn't support item deletion"))
    __delitem__.unwrap_spec = ['self', int]
    
    def __add__(self, w_other):
        self.check_valid()
        
        raise OperationError(self.space.w_SystemError,
            self.space.wrap("mmaps don't support concatenation"))
    __add__.unwrap_spec = ['self', W_Root]
    
    def __mul__(self, w_other):
        self.check_valid()
        
        raise OperationError(self.space.w_SystemError,
            self.space.wrap("mmaps don't support repeat operation"))
    __mul__.unwrap_spec = ['self', W_Root]


W_MMap.typedef = TypeDef("mmap",
    close = interp2app(W_MMap.close),
    read_byte = interp2app(W_MMap.read_byte),
    readline = interp2app(W_MMap.readline),
    read = interp2app(W_MMap.read),
    find = interp2app(W_MMap.find),
    seek = interp2app(W_MMap.seek),
    tell = interp2app(W_MMap.tell),
    size = interp2app(W_MMap.size),
    write = interp2app(W_MMap.write),
    write_byte = interp2app(W_MMap.write_byte),
    flush = interp2app(W_MMap.flush),
    move = interp2app(W_MMap.move),
    resize = interp2app(W_MMap.resize),

    __len__ = interp2app(W_MMap.__len__),
    __getitem__ = interp2app(W_MMap.__getitem__),
    __setitem__ = interp2app(W_MMap.__setitem__),
    __delitem__ = interp2app(W_MMap.__delitem__),
    __add__ = interp2app(W_MMap.__add__),
    __mul__ = interp2app(W_MMap.__mul__),   
)

def _check_map_size(space, size):
    if size < 0:
        raise OperationError(space.w_TypeError,
            space.wrap("memory mapped size must be positive"))
    if size_t(size).value != size:
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
            m.fd = os.dup(fd)

        res = libc.mmap(NULL, map_size, prot, flags, fd, 0)
        if cast(res, c_void_p).value == -1:
            raise OperationError(space.w_EnvironmentError,
                space.wrap(_get_error_msg()))
        
        m.setdata(res, map_size)

        return space.wrap(m)
    mmap.unwrap_spec = [ObjSpace, int, int, int, int, int]
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
        m.file_handle = c_int(INVALID_c_int_VALUE)
        m.map_handle = c_int(INVALID_c_int_VALUE)
        
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
                low, high = _get_file_size(space, c_int(fh))
                if _64BIT:
                    map_size = c_int((low << 32) + 1).value
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
            size_hi = c_int(0)
            size_lo = c_int(map_size)

        m.map_handle = c_int(CreateFileMapping(m.file_handle, NULL, flProtect,
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
                             space.wrap(_get_error_msg(dwErr)))
    mmap.unwrap_spec = [ObjSpace, int, int, str, int]
