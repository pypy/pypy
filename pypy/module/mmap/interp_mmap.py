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
    _header_ = "#include <sys/types.h>"
    size_t = ctypes_platform.SimpleType("size_t", c_long)
    off_t = ctypes_platform.SimpleType("off_t", c_long)

constants = {}
if _POSIX:
    CConfig._header_ = """
    %s
    #include <sys/mman.h>""" % CConfig._header_
    # constants, look in sys/mman.h and platform docs for the meaning
    # some constants are linux only so they will be correctly exposed outside 
    # depending on the OS
    constant_names = ['MAP_SHARED', 'MAP_PRIVATE', 'MAP_ANON', 'MAP_ANONYMOUS',
                      'PROT_READ', 'PROT_WRITE', 'PROT_EXEC', 'MAP_DENYWRITE', 'MAP_EXECUTABLE',
                      'MS_SYNC']
    for name in constant_names:
        setattr(CConfig, name, ctypes_platform.DefinedConstantInteger(name))
elif _MS_WINDOWS:
    CConfig._header_ = """
    %s
    #include <windows.h>""" % CConfig._header_
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

size_t = cConfig.size_t
off_t = cConfig.off_t
libc.strerror.restype = c_char_p
libc.strerror.argtypes = [c_int]
libc.memcpy.argtypes = [POINTER(c_char), c_char_p, c_int]
libc.memcpy.restype = c_void_p

if _POSIX:
    libc.mmap.argtypes = [c_void_p, size_t, c_int, c_int, c_int, off_t]
    libc.mmap.restype = c_void_p
    libc.close.argtypes = [c_int]
    libc.close.restype = c_int
    libc.munmap.argtypes = [c_void_p, size_t]
    libc.munmap.restype = c_int
    libc.msync.argtypes = [c_char_p, size_t, c_int]
    libc.msync.restype = c_int

    ## LINUX msync syscall helper stuff
    # you don't have addressof() in rctypes so I looked up the implementation
    # of addressof in ctypes source and come up with this.
    pythonapi.PyLong_FromVoidPtr.argtypes = [c_char_p]
    pythonapi.PyLong_FromVoidPtr.restype = c_int
    # we also need to alias msync to take a c_void_p instead of c_char_p
    linux_msync = libc["msync"]
    linux_msync.argtypes = [c_void_p, size_t, c_int]
    linux_msync.restype = c_int
    
    libc.memmove.argtypes = [c_char_p, c_char_p, size_t]
    libc.memmove.restype = c_void_p
    has_mremap = False
    if hasattr(libc, "mremap"):
        libc.mremap.argtypes = [POINTER(c_char), size_t, size_t, c_ulong]
        libc.mremap.restype = c_void_p
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
    LPVOID = c_void_p
    LPCVOID = LPVOID
    DWORD_PTR = DWORD
    HANDLE = wintypes.HANDLE
    INVALID_HANDLE_VALUE = HANDLE(-1).value
    
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
    windll.kernel32.GetFileSize.restype = DWORD
    GetCurrentProcess = windll.kernel32.GetCurrentProcess
    GetCurrentProcess.restype = HANDLE
    DuplicateHandle = windll.kernel32.DuplicateHandle
    DuplicateHandle.argtypes = [HANDLE, HANDLE, HANDLE, POINTER(HANDLE), DWORD,
                                BOOL, DWORD]
    DuplicateHandle.restype = BOOL
    CreateFileMapping = windll.kernel32.CreateFileMappingA
    CreateFileMapping.argtypes = [HANDLE, c_void_p, DWORD, DWORD, DWORD,
                                  c_char_p]
    CreateFileMapping.restype = HANDLE
    MapViewOfFile = windll.kernel32.MapViewOfFile
    MapViewOfFile.argtypes = [HANDLE, DWORD,  DWORD, DWORD, DWORD]
    MapViewOfFile.restype = c_void_p
    CloseHandle = windll.kernel32.CloseHandle
    CloseHandle.argtypes = [HANDLE]
    CloseHandle.restype = BOOL
    UnmapViewOfFile = windll.kernel32.UnmapViewOfFile
    UnmapViewOfFile.argtypes = [LPCVOID]
    UnmapViewOfFile.restype = BOOL
    FlushViewOfFile = windll.kernel32.FlushViewOfFile
    FlushViewOfFile.argtypes = [c_void_p, c_int]
    SetFilePointer = windll.kernel32.SetFilePointer
    SetFilePointer.argtypes = [HANDLE, LONG, POINTER(LONG), DWORD]
    SetEndOfFile = windll.kernel32.SetEndOfFile
    SetEndOfFile.argtypes = [HANDLE]
    
    def _get_page_size():
        si = SYSTEM_INFO()
        windll.kernel32.GetSystemInfo(byref(si))
        return int(si.dwPageSize)
    
    def _get_file_size(space, handle):
        low = DWORD()
        high = DWORD()
        low = DWORD(windll.kernel32.GetFileSize(handle, byref(high)))
        # low might just happen to have the value INVALID_FILE_SIZE
        # so we need to check the last error also
        INVALID_FILE_SIZE = DWORD(0xFFFFFFFF).value
        NO_ERROR = 0
        dwErr = GetLastError()
        if low.value == INVALID_FILE_SIZE and dwErr != NO_ERROR:
            raise OperationError(space.wrap(WinError), space.wrap(dwErr))
        return low, high

    def _get_error_msg():
        errno = GetLastError()
        return libc.strerror(errno)

PAGESIZE = _get_page_size()

class _mmap(Wrappable):
    def __init__(self, space):
        self.space = space
        self._size = 0
        self._pos = 0
        self._access = _ACCESS_DEFAULT

        if _MS_WINDOWS:
            self._map_handle = wintypes.HANDLE()
            self._file_handle = wintypes.HANDLE()
            self._tagname = ""
        elif _POSIX:
            self._fd = 0
            self._closed = False
    
    def _to_str(self):
        data = "".join([self._data[i] for i in range(self._size)])
        return self.space.wrap(data)
    _to_str.unwrap_spec = ['self']
    
    def _check_valid(self):
        if _MS_WINDOWS:
            to_close = self._map_handle.value == INVALID_HANDLE_VALUE
        elif _POSIX:
            to_close = self._closed

        if to_close:
            raise OperationError(self.space.w_ValueError, 
                    self.space.wrap("map closed or invalid"))
    _check_valid.unwrap_spec = ['self']
    
    def _check_writeable(self):
        if not (self._access != ACCESS_READ):
            raise OperationError(self.space.w_TypeError,
                self.space.wrap("mmap can't modify a readonly memory map."))
    _check_writeable.unwrap_spec = ['self']
    
    def _check_resizeable(self):
        if not (self._access == ACCESS_WRITE or self._access == _ACCESS_DEFAULT):
            raise OperationError(self.space.w_TypeError,
                self.space.wrap(
                    "mmap can't resize a readonly or copy-on-write memory map."))
    _check_resizeable.unwrap_spec = ['self']
    
    def close(self):
        if _MS_WINDOWS:
            if self._data:
                self._unmapview()
                self._data = None
            if self._map_handle.value != INVALID_HANDLE_VALUE:
                CloseHandle(self._map_handle)
                self._map_handle.value = INVALID_HANDLE_VALUE
            if self._file_handle.value != INVALID_HANDLE_VALUE:
                CloseHandle(self._file_handle)
                self._file_handle.value = INVALID_HANDLE_VALUE
        elif _POSIX:
            self._closed = True
            libc.close(self._fd)
            self._fd = -1
            if self._data:
                libc.munmap(self._data, self._size)
    close.unwrap_spec = ['self']
    
    def _unmapview(self):
        self._data = cast(self._data, c_void_p)
        UnmapViewOfFile(self._data)
    
    def read_byte(self):
        self._check_valid()

        if self._pos < self._size:
            value = self._data[self._pos]
            self._pos += 1
            return self.space.wrap(value)
        else:
            raise OperationError(self.space.w_ValueError,
                self.space.wrap("read byte out of range"))
    read_byte.unwrap_spec = ['self']
    
    def readline(self):
        self._check_valid()

        found = False
        for pos in range(self._pos, self._size):
            if self._data[pos] == '\n':
                found = True
                break

        if not found:
            eol = self._size
        else:
            eol = pos + 1 # we're interested in the position after new line

        # res = self._data[self._pos:eol-self._pos] XXX: can't use this slicing
        # in translation step
        res = "".join([self._data[i] for i in range(self._pos, eol-self._pos)])
        self._pos += eol - self._pos
        return self.space.wrap(res)
    readline.unwrap_spec = ['self']
    
    def read(self, num):
        self._check_valid()
        
        num_bytes = num
        
        # silently adjust out of range requests
        if self._pos + num_bytes > self._size:
            num_bytes -= (self._pos + num_bytes) - self._size
        
        # due to slicing of python, the last char is not always returned
        if num_bytes < self._size - 1:
            res = "".join([self._data[i] for i in range(self._pos, num_bytes)])
        else:
            res = "".join([self._data[i] for i in range(self._pos, self._size)])
        self._pos += num_bytes
        return self.space.wrap(res)
    read.unwrap_spec = ['self', int]

    def find(self, tofind, start=0):
        self._check_valid()
        
        # since we don't have to update positions we
        # gain advantage of python strings :-)
        w_str_data = self._to_str()
        str_data = self.space.str_w(w_str_data)
        assert start >= 0
        return self.space.wrap(str_data.find(tofind, start))
    find.unwrap_spec = ['self', str, int]

    def seek(self, pos, whence=0):
        self._check_valid()
        
        dist = pos
        how = whence
        
        if how == 0: # relative to start
            if dist < 0:
                raise OperationError(self.space.w_ValueError,
                    self.space.wrap("seek out of range"))
            where = dist
        elif how == 1: # relative to current position
            if self._pos + dist < 0:
                raise OperationError(self.space.w_ValueError,
                    self.space.wrap("seek out of range"))
            where = self._pos + dist
        elif how == 2: # relative to the end
            if self._size + dist < 0:
                raise OperationError(self.space.w_ValueError,
                    self.space.wrap("seek out of range"))
            where = self._size + dist
        else:
            raise OperationError(self.space.w_ValueError,
                    self.space.wrap("unknown seek type"))
        
        if where > self._size:
            raise OperationError(self.space.w_ValueError,
                    self.space.wrap("seek out of range"))
        
        self._pos = where
    seek.unwrap_spec = ['self', int, int]
    
    def tell(self):
        self._check_valid()
        
        return self.space.wrap(self._pos)
    tell.unwrap_spec = ['self']
    
    def size(self):
        self._check_valid()
        
        if _MS_WINDOWS:
            if self._file_handle.value != INVALID_HANDLE_VALUE:
                low, high = _get_file_size(self.space, self._file_handle)
                if not high and low.value < sys.maxint:
                    return self.space.wrap(int(low.value))
                size = (long(high.value) << 32) + low.value
                return self.space.wrap(long(size))
            else:
                return self.space.wrap(self._size)
        elif _POSIX:
            st = os.fstat(self._fd)
            SIZE_BIT = 6
            return self.space.wrap(st[SIZE_BIT])
    size.unwrap_spec = ['self']
    
    def write(self, data):
        self._check_valid()        
        self._check_writeable()
        
        data_len = len(data)
        if self._pos + data_len > self._size:
            raise OperationError(self.space.w_ValueError,
                self.space.wrap("data out of range"))
        
        p = c_char_p(data)
        libc.memcpy(self._data, p, data_len)
        self._pos += data_len
    write.unwrap_spec = ['self', str]
    
    def write_byte(self, byte):
        self._check_valid()
        
        if len(byte) > 1:
            raise OperationError(self.space.w_TypeError,
                self.space.wrap("write_byte() argument must be char"))
        
        self._check_writeable()
        
        str_data = self.space.str_w(self._to_str())
        str_data_lst = [i for i in str_data] 
        str_data_lst[self._pos] = byte
        str_data = "".join(str_data_lst)
        
        p = c_char_p(str_data)
        libc.memcpy(self._data, p, len(str_data))
        self._pos += 1
    write_byte.unwrap_spec = ['self', str]
    
    def flush(self, offset=0, size=0):
        self._check_valid()
        
        if size == 0:
            size = self._size
        
        if offset + size > self._size:
            raise OperationError(self.space.w_ValueError,
                self.space.wrap("flush values out of range"))
        else:
            data = c_char_p("".join([self._data[i] for i in range(offset, size)]))
            
            if _MS_WINDOWS:
                return self.space.wrap(FlushViewOfFile(data, size))
            elif _POSIX:
                if _LINUX:
                    # alignment of the address
                    value = pythonapi.PyLong_FromVoidPtr(data)
                    aligned_value = value & ~(PAGESIZE - 1)
                    # the size should be increased too. otherwise the final
                    # part is not "msynced"
                    new_size = size + value & (PAGESIZE - 1)
                    res = linux_msync(c_void_p(aligned_value), new_size, MS_SYNC)
                else:
                    res = libc.msync(data, size, MS_SYNC)
                if res == -1:
                    raise OperationError(self.space.w_EnvironmentError,
                        self.space.wrap(_get_error_msg()))
        
        return self.space.wrap(0)
    flush.unwrap_spec = ['self', int, int]
    
    def move(self, dest, src, count):
        self._check_valid()
        
        self._check_writeable()
        
        # check boundings
        if (src + count > self._size) or (dest + count > self._size):
            raise OperationError(self.space.w_ValueError,
                self.space.wrap("source or destination out of range"))
        
        data_dest = c_char_p("".join([self._data[i] for i in range(dest, self._size)]))
        data_src = c_char_p("".join([self._data[i] for i in range(src, src+count)]))
        libc.memmove(data_dest, data_src, count)
        
        assert dest >= 0
        str_left = self.space.str_w(self._to_str())[0:dest]
        final_str = "%s%s" % (str_left, data_dest.value)
        
        p = c_char_p(final_str)
        libc.memcpy(self._data, p, len(final_str))
    move.unwrap_spec = ['self', int, int, int]
    
    def resize(self, newsize):
        self._check_valid()
        
        self._check_resizeable()
        
        if _POSIX:
            if not has_mremap:
                msg = "mmap: resizing not available -- no mremap()"
                raise OperationError(self.space.w_EnvironmentError,
                    self.space.wrap(msg))
            
            # resize the underlying file first
            res = libc.ftruncate(self._fd, newsize)
            if res == -1:
                raise OperationError(self.space.w_EnvironmentError,
                    self.space.wrap(_get_error_msg()))
                
            # now resize the mmap
            MREMAP_MAYMOVE = 1
            libc.mremap(self._data, self._size, newsize, MREMAP_MAYMOVE)
            self._size = newsize
        elif _MS_WINDOWS:
            # disconnect the mapping
            self._unmapview()
            CloseHandle(self._map_handle)

            # move to the desired EOF position
            if _64BIT:
                newsize_high = DWORD(newsize >> 32)
                newsize_low = DWORD(newsize & 0xFFFFFFFF)
            else:
                newsize_high = DWORD(0)
                newsize_low = DWORD(newsize)

            FILE_BEGIN = DWORD(0)
            SetFilePointer(self._file_handle, LONG(newsize_low.value),    
                        LONG(newsize_high.value), FILE_BEGIN)
            # resize the file
            SetEndOfFile(self._file_handle)
            # create another mapping object and remap the file view
            res = CreateFileMapping(self._file_handle, None, PAGE_READWRITE,
                                 newsize_high, newsize_low, self._tagname)
            self._map_handle = HANDLE(res)

            dwErrCode = DWORD(0)
            if self._map_handle:
                self._data = MapViewOfFile(self._map_handle, FILE_MAP_WRITE,
                    0, 0, 0)
                if self._data:
                    self._data = cast(self._data, POINTER(c_char))
                    self._size = newsize
                    return
                else:
                    dwErrCode = GetLastError()
            else:
                dwErrCode = GetLastError()

            raise OperationError(self.space.wrap(WinError),
                              self.space.wrap(dwErrCode))
    resize.unwrap_spec = ['self', int]
    
    def __len__(self):
        self._check_valid()
        
        return self.space.wrap(self._size)
    __len__.unwrap_spec = ['self']
    
    def __getitem__(self, index):
        self._check_valid()

        # XXX this does not support slice() instances

        try:
            return self.space.wrap(self.space.str_w(self._to_str())[index])
        except IndexError:
            raise OperationError(self.space.w_IndexError,
                self.space.wrap("mmap index out of range"))
    __getitem__.unwrap_spec = ['self', int]
    
    def __setitem__(self, index, value):
        self._check_valid()
        self._check_writeable()
        
        # XXX this does not support slice() instances
        
        if len(value) != 1:
            raise OperationError(self.space.w_IndexError,
                self.space.wrap("mmap assignment must be single-character string"))

        str_data = ""
        try:
            str_data = self.space.str_w(self._to_str())
            str_data_lst = [i for i in str_data] 
            str_data_lst[index] = value
            str_data = "".join(str_data_lst)
        except IndexError:
            raise OperationError(self.space.w_IndexError,
                self.space.wrap("mmap index out of range"))
        
        p = c_char_p(str_data)
        libc.memcpy(self._data, p, len(str_data))
    __setitem__.unwrap_spec = ['self', int, str]
    
    def __delitem__(self, index):
        self._check_valid()
        
        # XXX this does not support slice() instances (does it matter?)
        
        raise OperationError(self.space.w_TypeError,
            self.space.wrap("mmap object doesn't support item deletion"))
    __delitem__.unwrap_spec = ['self', int]
    
    def __add__(self, w_other):
        self._check_valid()
        
        raise OperationError(self.space.w_SystemError,
            self.space.wrap("mmaps don't support concatenation"))
    __add__.unwrap_spec = ['self', W_Root]
    
    def __mul__(self, w_other):
        self._check_valid()
        
        raise OperationError(self.space.w_SystemError,
            self.space.wrap("mmaps don't support repeat operation"))
    __mul__.unwrap_spec = ['self', W_Root]


_mmap.typedef = TypeDef("_mmap",
    _to_str = interp2app(_mmap._to_str, unwrap_spec=_mmap._to_str.unwrap_spec),
    _check_valid = interp2app(_mmap._check_valid,
        unwrap_spec=_mmap._check_valid.unwrap_spec),
    _check_writeable = interp2app(_mmap._check_writeable,
        unwrap_spec=_mmap._check_writeable.unwrap_spec),
    _check_resizeable = interp2app(_mmap._check_resizeable,
        unwrap_spec=_mmap._check_resizeable.unwrap_spec),
    close = interp2app(_mmap.close, unwrap_spec=_mmap.close.unwrap_spec),
    read_byte = interp2app(_mmap.read_byte,
        unwrap_spec=_mmap.read_byte.unwrap_spec),
    readline = interp2app(_mmap.readline,
        unwrap_spec=_mmap.readline.unwrap_spec),
    read = interp2app(_mmap.read, unwrap_spec=_mmap.read.unwrap_spec),
    find = interp2app(_mmap.find, unwrap_spec=_mmap.find.unwrap_spec),
    seek = interp2app(_mmap.seek, unwrap_spec=_mmap.seek.unwrap_spec),
    tell = interp2app(_mmap.tell, unwrap_spec=_mmap.tell.unwrap_spec),
    size = interp2app(_mmap.size, unwrap_spec=_mmap.size.unwrap_spec),
    write = interp2app(_mmap.write, unwrap_spec=_mmap.write.unwrap_spec),
    write_byte = interp2app(_mmap.write_byte,
        unwrap_spec=_mmap.write_byte.unwrap_spec),
    flush = interp2app(_mmap.flush, unwrap_spec=_mmap.flush.unwrap_spec),
    move = interp2app(_mmap.move, unwrap_spec=_mmap.move.unwrap_spec),
    resize = interp2app(_mmap.resize, unwrap_spec=_mmap.resize.unwrap_spec),

    __len__ = interp2app(_mmap.__len__, unwrap_spec=_mmap.__len__.unwrap_spec),
    __getitem__ = interp2app(_mmap.__getitem__,
        unwrap_spec=_mmap.__getitem__.unwrap_spec),
    __setitem__ = interp2app(_mmap.__setitem__,
        unwrap_spec=_mmap.__setitem__.unwrap_spec),
    __delitem__ = interp2app(_mmap.__delitem__,
        unwrap_spec=_mmap.__delitem__.unwrap_spec),
    __add__ = interp2app(_mmap.__add__, unwrap_spec=_mmap.__add__.unwrap_spec),
    __mul__ = interp2app(_mmap.__mul__, unwrap_spec=_mmap.__mul__.unwrap_spec),   
)

def _check_map_size(space, size):
    if size < 0:
        raise OperationError(space.w_TypeError,
            space.wrap("memory mapped size must be positive"))
    if size == sys.maxint:
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
            raise OperationError(space.w_EnvironmentError,
                space.wrap("bad file descriptor"))
        MODE_BIT, SIZE_BIT = 0, 6 # cannot use st.st_mode and st.st_size
        mode = st[MODE_BIT]
        size = st[SIZE_BIT]
        if stat.S_ISREG(mode):
            if map_size == 0:
                map_size = size
            elif map_size > size:
                raise OperationError(space.w_ValueError,
                    space.wrap("mmap length is greater than file size"))

        m = _mmap(space)
        m._size = map_size
        if fd == -1:
            # Assume the caller wants to map anonymous memory.
            # This is the same behaviour as Windows.  mmap.mmap(-1, size)
            # on both Windows and Unix map anonymous memory.
            m._fd = -1

            flags |= MAP_ANONYMOUS

        else:
            m._fd = os.dup(fd)
            if m._fd == -1:
                raise OperationError(space.w_EnvironmentError,
                    space.wrap(_get_error_msg()))

        res = libc.mmap(c_void_p(0), map_size, prot, flags, fd, 0)
        if not res:
            raise OperationError(space.w_EnvironmentError,
                space.wrap(_get_error_msg()))
        m._data = cast(res, POINTER(c_char))
        m._access = access

        return space.wrap(m)
    mmap.unwrap_spec = [ObjSpace, int, int, int, int, int]
elif _MS_WINDOWS:
    def mmap(space, fileno, length, tagname="", access=_ACCESS_DEFAULT):
        # check size boundaries
        _check_map_size(space, length)
        map_size = length
        
        flProtect = WORD()
        dwDesiredAccess = WORD()
        fh = HANDLE(0)
        
        if access == ACCESS_READ:
            flProtect = DWORD(PAGE_READONLY)
            dwDesiredAccess = DWORD(FILE_MAP_READ)
        elif access == _ACCESS_DEFAULT or access == ACCESS_WRITE:
            flProtect = DWORD(PAGE_READWRITE)
            dwDesiredAccess = DWORD(FILE_MAP_WRITE)
        elif access == ACCESS_COPY:
            flProtect = DWORD(PAGE_WRITECOPY)
            dwDesiredAccess = DWORD(FILE_MAP_COPY)
        else:
            raise OperationError(space.w_ValueError,
                                 space.wrap("mmap invalid access parameter."))
        
        # assume -1 and 0 both mean invalid file descriptor
        # to 'anonymously' map memory.
        if fileno != -1 and fileno != 0:
            fh = cdll.msvcr71._get_osfhandle(fileno)
            if fh == -1:
                raise OperationError(space.w_EnvironmentError,
                                     space.wrap(_get_error_msg()))
            # Win9x appears to need us seeked to zero
            SEEK_SET = 0
            libc._lseek(fileno, 0, SEEK_SET)
        
        m = _mmap(space)
        m._file_handle = HANDLE(INVALID_HANDLE_VALUE)
        m._map_handle = HANDLE(INVALID_HANDLE_VALUE)
        
        if fh:
            res = BOOL()
            # it is necessary to duplicate the handle, so the
            # Python code can close it on us        
            res = DuplicateHandle(GetCurrentProcess(), # source process handle
                                  fh, # handle to be duplicated
                                  GetCurrentProcess(), # target process handle
                                  byref(m._file_handle), # result
                                  0, # access - ignored due to options value
                                  wintypes.BOOL(False), # inherited by child procs?
                                  DUPLICATE_SAME_ACCESS) # options
            if not res:
                raise OperationError(space.wrap(WinError), space.wrap(""))
        
            if not map_size:
                low, high = _get_file_size(space, fh)
                if _64BIT:
                    m._size = (c_long(low.value).value << 32) + 1
                else:
                    if high:
                        # file is too large to map completely
                        m._size = -1L
                    else:
                        m._size = low.value
            else:
                m._size = map_size
        else:
            m._size = map_size

        if tagname:
            m._tagname = tagname
        m._access = access
        
        # DWORD is a 4-byte int. If int > 4-byte it must be divided
        if _64BIT:
            size_hi = DWORD(m._size >> 32)
            size_lo = DWORD(m._size & 0xFFFFFFFF)
        else:
            size_hi = DWORD(0)
            size_lo = DWORD(m._size)

        m._map_handle = HANDLE(CreateFileMapping(m._file_handle, None, flProtect,
                                                 size_hi, size_lo, m._tagname))

        if m._map_handle:
            m._data = MapViewOfFile(m._map_handle, dwDesiredAccess,
                                    0, 0, 0)
            if m._data:
                m._data = cast(m._data, POINTER(c_char))
                return m
            else:
                dwErr = GetLastError()
        else:
            dwErr = GetLastError()

        raise OperationError(space.wrap(WinError), space.wrap(dwErr))
    mmap.unwrap_spec = [ObjSpace, int, int, str, int]
