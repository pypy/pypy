from pypy.rpython.rctypes.tool import ctypes_platform
import pypy.rpython.rctypes.implementation # this defines rctypes magic
from pypy.rpython.rctypes.aerrno import geterrno
from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import W_Root, ObjSpace, Wrappable
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.gateway import interp2app
from ctypes import *
import ctypes.util

from bzlib import bz_stream, BZFILE, FILE
from fileobject import PyFileObject

libbz2 = cdll.LoadLibrary(ctypes.util.find_library("bz2"))

c_void = None

class CConfig:
    _header_ = """
    #include <stdio.h>
    #include <sys/types.h>
    """
    off_t = ctypes_platform.SimpleType("off_t", c_longlong)
    size_t = ctypes_platform.SimpleType("size_t", c_ulong)
    BUFSIZ = ctypes_platform.ConstantInteger("BUFSIZ")

constants = {}
constant_names = ['BUFSIZ', 'BZ_RUN', 'BZ_FLUSH', 'BZ_FINISH', 'BZ_OK',
    'BZ_RUN_OK', 'BZ_FLUSH_OK', 'BZ_FINISH_OK', 'BZ_STREAM_END',
    'BZ_SEQUENCE_ERROR', 'BZ_PARAM_ERROR', 'BZ_MEM_ERROR', 'BZ_DATA_ERROR',
    'BZ_DATA_ERROR_MAGIC', 'BZ_IO_ERROR', 'BZ_UNEXPECTED_EOF',
    'BZ_OUTBUFF_FULL', 'BZ_CONFIG_ERROR']
for name in constant_names:
    setattr(CConfig, name, ctypes_platform.DefinedConstantInteger(name))
    
class cConfig:
    pass
cConfig.__dict__.update(ctypes_platform.configure(CConfig))

for name in constant_names:
    value = getattr(cConfig, name)
    if value is not None:
        constants[name] = value
locals().update(constants)

off_t = cConfig.off_t
BZ_OK = cConfig.BZ_OK
BZ_STREAM_END = cConfig.BZ_STREAM_END
BZ_CONFIG_ERROR = cConfig.BZ_CONFIG_ERROR
BZ_PARAM_ERROR = cConfig.BZ_PARAM_ERROR
BZ_DATA_ERROR = cConfig.BZ_DATA_ERROR
BZ_DATA_ERROR_MAGIC = cConfig.BZ_DATA_ERROR_MAGIC
BZ_IO_ERROR = cConfig.BZ_IO_ERROR
BZ_MEM_ERROR = cConfig.BZ_MEM_ERROR
BZ_UNEXPECTED_EOF = cConfig.BZ_UNEXPECTED_EOF
BZ_SEQUENCE_ERROR = cConfig.BZ_SEQUENCE_ERROR

# modes
MODE_CLOSED = 0
MODE_READ = 1
MODE_READ_EOF = 2
MODE_WRITE = 3

# bits in f_newlinetypes
NEWLINE_UNKNOWN	= 0	# No newline seen, yet
NEWLINE_CR = 1 # \r newline seen
NEWLINE_LF = 2 # \n newline seen
NEWLINE_CRLF = 4 # \r\n newline seen

pythonapi.PyFile_FromString.argtypes = [c_char_p, c_char_p]
pythonapi.PyFile_FromString.restype = POINTER(PyFileObject)
pythonapi.PyFile_SetBufSize.argtypes = [POINTER(PyFileObject), c_int]
pythonapi.PyFile_SetBufSize.restype = c_void
pythonapi.PyFile_AsFile.argtypes = [POINTER(PyFileObject)]
pythonapi.PyFile_AsFile.restype = POINTER(FILE)
libbz2.BZ2_bzReadOpen.argtypes = [POINTER(c_int), POINTER(FILE), c_int,
    c_int, c_void_p, c_int]
libbz2.BZ2_bzReadOpen.restype = POINTER(BZFILE)
libbz2.BZ2_bzWriteOpen.argtypes = [POINTER(c_int), POINTER(FILE), c_int,
    c_int, c_int]
libbz2.BZ2_bzWriteOpen.restype = POINTER(BZFILE)

def _catch_bz2_error(space, bzerror):
    if BZ_CONFIG_ERROR and bzerror == BZ_CONFIG_ERROR:
        raise OperationError(space.w_SystemError,
            space.wrap("the bz2 library was not compiled correctly"))
    if bzerror == BZ_PARAM_ERROR:
        raise OperationError(space.w_SystemError,
            space.wrap("the bz2 library has received wrong parameters"))
    elif bzerror == BZ_MEM_ERROR:
        raise OperationError(space.w_MemoryError, space.wrap(""))
    elif bzerror in (BZ_DATA_ERROR, BZ_DATA_ERROR_MAGIC):
        raise OperationError(space.w_IOError, space.wrap("invalid data stream"))
    elif bzerror == BZ_IO_ERROR:
        raise OperationError(space.w_IOError, space.wrap("unknown IO error"))
    elif bzerror == BZ_UNEXPECTED_EOF:
        raise OperationError(space.w_EOFError,
            space.wrap(
                "compressed file ended before the logical end-of-stream was detected"))
    elif bzerror == BZ_SEQUENCE_ERROR:
        raise OperationError(space.w_RuntimeError,
            space.wrap("wrong sequence of bz2 library commands used"))


class _BZ2File(Wrappable):
    def __init__(self, space, filename, mode='r', buffering=-1, compresslevel=9):
        self.space = space
        
        self.f_buf = c_char_p() # allocated readahead buffer
        self.f_bufend = c_char_p() # points after last occupied position
        self.f_bufptr = c_char_p() # current buffer position
        
        self.f_softspace = 0 # flag used by print command
        
        self.f_univ_newline = False # handle any newline convention
        self.f_newlinetypes = 0 # types of newlines seen
        self.f_skipnextlf = 0 # skip next \n
        
        self.mode = 0
        self.pos = 0
        self.size = 0
        
        self._init_bz2file(filename, mode, buffering, compresslevel)        
    
    def _init_bz2file(self, filename, mode_, buffering, compresslevel):
        self.size = -1
        
        name = filename
        mode_char = ""
        mode_list = mode_
        
        if compresslevel < 1 or compresslevel > 9:
            raise OperationError(self.space.w_ValueError,
                self.space.wrap("compresslevel must be between 1 and 9"))
        
        i = 1
        for mode in mode_list:
            error = False
            
            if mode in ['r', 'w']:
                if mode_char:
                    error = True
                mode_char = mode
            elif mode == 'b':
                pass
            elif mode == 'U':
                self.f_univ_newline = True
            else:
                error = True
            
            if error:
                raise OperationError(self.space.w_ValueError,
                    self.space.wrap("invalid mode char %s" % mode))
        
        if mode_char == 0:
            mode_char = 'r'
        mode = ('wb', 'rb')[mode_char == 'r']
        
        # open the file and set the buffer
        f = pythonapi.PyFile_FromString(name, mode)
        if not f:
            raise OperationError(self.space.w_IOError,
                self.space.wrap("cannot open file %s" % name))
        pythonapi.PyFile_SetBufSize(f, buffering)
        
        # store the FILE object
        self._file = pythonapi.PyFile_AsFile(f)
        
        bzerror = c_int()
        if mode_char == 'r':
            self.fp = libbz2.BZ2_bzReadOpen(byref(bzerror), self._file,
                0, 0, None, 0)
        else:
            self.fp = libbz2.BZ2_bzWriteOpen(byref(bzerror), self._file,
                compresslevel, 0, 0)
        
        if bzerror != BZ_OK:
            _catch_bz2_error(self.space, bzerror)
        
        self.mode = (MODE_WRITE, MODE_READ)[mode_char == 'r']
                  
_BZ2File.typedef = TypeDef("_BZ2File")

def BZ2File(space, filename, mode='r', buffering=-1, compresslevel=9):
    return _BZ2File(space, filename, mode, buffering, compresslevel)
BZ2File.unwrap_spec = [ObjSpace, str, str, int, int]

