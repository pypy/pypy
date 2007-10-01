from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.rpython.rctypes.tool import ctypes_platform
from pypy.rpython.tool import rffi_platform as platform
from pypy.rpython.rctypes.tool.util import find_library
from pypy.rpython.lltypesystem import rffi, lltype

import sys

#if sys.platform == 'darwin':
#    dllname = find_library('c')
#    assert dllname is not None
#    cryptlib = cdll.LoadLibrary(dllname)

c_crypt = rffi.llexternal('crypt', [rffi.CCHARP, rffi.CCHARP], rffi.CCHARP,
                          libraries=["crypt"], threadsafe=False)

def crypt(space, word, salt):
    """word will usually be a user's password. salt is a 2-character string
    which will be used to select one of 4096 variations of DES. The characters
    in salt must be either ".", "/", or an alphanumeric character. Returns
    the hashed password as a string, which will be composed of characters from
    the same alphabet as the salt."""
    res = c_crypt(word, salt)
    if not res:
        return space.w_None
    str_res = rffi.charp2str(res)
    return space.wrap(str_res) 

crypt.unwrap_spec = [ObjSpace, str, str]
