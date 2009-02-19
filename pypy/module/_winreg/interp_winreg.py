from pypy.interpreter.baseobjspace import Wrappable
from pypy.interpreter.baseobjspace import ObjSpace, W_Root
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.error import OperationError
from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rlib import rwinreg, rwin32

class W_HKEY(Wrappable):
    def __init__(self, hkey):
        self.hkey = hkey

    def __nonzero__(self):
        return self.hkey != 0

    def descr_repr(self, space):
        return space.wrap("<PyHKEY:%d>" % (self.hkey,))
    descr_repr.unwrap_spec = ['self', ObjSpace]

def new_HKEY(space, w_subtype, hkey):
    return space.wrap(W_HKEY(hkey))
descr_HKEY_new = interp2app(new_HKEY,
                            unwrap_spec=[ObjSpace, W_Root, int])

W_HKEY.typedef = TypeDef(
    "_winreg.HKEYType",
    __new__ = descr_HKEY_new,
    __repr__ = interp2app(W_HKEY.descr_repr),
    )

def hkey_w(w_key, space):
    if space.is_w(w_key, space.w_None):
        errstring = space.wrap("None is not a valid HKEY in this context")
        raise OperationError(space.w_TypeError, errstring)
    elif isinstance(w_key, W_HKEY):
        return w_key.hkey
    elif space.is_true(space.isinstance(w_key, space.w_int)):
        return space.int_w(w_key)
    elif space.is_true(space.isinstance(w_key, space.w_long)):
        return space.uint_w(w_key)
    else:
        errstring = space.wrap("The object is not a PyHKEY object")
        raise OperationError(space.w_TypeError, errstring)

def SetValue(space, w_key, w_subkey, typ, value):
    if typ != rwinreg.REG_SZ:
        errstring = space.wrap("Type must be _winreg.REG_SZ")
        raise OperationError(space.w_ValueError, errstring)
    key = hkey_w(w_key, space)
    if space.is_w(w_subkey, space.w_None):
        subkey = None
    else:
        subkey = space.str_w(w_subkey)
    dataptr = rffi.str2charp(value)
    try:
        ret = rwinreg.RegSetValue(key, subkey, rwinreg.REG_SZ, dataptr, len(value))
    finally:
        rffi.free_charp(dataptr)
    if ret != 0:
        rwin32.raiseWindowError(ret, 'RegSetValue')
SetValue.unwrap_spec = [ObjSpace, W_Root, W_Root, int, str]

def QueryValue(space, w_key, w_subkey):
    key = hkey_w(w_key, space)
    if space.is_w(w_subkey, space.w_None):
        subkey = None
    else:
        subkey = space.str_w(w_subkey)
    bufsize_p = lltype.malloc(rwin32.PLONG.TO, 1, flavor='raw')
    try:
        ret = rwinreg.RegQueryValue(key, subkey, None, bufsize_p)
        if ret != 0:
            rwin32.raiseWindowError(ret, 'RegQueryValue')
        buf = lltype.malloc(rffi.CCHARP.TO, bufsize_p[0], flavor='raw')
        try:
            ret = rwinreg.RegQueryValue(key, subkey, buf, bufsize_p)
            if ret != 0:
                rwin32.raiseWindowError(ret, 'RegQueryValue')
            return space.wrap(rffi.charp2strn(buf, bufsize_p[0] - 1))
        finally:
            lltype.free(buf, flavor='raw')
    finally:
        lltype.free(bufsize_p, flavor='raw')
    if ret != 0:
        rwin32.raiseWindowError(ret, 'RegQueryValue')
SetValue.unwrap_spec = [ObjSpace, W_Root, W_Root, int, str]
