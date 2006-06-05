from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.rpython.rctypes.tool import ctypes_platform
from pypy.rpython.rctypes.tool.util import find_library, load_library 

import sys
from ctypes import *

cryptfn = find_library("crypt")
cryptdll = load_library(cryptfn)

c_crypt = cryptdll.crypt 
c_crypt.argtypes = [c_char_p, c_char_p]
c_crypt.restype = c_char_p 

def crypt(space, word, salt):
    """word will usually be a user's password. salt is a 2-character string
    which will be used to select one of 4096 variations of DES. The characters
    in salt must be either ".", "/", or an alphanumeric character. Returns
    the hashed password as a string, which will be composed of characters from
    the same alphabet as the salt."""
    res = c_crypt(word, salt)
    return space.wrap(res) 

crypt.unwrap_spec = [ObjSpace, str, str]
