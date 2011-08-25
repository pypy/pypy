
from pypy.rpython.tool import rffi_platform
from pypy.rpython.lltypesystem import rffi, lltype, llmemory
from pypy.rlib import rposix
from pypy.translator.tool.cbuild import ExternalCompilationInfo
from pypy.rlib.nonconst import NonConstant

import sys
import os
import platform
import stat

_POSIX = os.name == "posix"
_MS_WINDOWS = os.name == "nt"
_LINUX = "linux" in sys.platform
_64BIT = "64bit" in platform.architecture()[0]

class RValueError(Exception):
    def __init__(self, message):
        self.message = message

class RTypeError(Exception):
    def __init__(self, message):
        self.message = message

class ROverflowError(Exception):
    def __init__(self, message):
        self.message = message

includes = ["sys/types.h"]
if _POSIX:
    includes += ['unistd.h', 'sys/mman.h']
elif _MS_WINDOWS:
    includes += ['winsock2.h','windows.h']

class CConfig:
    _compilation_info_ = ExternalCompilationInfo(
        includes=includes,
        #pre_include_bits=['#ifndef _GNU_SOURCE\n' +
        #                  '#define _GNU_SOURCE\n' +
        #                  '#endif']
        # ^^^ _GNU_SOURCE is always defined by the ExternalCompilationInfo now
    )
    size_t = rffi_platform.SimpleType("size_t", rffi.LONG)
    off_t = rffi_platform.SimpleType("off_t", rffi.LONG)

constants = {}
if _POSIX:
    # constants, look in sys/mman.h and platform docs for the meaning
    # some constants are linux only so they will be correctly exposed outside 
    # depending on the OS
    constant_names = ['MAP_SHARED', 'MAP_PRIVATE',
                      'PROT_READ', 'PROT_WRITE',
                      'MS_SYNC']
    opt_constant_names = ['MAP_ANON', 'MAP_ANONYMOUS', 'MAP_NORESERVE',
                          'PROT_EXEC',
                          'MAP_DENYWRITE', 'MAP_EXECUTABLE']
    for name in constant_names:
        setattr(CConfig, name, rffi_platform.ConstantInteger(name))
    for name in opt_constant_names:
        setattr(CConfig, name, rffi_platform.DefinedConstantInteger(name))

    CConfig.MREMAP_MAYMOVE = (
        rffi_platform.DefinedConstantInteger("MREMAP_MAYMOVE"))
    CConfig.has_mremap = rffi_platform.Has('mremap(NULL, 0, 0, 0)')
    # a dirty hack, this is probably a macro

elif _MS_WINDOWS:
    constant_names = ['PAGE_READONLY', 'PAGE_READWRITE', 'PAGE_WRITECOPY',
                      'FILE_MAP_READ', 'FILE_MAP_WRITE', 'FILE_MAP_COPY',
                      'DUPLICATE_SAME_ACCESS', 'MEM_COMMIT', 'MEM_RESERVE',
                      'MEM_RELEASE', 'PAGE_EXECUTE_READWRITE', 'PAGE_NOACCESS']
    for name in constant_names:
        setattr(CConfig, name, rffi_platform.ConstantInteger(name))

    from pypy.rlib import rwin32

    from pypy.rlib.rwin32 import HANDLE, LPHANDLE
    from pypy.rlib.rwin32 import NULL_HANDLE, INVALID_HANDLE_VALUE
    from pypy.rlib.rwin32 import DWORD, WORD, DWORD_PTR, LPDWORD
    from pypy.rlib.rwin32 import BOOL, LPVOID, LPCVOID, LPCSTR, SIZE_T
    from pypy.rlib.rwin32 import INT, LONG, PLONG

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
    unsafe = rffi.llexternal(name, args, result,
                             compilation_info=CConfig._compilation_info_)
    safe = rffi.llexternal(name, args, result,
                           compilation_info=CConfig._compilation_info_,
                           sandboxsafe=True, threadsafe=False)
    return unsafe, safe

def winexternal(name, args, result, **kwargs):
    return rffi.llexternal(name, args, result,
                           compilation_info=CConfig._compilation_info_,
                           calling_conv='win',
                           **kwargs)

PTR = rffi.CCHARP

c_memmove, _ = external('memmove', [PTR, PTR, size_t], lltype.Void)

if _POSIX:
    has_mremap = cConfig['has_mremap']
    c_mmap, c_mmap_safe = external('mmap', [PTR, size_t, rffi.INT, rffi.INT,
                               rffi.INT, off_t], PTR)
    _, c_munmap_safe = external('munmap', [PTR, size_t], rffi.INT)
    c_msync, _ = external('msync', [PTR, size_t, rffi.INT], rffi.INT)
    if has_mremap:
        c_mremap, _ = external('mremap',
                               [PTR, size_t, size_t, rffi.ULONG], PTR)

    # this one is always safe
    _, _get_page_size = external('getpagesize', [], rffi.INT)
    _get_allocation_granularity = _get_page_size

elif _MS_WINDOWS:

    class ComplexCConfig:
        _compilation_info_ = CConfig._compilation_info_

        SYSINFO_STRUCT = rffi.CStruct(
            'SYSINFO_STRUCT',
                ("wProcessorArchitecture", WORD),
                ("wReserved", WORD),
            )

        SYSINFO_UNION = rffi.CStruct(
            'union SYSINFO_UNION', 
                ("dwOemId", DWORD),
                ("_struct_", SYSINFO_STRUCT),
            )
        # sorry, I can't find a way to insert the above
        # because the union field has no name
        SYSTEM_INFO = rffi_platform.Struct(
            'SYSTEM_INFO', [
                ## ("_union_", SYSINFO_UNION),
                ## instead, we put the smaller fields, here
                ("wProcessorArchitecture", WORD),
                ("wReserved", WORD),
                ## should be a union. dwOemId is obsolete, anyway
                ("dwPageSize", DWORD),
                ("lpMinimumApplicationAddress", LPVOID),
                ("lpMaximumApplicationAddress", LPVOID),
                ("dwActiveProcessorMask", DWORD_PTR),
                ("dwNumberOfProcessors", DWORD),
                ("dwProcessorType", DWORD),
                ("dwAllocationGranularity", DWORD),
                ("wProcessorLevel", WORD),
                ("wProcessorRevision", WORD),
            ])

    config = rffi_platform.configure(ComplexCConfig)
    SYSTEM_INFO = config['SYSTEM_INFO']
    SYSTEM_INFO_P = lltype.Ptr(SYSTEM_INFO)

    GetSystemInfo = winexternal('GetSystemInfo', [SYSTEM_INFO_P], lltype.Void)
    GetFileSize = winexternal('GetFileSize', [HANDLE, LPDWORD], DWORD)
    GetCurrentProcess = winexternal('GetCurrentProcess', [], HANDLE)
    DuplicateHandle = winexternal('DuplicateHandle', [HANDLE, HANDLE, HANDLE, LPHANDLE, DWORD, BOOL, DWORD], BOOL)
    CreateFileMapping = winexternal('CreateFileMappingA', [HANDLE, rwin32.LPSECURITY_ATTRIBUTES, DWORD, DWORD, DWORD, LPCSTR], HANDLE)
    MapViewOfFile = winexternal('MapViewOfFile', [HANDLE, DWORD, DWORD, DWORD, SIZE_T], LPCSTR)##!!LPVOID)
    UnmapViewOfFile = winexternal('UnmapViewOfFile', [LPCVOID], BOOL,
                                  threadsafe=False)
    FlushViewOfFile = winexternal('FlushViewOfFile', [LPCVOID, SIZE_T], BOOL)
    SetFilePointer = winexternal('SetFilePointer', [HANDLE, LONG, PLONG, DWORD], DWORD)
    SetEndOfFile = winexternal('SetEndOfFile', [HANDLE], BOOL)
    VirtualAlloc = winexternal('VirtualAlloc',
                               [rffi.VOIDP, rffi.SIZE_T, DWORD, DWORD],
                               rffi.VOIDP)
    # VirtualProtect is used in llarena and should not release the GIL
    _VirtualProtect = winexternal('VirtualProtect',
                                  [rffi.VOIDP, rffi.SIZE_T, DWORD, LPDWORD],
                                  BOOL,
                                  _nowrapper=True)
    def VirtualProtect(addr, size, mode, oldmode_ptr):
        return _VirtualProtect(addr,
                               rffi.cast(rffi.SIZE_T, size),
                               rffi.cast(DWORD, mode),
                               oldmode_ptr)
    VirtualProtect._annspecialcase_ = 'specialize:ll'
    VirtualFree = winexternal('VirtualFree',
                              [rffi.VOIDP, rffi.SIZE_T, DWORD], BOOL)


    def _get_page_size():
        try:
            si = rffi.make(SYSTEM_INFO)
            GetSystemInfo(si)
            return int(si.c_dwPageSize)
        finally:
            lltype.free(si, flavor="raw")

    def _get_allocation_granularity():
        try:
            si = rffi.make(SYSTEM_INFO)
            GetSystemInfo(si)
            return int(si.c_dwAllocationGranularity)
        finally:
            lltype.free(si, flavor="raw")

    def _get_file_size(handle):
        # XXX use native Windows types like WORD
        high_ref = lltype.malloc(LPDWORD.TO, 1, flavor='raw')
        try:
            low = GetFileSize(handle, high_ref)
            low = rffi.cast(lltype.Signed, low)
            # XXX should be propagate the real type, allowing
            # for 2*sys.maxint?
            high = high_ref[0]
            # low might just happen to have the value INVALID_FILE_SIZE
            # so we need to check the last error also
            INVALID_FILE_SIZE = -1
            if low == INVALID_FILE_SIZE:
                err = rwin32.GetLastError()
                if err:
                    raise WindowsError(err, "mmap")
            return low, high
        finally:
            lltype.free(high_ref, flavor='raw')

    INVALID_HANDLE = INVALID_HANDLE_VALUE

PAGESIZE = _get_page_size()
ALLOCATIONGRANULARITY = _get_allocation_granularity()
NULL = lltype.nullptr(PTR.TO)
NODATA = lltype.nullptr(PTR.TO)

class MMap(object):
    def __init__(self, access, offset):
        self.size = 0
        self.pos = 0
        self.access = access
        self.offset = offset

        if _MS_WINDOWS:
            self.map_handle = NULL_HANDLE
            self.file_handle = NULL_HANDLE
            self.tagname = ""
        elif _POSIX:
            self.fd = -1
            self.closed = False
    
    def check_valid(self):
        if _MS_WINDOWS:
            to_close = self.map_handle == INVALID_HANDLE
        elif _POSIX:
            to_close = self.closed

        if to_close:
            raise RValueError("map closed or invalid")
    
    def check_writeable(self):
        if not (self.access != ACCESS_READ):
            raise RTypeError("mmap can't modify a readonly memory map.")
    
    def check_resizeable(self):
        if not (self.access == ACCESS_WRITE or self.access == _ACCESS_DEFAULT):
            raise RTypeError("mmap can't resize a readonly or copy-on-write memory map.")

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
            if self.map_handle != INVALID_HANDLE:
                rwin32.CloseHandle(self.map_handle)
                self.map_handle = INVALID_HANDLE
            if self.file_handle != INVALID_HANDLE:
                rwin32.CloseHandle(self.file_handle)
                self.file_handle = INVALID_HANDLE
        elif _POSIX:
            self.closed = True
            if self.fd != -1:
                os.close(self.fd)
                self.fd = -1
            if self.size > 0:
                c_munmap_safe(self.getptr(0), self.size)
                self.setdata(NODATA, 0)

    def __del__(self):
        self.close()

    def unmapview(self):
        UnmapViewOfFile(self.getptr(0))
    
    def read_byte(self):
        self.check_valid()

        if self.pos < self.size:
            value = self.data[self.pos]
            self.pos += 1
            return value
        else:
            raise RValueError("read byte out of range")
    
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
        return res
    
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
        return res

    def find(self, tofind, start, end, reverse=False):
        self.check_valid()

        # XXX naive! how can we reuse the rstr algorithm?
        if start < 0:
            start += self.size
            if start < 0:
                start = 0
        if end < 0:
            end += self.size
            if end < 0:
                end = 0
        elif end > self.size:
            end = self.size
        #
        upto = end - len(tofind)
        if not reverse:
            step = 1
            p = start
            if p > upto:
                return -1      # failure (empty range to search)
        else:
            step = -1
            p = upto
            upto = start
            if p < upto:
                return -1      # failure (empty range to search)
        #
        data = self.data
        while True:
            assert p >= 0
            for q in range(len(tofind)):
                if data[p+q] != tofind[q]:
                    break     # position 'p' is not a match
            else:
                # full match
                return p
            #
            if p == upto:
                return -1   # failure
            p += step

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
            raise RValueError("unknown seek type")

        if not (0 <= where <= self.size):
            raise RValueError("seek out of range")
        
        self.pos = where
    
    def tell(self):
        self.check_valid()
        return self.pos
    
    def file_size(self):
        self.check_valid()
        
        size = self.size
        if _MS_WINDOWS:
            if self.file_handle != INVALID_HANDLE:
                low, high = _get_file_size(self.file_handle)
                if not high and low <= sys.maxint:
                    return low
                size = (high << 32) + low
        elif _POSIX:
            st = os.fstat(self.fd)
            size = st[stat.ST_SIZE]
            if size > sys.maxint:
                size = sys.maxint
            else:
                size = int(size)
        return size
    
    def write(self, data):
        self.check_valid()        
        self.check_writeable()
        
        data_len = len(data)
        if self.pos + data_len > self.size:
            raise RValueError("data out of range")

        internaldata = self.data
        start = self.pos
        for i in range(data_len):
            internaldata[start+i] = data[i]
        self.pos = start + data_len
    
    def write_byte(self, byte):
        self.check_valid()
        
        if len(byte) != 1:
            raise RTypeError("write_byte() argument must be char")

        self.check_writeable()
        if self.pos >= self.size:
            raise RValueError("write byte out of range")

        self.data[self.pos] = byte[0]
        self.pos += 1

    def getptr(self, offset):
        return rffi.ptradd(self.data, offset)

    def flush(self, offset=0, size=0):
        self.check_valid()

        if size == 0:
            size = self.size
        if offset < 0 or size < 0 or offset + size > self.size:
            raise RValueError("flush values out of range")
        else:
            start = self.getptr(offset)
            if _MS_WINDOWS:
                res = FlushViewOfFile(start, size)
                # XXX res == 0 means that an error occurred, but in CPython
                # this is not checked
                return res
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
                    errno = rposix.get_errno()
                    raise OSError(errno, os.strerror(errno))
        
        return 0
    
    def move(self, dest, src, count):
        self.check_valid()
        
        self.check_writeable()
        
        # check boundings
        if (src < 0 or dest < 0 or count < 0 or
            src + count > self.size or dest + count > self.size):
            raise RValueError("source or destination out of range")

        datasrc = self.getptr(src)
        datadest = self.getptr(dest)
        c_memmove(datadest, datasrc, count)
    
    def resize(self, newsize):
        self.check_valid()
        
        self.check_resizeable()
        
        if _POSIX:
            if not has_mremap:
                raise RValueError("mmap: resizing not available--no mremap()")
            
            # resize the underlying file first
            os.ftruncate(self.fd, self.offset + newsize)
                
            # now resize the mmap
            newdata = c_mremap(self.getptr(0), self.size, newsize,
                               MREMAP_MAYMOVE or 0)
            self.setdata(newdata, newsize)
        elif _MS_WINDOWS:
            # disconnect the mapping
            self.unmapview()
            rwin32.CloseHandle(self.map_handle)

            # move to the desired EOF position
            if _64BIT:
                newsize_high = (self.offset + newsize) >> 32
                newsize_low = (self.offset + newsize) & 0xFFFFFFFF
                offset_high = self.offset >> 32
                offset_low = self.offset & 0xFFFFFFFF
            else:
                newsize_high = 0
                newsize_low = self.offset + newsize
                offset_high = 0
                offset_low = self.offset

            FILE_BEGIN = 0
            high_ref = lltype.malloc(PLONG.TO, 1, flavor='raw')
            try:
                high_ref[0] = newsize_high
                SetFilePointer(self.file_handle, newsize_low, high_ref,
                               FILE_BEGIN)
            finally:
                lltype.free(high_ref, flavor='raw')
            # resize the file
            SetEndOfFile(self.file_handle)
            # create another mapping object and remap the file view
            res = CreateFileMapping(self.file_handle, NULL, PAGE_READWRITE,
                                 newsize_high, newsize_low, self.tagname)
            self.map_handle = res

            dwErrCode = 0
            if self.map_handle:
                data = MapViewOfFile(self.map_handle, FILE_MAP_WRITE,
                                     offset_high, offset_low, newsize)
                if data:
                    # XXX we should have a real LPVOID which must always be casted
                    charp = rffi.cast(LPCSTR, data)
                    self.setdata(charp, newsize)
                    return
            winerror = rwin32.lastWindowsError()
            if self.map_handle:
                rwin32.CloseHandle(self.map_handle)
            self.map_handle = INVALID_HANDLE
            raise winerror

    def len(self):
        self.check_valid()
        
        return self.size
    
    def getitem(self, index):
        self.check_valid()
        # simplified version, for rpython
        if index < 0:
            index += self.size
        return self.data[index]

    def setitem(self, index, value):
        self.check_valid()
        self.check_writeable()

        if len(value) != 1:
            raise RValueError("mmap assignment must be "
                             "single-character string")
        if index < 0:
            index += self.size
        self.data[index] = value[0]

def _check_map_size(size):
    if size < 0:
        raise RTypeError("memory mapped size must be positive")
    if rffi.cast(size_t, size) != size:
        raise ROverflowError("memory mapped size is too large (limited by C int)")

if _POSIX:
    def mmap(fileno, length, flags=MAP_SHARED,
        prot=PROT_WRITE | PROT_READ, access=_ACCESS_DEFAULT, offset=0):

        fd = fileno

        # check access is not there when flags and prot are there
        if access != _ACCESS_DEFAULT and ((flags != MAP_SHARED) or\
                                          (prot != (PROT_WRITE | PROT_READ))):
            raise RValueError("mmap can't specify both access and flags, prot.")

        # check size boundaries
        _check_map_size(length)
        map_size = length
        if offset < 0:
            raise RValueError("negative offset")

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
            raise RValueError("mmap invalid access parameter.")

        if prot == PROT_READ:
            access = ACCESS_READ

        # check file size
        try:
            st = os.fstat(fd)
        except OSError:
            pass     # ignore errors and trust map_size
        else:
            mode = st[stat.ST_MODE]
            size = st[stat.ST_SIZE]
            size -= offset
            if size > sys.maxint:
                size = sys.maxint
            else:
                size = int(size)
            if stat.S_ISREG(mode):
                if map_size == 0:
                    map_size = size
                elif map_size > size:
                    raise RValueError("mmap length is greater than file size")

        m = MMap(access, offset)
        if fd == -1:
            # Assume the caller wants to map anonymous memory.
            # This is the same behaviour as Windows.  mmap.mmap(-1, size)
            # on both Windows and Unix map anonymous memory.
            m.fd = -1

            flags |= MAP_ANONYMOUS

        else:
            m.fd = os.dup(fd)

        # XXX if we use hintp below in alloc, the NonConstant
        #     is necessary since we want a general version of c_mmap
        #     to be annotated with a non-constant pointer.
        res = c_mmap(NonConstant(NULL), map_size, prot, flags, fd, offset)
        if res == rffi.cast(PTR, -1):
            errno = rposix.get_errno()
            raise OSError(errno, os.strerror(errno))
        
        m.setdata(res, map_size)
        return m

    # XXX is this really necessary?
    class Hint:
        pos = -0x4fff0000   # for reproducible results
    hint = Hint()

    def alloc(map_size):
        """Allocate memory.  This is intended to be used by the JIT,
        so the memory has the executable bit set and gets allocated
        internally in case of a sandboxed process.
        """
        flags = MAP_PRIVATE | MAP_ANONYMOUS
        prot = PROT_EXEC | PROT_READ | PROT_WRITE
        hintp = rffi.cast(PTR, hint.pos)
        res = c_mmap_safe(hintp, map_size, prot, flags, -1, 0)
        if res == rffi.cast(PTR, -1):
            # some systems (some versions of OS/X?) complain if they
            # are passed a non-zero address.  Try again.
            hintp = rffi.cast(PTR, 0)
            res = c_mmap_safe(hintp, map_size, prot, flags, -1, 0)
            if res == rffi.cast(PTR, -1):
                raise MemoryError
        else:
            hint.pos += map_size
        return res
    alloc._annenforceargs_ = (int,)

    free = c_munmap_safe
    
elif _MS_WINDOWS:
    def mmap(fileno, length, tagname="", access=_ACCESS_DEFAULT, offset=0):
        # check size boundaries
        _check_map_size(length)
        map_size = length
        if offset < 0:
            raise RValueError("negative offset")
        
        flProtect = 0
        dwDesiredAccess = 0
        fh = NULL_HANDLE
        
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
            raise RValueError("mmap invalid access parameter.")
        
        # assume -1 and 0 both mean invalid file descriptor
        # to 'anonymously' map memory.
        if fileno != -1 and fileno != 0:
            fh = rwin32._get_osfhandle(fileno)
            if fh == INVALID_HANDLE:
                errno = rposix.get_errno()
                raise OSError(errno, os.strerror(errno))
            # Win9x appears to need us seeked to zero
            # SEEK_SET = 0
            # libc._lseek(fileno, 0, SEEK_SET)
        
        m = MMap(access, offset)
        m.file_handle = INVALID_HANDLE
        m.map_handle = INVALID_HANDLE
        if fh:
            # it is necessary to duplicate the handle, so the
            # Python code can close it on us
            handle_ref = lltype.malloc(LPHANDLE.TO, 1, flavor='raw')
            handle_ref[0] = m.file_handle
            try:
                res = DuplicateHandle(GetCurrentProcess(), # source process handle
                                      fh, # handle to be duplicated
                                      GetCurrentProcess(), # target process handle
                                      handle_ref, # result  
                                      0, # access - ignored due to options value
                                      False, # inherited by child procs?
                                      DUPLICATE_SAME_ACCESS) # options
                if not res:
                    raise rwin32.lastWindowsError()
                m.file_handle = handle_ref[0]
            finally:
                lltype.free(handle_ref, flavor='raw')
            
            if not map_size:
                low, high = _get_file_size(fh)
                if _64BIT:
                    map_size = (low << 32) + 1
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
            size_hi = (map_size + offset) >> 32
            size_lo = (map_size + offset) & 0xFFFFFFFF
            offset_hi = offset >> 32
            offset_lo = offset & 0xFFFFFFFF
        else:
            size_hi = 0
            size_lo = map_size + offset
            offset_hi = 0
            offset_lo = offset

        m.map_handle = CreateFileMapping(m.file_handle, NULL, flProtect,
                                         size_hi, size_lo, m.tagname)

        if m.map_handle:
            data = MapViewOfFile(m.map_handle, dwDesiredAccess,
                                 offset_hi, offset_lo, length)
            if data:
                # XXX we should have a real LPVOID which must always be casted
                charp = rffi.cast(LPCSTR, data)
                m.setdata(charp, map_size)
                return m
        winerror = rwin32.lastWindowsError()
        if m.map_handle:
            rwin32.CloseHandle(m.map_handle)
        m.map_handle = INVALID_HANDLE
        raise winerror

    def alloc(map_size):
        """Allocate memory.  This is intended to be used by the JIT,
        so the memory has the executable bit set.  
        XXX implement me: it should get allocated internally in
        case of a sandboxed process
        """
        null = lltype.nullptr(rffi.VOIDP.TO)
        res = VirtualAlloc(null, map_size, MEM_COMMIT|MEM_RESERVE,
                           PAGE_EXECUTE_READWRITE)
        if not res:
            raise MemoryError
        arg = lltype.malloc(LPDWORD.TO, 1, zero=True, flavor='raw')
        VirtualProtect(res, map_size, PAGE_EXECUTE_READWRITE, arg)
        lltype.free(arg, flavor='raw')
        # ignore errors, just try
        return res
    alloc._annenforceargs_ = (int,)

    def free(ptr, map_size):
        VirtualFree(ptr, 0, MEM_RELEASE)
        
# register_external here?
